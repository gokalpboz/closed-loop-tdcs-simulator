
import time

class StimulatorAPI:
    """Abstract interface. Replace with a *certified* stimulator driver in HIL.
    This base class provides common ramping utilities. Do *not* subclass to real hardware
    without adding physical safety interlocks, impedance checks, and watchdogs.
    """
    def __init__(self):
        self.current_mA = 0.0
        self.polarity = 'anodal'
        self.is_on = False

    def connect(self): pass
    def disconnect(self): pass

    def set_polarity(self, polarity:str):
        assert polarity in ('anodal','cathodal')
        self.polarity = polarity

    def ramp_to(self, target_mA: float, seconds: float):
        """Ramp linearly to target over `seconds` to avoid abrupt steps."""
        if seconds <= 0:
            self.current_mA = float(target_mA)
            return
        steps = max(1, int(seconds * 10))
        start = self.current_mA
        for i in range(1, steps+1):
            self.current_mA = start + (target_mA - start) * (i/steps)
            self._apply_output(self.current_mA)
            time.sleep(seconds/steps)

    def start(self): self.is_on = True
    def stop(self): 
        self.is_on = False
        self._apply_output(0.0)
        self.current_mA = 0.0

    def _apply_output(self, mA: float):
        """Override in subclass to send command to hardware."""
        pass

class MockStimulator(StimulatorAPI):
    def __init__(self, log_fn=print):
        super().__init__()
        self.log = log_fn

    def connect(self):
        self.log("[MockStim] connected.")

    def disconnect(self):
        self.log("[MockStim] disconnected.")

    def _apply_output(self, mA: float):
        if self.is_on:
            self.log(f"[MockStim] output => {mA:.3f} mA ({self.polarity})")
        else:
            self.log(f"[MockStim] (standby) => {mA:.3f} mA")        
