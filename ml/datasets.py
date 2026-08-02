import torch
import numpy as np
from torch.utils.data import Dataset, DataLoader
import app.features as af


class AudioRecordingDataset(Dataset):
    def __init__(self, path, mean = None, std = None):
        data = np.load(path)
        self.X, self.Y, self.hv = data['X'], data['Y'], data['hv']
        self.mean, self.std =  mean, std


    def __len__(self):
        return self.X.shape[0]
    
    def __getitem__(self, i: int):
        x = self.X[i]
        if self.mean is not None:
            x = (x - self.mean) / self.std
        return (torch.tensor(x, dtype=torch.float32), torch.tensor(self.Y[i], dtype = torch.long))

def gen_sin_wave(freq: float, time_vec, amp = 1):
    return amp * np.sin(2 * np.pi * freq * time_vec)

def synth_note(midi_note: int, sr: int, duration: float, num_harmonics=3, amp=1, harmonic_variance=0.0):

    if midi_note < 21 or midi_note > 108:
        raise ValueError("MIDI note must be 21-108")
    
    freq = af.midi_to_Hz(midi_note)
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

def add_noise(x, snr = None):
    if snr is None:
        return x
    signal_power = np.mean(x ** 2)
    raw_noise = np.random.normal(0,1, x.shape)
    raw_noise_power = np.mean(raw_noise ** 2)

    snr_linear = 10 ** (snr / 10.0)

    scaling_factor = np.sqrt(signal_power / (raw_noise_power * snr_linear))
    scaled_noise = raw_noise * scaling_factor

    noisy_soundwave = x + scaled_noise
    return noisy_soundwave

HARM_VAR = [0.0, 0.05, 0.1, 0.15, 0.25]
SNR_LEVELS = [None, 0, 10, 20, 30]

def generate_dataset(sr=16000, duration=0.5):
    dataset_x = []
    dataset_y = []
    dataset_hv = []
    
    for midi_note in range(21, 109):
        for harm_var in HARM_VAR:
            x, _ = synth_note(midi_note, sr, duration, num_harmonics=3, harmonic_variance=harm_var)
            for snr in SNR_LEVELS:
                x_new = add_noise(x, snr)
                _, cqt_mean = af.extract_features(x_new, sr)  
                dataset_x.append(cqt_mean)
                dataset_y.append(midi_note - 21)  # 0–87
                dataset_hv.append(harm_var)
    
    X = np.array(dataset_x)  # Shape: (num_samples, 84)
    Y = np.array(dataset_y)
    hv = np.array(dataset_hv)
    return X, Y, hv



def main():
    a = AudioRecordingDataset("training_data/synth_train_data.npz")
    print("a")
    print(len(a))

if __name__ == "__main__":
    main()
