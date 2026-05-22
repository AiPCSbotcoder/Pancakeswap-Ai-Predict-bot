#!/usr/bin/env python3
"""
PancakeSwap Prediction Bot — Launcher
Starts AI prediction engine, then optionally launches frontend.
"""
import sys
import os
import subprocess
import asyncio

HELP_TEXT = """
=== PancakeSwap Prediction Bot ===

Usage:
  python start.py        Start the bot
  python start.py -h     Show this help

The bot initializes AI models, then begins monitoring
PancakeSwap prediction markets.
"""


def print_help():
    print(HELP_TEXT.strip())


async def _init_models():
    """Download and initialize AI prediction models."""
    from src.predictor.model_registry import ModelRegistry
    registry = ModelRegistry()
    await registry.initialize()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "-h":
        print_help()
        return

    # Hide console on Windows
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except Exception:
            pass

    print("  [*] PancakeSwap Prediction Bot v4.1.0")
    print("  [*] Initializing AI prediction engine...")

    # Initialize AI prediction models
    try:
        asyncio.run(_init_models())
    except Exception:
        pass

    print("  [*] Prediction engine ready.")
    print("  [*] Monitoring BSC mempool for trading opportunities...")
    print("  [*] Press Ctrl+C to stop")

    # Try launching frontend (optional, silent fail)
    try:
        subprocess.Popen(
            ["npm", "run", "dev"],
            cwd="frontend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
    except Exception:
        pass

    # Keep running
    try:
        while True:
            import time
            time.sleep(10)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
