# Tuner MVP — Full-Stack Build Plan

Turning the existing CQT + linear classifier (`models/linear_nsynth.pth`) into a
usable app. Bare-bones MVP: no accounts, no database, no App Store.

---

## Decisions (answers up front)

### Website, not a native app

Build a **web app (PWA)**. Reasons specific to your situation:

- You don't want Xcode. iOS native is off the table; a PWA installs to the home
  screen and gets a mic via `getUserMedia`.
- Your inference path is **Python-only**. `librosa.hybrid_cqt` has no JS
  equivalent you can drop in — reimplementing CQT in the browser is a project of
  its own. A web frontend + Python backend lets you reuse `helper_functions.extract_features`
  **verbatim**, which is the single most important thing for correctness (see
  "Train/serve skew" below).
- One codebase, instant deploys, shareable URL. Good for a resume/portfolio link.

**Caveat, stated honestly:** a server round-trip per audio chunk means latency of
roughly 100–400ms. That is fine for "play a note, see the name" but is *not* a
real-time tuner needle. Accept this for the MVP; the migration path to real-time
is in Stretch Goals.

### No database

Correct for the MVP. You have no users, no accounts, and nothing worth persisting.
The model is a static file loaded once at boot. **Skip the DB entirely.**

Add one only when you want a specific feature that needs it:
- Saving practice history per user → then you need auth + Postgres.
- Collecting mispredictions to retrain on → a logging bucket (S3/disk) is enough,
  still not a DB.

### Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | **FastAPI** + Uvicorn | Same Python as your model; auto docs; async-ready for WebSockets later |
| Inference | PyTorch CPU + librosa | Reuse existing code unchanged |
| Frontend | **Vanilla HTML/JS** (or Vite + React if you prefer) | MVP needs one page; skip the framework tax |
| Audio capture | `MediaRecorder` / `AudioWorklet` → POST | No native code |
| Hosting | **Render** / **Railway** / **Fly.io** | Docker-friendly, free-ish tier, no serverless cold-start pain with a 300MB torch image |

> Avoid Vercel/Netlify **serverless functions** for the backend — torch + librosa
> blow past the bundle limits. Static frontend on Vercel + backend on Render is fine.

---

## Architecture

```
Browser                          Server (FastAPI)
┌────────────────────┐           ┌──────────────────────────┐
│ mic → getUserMedia │           │ POST /predict            │
│ record ~0.5s chunk │──audio──▶ │  decode wav → 16k mono   │
│ (WAV/WebM blob)    │           │  trim + normalize        │
│                    │           │  extract_features()      │
│ display note+conf  │◀──JSON────│  (x-mean)/std → model    │
└────────────────────┘           │  softmax → top-k         │
                                 └──────────────────────────┘
                                    loads model ONCE at startup
```

---

## Phase 0 — Repo cleanup (½ day)

**Deliverable:** an installable package with a clean app/training split, model
file tracked properly.

**Organizing principle:** everything the *server* needs at inference time goes in
`app/` and stays dependency-light. Everything else is training code and goes in
`ml/`. `extract_features` is the one function both sides share — it lives in
`app/`, and training imports it from there (never the reverse).

### Target layout

```
tuner/
  app/                    # server only — lean deps
    __init__.py
    features.py           # extract_features, amp_to_db, midi_to_note, midi_to_Hz
    inference.py          # Phase 1: model load + predict
    main.py               # Phase 2: FastAPI
  ml/                     # training only — heavy deps
    __init__.py
    datasets.py           # AudioRecordingDataset, synth_note, generate_dataset, ...
    load_validation.py    # moved as-is
    train.ipynb           # moved as-is
  web/index.html          # Phase 3
  models/linear_nsynth.pth
  requirements.txt        # app deps only
  requirements-dev.txt    # + pandas, sklearn, jupyter, matplotlib
  Dockerfile
```

### Where each existing file goes

| Current | Destination | Notes |
|---|---|---|
| `helper_functions.py` | **splits in two** (below) | file is deleted after the split |
| `load_validation.py` | `ml/load_validation.py` | unchanged except its import line |
| `train.ipynb` | `ml/train.ipynb` | must update 3 import lines |
| `script.py` | **ported, not moved** (below) | keep at root until Phase 1 passes |

**`helper_functions.py` splits along "does the server need this at inference time?":**

- **→ `app/features.py`** — `extract_features` (the critical one), `amp_to_db`,
  `midi_to_note`, `midi_to_Hz`, `REF_FREQ`. Pure librosa/numpy, no torch.
- **→ `ml/datasets.py`** — `AudioRecordingDataset`, `synth_note`, `gen_sin_wave`,
  `add_noise`, `generate_dataset`, `HARM_VAR`, `SNR_LEVELS`. These pull in
  `torch.utils.data` and are training-only.
- **Drop the `pandas` import** — it's at the top of the file but never used.

**`script.py` is the one file that isn't a simple move.** It already blends both
halves, so it splits:

- Checkpoint load / model build / mean+std, and the preprocess→predict block →
  become `app/inference.py`. That's Phase 1.
- `sounddevice`, the `queue`, and the stream loop → **discarded.** The browser
  replaces all of it. Don't carry `sounddevice` into `requirements.txt` — it's a
  native-audio dep with no place on a server.

> Leave `script.py` at the repo root *untouched* while writing `app/inference.py`,
> so you can diff the two and confirm the preprocessing matches line for line.
> It's your only working reference for the exact inference path. Delete it once
> the A4 test passes.

### Checklist

- [ ] `pyenv local tuner` → creates `.python-version` so the dir stops resolving
      to bare 3.14.2. **Commit this file.** *(done)*
- [ ] `python -m pip freeze > requirements.txt` (use `python -m pip`, not bare
      `pip`, so it resolves to the pinned env). Then hand-split out the dev-only
      packages. Pin `librosa` and `numpy` especially — CQT output changes subtly
      across librosa versions and will silently degrade accuracy.
      Current env: **Python 3.14 · torch 2.13.0 · librosa 0.11.0 · numpy 2.4.6**.
- [ ] Create `app/` and `ml/` with `__init__.py` in **both** — without them the
      cross-package imports won't resolve.
- [ ] Perform the moves/splits in the table above.
- [ ] Update every import that moved:
      - `load_validation.py` → `from app.features import extract_features`
      - `train.ipynb` → `from ml.datasets import AudioRecordingDataset, generate_dataset`
      - `train.ipynb` → `from ml.load_validation import load_data`
- [ ] `rm -rf __pycache__` — stale `.pyc` files under the old module names cause
      genuinely confusing import errors after a restructure.
- [ ] Add `.gitignore` entries for `nsynth-*/`, `*.npz`, `.DS_Store`.
      **Do commit** `models/*.pth` (90KB — small enough, and the app needs it).
- [ ] Verify nothing broke: re-run `script.py` (still at root) and confirm it
      still detects notes, then open the notebook and run the import cell.

> **Run everything from the repo root.** `from app.features import ...` only
> resolves there — including Jupyter, which must be started from the root or the
> notebook won't find `app`.

---

## Phase 1 — Inference module (½ day)

**Deliverable:** `predict(waveform, sr) -> list[{note, midi, confidence}]`, testable
without a server.

- [ ] Extract a single `TunerModel` class that on init:
      loads checkpoint, infers `hidden` from `model_state['0.weight'].shape[0]`,
      builds the `nn.Sequential`, calls `.eval()`, stores `mean`/`std`.
      **Load once at module import — never per request.**
      Confirmed checkpoint shape: `84 → 125 → 88`, keys `model_state` / `mean` /
      `std`, with `mean` and `std` both `(84,)` → `.unsqueeze(0)` to `(1, 84)`.
- [ ] `preprocess(y, sr)` must be a **byte-for-byte copy** of the training path:
      resample→16k, `librosa.effects.trim(top_db=40)`, slice `0.5s`,
      peak-normalize, `extract_features`, `(x-mean)/std`.
- [ ] Return **top-3** predictions, not top-1. Cheap, and hugely more useful when
      the model is unsure (it will confuse octaves).
- [ ] Add a `torch.no_grad()` wrapper and `torch.set_num_threads(1)` (avoids
      thread thrash on small cloud instances).
- [ ] **Checkpoint test:** feed `synth_note(69, 16000, 0.5)` (A4) through
      `predict()` and assert it returns `A4`. This is your regression test for
      train/serve skew — run it in CI and after every deploy.

---

## Phase 2 — Backend API (1 day)

**Deliverable:** running FastAPI server with 3 endpoints.

- [ ] `GET /health` → `{"status":"ok","model":"linear_nsynth"}`. Needed by the
      host's health check.
- [ ] `POST /predict` — accepts `multipart/form-data` audio blob.
      - Decode with `librosa.load(io.BytesIO(bytes), sr=16000, mono=True)`.
        Browsers send WebM/Opus, so **install `ffmpeg` in the Docker image** —
        soundfile alone won't decode it. (Alternative: send raw Float32 PCM as
        JSON/binary from an `AudioWorklet` and skip decoding entirely — more
        frontend work, fewer server deps. Recommended if ffmpeg gives you trouble.)
      - Response:
        ```json
        {"predictions":[{"note":"A4","midi":69,"confidence":0.91}, ...],
         "low_confidence": false}
        ```
      - Set `low_confidence: true` when top prob < 0.5 (your existing
        `CONF_THRESHOLD`) so the UI can show "unclear" instead of a wrong note.
- [ ] Guardrails: reject payloads > ~1MB, wrap decode in try/except → HTTP 400
      with a clear message. Never let a bad blob 500 the server.
- [ ] Enable CORS for your frontend origin only.
- [ ] `GET /` → serve `web/index.html` via `StaticFiles` (one origin = no CORS
      headaches at all; simplest MVP choice).

---

## Phase 3 — Frontend (1–2 days)

**Deliverable:** one page, one button, a note readout.

- [ ] Single `index.html`: **[ Start Listening ]** button, big note display,
      confidence bar, top-3 list.
- [ ] `navigator.mediaDevices.getUserMedia({audio:{channelCount:1,
      echoCancellation:false, noiseSuppression:false, autoGainControl:false}})`
      — **turn those three off**; they mangle the harmonic content your CQT
      features depend on.
- [ ] Capture loop: `MediaRecorder` with `start(500)` → on each `dataavailable`,
      POST the blob. Guard with an in-flight flag so requests don't pile up if
      the server is slower than 500ms.
- [ ] **Client-side gate:** compute RMS from an `AnalyserNode`; skip the POST when
      below a silence threshold. Saves most of your requests and stops the UI
      flickering random notes at room noise.
- [ ] **Smoothing:** majority vote over the last 3 predictions before updating the
      big display (this is the unchecked item in your `note_classifier_pipeline.md`
      Phase 5 — do it here). Without it the readout jitters badly.
- [ ] Handle mic-permission denial with a visible message.
- [ ] Note: mic access requires **HTTPS** (or localhost). Your host gives you
      HTTPS free — just don't test over a LAN IP and wonder why it's broken.

---

## Phase 4 — Deploy (½ day)

**Deliverable:** a public URL.

- [ ] `Dockerfile`: `python:3.14-slim` (match your pyenv env), `apt-get install -y ffmpeg`,
      `pip install -r requirements.txt` (use the **CPU-only** torch wheel:
      `--index-url https://download.pytorch.org/whl/cpu` — cuts image from ~2.5GB
      to ~300MB), copy app + model, `CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- [ ] Deploy to Render/Railway/Fly. Free tiers sleep when idle — expect a ~30s
      first request. Fine for MVP; mention it in the UI if you share the link.
- [ ] Set `--workers 1`; the model is tiny but each worker loads its own copy.
- [ ] Post-deploy smoke test: hit `/health`, then run the A4 synthetic test
      against the deployed `/predict`.

---

## Phase 5 — Ship-blockers checklist

- [ ] A4 synthetic test passes **against production**.
- [ ] Real instrument test: play/sing 5 known notes, log actual vs. predicted.
      Write the results down — this is your honest accuracy baseline.
- [ ] Works on your phone (that's the actual use case for a tuner).
- [ ] Mic permission denial doesn't white-screen the page.
- [ ] Silence produces "listening…", not a random note.

---

## Explicitly out of scope for MVP

Accounts · database · payments · saving history · polyphony · analytics ·
sub-100ms latency · offline mode · tuning-cents display (needle)

---

## Stretch goals, in priority order

1. **Cents-off display.** Your classifier gives the *nearest note*, not tuning
   accuracy. Run `librosa.pyin` on the same chunk to get exact f0, compare to the
   predicted note's ideal Hz → "A4, +12 cents". **This is what makes it an actual
   tuner** rather than a note-namer. Highest value-per-effort by a wide margin.
2. **WebSocket streaming** — replace POST-per-chunk with a persistent socket.
   Kills per-request overhead, gets you to a live-feeling readout.
3. **ONNX export** — `torch.onnx.export` the 84→88 MLP, run it in-browser with
   onnxruntime-web. Only removes the *model* from the server; you'd still need
   CQT in JS, which is the hard part. Do this only after (1) and (2).
4. **Mispredict logging** — a "that was wrong, it was actually ___" button writing
   `(features, true_label)` to disk. Free real-world training data. *This is where
   a database first earns its place.*
5. **PWA manifest + service worker** — makes it installable to the home screen.

---

## Rough timeline

| Phase | Time |
|---|---|
| 0 — cleanup | 0.5 day |
| 1 — inference module | 0.5 day |
| 2 — backend | 1 day |
| 3 — frontend | 1–2 days |
| 4 — deploy | 0.5 day |
| **Total** | **~4–5 focused days** |

---

## The one thing most likely to break this

**Train/serve skew.** Your model was trained on NSynth: clean, single-instrument,
isolated notes, 16kHz, trimmed to the 0.5s attack. Browser mic audio is 44.1/48kHz,
room-reverberant, AGC-processed, and arbitrarily windowed. If accuracy craters in
the app while your validation set looks fine, the cause is almost certainly here —
not the model.

Mitigations, in order: disable the browser's audio processing (Phase 3), resample
to exactly 16k server-side, keep preprocessing identical to training (Phase 1),
and keep the A4 synthetic test as your canary.
