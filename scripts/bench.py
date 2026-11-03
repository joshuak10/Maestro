"""
Measure prediction latency locally (predict() in-process) and/or through the server.


"""
import argparse
import json
import os
import sys
import time
import urllib.request

import librosa
import numpy as np

# run from the repo root: `python scripts/bench.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SR = 16000
DURATION = 2048 / SR # same window the frontend sends (WINDOW in pcm-processor.js)


def stats(name, ms):
    ms = np.asarray(ms)
    print(f"  {name:<22} median {np.median(ms):7.2f} ms   p95 {np.percentile(ms, 95):7.2f} ms   max {ms.max():7.2f} ms")


def bench_local(y, n):
    import torch
    t0 = time.perf_counter()
    from app.inference import predict, preprocess, model #model loads on import
    load = (time.perf_counter() - t0) * 1e3

    t0 = time.perf_counter()
    predict(y, SR) #first call pays for librosa/numba compilation
    cold = (time.perf_counter() - t0) * 1e3

    pre, fwd, total = [], [], []
    for _ in range(n):
        t0 = time.perf_counter()
        x = preprocess(y, sr=SR)
        t1 = time.perf_counter()
        if x is not None:
            with torch.no_grad():
                model(x).softmax(1)
        t2 = time.perf_counter()
        pre.append((t1 - t0) * 1e3)
        fwd.append((t2 - t1) * 1e3)

        t0 = time.perf_counter()
        res = predict(y, SR)
        total.append((time.perf_counter() - t0) * 1e3)

    print(f"\nLOCAL  (n={n}, top: {res[0]['note'] if res else 'none (silent)'})")
    print(f"  {'model load':<22} {load:7.0f} ms")
    print(f"  {'first predict (cold)':<22} {cold:7.0f} ms")
    stats("preprocess", pre)
    stats("model forward", fwd)
    stats("predict()", total)


def bench_server(y, n, url):
    body = y.astype(np.float32).tobytes()

    def post():
        req = urllib.request.Request(f"{url}/predict?sr={SR}", data=body, method="POST")
        t0 = time.perf_counter()
        with urllib.request.urlopen(req) as r:
            out = json.load(r)
            timing = r.headers.get("Server-Timing", "")
        rt = (time.perf_counter() - t0) * 1e3
        server = float(timing.split("dur=")[1]) if "dur=" in timing else float("nan")
        return rt, server, out

    try:
        for _ in range(5): #warm up the connection path
            post()
    except OSError as e:
        print(f"\nSERVER  could not reach {url} ({e}). Start it with: uvicorn app.main:app")
        return

    rts, servers = [], []
    for _ in range(n):
        rt, server, out = post()
        rts.append(rt)
        servers.append(server)

    preds = out["predictions"]
    print(f"\nSERVER  {url}  (n={n}, top: {preds[0]['note'] if preds else 'none (silent)'})")
    stats("predict() on server", servers)
    stats("round trip", rts)
    stats("overhead (rt - pred)", np.array(rts) - np.array(servers))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["local", "server", "both"], default="both")
    ap.add_argument("--file", default="audio_files/A_1.wav")
    ap.add_argument("--offset", type=float, default=0.0, help="seconds into the file to start the chunk")
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("-n", type=int, default=200)
    args = ap.parse_args()

    y, _ = librosa.load(args.file, sr=SR, offset=args.offset, duration=DURATION)
    print(f"input: {args.file} @ {args.offset}s, {len(y)} samples")

    if args.mode in ("local", "both"):
        bench_local(y, args.n)
    if args.mode in ("server", "both"):
        bench_server(y, args.n, args.url)


if __name__ == "__main__":
    main()
