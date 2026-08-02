import librosa
import numpy as np
import torch 

REF_FREQ = 440

def extract_features(y, sr):
    '''''''''

    Takes time-series, converts to CQT (frequency time domain). Averages each bin value across the recording(should take short windows)
    
    '''''''''
    
    cqt = librosa.hybrid_cqt(y, sr = sr, n_bins = 84, bins_per_octave= 12, tuning = 0.0)
    #cqt = amp_to_db(cqt)
    cqt = librosa.amplitude_to_db(S = cqt, top_db = 80)
    cqt_mean = np.mean(cqt, axis = 1)
    return cqt, cqt_mean

def amp_to_db(cqt, ref = 1):
    return 20 * np.log10(np.maximum(np.abs(cqt), 1e-10)/ref)

def midi_to_note(midi):
    return librosa.midi_to_note(midi)

def midi_to_Hz(midi_note: int) -> float:
    return REF_FREQ * 2 ** ((midi_note - 69)/12)