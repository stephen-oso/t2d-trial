import json
import logging
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
from api.models import (
    MatchRequest, MatchResponse, TrialSummary,
    HealthResponse, MetricsResponse
)
from matching.agent import run_match

app = FastAPI(title="T2D Trial Pre-Screener", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory metrics — resets on server restart
_metrics = {
    "total_requests": 0,
    "successful_requests": 0,
    "error_count": 0,
    "total_latency_ms": 0.0,
}


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="healthy", model="claude-haiku-4-5-20251001")


@app.get("/trials", response_model=list[TrialSummary])
def list_trials():
    trials_dir = Path("data/trials")
    summaries = []
    for f in sorted(trials_dir.glob("*.json")):
        data = json.loads(f.read_text())
        summaries.append(TrialSummary(
            trial_id=data["trial_id"],
            title=data["title"],
        ))
    return summaries


@app.post("/match", response_model=MatchResponse)
def match(request: MatchRequest):
    _metrics["total_requests"] += 1
    start = time.time()
    try:
        result = run_match(request.note)
        _metrics["successful_requests"] += 1
        _metrics["total_latency_ms"] += (time.time() - start) * 1000
        return MatchResponse(**result)
    except Exception as e:
        _metrics["error_count"] += 1
        logging.exception("run_match failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics", response_model=MetricsResponse)
def metrics():
    avg_latency = (
        _metrics["total_latency_ms"] / _metrics["successful_requests"]
        if _metrics["successful_requests"] > 0 else 0.0
    )
    return MetricsResponse(
        total_requests=_metrics["total_requests"],
        successful_requests=_metrics["successful_requests"],
        error_count=_metrics["error_count"],
        avg_latency_ms=round(avg_latency, 1),
    )
