import os
import librosa
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader

REF_FREQ = 440

class AudioRecordingDataset(Dataset):
    def __init__(self, path):
        data = np.load(path)
        self.X, self.Y = data['X'], data['Y']


    def __len__(self):
        return self.X.shape[0]
    
    def __getitem__(self, i: int):
        return (torch.tensor(self.X[i], dtype=torch.float32), torch.tensor(self.Y[i], dtype = torch.long))

def midi_to_note(midi):
    return librosa.midi_to_note(midi)

def amp_to_db(cqt, ref = 1):
    return np.multiply(20, np.log10(cqt/ref))

def midi_to_Hz(midi_note: int) -> float:
    return REF_FREQ * 2 ** ((midi_note - 69)/12)

def gen_sin_wave(freq: float, time_vec, amp = 1):
    return amp * np.sin(2 * np.pi * freq * time_vec)

def extract_features(y, sr):
    '''''''''

    Takes time-series, converts to CQT (frequency time domain). Averages each bin value across the recording(should take short windows)
    
    '''''''''
    
    cqt = librosa.hybrid_cqt(y, sr = sr, n_bins = 84, bins_per_octave= 12, tuning = 0.0)
    cqt = amp_to_db(cqt)
    cqt_mean = np.mean(cqt, axis = 1)
    return cqt, cqt_mean

def synth_note(midi_note: int, sr: int, duration: float, num_harmonics=3, amp=1, harmonic_variance=0.0):

    if midi_note < 21 or midi_note > 108:
        raise ValueError("MIDI note must be 21-108")
    
    freq = midi_to_Hz(midi_note)
    t_samp = int(sr * duration)
    t = np.linspace(0, duration, t_samp, endpoint=False)
    
    y = gen_sin_wave(freq, t, amp=amp)
    
    for i in range(2, num_harmonics + 2):
        base_harmonic_amp = amp * (1 / i)
        variance_factor = np.random.uniform(1 - harmonic_variance, 1 + harmonic_variance)
        harmonic_amp = base_harmonic_amp * variance_factor
        y += gen_sin_wave(freq * i, t, amp=harmonic_amp)
    
    y = y / (np.max(np.abs(y)) + 1e-8)
    
    fade_duration = min(0.1, duration * 0.2)
    fade_samples = int(fade_duration * sr)
    fade_in_curve = np.linspace(0.0, 1.0, fade_samples)
    fade_out_curve = np.linspace(1.0, 0.0, fade_samples)
    y[:fade_samples] = y[:fade_samples] * fade_in_curve
    y[-fade_samples:] = y[-fade_samples:] * fade_out_curve
    
    return y, freq

def add_noise(x, snr = 0):
    if snr == 0:
        return x
    signal_power = np.mean(x ** 2)
    raw_noise = np.random.normal(0,1, x.shape)
    raw_noise_power = np.mean(raw_noise ** 2)

    snr_linear = 10 ** (snr / 10.0)

    scaling_factor = np.sqrt(signal_power / (raw_noise_power * snr_linear))
    scaled_noise = raw_noise * scaling_factor

    noisy_soundwave = x + scaled_noise
    return noisy_soundwave

def generate_dataset(sr=44100, duration=2):
    dataset_x = []
    dataset_y = []
    
    for midi_note in range(21, 109):
        for harm_var in [0.0, 0.05, 0.1, 0.15]:
            x, _ = synth_note(midi_note, sr, duration, num_harmonics=3, harmonic_variance=harm_var)
            for snr in [0, 10, 20, 30]:
                x_new = add_noise(x, snr)
                _, cqt_mean = extract_features(x_new, sr)  
                dataset_x.append(cqt_mean)
                dataset_y.append(midi_note - 21)  # 0–87
    
    X = np.array(dataset_x)  # Shape: (num_samples, 84)
    Y = np.array(dataset_y)
    return X, Y



def main():
    a = AudioRecordingDataset("training_data/synth_train_data.npz")
    print("a")
    print(len(a))

if __name__ == "__main__":
    main()
