
import numpy as np
from ..utils.signal import welch_bandpower, ema

class EEGPipeline:
    def __init__(self, fs, bands, detrend=True, chunk_sec=1.0, smoothing=0.3):
        self.fs = fs
        self.bands = bands
        self.detrend = detrend
        self.chunk_sec = chunk_sec
        self.smoothing = smoothing
        self._ema_beta = None

    def features(self, chunk):
        """chunk: ndarray [n_channels, n_samples]
        returns dict with bandpowers averaged across channels
        """
        n_channels, n_samples = chunk.shape
        feats = {}
        for band_name, (fmin, fmax) in self.bands.items():
            vals = []
            for ch in range(n_channels):
                vals.append(welch_bandpower(chunk[ch], self.fs, fmin, fmax, detrend=self.detrend))
            feats[f"{band_name}_power"] = float(np.mean(vals))
        # Smooth one key marker (beta) for control stability
        beta = feats.get("beta_power", 0.0)
        feats["beta_power_smooth"] = ema(self._ema_beta, beta, self.smoothing)
        self._ema_beta = feats["beta_power_smooth"]
        return feats
