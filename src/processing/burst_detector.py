
import time
from collections import deque
import math

class BetaBurstDetector:
    """Detects beta 'bursts' on a streaming beta-power scalar.
    Uses an EWMA/EWMSD baseline and a z-threshold with hysteresis and min duration.
    This avoids requiring SciPy filters while giving a robust event detector.
    """
    def __init__(self, ema_alpha=0.05, z_thresh=2.0, hysteresis=0.5, min_duration_sec=2.0):
        self.ema_alpha = float(ema_alpha)
        self.z_thresh = float(z_thresh)
        self.hysteresis = float(hysteresis)
        self.min_duration_sec = float(min_duration_sec)
        self.mu = None
        self.var = None  # EW variance approximation
        self._above_since = None
        self.active = False
        self.last_event_ts = None

    def _update_ew(self, x):
        # EWMA & EW variance (approximate)
        if self.mu is None:
            self.mu = x
            self.var = 0.0
            return
        a = self.ema_alpha
        prev_mu = self.mu
        self.mu = (1 - a) * self.mu + a * x
        # Welford-like EW variance update
        self.var = (1 - a) * (self.var + a * (x - prev_mu) * (x - self.mu))

    def update(self, beta_value, timestamp=None):
        """Feed one beta-power (already smoothed if you like). Returns an event dict:
        {
          'active': bool,             # whether in-burst state
          'just_started': bool,       # rising edge
          'just_ended': bool,         # falling edge
          'z_score': float,           # current z relative to baseline
          'baseline': float           # EWMA baseline
        }
        """
        now = time.time() if timestamp is None else float(timestamp)
        self._update_ew(float(beta_value))
        sigma = math.sqrt(max(1e-12, self.var))
        z = 0.0 if sigma == 0.0 else (beta_value - self.mu) / sigma

        hi = self.z_thresh
        lo = self.z_thresh - self.hysteresis

        just_started = False
        just_ended = False

        if not self.active:
            if z >= hi:
                # not active yet, begin timing
                if self._above_since is None:
                    self._above_since = now
                # activate if sustained
                if (now - self._above_since) >= self.min_duration_sec:
                    self.active = True
                    just_started = True
                    self.last_event_ts = now
            else:
                self._above_since = None
        else:
            # active -> check for end with hysteresis
            if z <= lo:
                self.active = False
                just_ended = True
                self._above_since = None

        return {
            'active': self.active,
            'just_started': just_started,
            'just_ended': just_ended,
            'z_score': z,
            'baseline': self.mu
        }
