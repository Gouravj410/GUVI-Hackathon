# AI Voice Detector - Deployment & Evaluator Guide

## Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- pip

### Install & Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export API_KEY="your-secret-api-key-here"

# Run the API (from project root)
uvicorn voice_detector.app:app --host 0.0.0.0 --port 8000 --reload
```

Health check:
```bash
curl http://localhost:8000/health
# Response: {"status": "ok"}
```

---

## Docker Deployment (Recommended for Evaluators)

### Build Docker Image

```bash
docker build -t ai-voice-detector .
```

### Run Locally with Docker

```bash
docker run \
  -e API_KEY="your-secret-api-key" \
  -p 8000:8000 \
  ai-voice-detector
```

Then visit `http://localhost:8000/health` to verify it's running.

---

## Deploy to Render (Production)

This is the easiest way to get a **public URL** for evaluation.

### Step 1: Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up (GitHub recommended)
3. Create a new Web Service

### Step 2: Configure Render Service
- **Repository**: Your GitHub repo with the code
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn voice_detector.app:app --host 0.0.0.0 --port 8000 --workers 1`
- **Instance Type**: Free tier (or Starter for better reliability)

### Step 3: Set Environment Variables
In Render dashboard:
- Add environment variable `API_KEY` with your secret key
- (Never commit API_KEY to git)

### Step 4: Add Health Check
In Render dashboard → Health Check:
- URL: `/health`
- Check interval: 10 minutes
- This helps Render restart the app if it crashes

### Step 5: Deploy
Push your code to GitHub (or use Render's git integration). Render will automatically deploy.

**Your public API URL will be**: `https://your-service-name.onrender.com`

---

## Usage for Evaluators

### Endpoint: `/detect`

**Method**: `POST`

**Headers**:
```
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

**Request Body**:
```json
{
  "audio_base64": "<base64-encoded MP3 file>",
  "language": "en"
}
```

**Supported Languages**:
- `en` - English
- `ta` - Tamil
- `hi` - Hindi
- `ml` - Malayalam
- `te` - Telugu

**Response (HTTP 200)**:
```json
{
  "result": "AI_GENERATED",
  "confidence": 0.875
}
```

**Error Responses**:
- `401 Unauthorized` - Invalid or missing API key
- `400 Bad Request` - Invalid base64, unsupported language, invalid MP3, or file too large/small

---

## Sample curl Command

### Encode MP3 to base64 and make a request:

```bash
# Assuming you have a test.mp3 file
BASE64_AUDIO=$(cat test.mp3 | base64)

curl -X POST https://your-service-name.onrender.com/detect \
  -H "Authorization: Bearer your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d "{
    \"audio_base64\": \"$BASE64_AUDIO\",
    \"language\": \"en\"
  }"
```

---

## Health Check

**Endpoint**: `/health`

**Method**: `GET`

**Response**:
```json
{"status": "ok"}
```

Use this to verify the service is up and running before sending audio requests.

---

## API Key Security

- The API key is required as an environment variable and must be set before starting the service
- Keys are compared using constant-time comparison (resistant to timing attacks)
- Supports two header formats:
  - `Authorization: Bearer <key>`
  - `x-api-key: <key>` (as a header)

---

## Constraints & Limits

- **Max file size**: 2 MB
- **Max duration**: 30 seconds
- **Min duration**: 0.5 seconds
- **Request timeout**: 10 seconds
- **Sample rate**: Internally normalized to 16 kHz

---

## Performance & Reliability

- **Latency**: Typically 1-3 seconds per request (depends on file size)
- **Uptime**: Render provides 99.99% SLA on paid instances
- **Failover**: Health checks enable automatic recovery

---

## Troubleshooting

### Issue: `401 Unauthorized`
- Verify your API_KEY is set correctly
- Ensure you're using the correct header format

### Issue: `400 Bad Request` with "Invalid audio"
- Confirm the MP3 file is valid and not corrupted
- Check file size is under 2 MB
- Check audio duration is between 0.5 and 30 seconds

### Issue: Service timeout
- Audio processing may be slow for very long or complex files
- Reduce audio duration if possible

---

## Model & Explainability

The classifier uses a **heuristic model** based on audio feature analysis:
- **Pitch Stability** (45% weight): AI voices have more consistent pitch
- **Zero-Crossing Rate** (25% weight): AI voices have lower ZCR
- **Spectral Variance** (20% weight): AI voices have lower spectral variance
- **Spectral Flatness** (10% weight): AI voices have lower flatness

The final confidence score is on a scale of 0.0–1.0, where:
- 0.0–0.5 = **HUMAN**
- 0.5–1.0 = **AI_GENERATED**

---

## Support & Contact

For issues or questions:
1. Check the error message returned by the API
2. Review this guide for common solutions
3. Ensure the MP3 file is valid

---

## Version & Updates

- **API Version**: 1.0
- **Last Updated**: February 2026
- **Model Version**: Heuristic v1 (no trained model)
