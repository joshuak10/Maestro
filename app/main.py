from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
import numpy as np
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from app.inference import predict

#html vs main.py server (are they separate?)

MIN_CONF = 0.5

app = FastAPI()

#Add multiple local hosts so API can communicate between them
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins= origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API health checker required
@app.get("/health")
def health_check():
    return {"status": "ok", "model": "nsynth"}

# API prediction call
@app.post("/predict")
async def predict_endpoint(request: Request, sr: int = 16000): #request because audio sample is a non-trivial data type
    if sr != 16000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail = "Sampling Rate must be 16000")

    body = await request.body() #take in the rawbye data
    if len(body) > 40000: #0.5 secs of 16khz audio should be 16k
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail = f"byte count: {len(body)} too high")

    try:
        y = np.frombuffer(body, dtype=np.float32) #raw byte arra, make it mutable, check for length, and NaN values
    except:
        raise HTTPException(400, f"malformed PCM body")
    y = y.copy()

    if y.size == 0:
        raise HTTPException(400, "empty body")
    if np.any(~np.isfinite(y)):
        raise HTTPException(400, "contains non-finite samples")

    predictions = await run_in_threadpool(predict, y, sr)
    low_confidence = True if not predictions else predictions[0]["confidence"] < MIN_CONF
    return {"predictions": predictions, "low_confidence": low_confidence}

_dist = Path(__file__).resolve().parent.parent / "web" / "dist" #strip two dirs, go to /web/dist
if _dist.is_dir():
    app.mount("/", StaticFiles(directory =_dist, html=True), name="static")