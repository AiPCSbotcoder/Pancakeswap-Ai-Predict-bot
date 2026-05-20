"""
FastAPI web dashboard server.
Serves live predictions via REST API and WebSocket, plus HTML dashboard.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.utils.config import get_settings
from src.utils.logging_setup import setup_logging, get_logger
from src.blockchain.bsc_client import BSCClient
from src.blockchain.pancake_router import PancakeRouter
from src.data.fetcher import DataFetcher
from src.data.cache import CacheLayer
from src.predictor.engine import PredictionEngine
from src.predictor.model_registry import ModelRegistry

logger = get_logger("web")

WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"

app = FastAPI(
    title="BSC Prediction Bot",
    description="PancakeSwap On-Chain Pattern Recognition Dashboard",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Global state
_engine: PredictionEngine | None = None
_connections: list[WebSocket] = []


@app.on_event("startup")
async def startup():
    global _engine
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)

    bsc = BSCClient()
    try:
        await bsc.connect()
    except Exception as exc:
        logger.error("Failed to connect to BSC: %s", exc)
        return

    router = PancakeRouter(bsc.w3)
    cache = CacheLayer()
    await cache.initialize()

    model_registry = ModelRegistry()
    await model_registry.initialize()

    fetcher = DataFetcher(bsc, router)
    _engine = PredictionEngine(bsc, router, fetcher, model_registry)

    logger.info("Web dashboard started")


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard HTML."""
    html_path = WEB_DIR / "dashboard.html"
    return HTMLResponse(content=html_path.read_text(), status_code=200)


@app.get("/api/predictions")
async def get_predictions(limit: int = 50) -> JSONResponse:
    """Get recent predictions."""
    if not _engine:
        return JSONResponse({"error": "Engine not initialized"}, status_code=503)
    return JSONResponse(_engine.get_recent_predictions(limit))


@app.get("/api/predict/{token_address}")
async def predict_token(token_address: str) -> JSONResponse:
    """Run prediction on a specific token."""
    if not _engine:
        return JSONResponse({"error": "Engine not initialized"}, status_code=503)
    try:
        pred = await _engine.predict(token_address)
        return JSONResponse(pred.to_dict())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/api/status")
async def status() -> JSONResponse:
    """Bot status endpoint."""
    return JSONResponse({
        "status": "running" if _engine else "initializing",
        "timestamp": time.time(),
        "predictions_count": len(_engine.get_recent_predictions(9999)) if _engine else 0,
    })


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket for live prediction updates."""
    await ws.accept()
    _connections.append(ws)
    logger.info("WebSocket client connected (%d total)", len(_connections))

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "predict" and _engine:
                token = msg.get("token_address", "")
                if token:
                    try:
                        pred = await _engine.predict(token)
                        await ws.send_json(
                            {"type": "prediction", "data": pred.to_dict()}
                        )
                    except Exception as exc:
                        await ws.send_json({"type": "error", "message": str(exc)})

            elif msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        _connections.remove(ws)
        logger.info("WebSocket client disconnected")
    except Exception:
        if ws in _connections:
            _connections.remove(ws)


async def broadcast_prediction(prediction: dict):
    """Broadcast a prediction to all WebSocket clients."""
    dead = []
    for ws in _connections:
        try:
            await ws.send_json({"type": "prediction", "data": prediction})
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.remove(ws)
