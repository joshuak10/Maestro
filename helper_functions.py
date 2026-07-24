import os
import librosa
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader


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



def main():
    a = AudioRecordingDataset("training_data/synth_train_data.npz")
    print("a")
    print(len(a))

if __name__ == "__main__":
    main()
