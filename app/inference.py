import torch
import torch.nn as nn
import numpy as np
import librosa
from app.features import extract_features

torch.set_num_threads(1)

checkpoint = torch.load('models/linear_nsynth.pth', map_location='cpu')
mean = checkpoint['mean'].unsqueeze(0)
std = checkpoint['std'].unsqueeze(0)
hidden = checkpoint['model_state']['0.weight'].shape[0]
model = nn.Sequential(
    nn.Linear(84, hidden),
    nn.ReLU(),
    nn.Dropout(p=0.3),
    nn.Linear(hidden, 88) # 88 = num of valid midi_notes
)
model.load_state_dict(checkpoint['model_state'])
model.eval()

def preprocess(y, sr = 16000, duration = 0.5):
    y, _ = librosa.effects.trim(y, top_db= 40)
    y = y[:int(sr * duration)]
    if y.size == 0:
        return None
    peak = np.max(np.abs(y))
    if peak < 1e-3:
        return None
    y = y / (np.max(np.abs(y)) + 1e-8)
    _, cqt_mean = extract_features(y, sr= sr)
    x = torch.as_tensor(cqt_mean, dtype = torch.float32).unsqueeze(0)
    x = (x- mean)/std
    return x

def predict(y,sr = 16000, k=3): #k = kth most likely note
    y = preprocess(y, sr = sr)
    if y is None:
        return []
    with torch.no_grad():
        probs = model(y).softmax(1).squeeze(0)
    top_values, top_indexes = torch.topk(probs, k= k)
    res = []
    for i in range(len(top_values)):
        midi = int(top_indexes[i].item()) + 21
        json = {
            "note": str(librosa.midi_to_note(midi)),
            "midi": midi,
            "confidence": float(top_values[i].item())
        }
        res.append(json)
    return res

