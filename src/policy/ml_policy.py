
import numpy as np
import os

class MLPolicy:
    """Pure NumPy MLP inference stub.
    Expects a weights file (npz) with keys: W1,b1,W2,b2
    Input: feature vector [beta_power, alpha_power, beta/alpha, ...]
    Output: recommended absolute mA (not delta) which will be clamped by SafetyManager.
    """
    def __init__(self, weights_path):
        if not os.path.exists(weights_path):
            raise FileNotFoundError(f"Weights not found: {weights_path}")
        d = np.load(weights_path, allow_pickle=False)
        self.W1, self.b1 = d['W1'], d['b1']
        self.W2, self.b2 = d['W2'], d['b2']

    @staticmethod
    def _relu(x): return np.maximum(0, x)

    def predict_mA(self, features):
        x = np.asarray(features, dtype=float).reshape(1, -1)
        h = self._relu(x @ self.W1 + self.b1)
        y = h @ self.W2 + self.b2
        return float(y.ravel()[0])
