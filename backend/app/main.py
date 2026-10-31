"""GapScope API (FastAPI). Serves the static frontend from the same
service, so one repo = one deploy (Render, single web service).

Endpoints:
  GET  /api/templates       decision templates
  POST /api/analyze         run the full pipeline (spec section 4)
  GET  /api/demo-session    cached demo analysis input for reliable demos
  POST /api/discover        web search + fetch for a question
  GET  /                       the frontend
Env: GEMINI_API_KEY (optional; without it the rule-based extractor runs,
so the demo never depends on a live LLM call).
TAVILY_API_KEY (optional; without it /api/discover reports that web
search is not configured, and the paste flow still works).
"""
import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import discover as discover_mod
from .discover import DiscoverNotConfigured, SearchFailed
from .engine import analyze
from .models import (AnalysisRequest, AnalysisResult, DiscoverRequest,
                     DiscoverResponse)
from .templates import TEMPLATES

BASE = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE / "frontend"

app = FastAPI(title="GapScope")


@app.get("/api/templates")
def list_templates():
    return {k: v.model_dump() for k, v in TEMPLATES.items()}


@app.post("/api/analyze", response_model=AnalysisResult)
def analyze_endpoint(req: AnalysisRequest):
    return analyze(req)


@app.post("/api/discover", response_model=DiscoverResponse)
def discover_endpoint(req: DiscoverRequest):
    try:
        result = discover_mod.discover(req.question,
                                       max_results=req.max_results)
    except DiscoverNotConfigured as exc:
        return JSONResponse({"detail": str(exc)}, status_code=503)
    except SearchFailed as exc:
        return JSONResponse({"detail": str(exc)}, status_code=502)
    return DiscoverResponse(**result)


@app.get("/api/demo-session")
def demo_session():
    path = BASE / "demo_session.json"
    if path.exists():
        return JSONResponse(json.loads(path.read_text(encoding="utf-8")))
    return JSONResponse({"detail": "no demo session yet"}, status_code=404)


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True),
                name="frontend")
