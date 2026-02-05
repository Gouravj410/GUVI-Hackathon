import librosa
import numpy as np

def extract_features(file_path: str) -> dict:
    y, sr = librosa.load(file_path, sr=16000, mono=True)
    duration = float(len(y) / sr) if sr > 0 else 0.0

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    zcr = librosa.feature.zero_crossing_rate(y)
    spec_cent = librosa.feature.spectral_centroid(y=y, sr=sr)
    flatness = librosa.feature.spectral_flatness(y=y)

    # estimate fundamental frequency variance (pitch stability)
    try:
        f0 = librosa.yin(y, fmin=50, fmax=500, sr=sr)
        f0_clean = f0[np.isfinite(f0)]
        f0_var = float(np.var(f0_clean)) if f0_clean.size > 0 else float("inf")
        f0_mean = float(np.mean(f0_clean)) if f0_clean.size > 0 else 0.0
    except Exception:
        f0_var = float("inf")
        f0_mean = 0.0

    feats = {
        "duration": duration,
        "mfcc_mean": np.mean(mfcc, axis=1).tolist(),
        "zcr_mean": float(np.mean(zcr)),
        "zcr_var": float(np.var(zcr)),
        "spec_centroid_mean": float(np.mean(spec_cent)),
        "spec_centroid_var": float(np.var(spec_cent)),
        "flatness_mean": float(np.mean(flatness)),
        "f0_mean": f0_mean,
        "f0_var": f0_var,
    }

    return feats
