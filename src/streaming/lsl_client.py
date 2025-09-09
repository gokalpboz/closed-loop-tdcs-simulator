
import numpy as np
import time

try:
    from pylsl import StreamInlet, resolve_stream
except Exception:
    StreamInlet = None
    resolve_stream = None

class EEGSource:
    """Return EEG chunks [n_channels, n_samples] at a fixed fs and chunk length.
    In simulation mode, emits synthetic EEG with variable beta bursts.
    """
    def __init__(self, mode='simulation', fs=250, n_channels=8, chunk_sec=1.0, log_fn=print):
        self.mode = mode
        self.fs = fs
        self.n_channels = n_channels
        self.n_samples = int(fs*chunk_sec)
        self.log = log_fn
        self._t = 0
        self._beta_amp = 2.0
        self._rng = np.random.default_rng(42)
        if self.mode == 'lsl':
            if resolve_stream is None:
                raise RuntimeError("pylsl not installed.")
            streams = resolve_stream('type','EEG', timeout=3.0)
            if not streams:
                raise RuntimeError("No LSL EEG stream found.")
            self.inlet = StreamInlet(streams[0])
            self.log("[EEG] Connected to LSL stream.")
        else:
            self.inlet = None
            self.log("[EEG] Simulation mode.")

    def next_chunk(self):
        if self.mode == 'lsl' and self.inlet is not None:
            samples, timestamps = self.inlet.pull_chunk(timeout=2.0, max_samples=self.n_samples)
            if not samples or len(samples) < self.n_samples:
                time.sleep(self.n_samples/self.fs)
                return self.next_chunk()
            arr = np.array(samples).T
            if arr.shape[0] > self.n_channels:
                arr = arr[:self.n_channels]
            return arr[:, :self.n_samples]
        else:
            # Simulation: 1/f noise + oscillations + occasional beta bursts tied to hidden state
            t = np.arange(self.n_samples)/self.fs
            out = []
            # hidden state: occasionally increases beta amplitude
            if self._rng.random() < 0.2:
                self._beta_amp = float(np.clip(self._beta_amp + self._rng.normal(0,0.3), 0.5, 5.0))
            for ch in range(self.n_channels):
                noise = self._rng.normal(0, 1.0, size=self.n_samples) * (1/np.sqrt(np.maximum(1, np.arange(1,self.n_samples+1))))
                alpha = 10*np.sin(2*np.pi*10*(t + ch*0.01))
                beta = self._beta_amp*np.sin(2*np.pi*20*(t + ch*0.02))
                sig = 0.2*noise + 0.5*alpha + 0.8*beta
                out.append(sig.astype(float))
            time.sleep(self.n_samples/self.fs)
            return np.vstack(out)
