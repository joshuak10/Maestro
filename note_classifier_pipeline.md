# Real-Time Note Classifier — Build Pipeline

A step-by-step plan for building your own ML model that classifies audio input
to the closest musical note. Work through phases in order — each one validates
the previous before adding complexity.

---

## Phase 0: Setup

- [ ] Install dependencies: `librosa`, `numpy`, `torch`, `sounddevice`
- [ ] Confirm you can load and play back an audio file with librosa
- [ ] Decide your target label space:
  - **Recommended for v1**: 88 piano keys, MIDI notes 21–108
  - Alternative: 12 pitch classes only (octave-agnostic), simpler but less useful

---

## Phase 1: Feature Extraction

**Goal:** convert raw audio into a fixed-size numeric vector a model can consume.

- [x] Write `extract_features(y, sr)` using `librosa.cqt` (Constant-Q Transform)
  - Use 84 bins / 12 bins-per-octave (7 octaves) as a starting point
  - Convert amplitude to dB scale (`librosa.amplitude_to_db`)
- [x] For a single prediction, average CQT across time frames to get one
      `(84,)` vector per audio chunk
- [x] **Sanity check**: generate a known pure tone (e.g. A4 = 440Hz), run it
      through `extract_features`, and confirm the peak energy bin corresponds
      to the correct note. Do this before writing any model code.

---

## Phase 2: Synthetic Dataset

**Goal:** build a dataset with perfect, zero-effort labels to validate your pipeline.

- [x ] Write `synth_note(midi_note, sr, duration)` that generates a waveform
      with a fundamental + a couple of harmonics (not a pure sine — real
      instruments have overtones)
- [ x] Generate multiple variations per note: different durations, added noise,
      slight amplitude/harmonic variation
- [ x] Build a `Dataset`/`DataLoader` (PyTorch) that yields
      `(features, label)` pairs, where `label = midi_note - 21`
- [x ] **Split train/val by generation seed or variation index**, not randomly
      per-sample — avoid leaking near-duplicate variations of the same note
      across the split

---

## Phase 3: Model + Training

**Goal:** confirm the model can learn on synthetic data (this tests your
pipeline, not real-world generalization yet).

- [ ] Start with a simple feedforward network (Linear → ReLU → Dropout →
      Linear → ReLU → Linear), input size 84, output size 88
- [ ] Normalize features before training (subtract mean, divide by std, or
      min-max scale) — raw dB-scale CQT values can destabilize training
- [ ] Train with `CrossEntropyLoss` + Adam optimizer, ~20 epochs to start
- [ ] Track train vs. val accuracy per epoch
- [ ] **Target**: near-100% val accuracy on synthetic data. If you don't hit
      this, debug the pipeline (features, labels, normalization) before moving on

---

## Phase 4: Real Data

**Goal:** see how the model performs on real instrument timbres, and expect
accuracy to drop — this is where the real learning happens.

- [ ] Choose a real dataset:
  - NSynth (Google) — large, varied instrument/pitch dataset
  - University of Iowa Musical Instrument Samples (MIS) — cleaner, smaller
  - MAESTRO — real piano recordings (more complex, polyphonic)
- [ ] Re-run feature extraction + training on this new dataset
- [ ] Compare val accuracy to Phase 3. Investigate misclassifications:
  - Confusions between octaves? → may need better bin resolution or more bins
  - Confusions between adjacent semitones? → may need better time-frame
    handling or longer analysis windows for low notes
- [ ] (Optional) If moving to a 2D CQT spectrogram (freq × time) instead of a
      time-averaged vector, swap the feedforward net for a small CNN to
      capture onset/attack patterns

---

## Phase 5: Real-Time Inference

**Goal:** wire the trained model into a live audio stream.

- [ ] Use `sounddevice.InputStream` to capture live audio in small blocks
      (e.g. ~0.25–0.5s chunks)
- [ ] In the callback: extract features from the chunk, normalize using the
      **same stats computed during training**, run through the model, convert
      predicted class back to a MIDI note / note name
- [ ] Add smoothing across consecutive predictions (e.g. majority vote over
      last N frames) to reduce flicker/jitter in the output
- [ ] Test against a real instrument or your own voice/tuner as ground truth

---

## Notes / Things to Revisit Later

- Low notes need longer time windows for good frequency resolution in CQT —
  watch for degraded accuracy on bass notes with short chunk sizes
- Consider comparing your trained model's output against `librosa.pyin`
  (direct pitch tracking) as a sanity baseline
- Polyphonic input (multiple notes at once) is a much harder problem — this
  pipeline assumes monophonic (one note at a time) input throughout
