"""
Mempool monitor for BSC pending transactions.
WebSocket connection to BSC node for real-time tx stream.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Optional

import websockets

from src.utils.config import get_settings
from src.utils.logging_setup import get_logger

logger = get_logger("mempool")

PANCAKE_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E".lower()

SWAP_SIGNATURES = {
    "0x38ed1739": "swapExactTokensForTokens",
    "0x7ff36ab5": "swapExactETHForTokens",
    "0x18cbafe5": "swapExactTokensForETH",
    "0xfb3bdb41": "swapETHForExactTokens",
    "0x4a25d94a": "swapTokensForExactETH",
    "0x8803dbee": "swapTokensForExactTokens",
}


class MempoolMonitor:
    """Monitor BSC mempool for PancakeSwap-related pending transactions."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._ws: Optional[Any] = None
        self._running = False
        self._callbacks: list[Callable] = []
        self._stats = {"total_seen": 0, "pancake_txs": 0, "large_txs": 0}

    def on_transaction(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    async def start(self) -> None:
        self._running = True
        logger.info("Starting mempool monitor on %s", self._settings.bsc_ws_url)

        while self._running:
            try:
                async with websockets.connect(
                    self._settings.bsc_ws_url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    sub = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_subscribe",
                        "params": ["newPendingTransactions"],
                    }
                    await ws.send(json.dumps(sub))
                    resp = await ws.recv()
                    logger.info("Subscribed to pending txs: %s", resp)

                    async for message in ws:
                        if not self._running:
                            break
                        try:
                            data = json.loads(message)
                            tx_hash = data.get("params", {}).get("result")
                            if tx_hash:
                                self._stats["total_seen"] += 1
                                await self._process_tx(tx_hash)
                        except json.JSONDecodeError:
                            continue

            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket closed, reconnecting in 5s...")
                await asyncio.sleep(5)
            except Exception as exc:
                logger.error("Mempool monitor error: %s", exc)
                await asyncio.sleep(10)

    async def _process_tx(self, tx_hash: str) -> None:
        pass  # In production, fetch tx details and filter

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
        logger.info("Mempool monitor stopped. Stats: %s", self._stats)

    def get_stats(self) -> dict:
        return self._stats.copy()
