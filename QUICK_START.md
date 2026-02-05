# Quick Start Guide - AI Voice Detector v2.0

## 🚀 Get Running in 5 Minutes

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set API Key
```powershell
# Windows PowerShell
$env:API_KEY = "your-secret-key-here"

# Or create .env file
API_KEY=your-secret-key-here
```

### 3. Train ML Model (Optional)
```bash
# Train main model
python train_model.py

# Train per-language models
python train_language_models.py
```

### 4. Generate Test Data
```bash
python tests/generate_test_audio.py
```

### 5. Run API
```bash
uvicorn voice_detector.app:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Test
- **Web UI**: Open `http://localhost:8000/`
- **Health Check**: `curl http://localhost:8000/health`
- **Run Tests**: `pytest tests/test_api.py -v`

---

## 📋 What's New (v1.0 → v2.0)

| Feature | v1.0 | v2.0 |
|---------|------|------|
| Classifier | Heuristic | ML-trained (95% accuracy) |
| Logging | Basic errors | Full request logging |
| Monitoring | No | `/metrics` endpoint |
| Rate Limiting | No | 10 req/min per IP |
| Database | No | SQLite detection history |
| Web UI | No | Full interactive UI |
| Per-language | No | Separate models per language |
| CI/CD | No | GitHub Actions pipeline |

---

## 🔧 Key Configuration

### Environment Variables
```bash
# Required
API_KEY=your-secret-api-key

# Optional
DATABASE_URL=sqlite:///./detections.db  # Change for PostgreSQL
LOG_LEVEL=INFO
```

### Constraints
- Max file size: 2 MB
- Max duration: 30 seconds
- Min duration: 0.5 seconds
- Request timeout: 10 seconds
- Rate limit: 10 requests/minute per IP

---

## 📊 Monitoring

### View Metrics
```bash
curl -H "Authorization: Bearer your-api-key" http://localhost:8000/metrics
```

### Check Logs
```bash
# View recent logs
tail -f detections.log

# Search for errors
grep "ERROR" detections.log
```

### Query Database
```bash
sqlite3 detections.db "SELECT COUNT(*) FROM detections;"
sqlite3 detections.db "SELECT language, COUNT(*) FROM detections GROUP BY language;"
```

---

## 🧪 Testing

### Run Unit Tests
```bash
pytest tests/test_api.py -v --tb=short
```

### Test with Sample MP3
```python
import base64
import requests

# Read MP3 file
with open("test.mp3", "rb") as f:
    audio_base64 = base64.b64encode(f.read()).decode()

# Make request
response = requests.post(
    "http://localhost:8000/detect",
    json={
        "audio_base64": audio_base64,
        "language": "en"
    },
    headers={"Authorization": "Bearer your-api-key"}
)

print(response.json())
```

---

## 🐳 Docker

### Build
```bash
docker build -t voice-detector .
```

### Run Locally
```bash
docker run \
  -e API_KEY="your-secret-key" \
  -p 8000:8000 \
  voice-detector
```

### Run with Volume (persistence)
```bash
docker run \
  -e API_KEY="your-secret-key" \
  -v $(pwd)/data:/app/data \
  -p 8000:8000 \
  voice-detector
```

---

## ☁️ Deploy to Cloud

### Option 1: Render (Easiest)
1. Push code to GitHub
2. Connect to Render
3. Set `API_KEY` env var
4. Deploy!

See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step.

### Option 2: AWS / GCP
See [AWS_GCP_DEPLOYMENT.md](AWS_GCP_DEPLOYMENT.md)

---

## 📡 API Examples

### Detect Voice
```bash
curl -X POST http://localhost:8000/detect \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_base64": "ID3...",
    "language": "en"
  }'
```

### Get Metrics
```bash
curl http://localhost:8000/metrics \
  -H "Authorization: Bearer your-api-key"
```

### Health Check
```bash
curl http://localhost:8000/health
```

---

## 🔍 Troubleshooting

### Error: `API_KEY environment variable is not set`
```bash
# Windows PowerShell
$env:API_KEY = "your-key"

# Linux/Mac
export API_KEY="your-key"
```

### Error: `Module not found: voice_detector.database`
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Port 8000 already in use
```bash
# Use different port
uvicorn voice_detector.app:app --port 8001
```

### Model files not found
```bash
# Train model first
python train_model.py
# App will fallback to heuristic if model not found
```

---

## 📈 Performance Tips

### For Local Development
- Use `--reload` flag for hot reload
- Keep test MP3s < 1 MB
- Run on SSD for faster I/O

### For Production
- Use multiple workers: `--workers 4`
- Enable gzip compression
- Use reverse proxy (nginx) for caching
- Monitor with `/metrics` endpoint

---

## 📚 Documentation

- **Full API Reference**: See docstrings in `app.py`
- **Database Schema**: See `database.py`
- **Feature Extraction**: See `utils/audio.py`
- **Model Training**: See `train_model.py`
- **Detailed Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 🎯 Next Steps

1. ✅ Run locally and test
2. ✅ Deploy to Render (free)
3. ✅ Train models on your data
4. ✅ Monitor with `/metrics`
5. ✅ Integrate into your app

---

## 💬 Common Questions

**Q: Can I use WAV/OGG instead of MP3?**
A: Currently MP3 only. Modify `app.py` to accept other formats via `librosa`.

**Q: How accurate is the detector?**
A: ML model ~95% on training data. Real-world accuracy depends on data quality.

**Q: Can I use a PostgreSQL database?**
A: Yes, set `DATABASE_URL=postgresql://user:pass@host/db`

**Q: How do I train models on my own data?**
A: Modify `train_model.py` to use your labeled dataset instead of synthetic data.

**Q: Can I run this offline?**
A: Yes, all processing is local. Only requires internet for initial setup/deployment.

---

## 📞 Support

- **Issues**: Check logs in `detections.log`
- **API Errors**: Read error message in response
- **Performance**: Use `/metrics` to identify bottlenecks
- **Database**: Query with `sqlite3` command-line tool

---

**Happy detecting! 🎙️**
