# Cleanup Plan — Low-Latency Violin Tuner

Target: violin now (G3–E7), general instruments later. Written 2026-08-01.

The goal of this cleanup is to cut end-to-end latency from ~500–1000ms to
~100–200ms **without** retraining, then unlock the remaining wins that do
require retraining.

---

## Measured baseline

All measured on this machine, 16kHz mono, `librosa.hybrid_cqt(n_bins=84)`:

| Operation | Cost |
|---|---|
| `hybrid_cqt`, 0.5s block | 14.7 ms |
| `hybrid_cqt`, 0.25s block | 14.2 ms |
| `hybrid_cqt`, 0.125s block | 14.0 ms |
| `librosa.effects.trim` (warm) | 0.1 ms |
| `cqt`, 48 bins from G3, any length | ~8.2 ms |

**Compute is not the bottleneck.** CQT cost is flat with respect to window
length (librosa zero-pads short inputs), so shortening the window buys nothing
on CPU. Every meaningful latency win is structural.

### Where the latency actually is

| Source | Cost | Fix |
|---|---|---|
| `blocksize = 8000` — callback waits for 0.5s of audio | 500 ms | Task 1 |
| Non-overlapping blocks — note onset waits for block boundary | 0–500 ms | Task 1 |
| Feature + model inference | ~15 ms | not worth touching |

---

## Violin range facts

| Note | MIDI | Hz | Period |
|---|---|---|---|
| G3 (lowest open string) | 55 | 196.00 | 5.10 ms |
| D4 | 62 | 293.66 | 3.41 ms |
| A4 | 69 | 440.00 | 2.27 ms |
| E5 | 76 | 659.26 | 1.52 ms |
| E7 (practical top) | 100 | 2637.02 | 0.38 ms |

G3–E7 spans **46 semitones**. The current CQT uses 84 bins from **C1
(MIDI 24)** — so bins 0–30 sit entirely below the violin's range and bins
77–83 sit above it. Roughly **45% of the feature vector is dead weight** for
violin.

This matters more than it looks: those dead low bins are exactly the ones that
need long windows to resolve. Dropping them is what makes a short window
honest rather than just fast.

### How short can the window actually go?

Measured on **112 NSynth `string` samples in G3–E7**, using raw CQT-peak pitch
(`fmin=G3`, 48 bins) as a model-free proxy for resolution quality:

| Window | Peak-pick accuracy |
|---|---|
| 0.250s | 83.0% |
| 0.150s | 75.0% |
| 0.100s | 73.2% |
| 0.064s | 75.0% |
| 0.032s | 49.1% |

Read this as a resolution floor, not as a target accuracy — a trained model on
the full 48-bin vector should beat naive peak-picking at every row. The shape
is what matters:

- **0.25s → 0.15s** costs ~8 points. Real but affordable.
- **0.15s → 0.064s** is roughly flat.
- **Below ~0.05s it collapses.** Not a tuning problem — there is not enough
  signal to resolve a semitone at G3.

**Decision: 128ms analysis window, 32ms hop.** Sits in the flat region with
margin, gives ~4 CQT frames to average, and yields a new prediction every
32ms. Earlier synthetic pure-tone tests suggested 32ms windows were viable —
they are not; that test was too easy and the real-audio numbers above
supersede it.

---

## Task 1 — Decouple audio block from analysis window

**Biggest win. No retraining. Do this first.**

Currently `blocksize = int(SAMPLE_RATE * duration)` = 8000 samples, so
`audio_callback` fires only every 500ms, and blocks tile end-to-end.

Change to: small `blocksize` (512 samples = 32ms) feeding a **ring buffer**.
The analysis thread reads a sliding 128ms window off the buffer every hop.

- Analysis window stays long enough for frequency resolution.
- Predictions arrive every 32ms instead of every 500ms.
- Expected latency: `window/2 + ~15ms` ≈ **~80ms**, down from 500–1000ms.

Also replace the unbounded `queue.Queue` with a fixed-size ring buffer —
if the consumer stalls, the current queue grows without limit and predictions
fall further and further behind live audio. A ring buffer drops stale audio
instead, which is the correct failure mode for a real-time tuner.

## Task 2 — Remove `librosa.effects.trim` from the live path

**This is a correctness bug, independent of latency.**

`script.py:50-51` does:

```python
y, _ = librosa.effects.trim(y, top_db=TOP_DB)
y = y[:int(SAMPLE_RATE * duration)]
```

This was copied from `load_validation.py:49`, where it is correct — NSynth
files are one isolated note with leading silence, so trimming finds the attack.

On a live stream it does something different. A block holding the tail of note
A plus the attack of note B has no silence at either edge, so `trim` returns
the whole block unchanged; `cqt_mean` then averages two different pitches into
one vector matching neither. At fast BPM this is the common case, not an edge
case. `trim` also shifts onset timing by an unpredictable amount, so it
actively fights Task 3.

Replace with an RMS gate: compute RMS on the window, skip inference below a
floor. Preserves onset timing, costs ~0ms.

Note this makes live preprocessing differ from training preprocessing. That is
a real concern — but the current code already has that mismatch and handles it
strictly worse. Task 5 closes the gap properly.

## Task 3 — Onset-aligned analysis

**This is what actually buys fast-BPM support.** Tasks 1–2 reduce latency;
this one makes note *separation* work.

Run `librosa.onset.onset_detect` on the ring buffer and classify the window
starting at each detected onset, rather than at arbitrary hop boundaries. A
window aligned to a note boundary contains one note; a window on a fixed grid
frequently straddles two.

Shortening the window alone cannot fix straddling — it only makes it less
likely. Onset alignment addresses it directly.

## Task 4 — Smoothing, sized against the hop

Phase 5 of `note_classifier_pipeline.md` calls for majority vote over N frames.
Worth doing, but note it **adds latency proportional to N**:

- At a 32ms hop, a 3-frame median vote costs ~96ms — affordable.
- At the current 500ms block, even a 3-frame vote costs 1.5s — not affordable.

Task 1 is what makes smoothing usable at all. Do it in that order.

## Task 5 — Retrain with violin-appropriate bins

Requires retraining, so it comes last. Two changes:

1. **`fmin=G3`, `n_bins=48`** instead of `fmin=C1`, `n_bins=84`. Drops ~45% of
   the input that is dead for violin, halves CQT cost (14.7ms → 8.2ms), and
   removes the low bins that force long windows. Keep the 88-class output head
   so the general-instrument goal stays open — only the *input* narrows.
2. **Train on 128ms windows**, matching Task 1, and apply the same RMS gate
   used live so train and inference preprocessing agree.

### Known limit: mean-pooling

The model consumes `cqt_mean` — CQT averaged across time (`helper_functions.py:51`).
Averaging across a note transition produces a vector matching neither note.
Onset alignment (Task 3) mitigates this, but if you later want notes *shorter*
than the analysis window, mean-pooling itself becomes the ceiling and the model
needs to consume the full `(48, n_frames)` CQT. Worth knowing now; not worth
fixing yet.

---

## Order of work

| # | Task | Retrain? | Latency win |
|---|---|---|---|
| 1 | Ring buffer, decouple block from window | No | 500–1000ms → ~80ms |
| 2 | Drop `trim`, add RMS gate | No | correctness, ~0ms |
| 3 | Onset-aligned windows | No | note separation |
| 4 | Median-vote smoothing | No | costs ~96ms, buys stability |
| 5 | Retrain: `fmin=G3`, 48 bins, 128ms | **Yes** | 14.7ms → 8.2ms + accuracy |

Tasks 1–3 are the ones that matter and none require retraining.

---

## Open question

Tasks 1–4 assume the current 84-bin C1-based model stays in place, fed 128ms
windows it was never trained on (it was trained on 0.5s). Accuracy will drop
somewhat until Task 5 retrains it.

Two ways to sequence this:

- **A:** Ship Tasks 1–3 against the current model, accept degraded accuracy,
  measure how bad it is, then retrain. Fast feedback on whether the latency
  architecture is right.
- **B:** Do Task 5 first so every later measurement reflects the real model.
  Slower start, cleaner numbers.

A is probably right — the architecture change is independent of the model, and
Task 5 is cheap to redo once the harness exists.
