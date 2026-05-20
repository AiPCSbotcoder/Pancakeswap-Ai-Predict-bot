"""
Pair scanner - scans for new LP pairs on PancakeSwap.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from src.blockchain.bsc_client import BSCClient
from src.blockchain.pancake_router import PancakeRouter, WBNB_ADDRESS
from src.utils.logging_setup import get_logger

logger = get_logger("pair_scanner")


class PairScanner:
    """Scans PancakeSwap for new LP pairs and analyzes them."""

    def __init__(self, bsc: BSCClient, router: PancakeRouter) -> None:
        self._bsc = bsc
        self._router = router
        self._last_pair_index: int = 0
        self._known_pairs: set[str] = set()

    async def initialize(self) -> None:
        total = await self._router.get_total_pairs()
        self._last_pair_index = total
        logger.info("Pair scanner initialized. Total pairs: %d", total)

    async def scan_new_pairs(self, lookback: int = 20) -> list[dict[str, Any]]:
        total = await self._router.get_total_pairs()
        start = max(self._last_pair_index, total - lookback)
        new_pairs = []

        for i in range(start, total):
            try:
                pair_addr = await self._router.get_pair_by_index(i)
                if pair_addr in self._known_pairs:
                    continue

                reserves = await self._router.get_reserves(pair_addr)
                token0_info = await self._bsc.get_token_info(reserves["token0"])
                token1_info = await self._bsc.get_token_info(reserves["token1"])

                wbnb = WBNB_ADDRESS.lower()
                is_bnb_pair = (
                    reserves["token0"].lower() == wbnb
                    or reserves["token1"].lower() == wbnb
                )

                if is_bnb_pair:
                    if reserves["token0"].lower() == wbnb:
                        bnb_reserve = reserves["reserve0"]
                        token_info = token1_info
                    else:
                        bnb_reserve = reserves["reserve1"]
                        token_info = token0_info
                    liquidity_bnb = float(self._bsc.w3.from_wei(bnb_reserve, "ether"))
                else:
                    liquidity_bnb = 0.0
                    token_info = token0_info

                pair_data = {
                    "index": i,
                    "pair_address": pair_addr,
                    "token0": token0_info,
                    "token1": token1_info,
                    "is_bnb_pair": is_bnb_pair,
                    "liquidity_bnb": liquidity_bnb,
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                }

                new_pairs.append(pair_data)
                self._known_pairs.add(pair_addr)
                logger.info(
                    "New pair: %s/%s | Liq: %.2f BNB",
                    token0_info["symbol"],
                    token1_info["symbol"],
                    liquidity_bnb,
                )
            except Exception as exc:
                logger.warning("Error scanning pair #%d: %s", i, exc)
                continue

        self._last_pair_index = total
        return new_pairs

    async def continuous_scan(
        self, interval: int = 10, callback=None
    ) -> None:
        logger.info("Starting continuous pair scanning (every %ds)...", interval)
        while True:
            try:
                new_pairs = await self.scan_new_pairs(lookback=5)
                if new_pairs and callback:
                    for pair in new_pairs:
                        await callback(pair)
            except Exception as exc:
                logger.error("Scan cycle error: %s", exc)
            await asyncio.sleep(interval)
