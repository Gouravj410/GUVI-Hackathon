# Comparative Analysis and Remediation Instructions

This document compares the current `voice_detector` app with the expected evaluator requirements, lists gaps and risks, and provides concrete step-by-step instructions to reach evaluator readiness.

## Comparison Table

| Feature / Requirement | Present in My App | How It Is Implemented | Gap / Issue | Recommendation to Fix or Improve |
|---|---:|---|---|---|
| Accepts one Base64-encoded MP3 per request | Partial | `POST /detect` expects JSON `audio_base64`, decodes base64 and writes a temp `.mp3`. Performs a simple MP3 signature check. | Signature check is brittle; no max size/duration limits; may reject valid MP3 variants. | Replace signature check with a decode attempt (librosa/ffmpeg), add max file size and duration checks, and request timeouts. |
| Supports Tamil, English, Hindi, Malayalam, Telugu | Partial | `SUPPORTED` dict accepts `en, ta, hi, ml, te`. Rejects other language codes. | No verification that audio matches declared language; no per-language calibration. | Add optional language detection or per-language thresholds/models; document supported language codes clearly. |
| Classify audio as `AI_GENERATED` or `HUMAN` (no hard-coding) | Partial | Heuristic classifier uses features (pitch variance, ZCR, spectral variance, flatness) and threshold 0.5 to decide. | Heuristic is simplistic, untrained, uncalibrated; accuracy uncertain. | Train a small ML model (per-language if possible), or at minimum calibrate the heuristic with validation data and expose model version in logs. |
| Return confidence float between 0.0 and 1.0 | Yes | Confidence computed from heuristic score and clamped to [0,1]. | Not probability-calibrated; precision not specified. | Calibrate probabilities (Platt/isotonic), round to a consistent decimal (e.g., 2-3 digits). |
| API key authentication | Partial | Accepts `Authorization: Bearer <key>` or `x-api-key`; reads `API_KEY` env var but falls back to default `YOUR_SECRET_KEY`. | Default key is insecure; comparison not constant-time; no rate limiting or logging. | Require `API_KEY` env var at startup (fail if missing), use `hmac.compare_digest` for comparison, add rate limiting and request logs. |
| Return proper JSON exactly `{result, confidence}` with HTTP 200 | Partial | Success responses return the two fields currently, errors use FastAPI `HTTPException` with `detail`. | Some older templates attempted model loads that would crash if model files missing; ensure success responses never include extra fields and always return HTTP 200 on success. | Add tests to assert response shape; return only `result` and `confidence` on success and 200. |
| Live, stable, and fast (suitable for automated evaluation) | No / Partial | FastAPI app with CPU-bound `librosa` processing. No deployment or timeout settings included. | Potentially slow (pitch extraction, MFCC), no timeouts, no concurrency tuning, no public endpoint. | Limit audio length, add per-request timeout, use worker pool or optimized libs, containerize and deploy to a public host with health checks. |
| Avoid restricted external detection APIs | Yes | All processing is local using `librosa` and NumPy. | None. | Keep processing local; if adding external services, implement graceful fallback and circuit breakers. |
| Explainability (basic) | Partial | Heuristic weights present in code (comments) but not returned to caller. | No explainability returned to requester; debugging difficult during evaluation. | Add optional authenticated debug output or logs with feature contributions (not in production payload). |
| Handle invalid input and return proper HTTP codes | Partial | Base64 and decoding errors are caught and return 400/401. | Some edge errors may still produce 500; MP3 check may reject valid files. | Harden exception handling, add targeted error messages, and write tests for invalid inputs. |
| No hard-coding of labels or fixed answers | Yes (not hard-coded per-request) | Labels derived from computed score per request. | Heuristic threshold is fixed and fragile. | Train a small ML classifier and/or calibrate heuristic on labeled data. |
| Single audio per request enforced | Yes | `AudioRequest` Pydantic model enforces single `audio_base64`. | None. | None. |
| Model files / trained model present | No | `model/` folder is empty; earlier code attempted to load models in template. | Missing model reduces accuracy; attempt to load non-existent model may crash older code. | Add a small joblib model or remove model-loading code; implement CI tests around model presence. |
| Public deployment ready | No | No Dockerfile, no deployment scripts, no `/health` endpoint. | Evaluator requires public stable URL; local-only app will fail. | Add Dockerfile, `/health` endpoint, deploy to Render/Railway/AWS, set `API_KEY` env var. |

## Risks That Cause Evaluation Failure (High Priority)

- Authentication: default `API_KEY` or mismatched header format → 401. Set `API_KEY` env var and require `Authorization: Bearer` or `x-api-key` as documented. Use `hmac.compare_digest` for comparison.
- Response format: any extra fields or wrong types → rejection. Ensure success responses are exactly `{ "result": "...", "confidence": 0.xx }` and HTTP 200.
- MP3 decode errors: brittle signature or decode failure → 400. Use decode-first approach with `librosa`/`ffmpeg` and accept common MP3 variants.
- Performance/timeouts: `librosa.yin` and MFCCs may be slow → timeouts. Limit audio length, add request timeout, and consider faster estimators.
- Deployment missing: no public URL → instant fail. Provide a public deployed endpoint.

## Concise Remediation Plan (step-by-step)

1) Secure API key and auth
   - Require `API_KEY` env var on startup; exit if missing.
   - Compare using `hmac.compare_digest(header_value, API_KEY)` for constant-time comparison.
   - Support `Authorization: Bearer <key>` and `x-api-key` headers; document header format.
   - Add basic rate limiting (e.g., `slowapi` or a reverse-proxy limiter) and request logging.

2) Robust MP3 decoding and validation
   - Remove brittle signature checks; attempt to load audio with `librosa.load()` or call `ffmpeg`/`ffprobe` to probe format.
   - Enforce maximum file size (e.g., 2MB) and duration (e.g., 10s) before heavy processing.
   - Add per-request timeout (e.g., using `asyncio.wait_for` around CPU-bound work or deploy with a proxy that enforces timeouts).

3) Response stability & format
   - Ensure success responses contain only `result` and `confidence` and return HTTP 200.
   - Round `confidence` to 3 decimals before returning.
   - Add unit/integration tests that call `/detect` with a valid test MP3 and assert exact response shape.

4) Improve classifier quality and explainability
   - Short-term: calibrate heuristic using a small labeled validation set; tune weights and threshold per language.
   - Medium-term: train a lightweight classifier (e.g., RandomForest or an MLP) on extracted features and persist with `joblib` in `model/`.
   - Always log model version and feature vector for each request (do not expose in success payload). Add an optional authenticated `?debug=true` parameter to return feature contributions for debugging only.

5) Performance and deployment
   - Limit audio length to keep processing under a few seconds.
   - Move heavy work to a threadpool or worker queue if needed; use `uvicorn` with multiple workers for concurrency.
   - Add `/health` returning 200 to indicate readiness.
   - Add a Dockerfile and deploy to Render or Railway. Set `API_KEY` in the host env and expose port 80/443.

6) Tests and CI
   - Add tests: valid MP3 positive/negative, invalid base64, unsupported language, auth failure.
   - Add CI step to run tests and linting.

7) Documentation for evaluator
   - Provide a README with endpoint URL, required header (`Authorization: Bearer <API_KEY>`), sample curl command, and supported language codes.

## Quick Implementation Checklist (small PRs)

- [ ] Enforce `API_KEY` env var and `hmac.compare_digest` in `voice_detector/app.py`.
- [ ] Add `/health` endpoint.
- [ ] Replace MP3 signature check with `librosa` load + size/duration checks.
- [ ] Round `confidence` and enforce response shape.
- [ ] Add Dockerfile and simple deploy instructions for Render.
- [ ] Add a small tests folder with sample MP3s and CI configuration.

## Deployment notes (Render / Railway)

- Build a Docker image exposing port 8000 and run `uvicorn voice_detector.app:app --host 0.0.0.0 --port 8000 --workers 1`.
- Configure the `API_KEY` env var in the deployment dashboard.
- Add a health check URL pointing to `/health`.

---

If you want, I can implement the high-priority fixes now: (A) enforce `API_KEY` and constant-time compare plus `/health`, (B) replace the MP3 signature check with a `librosa`-based decode attempt and add size/duration limits, or (C) add a Dockerfile and deployment guide for Render. Tell me which one to implement first and I'll proceed.
