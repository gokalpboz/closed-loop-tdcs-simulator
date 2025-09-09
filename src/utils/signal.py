
import numpy as np

def welch_bandpower(x, fs, fmin, fmax, nperseg=None, noverlap=None, detrend=True):
    """Compute band power via simple Welch periodogram (NumPy only).
    x: 1D array (samples)
    fs: sampling rate (Hz)
    Returns power in uV^2 (relative units if input is arbitrary).
    """
    x = np.asarray(x)
    if detrend:
        x = x - np.mean(x)
    if nperseg is None:
        nperseg = min(len(x), 256)
    if noverlap is None:
        noverlap = nperseg // 2
    step = nperseg - noverlap
    if nperseg <= 0 or step <= 0 or len(x) < nperseg:
        # fallback to single FFT on full window
        freqs = np.fft.rfftfreq(len(x), 1.0/fs)
        psd = (np.abs(np.fft.rfft(x))**2) / (fs * len(x))
        band = (freqs >= fmin) & (freqs <= fmax)
        return float(np.trapz(psd[band], freqs[band]))
    # segment
    psds = []
    for start in range(0, len(x)-nperseg+1, step):
        seg = x[start:start+nperseg]
        seg = seg * np.hanning(len(seg))
        fft = np.fft.rfft(seg)
        psd = (np.abs(fft)**2) / (fs * np.sum(np.hanning(len(seg))**2))
        psds.append(psd)
    psd = np.mean(psds, axis=0)
    freqs = np.fft.rfftfreq(nperseg, 1.0/fs)
    band = (freqs >= fmin) & (freqs <= fmax)
    return float(np.trapz(psd[band], freqs[band]))

def ema(prev, new, alpha):
    if prev is None:
        return new
    return alpha * new + (1 - alpha) * prev
