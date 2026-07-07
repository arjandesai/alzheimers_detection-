import pytest
from fastapi.testclient import TestClient

from alzheimers_detection.api.main import app


@pytest.fixture
def client(monkeypatch, fake_asr_engine):
    # Patch the factory the pipeline calls internally so the API test
    # never tries to load a real (large) ASR model.
    monkeypatch.setattr(
        "alzheimers_detection.speech.pipeline.get_asr_engine",
        lambda backend, model_size: fake_asr_engine,
    )
    return TestClient(app)


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root_includes_disclaimer(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "not" in resp.json()["disclaimer"].lower()


def test_analyze_speech_success(client, tiny_wav_bytes):
    resp = client.post(
        "/api/v1/speech/analyze",
        files={"file": ("clip.wav", tiny_wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "disclaimer" in body
    assert "risk_band" in body
    assert body["transcript"]["asr_backend"] == "fake"


def test_analyze_speech_rejects_empty_file(client):
    resp = client.post(
        "/api/v1/speech/analyze",
        files={"file": ("empty.wav", b"", "audio/wav")},
    )
    assert resp.status_code == 400


def test_analyze_speech_rejects_unsupported_content_type(client, tiny_wav_bytes):
    resp = client.post(
        "/api/v1/speech/analyze",
        files={"file": ("clip.txt", tiny_wav_bytes, "text/plain")},
    )
    assert resp.status_code == 415
