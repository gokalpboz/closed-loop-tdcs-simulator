
# closed-loop-tdcs (Research-Only)

**⚠️ Safety first: This repository is for simulation and benchtop/hardware-in-the-loop (HIL) testing _only_. It is *not* a medical device and must not be used on humans.**  
**Do not connect this code to any device delivering current to a human subject without full ethics/regulatory approval, medical supervision, and certified medical hardware with all safety interlocks.**

This project provides a modular, *GitHub-ready* scaffold for an **AI-assisted closed-loop neuromodulation** pipeline that *listens* to EEG, extracts biomarkers (e.g., beta-band power), and computes **recommended** tDCS/tsDCS parameter adjustments under strict software safety guards. By default, it runs in **simulation mode** with a mock stimulator and synthetic EEG.

> Motivation: Translate the adaptive closed-loop principle—well explored in invasive DBS—to **non-invasive** neuromodulation (tDCS/tsDCS) by integrating real‑time sensing (EEG/wearables) and AI-driven policies to personalize stimulation. See the attached project description for context and goals. 

## Key capabilities
- Real-time (or simulated) EEG stream interface (`src/streaming`).
- Online signal processing with conservative, transparent feature extraction (`src/processing`).
- Pluggable control policies (rule-based, PID-like, or ML policy stubs) (`src/policy`).
- **SafetyManager** enforcing hard bounds, ramp-rate limits, and session dose constraints (`src/safety`).
- Abstract **StimulatorAPI** with a **MockStimulator** for HIL/simulation (`src/hardware`). No real hardware control is shipped.
- A single entry-point app to orchestrate the closed loop (`src/app/closed_loop.py`).

## Absolutely critical safety notes
- Parameters here are placeholders for **simulation**. They are **not** clinical recommendations.  
- Any human-facing implementation requires: medical-grade stimulator APIs, double‑redundant hardware interlocks, impedance monitoring, per‑site current density calculation, IRB/ethics & regulatory approvals, clinician sign‑off, and emergency stop procedures.
- The default loop demands **human confirmation** before applying a change. Keep it that way during prototyping.

## Quick start (simulation)
```bash
python -m src.app.closed_loop --mode simulation --seconds 30
```
This will spin up a synthetic EEG generator with variable beta bursts and a mock stimulator. The controller tries to keep the beta-band marker near a configurable target while obeying safety gates.

## Project layout
```
src/
  app/closed_loop.py            # Orchestrator (main loop)
  streaming/lsl_client.py       # LSL client (optional) + EEG simulator
  processing/eeg_pipeline.py    # Bandpower features (NumPy)
  policy/bandpower_controller.py# Simple safe controller
  policy/ml_policy.py           # Optional ML policy stub (pure NumPy inference)
  hardware/stimulator_api.py    # Abstract API + Mock stim
  safety/safety_manager.py      # Hard limits, ramp, and dose checks
  utils/signal.py               # Spectral helpers (Welch/FFT)
configs/config.yaml             # All tunables in one place
```

## Configuration
See `configs/config.yaml` for:
- EEG sampling rate, window sizes
- Feature bands (beta, alpha, etc.)
- Target biomarker level and control gains
- Safety bounds (max current, ramp rate, max session minutes, min interval between changes)
- Mode: `simulation` vs `lsl` (experimental)

## Tests
Minimal smoke tests live in `tests/`. Expand with real CI once you integrate hardware.

## License
MIT (see `LICENSE`).

## Citation/context
This scaffold was authored to support a PhD project on **Tailored Neuromodulation for Optimizing Motor‑Cognitive Rehabilitation in Parkinson’s Disease** and its aim to use AI for real‑time adaptive stimulation. See the project brief for details.
