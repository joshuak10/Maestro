import os
import pandas as pd
import numpy as np
from torch.utils.data import Dataset, DataLoader


class AudioRecordingDataset(Dataset):
    def __init__(self, path):
        loaded = np.load(path)
        self.X = np.load[0]
        self.Y = np.load[1]


    def __len__(self):
        return self.X.shape[0]
    
    def __getitem__(self):
        

