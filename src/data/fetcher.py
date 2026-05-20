"""
Price, volume, and liquidity data fetcher.
Aggregates data from on-chain and external sources.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from src.blockchain.bsc_client import BSCClient
from src.blockchain.pancake_router import PancakeRouter
from src.utils.logging_setup import get_logger

logger = get_logger("fetcher")


@dataclass
class TokenMetrics:
    """Aggregated token metrics snapshot."""
    address: str
    symbol: str
    name: str
    price_bnb: float = 0.0
    liquidity_bnb: float = 0.0
    volume_24h: float = 0.0
    holder_count: int = 0
    top_holder_pct: float = 0.0
    price_change_5m: float = 0.0
    price_change_1h: float = 0.0
    buy_count: int = 0
    sell_count: int = 0
    timestamp: float = field(default_factory=time.time)


class DataFetcher:
    """Fetches and aggregates token market data."""

    def __init__(self, bsc: BSCClient, router: PancakeRouter) -> None:
        self._bsc = bsc
        self._router = router
        self._price_history: dict[str, list[tuple[float, float]]] = {}

    async def get_token_metrics(self, token_address: str) -> TokenMetrics:
        token_info = await self._bsc.get_token_info(token_address)
        price_bnb = await self._router.get_token_price_bnb(token_address)
        liquidity = await self._router.get_liquidity_bnb(token_address)
        holders = await self._bsc.get_top_holders(token_address, limit=10)

        top_pct = 0.0
        if holders and token_info["total_supply"] > 0:
            for h in holders[:10]:
                bal = float(h.get("TokenHolderQuantity", 0))
                top_pct += (bal / token_info["total_supply"]) * 100

        now = time.time()
        if token_address not in self._price_history:
            self._price_history[token_address] = []
        self._price_history[token_address].append((now, price_bnb))
        hist = self._price_history[token_address]
        if len(hist) > 1000:
            self._price_history[token_address] = hist[-500:]

        change_5m = self._calc_change(hist, 300)
        change_1h = self._calc_change(hist, 3600)

        return TokenMetrics(
            address=token_address,
            symbol=token_info["symbol"],
            name=token_info["name"],
            price_bnb=price_bnb,
            liquidity_bnb=liquidity,
            holder_count=len(holders),
            top_holder_pct=top_pct,
            price_change_5m=change_5m,
            price_change_1h=change_1h,
            timestamp=now,
        )

    def _calc_change(
        self, history: list[tuple[float, float]], seconds: int
    ) -> float:
        if len(history) < 2:
            return 0.0
        now = time.time()
        cutoff = now - seconds
        old_prices = [p for t, p in history if t <= cutoff]
        if not old_prices:
            old_price = history[0][1]
        else:
            old_price = old_prices[-1]
        current = history[-1][1]
        if old_price == 0:
            return 0.0
        return ((current - old_price) / old_price) * 100

    async def get_price_history(
        self, token_address: str
    ) -> list[tuple[float, float]]:
        return self._price_history.get(token_address, [])
