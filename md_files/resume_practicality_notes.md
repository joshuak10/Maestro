# Note Classifier Project — Resume Practicality Notes

**Context:** This is an undergraduate resume project (real-time note classification
pipeline: synthetic dataset → CQT feature extraction → PyTorch classifier →
real-time inference). Question: does the ML model need to be more *practical*
than a simple frequency-to-note conversion to be worth it?

---

## Short answer

For a resume project, practicality in the "does this need to beat argmax in
production" sense matters far less than what the project demonstrates you can
do. What matters is the pipeline, the engineering judgment, and the ability to
explain tradeoffs — not squeezing out a few extra points of accuracy.

---

## What actually reads well on a resume / in an interview

1. **The full pipeline, not just the model.**
   Signal processing (CQT feature extraction), synthetic data generation with
   deliberate variation (noise, harmonics, duration), a proper train/val split
   strategy that avoids leakage, a PyTorch training loop, and (if reached)
   real-time inference — this is a legitimate end-to-end ML systems project.
   That breadth is more attractive to a reviewer than whether the neural net
   beat a one-liner.

2. **Showing you understand when ML *isn't* the right tool is a strength, not
   an admission of failure.**
   Building both the classifier and a trivial baseline (argmax on the CQT
   vector, or `librosa.pyin` direct pitch tracking), then writing up "here's
   where the model adds value (noisy/inharmonic input) and here's where a
   simple rule is just as good (clean sine tones)" — is more sophisticated
   than a project that only reports a single accuracy number. Interviewers
   notice when someone benchmarks against a trivial baseline instead of
   jumping straight to "98% accuracy."

3. **It's a talking-point generator.**
   "I built a note classifier and benchmarked it against direct pitch
   detection, and found the ML approach won under noise but not on clean
   audio" is a strong, specific answer to "tell me about a project" — much
   better than a vague "I built an ML model that does X."

## What doesn't matter much

Whether the model beats argmax by 2% or 20% won't move the needle on a
resume. No one will ask for a precision-recall curve. What they *will* ask is
"why did you choose this approach" and "what did you learn" — having the
comparison already done means answering crisply instead of guessing on the
spot.

## Practical recommendation

- Don't drop the ML pipeline — finish it. Most of the resume value comes from
  feature engineering, dataset design, training pipeline, and evaluation.
- Also build the trivial baseline (`argmax(cqt_mean)` or `librosa.pyin`) and
  explicitly compare it to the trained model in the README/writeup.
- State clearly:
  - **Clean synthetic data:** model should roughly *match* argmax (near
    100% is the actual success condition — beating it here would be a red
    flag, e.g. overfitting or a label leak).
  - **Noisy / high harmonic-variance data:** model should *beat* argmax,
    or the added complexity isn't earning its keep.
  - **Real instrument data (Phase 4):** model should *clearly beat* the
    naive baseline — this is the strongest test of whether the ML approach
    was worth building at all.

This comparison, plus an honest conclusion about when each approach wins, is
arguably more impressive than the classifier alone — it demonstrates
engineering judgment, not just "I trained a model."
