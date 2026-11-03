"""
Measure how note accuracy depends on the analysis window length.

The app sends predict() the latest WINDOW samples of mic audio (see
web/public/pcm-processor.js). This does the same offline: cut labeled NSynth
clips down to each window length, run them through the same predict(), and
score the result against the label.

    python scripts/eval_window.py
    python scripts/eval_window.py --family string --limit 200

Positions:
    attack   window starts at the note onset (what training saw)
    sustain  window starts 1s after onset, mid-note (what a held tuning note looks like)
Modes:
    app      predict() exactly as the server runs it (includes librosa trim)
    no-trim  same, minus trim (what an RMS gate in place of trim would feed the model)
"""
import argparse
import json
import os
import sys
import time

import librosa
import numpy as np
import torch

# run from the repo root: `python scripts/eval_window.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.features import extract_features
from app.inference import mean, model, predict, std

SR = 16000
VIOLIN_MIN, VIOLIN_MAX = 55, 100 # G3 - E7
SUSTAIN_OFFSET = 1.0 # seconds after onset; NSynth notes are held for 3s
POSITIONS = ("attack", "sustain")
MODES = ("app", "no-trim")


def top_k_no_trim(y, k=3):
    '''predict() without the trim step; returns top-k midi notes or [] if gated'''
    peak = np.max(np.abs(y))
    if peak < 1e-3:
        return []
    y = y / (peak + 1e-8)
    _, cqt_mean = extract_features(y, sr=SR)
    x = (torch.as_tensor(cqt_mean, dtype=torch.float32).unsqueeze(0) - mean) / std
    with torch.no_grad():
        probs = model(x).softmax(1).squeeze(0)
    return [int(i) + 21 for i in torch.topk(probs, k=k).indices]


def top_k_app(y, k=3):
    return [p["midi"] for p in predict(y, SR, k=k)]


def load_clips(path, family, limit):
    with open(os.path.join(path, "examples.json")) as f:
        labels = json.load(f)
    clips = [(name, info["pitch"]) for name, info in labels.items()
             if VIOLIN_MIN <= info["pitch"] <= VIOLIN_MAX
             and (family is None or info["instrument_family_str"] == family)]
    return clips[:limit] if limit else clips


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/nsynth-test")
    ap.add_argument("--family", default=None, help="NSynth instrument family, e.g. string")
    ap.add_argument("--windows", default="0.5,0.256,0.128,0.064", help="window lengths in seconds")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    windows = [int(float(w) * SR) for w in args.windows.split(",")]
    clips = load_clips(args.data, args.family, args.limit)
    print(f"{len(clips)} clips in G3-E7 from {args.data}"
          + (f" (family={args.family})" if args.family else ""))

    scorers = {"app": top_k_app, "no-trim": top_k_no_trim}
    # results[(window, position, mode)] -> list of (label, top-k list)
    results = {(n, pos, mode): [] for n in windows for pos in POSITIONS for mode in MODES}

    t0 = time.perf_counter()
    for i, (name, pitch) in enumerate(clips):
        y, _ = librosa.load(os.path.join(args.data, "audio", f"{name}.wav"), sr=SR)
        _, (onset, _) = librosa.effects.trim(y, top_db=40)
        starts = {"attack": onset, "sustain": onset + int(SUSTAIN_OFFSET * SR)}

        for n in windows:
            for pos, start in starts.items():
                seg = y[start:start + n]
                if len(seg) < n:
                    continue
                for mode, scorer in scorers.items():
                    results[(n, pos, mode)].append((pitch, scorer(seg)))

        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(clips)}  ({time.perf_counter() - t0:.0f}s)", flush=True)

    def score(rows):
        n = len(rows)
        top1 = sum(1 for p, top in rows if top and top[0] == p) / n
        top3 = sum(1 for p, top in rows if p in top) / n
        octave = sum(1 for p, top in rows if top and top[0] != p and (top[0] - p) % 12 == 0) / n
        gated = sum(1 for _, top in rows if not top) / n
        return top1, top3, octave, gated

    print(f"\n{'window':>8}  {'position':<8} {'mode':<8} {'n':>5}  {'top-1':>6} {'top-3':>6} {'octave':>7} {'gated':>6}")
    for n in windows:
        for pos in POSITIONS:
            for mode in MODES:
                rows = results[(n, pos, mode)]
                if not rows:
                    continue
                top1, top3, octave, gated = score(rows)
                print(f"{n / SR:>7.3f}s  {pos:<8} {mode:<8} {len(rows):>5}  "
                      f"{top1:>6.1%} {top3:>6.1%} {octave:>7.1%} {gated:>6.1%}")
        print()

    # where in the violin range does a short window hurt?
    registers = [("G3-B3", 55, 59), ("C4-B4", 60, 71), ("C5-B5", 72, 83), ("C6-E7", 84, 100)]
    print("top-1 by register (attack, app)")
    print(f"{'window':>8}  " + "  ".join(f"{r:>7}" for r, _, _ in registers))
    for n in windows:
        rows = results[(n, "attack", "app")]
        cells = []
        for _, lo, hi in registers:
            sub = [(p, top) for p, top in rows if lo <= p <= hi]
            cells.append(f"{score(sub)[0]:>7.1%}" if sub else f"{'-':>7}")
        print(f"{n / SR:>7.3f}s  " + "  ".join(cells))


if __name__ == "__main__":
    main()
