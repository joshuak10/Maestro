import sounddevice as sd
import queue
import torch
import numpy as np
import torch.nn as nn
import librosa
from app.features import extract_features

SAMPLE_RATE = 16000
channels = 1
duration = 0.5
block_size = int(SAMPLE_RATE * duration)

MIDI_MIN = 21
CONF_THRESHOLD = 0.5
TOP_DB = 40

audio_queue = queue.Queue()

checkpoint = torch.load('models/linear_nsynth.pth', map_location='cpu')
hidden = checkpoint['model_state']['0.weight'].shape[0]
model = nn.Sequential(
    nn.Linear(84, hidden),
    nn.ReLU(),
    nn.Dropout(p=0.3),
    nn.Linear(hidden, 88) # 88 = num of valid midi_notes
)
model.load_state_dict(checkpoint['model_state'])
model.eval()

# (84,) -> (1, 84) so they broadcast over a batch of one frame
mean = checkpoint['mean'].unsqueeze(0)
std = checkpoint['std'].unsqueeze(0)


def audio_callback(indata, frames, time, status):
    if status:
        print(status, flush=True)
    audio_queue.put(indata.copy())

def ml_process_loop():
    try:
        while True:
            try:
                y = audio_queue.get(timeout=0.1)[:, 0]
            except queue.Empty:
                continue

            # same preprocessing as training (see load_validation.load_data)
            y, _ = librosa.effects.trim(y, top_db=TOP_DB)
            y = y[:int(SAMPLE_RATE * duration)]
            if y.size == 0:
                continue
            y = y / (np.max(np.abs(y)) + 1e-8)

            _, cqt_mean = extract_features(y, sr=SAMPLE_RATE)
            x = torch.as_tensor(cqt_mean, dtype=torch.float32).unsqueeze(0)
            x = (x - mean) / std

            with torch.no_grad():
                probs = model(x).softmax(1).squeeze(0)

            conf, idx = probs.max(0)
            if conf.item() > CONF_THRESHOLD:
                print(f"{librosa.midi_to_note(idx.item() + MIDI_MIN)}  {conf.item():.2f}")

    except KeyboardInterrupt:
        print("Recording Stopped")


stream = sd.InputStream(samplerate=SAMPLE_RATE, channels= channels, blocksize= block_size, callback=audio_callback)

with stream:
    print(f"Listening at {SAMPLE_RATE} Hz ({duration}s blocks). Ctrl-C to stop.")
    ml_process_loop()
