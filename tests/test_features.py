import numpy as np
import pytest
from app.features import extract_features, midi_to_Hz
from conftest import SR, tone


def test_extract_features_shapes():
    cqt, cqt_mean = extract_features(tone(440.0), sr=SR)
    assert cqt.shape[0] == 84
    assert cqt_mean.shape == (84,)
    assert np.all(np.isfinite(cqt_mean))


def test_cqt_peak_is_at_a4():
    _, cqt_mean = extract_features(tone(440.0), sr=SR)
    assert int(np.argmax(cqt_mean)) == 69 - 24


@pytest.mark.parametrize("midi, hz", [(69, 440.0), (57, 220.0), (81, 880.0)])
def test_midi_to_hz(midi, hz):
    assert midi_to_Hz(midi) == pytest.approx(hz)
