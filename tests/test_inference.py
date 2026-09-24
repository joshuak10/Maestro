import numpy as np
import pytest
import librosa
from app.inference import preprocess, predict
from conftest import SR, tone


def test_preprocess_returns_model_input(a4):
    x = preprocess(a4, sr=SR)
    assert x.shape == (1, 84)


@pytest.mark.parametrize("y", [
    np.zeros(8000, dtype=np.float32),
    np.full(8000, 1e-4, dtype=np.float32),
])
def test_quiet_input_is_rejected(y):
    assert preprocess(y, sr=SR) is None
    assert predict(y, SR) == []


@pytest.mark.parametrize("freq, note", [(440.0, "A4"), (220.0, "A3"), (329.63, "E4")])
def test_predicts_pure_tones(freq, note):
    assert predict(tone(freq), SR)[0]["note"] == note


def test_prediction_format(a4):
    res = predict(a4, SR, k=3)
    assert len(res) == 3
    assert [r["confidence"] for r in res] == sorted((r["confidence"] for r in res), reverse=True)
    for r in res:
        assert set(r) == {"note", "midi", "confidence"}
        assert 21 <= r["midi"] <= 108
        assert 0.0 <= r["confidence"] <= 1.0


def test_volume_does_not_change_prediction():
    assert predict(tone(440.0, amp=0.05), SR)[0]["note"] == predict(tone(440.0, amp=0.9), SR)[0]["note"]


def test_real_recording():
    y, _ = librosa.load("audio_files/A_1.wav", sr=SR, duration=0.5)
    assert predict(y, SR)[0]["note"] == "A4"
