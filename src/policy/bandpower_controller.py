
import numpy as np

class BandpowerPIDController:
    """Very conservative PID-like controller mapping beta error -> delta mA.
    All gains and limits are in config. Integral/derivative default to 0.
    """
    def __init__(self, kp=0.15, ki=0.0, kd=0.0, max_step_mA=0.2):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.max_step = max_step_mA
        self._int = 0.0
        self._prev_err = None

    def propose_delta(self, beta_power, target_beta):
        err = float(target_beta - beta_power)
        self._int += err
        derr = 0.0 if self._prev_err is None else (err - self._prev_err)
        self._prev_err = err
        delta = self.kp * err + self.ki * self._int + self.kd * derr
        # hard limit per-decision change
        delta = float(np.clip(delta, -self.max_step, self.max_step))
        return delta
