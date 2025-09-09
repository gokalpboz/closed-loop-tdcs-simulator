
import time

class SafetyManager:
    def __init__(self, max_mA=2.0, min_mA=0.0, ramp_rate_mA_per_min=0.5,
                 min_seconds_between_changes=30, max_session_minutes=20,
                 require_human_confirm=True, emergency_stop_key='q', log_fn=print):
        self.max_mA = max_mA
        self.min_mA = min_mA
        self.ramp_rate = ramp_rate_mA_per_min
        self.min_interval = min_seconds_between_changes
        self.max_session_sec = max_session_minutes * 60
        self.require_confirm = require_human_confirm
        self.emergency_key = emergency_stop_key
        self.log = log_fn
        self._last_change_ts = 0.0
        self._session_start_ts = time.time()

    def within_session_limits(self):
        elapsed = time.time() - self._session_start_ts
        if elapsed > self.max_session_sec:
            self.log("[SAFETY] Max session time exceeded. Stopping.")
            return False
        return True

    def clamp_target(self, proposed_mA, current_mA):
        # clamp absolute bounds
        target = max(self.min_mA, min(self.max_mA, proposed_mA))
        # enforce ramp-rate in mA per minute -> convert to per change window (min_interval)
        max_delta = self.ramp_rate * (self.min_interval/60.0)
        delta = target - current_mA
        if abs(delta) > max_delta:
            target = current_mA + (max_delta if delta > 0 else -max_delta)
        return target

    def can_change_now(self):
        return (time.time() - self._last_change_ts) >= self.min_interval

    def mark_changed(self):
        self._last_change_ts = time.time()

    def maybe_confirm(self, proposed_mA):
        if not self.require_confirm:
            return True
        self.log(f"[CONFIRM] Apply new target {proposed_mA:.3f} mA? [y/N]")
        try:
            import sys, select
            # Wait up to 10 seconds for user input
            i, _, _ = select.select([sys.stdin], [], [], 10.0)
            if i:
                resp = sys.stdin.readline().strip().lower()
                return resp in ('y','yes')
            return False
        except Exception:
            return False
