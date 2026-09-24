import numpy as np
import pytest
from conftest import tone


def post(client, body, sr=16000):
    return client.post(f"/predict?sr={sr}", content=body)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_predict_happy_path(client):
    r = post(client, tone(440.0).tobytes())
    assert r.status_code == 200
    body = r.json()
    assert body["predictions"][0]["note"] == "A4"
    assert body["low_confidence"] is False
    assert r.headers["Server-Timing"].startswith("predict;dur=")


def test_silence_is_low_confidence(client):
    r = post(client, np.zeros(8000, dtype=np.float32).tobytes())
    assert r.status_code == 200
    assert r.json() == {"predictions": [], "low_confidence": True}


@pytest.mark.parametrize("body, sr", [
    (tone(440.0).tobytes(), 44100),
    (b"", 16000),
    (b"\x00" * 7, 16000),
    (np.zeros(10001, dtype=np.float32).tobytes(), 16000),
    (np.array([0.1, np.nan, 0.2], dtype=np.float32).tobytes(), 16000),
    (np.array([0.1, np.inf, 0.2], dtype=np.float32).tobytes(), 16000),
])
def test_bad_requests_are_rejected(client, body, sr):
    assert post(client, body, sr).status_code == 400
