FROM python:3.12-slim AS base

# ffmpeg: required by whisper-family ASR backends for audio decoding.
# libsndfile1: required by the `soundfile` package.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

# Install with the 'speech' extra baked in -- the whole point of this
# image is to run the ASR + acoustic pipeline, not just the API shell.
RUN pip install --no-cache-dir ".[speech]"

COPY . .

ENV ALZDX_ENVIRONMENT=production \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "alzheimers_detection.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
