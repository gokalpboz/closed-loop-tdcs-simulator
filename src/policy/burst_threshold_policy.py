
import time

class BurstThresholdPolicy:
    """Threshold/State-based controller driven by beta-burst detection.
    - On burst start: propose a small upward step (+step_up_mA) once per cooldown.
    - In prolonged quiet: after quiet_sec with no active burst, propose a small downward step (-step_down_mA).
    SafetyManager will clamp/ramp and enforce change intervals.
    """
    def __init__(self, step_up_mA=0.10, step_down_mA=0.05, cooldown_sec=60, quiet_sec=120, log_fn=print):
        self.step_up = float(step_up_mA)
        self.step_down = float(step_down_mA)
        self.cooldown = int(cooldown_sec)
        self.quiet_sec = int(quiet_sec)
        self._last_up_ts = 0.0
        self._last_any_burst_ts = 0.0
        self.log = log_fn

    def propose_delta(self, burst_event, now=None):
        now = time.time() if now is None else float(now)
        delta = 0.0

        if burst_event['just_started']:
            self._last_any_burst_ts = now
            if (now - self._last_up_ts) >= self.cooldown:
                delta = +self.step_up
                self._last_up_ts = now
                self.log(f"[POLICY] Burst start -> +{self.step_up:.3f} mA (cooldown ok)")
            else:
                self.log("[POLICY] Burst start within cooldown -> no change")
        elif burst_event['active']:
            self._last_any_burst_ts = now  # update last active time each tick
        else:
            # No active burst. If it's been quiet for a while, nudge down.
            quiet_for = now - self._last_any_burst_ts
            if quiet_for >= self.quiet_sec:
                delta = -self.step_down
                self._last_any_burst_ts = now  # avoid repeated downs each second
                self.log(f"[POLICY] Quiet for {quiet_for:.0f}s -> -{self.step_down:.3f} mA")

        return float(delta)
