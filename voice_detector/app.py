from fastapi import FastAPI, Header, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import base64
import os
import sys
import tempfile
import numpy as np
import hmac
import asyncio
import joblib
import logging
import uuid
from datetime import datetime, timedelta
from collections import defaultdict
from voice_detector.utils.audio import extract_features
from voice_detector.database import Detection, SessionLocal, get_db
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("detections.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Enforce API_KEY env var at startup
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    logger.error("API_KEY environment variable is not set. Exiting.")
    sys.exit(1)

logger.info("API initialized with API key")

app = FastAPI(title="AI Voice Detector", version="2.0")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

SUPPORTED = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "ml": "Malayalam",
    "te": "Telugu",
}

MAX_AUDIO_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_AUDIO_DURATION = 30.0  # seconds
REQUEST_TIMEOUT = 10.0  # seconds

# Load ML model and scaler
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
try:
    if os.path.exists(os.path.join(MODEL_DIR, "voice_classifier.joblib")):
        model = joblib.load(os.path.join(MODEL_DIR, "voice_classifier.joblib"))
        scaler = joblib.load(os.path.join(MODEL_DIR, "feature_scaler.joblib"))
        metadata = joblib.load(os.path.join(MODEL_DIR, "model_metadata.joblib"))
        MODEL_AVAILABLE = True
        logger.info(f"Loaded ML model: {metadata['model_type']} v{metadata['version']}")
    else:
        logger.warning("Model files not found. Using heuristic classifier.")
        MODEL_AVAILABLE = False
        model = None
        scaler = None
        metadata = None
except Exception as e:
    logger.warning(f"Failed to load model: {e}. Using heuristic classifier.")
    MODEL_AVAILABLE = False
    model = None
    scaler = None
    metadata = None

# Metrics tracking
metrics = {
    "total_requests": 0,
    "successful_detections": 0,
    "failed_requests": 0,
    "auth_failures": 0,
    "by_language": defaultdict(int),
    "by_result": defaultdict(int),
    "request_times": [],
    "last_reset": datetime.utcnow()
}


class AudioRequest(BaseModel):
    audio_base64: str
    language: str


class DetectionResponse(BaseModel):
    result: str
    confidence: float
    request_id: str = None


def _check_api_key(header_value: str | None, x_api_key: str | None) -> bool:
    """Constant-time API key comparison."""
    if header_value:
        parts = header_value.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return hmac.compare_digest(parts[1], API_KEY)
    if x_api_key:
        return hmac.compare_digest(x_api_key, API_KEY)
    return False


def _rate_limit_check(client_ip: str) -> bool:
    """Simple rate limiter: max 100 requests per minute per IP (increased for testing)."""
    if not hasattr(_rate_limit_check, "clients"):
        _rate_limit_check.clients = {}
    
    now = datetime.utcnow()
    
    if client_ip not in _rate_limit_check.clients:
        _rate_limit_check.clients[client_ip] = []
    
    # Remove old requests (older than 1 minute)
    _rate_limit_check.clients[client_ip] = [
        ts for ts in _rate_limit_check.clients[client_ip]
        if (now - ts).total_seconds() < 60
    ]
    
    # Check limit
    if len(_rate_limit_check.clients[client_ip]) >= 100:
        return False
    
    _rate_limit_check.clients[client_ip].append(now)
    return True


def _classify_ml(feats: dict) -> tuple[str, float]:
    """Classify using trained ML model."""
    try:
        feature_list = [
            feats.get("duration", 1.0),
            feats.get("f0_var", 500.0),
            feats.get("zcr_mean", 0.1),
            feats.get("spec_centroid_var", 5000.0),
            feats.get("flatness_mean", 0.5)
        ]
        
        # Scale features
        X_scaled = scaler.transform([feature_list])
        
        # Predict
        proba = model.predict_proba(X_scaled)[0]
        confidence = float(proba[1])  # Probability of AI_GENERATED
        label = "AI_GENERATED" if confidence >= 0.5 else "HUMAN"
        
        return label, confidence
    except Exception as e:
        logger.warning(f"ML classification failed: {e}. Falling back to heuristic.")
        return _classify_heuristic(feats)


def _classify_heuristic(feats: dict) -> tuple[str, float]:
    """Fallback heuristic classifier."""
    dur = min(max(feats.get("duration", 1.0), 0.1), 10.0)
    f0_var = feats.get("f0_var", 1000.0)
    zcr = feats.get("zcr_mean", 0.1)
    spec_cent_var = feats.get("spec_centroid_var", 10000.0)
    flatness = feats.get("flatness_mean", 0.5)

    s_f0 = 1.0 - (min(f0_var, 500.0) / 500.0)
    s_zcr = 1.0 - min(zcr / 0.5, 1.0)
    s_spec = 1.0 - (min(spec_cent_var / 5000.0, 1.0))
    s_flat = 1.0 - min(flatness, 1.0)

    score = (0.45 * s_f0) + (0.25 * s_zcr) + (0.2 * s_spec) + (0.1 * s_flat)
    confidence = float(max(0.0, min(1.0, score)))
    label = "AI_GENERATED" if confidence >= 0.5 else "HUMAN"
    
    return label, confidence


@app.get("/")
async def web_ui():
    """Serve the web UI."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Web UI not available"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "model": "ml" if MODEL_AVAILABLE else "heuristic"}


@app.get("/metrics")
async def get_metrics(request: Request, x_api_key: str | None = Header(None)):
    """Get API metrics and statistics."""
    auth_header = request.headers.get("authorization")
    if not _check_api_key(auth_header, x_api_key):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    uptime = datetime.utcnow() - metrics["last_reset"]
    avg_request_time = (
        sum(metrics["request_times"]) / len(metrics["request_times"])
        if metrics["request_times"] else 0
    )
    
    return {
        "uptime_seconds": uptime.total_seconds(),
        "total_requests": metrics["total_requests"],
        "successful_detections": metrics["successful_detections"],
        "failed_requests": metrics["failed_requests"],
        "auth_failures": metrics["auth_failures"],
        "success_rate": (
            metrics["successful_detections"] / metrics["total_requests"]
            if metrics["total_requests"] > 0 else 0
        ),
        "avg_request_time_ms": avg_request_time * 1000,
        "by_language": dict(metrics["by_language"]),
        "by_result": dict(metrics["by_result"]),
        "model_version": metadata["version"] if metadata else "heuristic",
        "model_type": metadata["model_type"] if metadata else "heuristic"
    }




@app.post("/detect")
async def detect_voice(
    data: AudioRequest,
    request: Request,
    x_api_key: str | None = Header(None),
    db: Session = Depends(get_db)
):
    """
    Detect AI-generated vs. human voice.
    
    Request:
    {
      "audio_base64": "<base64-encoded MP3>",
      "language": "en|ta|hi|ml|te"
    }
    
    Response:
    {
      "result": "AI_GENERATED" | "HUMAN",
      "confidence": <float 0.0-1.0>
    }
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.utcnow()
    
    try:
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Rate limit check
        metrics["total_requests"] += 1
        if not _rate_limit_check(client_ip):
            metrics["failed_requests"] += 1
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(status_code=429, detail="Too many requests")
        
        # Authenticate
        auth_header = request.headers.get("authorization")
        if not _check_api_key(auth_header, x_api_key):
            metrics["auth_failures"] += 1
            logger.warning(f"Auth failure for {request_id}")
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Validate language
        lang = (data.language or "").lower()
        if lang not in SUPPORTED:
            metrics["failed_requests"] += 1
            logger.warning(f"Unsupported language: {lang}")
            raise HTTPException(status_code=400, detail=f"Unsupported language: {lang}")

        # Decode base64
        try:
            audio_bytes = base64.b64decode(data.audio_base64)
        except Exception:
            metrics["failed_requests"] += 1
            logger.warning(f"Invalid base64 in request {request_id}")
            raise HTTPException(status_code=400, detail="audio_base64 must be valid base64")

        # Validate file size
        if len(audio_bytes) > MAX_AUDIO_FILE_SIZE:
            metrics["failed_requests"] += 1
            logger.warning(f"File too large in request {request_id}")
            raise HTTPException(status_code=400, detail=f"Audio file exceeds {MAX_AUDIO_FILE_SIZE} bytes")

        if len(audio_bytes) < 100:
            metrics["failed_requests"] += 1
            logger.warning(f"File too small in request {request_id}")
            raise HTTPException(status_code=400, detail="Audio file is too small")

        # Extract features with timeout
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                f.write(audio_bytes)
                temp_file = f.name

            try:
                async def load_and_extract():
                    import librosa
                    y, sr = librosa.load(temp_file, sr=16000, mono=True)
                    duration = float(len(y) / sr) if sr > 0 else 0.0
                    
                    if duration > MAX_AUDIO_DURATION:
                        raise ValueError(f"Audio duration exceeds {MAX_AUDIO_DURATION} seconds")
                    if duration < 0.5:
                        raise ValueError("Audio duration is too short (< 0.5 seconds)")
                    
                    return extract_features(temp_file)

                feats = await asyncio.wait_for(load_and_extract(), timeout=REQUEST_TIMEOUT)

            finally:
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

        except asyncio.TimeoutError:
            metrics["failed_requests"] += 1
            logger.warning(f"Processing timeout in request {request_id}")
            raise HTTPException(status_code=400, detail="Audio processing timeout")
        except ValueError as e:
            metrics["failed_requests"] += 1
            logger.warning(f"Invalid audio in request {request_id}: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid audio: {str(e)}")
        except Exception as e:
            metrics["failed_requests"] += 1
            logger.error(f"Feature extraction error in {request_id}: {e}")
            raise HTTPException(status_code=400, detail="Could not decode audio or extract features")

        # Classify
        if MODEL_AVAILABLE:
            result, confidence = _classify_ml(feats)
            model_version = metadata["version"]
        else:
            result, confidence = _classify_heuristic(feats)
            model_version = "heuristic"
        
        confidence = round(confidence, 3)

        # Log metrics
        metrics["successful_detections"] += 1
        metrics["by_language"][lang] += 1
        metrics["by_result"][result] += 1
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        metrics["request_times"].append(elapsed)
        if len(metrics["request_times"]) > 1000:
            metrics["request_times"] = metrics["request_times"][-1000:]
        
        logger.info(f"{request_id} | {lang} | {result} | {confidence:.3f} | {elapsed:.3f}s")

        # Store in database
        try:
            detection = Detection(
                id=request_id,
                language=lang,
                result=result,
                confidence=confidence,
                model_version=model_version
            )
            db.add(detection)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to store detection in DB: {e}")
            db.rollback()

        return {
            "result": result,
            "confidence": confidence
        }

    except HTTPException:
        raise
    except Exception as e:
        metrics["failed_requests"] += 1
        logger.error(f"Unexpected error in {request_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
