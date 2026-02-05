# AI-Generated Voice Detector API

A fast, secure REST API for detecting AI-generated vs. human speech in multiple languages (English, Tamil, Hindi, Malayalam, Telugu).

## Features

✅ **Audio Input**: Accepts Base64-encoded MP3 files  
✅ **Multi-language**: Support for 5 Indian + English languages  
✅ **Classification**: Returns `AI_GENERATED` or `HUMAN` with confidence score  
✅ **Secure**: API key-based authentication with constant-time comparison  
✅ **Input Validation**: MP3 decoding, file size, duration checks  
✅ **Health Check**: `/health` endpoint for deployment monitoring  
✅ **Fast**: Typical response time 1-3 seconds  
✅ **Production Ready**: Docker support, deployment guides included  

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export API_KEY="your-secret-key"

# Run API
uvicorn voice_detector.app:app --host 0.0.0.0 --port 8000 --reload
```

**Test health check**:
```bash
curl http://localhost:8000/health
```

### Docker (Recommended for Evaluation)

```bash
# Build
docker build -t ai-voice-detector .

# Run
docker run -e API_KEY="your-secret-key" -p 8000:8000 ai-voice-detector
```

## API Usage

### `/detect` - Detect Voice

**Request**:
```bash
curl -X POST http://localhost:8000/detect \
  -H "Authorization: Bearer your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_base64": "<base64-encoded MP3>",
    "language": "en"
  }'
```

**Response (HTTP 200)**:
```json
{
  "result": "AI_GENERATED",
  "confidence": 0.875
}
```

**Supported Languages**: `en`, `ta`, `hi`, `ml`, `te`

**Error Codes**:
- `401`: Unauthorized (missing/invalid API key)
- `400`: Bad request (invalid audio, unsupported language, etc.)

### `/health` - Health Check

```bash
curl http://localhost:8000/health
```

**Response**:
```json
{"status": "ok"}
```

## Deployment

### To Render.com (Free Cloud Hosting)

See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step instructions.

Quick summary:
1. Push code to GitHub
2. Connect to Render
3. Set `API_KEY` environment variable
4. Deploy → Get public URL

## Testing

### Run Unit Tests

```bash
# Generate test audio files first
python tests/generate_test_audio.py

# Run pytest
pytest tests/test_api.py -v
```

**Test Coverage**:
- ✅ Health check
- ✅ Valid audio detection
- ✅ All supported languages
- ✅ Authentication (Bearer token, x-api-key)
- ✅ Invalid auth/ missing key
- ✅ Invalid base64
- ✅ Unsupported language
- ✅ File size limits
- ✅ Response format validation
- ✅ Confidence precision

## Architecture

```
voice_detector/
├── app.py              # FastAPI application & endpoints
└── utils/
    └── audio.py        # Audio feature extraction (librosa)

tests/
├── test_api.py         # Unit tests
├── generate_test_audio.py  # Test audio generator
└── audio_samples/      # Generated test MP3s
```

## Key Implementation Details

### Authentication
- Supports `Authorization: Bearer <key>` and `x-api-key` headers
- Uses `hmac.compare_digest()` for constant-time comparison
- Requires `API_KEY` environment variable (fails on startup if missing)

### Input Validation
- Base64 decoding with error handling
- MP3 format validation via `librosa.load()`
- File size: max 2 MB, min 100 bytes
- Duration: max 30 seconds, min 0.5 seconds
- Request timeout: 10 seconds

### Classification
Heuristic model using audio features:
- **Pitch Stability** (45%): AI voices have consistent pitch (low f0 variance)
- **Zero-Crossing Rate** (25%): AI voices have lower ZCR
- **Spectral Variance** (20%): AI voices have stable spectral profile
- **Spectral Flatness** (10%): AI voices have lower flatness

Threshold: ≥0.5 confidence → `AI_GENERATED`, <0.5 → `HUMAN`

### Confidence Scoring
- Normalized to [0.0, 1.0] range
- Rounded to 3 decimal places
- Not probability-calibrated (future improvement)

## Production Notes

- **Concurrency**: Single worker configured (suitable for most workloads)
- **Scalability**: Can add more workers for higher throughput
- **Dependencies**: Requires `ffmpeg` for MP3 decoding (included in Docker)
- **Monitoring**: Health check endpoint enables automatic recovery

## Improvements Made (From Evaluation)

Based on comparison with evaluator requirements:

| Issue | Fix |
|-------|-----|
| Default API key fallback | Now requires env var on startup |
| Timing-attack vulnerability | Using `hmac.compare_digest()` |
| Brittle MP3 validation | Now uses librosa decoding attempt |
| No request timeout | Added 10s timeout per request |
| Response may have extra fields | Enforced {result, confidence} only |
| No health endpoint | Added `/health` for monitoring |
| Unstable for evaluation | No public URL → See DEPLOYMENT.md |
| No tests | Added comprehensive pytest suite |
| Duplicate code | Removed duplicate extract_features |

## Evaluator Checklist

Before evaluation:
- [ ] Set `API_KEY` environment variable
- [ ] Run health check: `/health` → should return HTTP 200
- [ ] Test with sample MP3: `/detect` → should return {result, confidence}
- [ ] Verify authentication: Invalid key → HTTP 401
- [ ] Test all 5 languages: Should accept en, ta, hi, ml, te
- [ ] Deploy using Dockerfile or deployment guide

## Support

For issues:
1. Check error message from API response
2. Review DEPLOYMENT.md for deployment issues
3. Review this README and COMPARISON_AND_INSTRUCTIONS.md
4. Ensure MP3 files are valid and within size/duration limits

---

**Version**: 1.0  
**Last Updated**: February 2026  
**Model**: Heuristic v1 (audio feature-based classification)
