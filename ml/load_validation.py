import json
import os

import librosa
import numpy as np

from helper_functions import extract_features

DEFAULT_DATA_PATH = "nsynth-test"
MIDI_MIN, MIDI_MAX = 21, 108


def load_data(path=DEFAULT_DATA_PATH, target_sr=16000, duration=0.5, top_db=40,
              limit=None, verbose=True):
    '''
    params:
        path       - NSynth split directory (e.g. "nsynth-valid")
        target_sr  - resample rate; must match training (16000)
        duration   - seconds kept after trimming; must match training (0.5)
        top_db     - silence threshold for librosa.effects.trim
        limit      - if set, stop after this many accepted samples (for quick tests)
        verbose    - print progress

    returns:
        X    (n, 84) float32 - CQT-mean features
        Y    (n,)    int64   - labels, midi pitch shifted to 0-87
        meta dict of parallel arrays: instrument_family, instrument_source,
             instrument, velocity, note_str  (for slicing results later)
    '''
    with open(os.path.join(path, "examples.json"), "r") as f:
        data_labels = json.load(f)

    dataset_x, dataset_y = [], []
    fam, src, inst, vel, names = [], [], [], [], []

    total = len(data_labels)

    for i, task in enumerate(data_labels.keys()):
        audio_task_data = data_labels[task]

        midi_note = audio_task_data['pitch']
        if not MIDI_MIN <= midi_note <= MIDI_MAX:
            continue

        audio_file_path = os.path.join(path, "audio", f"{task}.wav")
        y, sr = librosa.load(audio_file_path, sr=target_sr)

        # trim silence, then take a fixed-length window from the attack
        y, _ = librosa.effects.trim(y, top_db=top_db)
        y = y[:int(sr * duration)]
        if y.size == 0:
            continue
        y = y / (np.max(np.abs(y)) + 1e-8)

        _, cqt_mean = extract_features(y, sr=target_sr)

        dataset_x.append(cqt_mean)
        dataset_y.append(midi_note - MIDI_MIN)
        fam.append(audio_task_data['instrument_family'])
        src.append(audio_task_data['instrument_source'])
        inst.append(audio_task_data['instrument'])
        vel.append(audio_task_data['velocity'])
        names.append(task)

        if verbose and (i + 1) % 500 == 0:
            print(f"  {i + 1}/{total} scanned, {len(dataset_x)} kept", flush=True)
        if limit is not None and len(dataset_x) >= limit:
            break

    X = np.asarray(dataset_x, dtype=np.float32)
    Y = np.asarray(dataset_y, dtype=np.int64)
    meta = {
        "instrument_family": np.asarray(fam, dtype=np.int64),
        "instrument_source": np.asarray(src, dtype=np.int64),
        "instrument": np.asarray(inst, dtype=np.int64),
        "velocity": np.asarray(vel, dtype=np.int64),
        "note_str": np.asarray(names),
    }
    if verbose:
        print(f"done: {X.shape[0]} samples from {path}")
    return X, Y, meta

