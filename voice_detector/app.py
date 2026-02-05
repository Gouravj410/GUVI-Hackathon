from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
import base64
import os
import tempfile
import numpy as np
from utils.audio import extract_features

API_KEY = os.getenv("API_KEY", "YOUR_SECRET_KEY")

app = FastAPI()

SUPPORTED = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "ml": "Malayalam",
    "te": "Telugu",
}


class AudioRequest(BaseModel):
    audio_base64: str
    language: str


def _check_api_key(header_value: str | None, x_api_key: str | None) -> bool:
    if header_value:
        # Accept Bearer <key>
        parts = header_value.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1] == API_KEY
    if x_api_key:
        return x_api_key == API_KEY
    return False


@app.post("/detect")
async def detect_voice(data: AudioRequest, request: Request, x_api_key: str | None = Header(None)):
    auth_header = request.headers.get("authorization")
    if not _check_api_key(auth_header, x_api_key):
        raise HTTPException(status_code=401, detail="Unauthorized")

    lang = (data.language or "").lower()
    if lang not in SUPPORTED:
        raise HTTPException(status_code=400, detail="Unsupported language")

    try:
        audio_bytes = base64.b64decode(data.audio_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="audio_base64 must be valid base64")

    # quick mp3 signature check
    if len(audio_bytes) < 4 or not (audio_bytes.startswith(b"ID3") or (audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0)):
        raise HTTPException(status_code=400, detail="audio must be MP3 format")

    # write to temp file and extract features
    with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as f:
        f.write(audio_bytes)
        f.flush()
        try:
            feats = extract_features(f.name)
        except Exception:
            raise HTTPException(status_code=400, detail="Could not decode audio or extract features")

    # simple heuristic classifier (no hard-coded labels; uses audio features)
    # features: dict with keys like 'duration','f0_var','zcr_mean','spec_centroid_var','flatness_mean'
    def classify(feats: dict) -> tuple[str, float]:
        # normalize-ish mappings (coarse)
        dur = min(max(feats.get("duration", 1.0), 0.1), 10.0)
        f0_var = feats.get("f0_var", 1000.0)
        zcr = feats.get("zcr_mean", 0.1)
        spec_cent_var = feats.get("spec_centroid_var", 10000.0)
        flatness = feats.get("flatness_mean", 0.5)

        # heuristics: AI voices tend to have more stable pitch (low f0_var), lower ZCR, and lower spectral variance
        s_f0 = 1.0 - (min(f0_var, 500.0) / 500.0)
        s_zcr = 1.0 - min(zcr / 0.5, 1.0)
        s_spec = 1.0 - (min(spec_cent_var / 5000.0, 1.0))
        s_flat = 1.0 - min(flatness, 1.0)

        # weighted score towards AI
        score = (0.45 * s_f0) + (0.25 * s_zcr) + (0.2 * s_spec) + (0.1 * s_flat)
        confidence = float(max(0.0, min(1.0, score)))
        label = "AI_GENERATED" if confidence >= 0.5 else "HUMAN"
        return label, confidence

    result, confidence = classify(feats)

    return {"result": result, "confidence": confidence}
