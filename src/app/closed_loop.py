
import argparse, time, sys, os, json
import numpy as np

from ..streaming.lsl_client import EEGSource
from ..processing.eeg_pipeline import EEGPipeline
from ..processing.burst_detector import BetaBurstDetector
from ..policy.bandpower_controller import BandpowerPIDController
from ..policy.burst_threshold_policy import BurstThresholdPolicy
from ..policy.ml_policy import MLPolicy
from ..hardware.stimulator_api import MockStimulator
from ..safety.safety_manager import SafetyManager

def load_config(path):
    import yaml
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', default='configs/config.yaml')
    p.add_argument('--mode', choices=['simulation','lsl'], default=None)
    p.add_argument('--seconds', type=int, default=None)
    args = p.parse_args()

    cfg = load_config(args.config)
    if args.mode is not None:
        cfg['mode'] = args.mode
    if args.seconds is not None:
        cfg['seconds'] = args.seconds

    # Logging
    def log(msg): print(msg)

    # EEG
    eeg_cfg = cfg['eeg']
    src = EEGSource(mode=cfg['mode'], fs=eeg_cfg['fs'], n_channels=eeg_cfg['n_channels'],
                    chunk_sec=eeg_cfg['chunk_sec'], log_fn=log)
    pipe = EEGPipeline(fs=eeg_cfg['fs'], bands=eeg_cfg['bands'], detrend=eeg_cfg['detrend'],
                       chunk_sec=eeg_cfg['chunk_sec'], smoothing=cfg['biomarker']['smoothing'])

    # Controller
    if cfg['controller']['kind'] == 'bandpower_pid':
        ctrl = BandpowerPIDController(kp=cfg['controller']['kp'],
                                      ki=cfg['controller']['ki'],
                                      kd=cfg['controller']['kd'],
                                      max_step_mA=cfg['controller']['max_step_mA'])
        ml = None
    elif cfg['controller']['kind'] == 'burst_threshold':
        ctrl = BurstThresholdPolicy(
            step_up_mA=cfg['controller'].get('step_up_mA', 0.10),
            step_down_mA=cfg['controller'].get('step_down_mA', 0.05),
            cooldown_sec=cfg['controller'].get('cooldown_sec', 60),
            quiet_sec=cfg['controller'].get('quiet_sec', 120),
            log_fn=log
        )
        ml = None
    else:
        weights_path = cfg['controller'].get('weights_path', 'models/ml_policy_weights.npz')
        try:
            ml = MLPolicy(weights_path)
        except Exception as e:
            log(f"[WARN] MLPolicy unavailable: {e}. Falling back to PID.")
            ctrl = BandpowerPIDController(kp=cfg['controller']['kp'],
                                          ki=cfg['controller']['ki'],
                                          kd=cfg['controller']['kd'],
                                          max_step_mA=cfg['controller']['max_step_mA'])
            ml = None

    # Stimulator (mock by default)
    stim = MockStimulator(log_fn=log)
    stim.connect()
    stim.set_polarity(cfg['stimulator']['polarity'])
    stim.start()
    stim.current_mA = cfg['stimulator']['initial_mA']

    # Burst detector
    bd_cfg = cfg.get('burst_detector', {'ema_alpha':0.05,'z_thresh':2.0,'hysteresis':0.5,'min_duration_sec':2.0})
    burst = BetaBurstDetector(
        ema_alpha=bd_cfg.get('ema_alpha', 0.05),
        z_thresh=bd_cfg.get('z_thresh', 2.0),
        hysteresis=bd_cfg.get('hysteresis', 0.5),
        min_duration_sec=bd_cfg.get('min_duration_sec', 2.0)
    )

    # Safety
    s = cfg['safety']
    safety = SafetyManager(max_mA=s['max_mA'], min_mA=s['min_mA'],
                           ramp_rate_mA_per_min=s['ramp_rate_mA_per_min'],
                           min_seconds_between_changes=s['min_seconds_between_changes'],
                           max_session_minutes=s['max_session_minutes'],
                           require_human_confirm=s['require_human_confirm'],
                           emergency_stop_key=s['emergency_stop_key'],
                           log_fn=log)

    # Loop
    target_beta = cfg['biomarker']['target_beta_uV2']
    end_ts = time.time() + max(1, int(cfg['seconds']))
    changes = 0

    log(f"[START] mode={cfg['mode']} session={cfg['seconds']}s target_beta={target_beta}")
    try:
        while time.time() < end_ts:
            if not safety.within_session_limits():
                break
            chunk = src.next_chunk()  # [channels, samples]
            feats = pipe.features(chunk)
            beta = feats['beta_power_smooth']
            alpha = feats.get('alpha_power', 0.0)
            ratio = beta / max(1e-6, alpha)
            log(f"[EEG] beta={feats['beta_power']:.3f} beta_s={beta:.3f} alpha={alpha:.3f} ratio={ratio:.3f}")

            # Update burst detector
            b_evt = burst.update(beta)
            if b_evt['just_started']:
                log(f"[BURST] started (z={b_evt['z_score']:.2f}, baseline={b_evt['baseline']:.3f})")
            elif b_evt['just_ended']:
                log(f"[BURST] ended (z={b_evt['z_score']:.2f})")

            if safety.can_change_now():
                if isinstance(ctrl, BurstThresholdPolicy):
                    delta = ctrl.propose_delta(b_evt)
                    proposed_abs = stim.current_mA + delta
                    target_mA = safety.clamp_target(proposed_abs, stim.current_mA)
                elif ml is not None:
                    features_vec = [beta, alpha, ratio]
                    proposed_abs = ml.predict_mA(features_vec)
                    target_mA = safety.clamp_target(proposed_abs, stim.current_mA)
                else:
                    delta = ctrl.propose_delta(beta, target_beta)
                    proposed_abs = stim.current_mA + delta
                    target_mA = safety.clamp_target(proposed_abs, stim.current_mA)

                log(f"[CTRL] proposed={proposed_abs:.3f} mA -> clamped target={target_mA:.3f} mA (now={stim.current_mA:.3f})")
                if safety.maybe_confirm(target_mA):
                    # Ramp time derived from allowed ramp rate and delta
                    delta = abs(target_mA - stim.current_mA)
                    # Convert ramp_rate mA/min into a seconds ramp; ensure >= 2s
                    seconds = max(2.0, 60.0 * (delta / max(1e-6, safety.ramp_rate)))
                    stim.ramp_to(target_mA, seconds=seconds)
                    safety.mark_changed()
                    changes += 1
                else:
                    log("[CTRL] Change not confirmed or confirmation timed out.")
    except KeyboardInterrupt:
        log("[STOP] Interrupted by user.")
    finally:
        stim.stop()
        stim.disconnect()
        log(f"[END] Applied changes: {changes}")

if __name__ == '__main__':
    main()
