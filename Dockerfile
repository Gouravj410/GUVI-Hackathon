FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (ffmpeg needed by librosa for MP3 decoding)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY voice_detector/ ./voice_detector/

# Expose port for FastAPI
EXPOSE 8000

# Run the FastAPI application
# API_KEY environment variable MUST be set at runtime
CMD ["uvicorn", "voice_detector.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
