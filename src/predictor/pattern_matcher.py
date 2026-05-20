"""
Pattern matcher - detects known pump, dump, accumulation, and sandwich patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from src.data.fetcher import TokenMetrics
from src.utils.logging_setup import get_logger

logger = get_logger("pattern_matcher")


class PatternType(str, Enum):
    PUMP = "PUMP"
    DUMP = "DUMP"
    ACCUMULATION = "ACCUMULATION"
    SANDWICH = "SANDWICH"
    WHALE_ENTRY = "WHALE_ENTRY"
    WHALE_EXIT = "WHALE_EXIT"
    ORGANIC_GROWTH = "ORGANIC_GROWTH"
    RUG_SETUP = "RUG_SETUP"


@dataclass
class PatternMatch:
    """A detected pattern with confidence."""
    pattern_type: PatternType
    confidence: float  # 0-100
    details: str
    indicators: dict[str, Any]


class PatternMatcher:
    """Detects known on-chain trading patterns."""

    # Fibonacci levels for price targets
    FIB_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.618, 2.618]

    def __init__(self) -> None:
        self._history: dict[str, list[TokenMetrics]] = {}

    def add_metrics(self, metrics: TokenMetrics) -> None:
        addr = metrics.address
        if addr not in self._history:
            self._history[addr] = []
        self._history[addr].append(metrics)
        if len(self._history[addr]) > 500:
            self._history[addr] = self._history[addr][-250:]

    def detect_patterns(self, metrics: TokenMetrics) -> list[PatternMatch]:
        patterns = []
        self.add_metrics(metrics)

        patterns.extend(self._check_pump_pattern(metrics))
        patterns.extend(self._check_accumulation(metrics))
        patterns.extend(self._check_whale_activity(metrics))
        patterns.extend(self._check_rug_setup(metrics))

        return sorted(patterns, key=lambda p: p.confidence, reverse=True)

    def _check_pump_pattern(self, m: TokenMetrics) -> list[PatternMatch]:
        results = []
        if m.price_change_5m > 20:
            conf = min(95, 40 + m.price_change_5m)
            results.append(PatternMatch(
                pattern_type=PatternType.PUMP,
                confidence=conf,
                details=f"Rapid price increase: {m.price_change_5m:.1f}% in 5min",
                indicators={
                    "price_change_5m": m.price_change_5m,
                    "liquidity_bnb": m.liquidity_bnb,
                },
            ))
        if m.price_change_5m < -20:
            conf = min(95, 40 + abs(m.price_change_5m))
            results.append(PatternMatch(
                pattern_type=PatternType.DUMP,
                confidence=conf,
                details=f"Sharp price drop: {m.price_change_5m:.1f}% in 5min",
                indicators={
                    "price_change_5m": m.price_change_5m,
                    "liquidity_bnb": m.liquidity_bnb,
                },
            ))
        return results

    def _check_accumulation(self, m: TokenMetrics) -> list[PatternMatch]:
        results = []
        history = self._history.get(m.address, [])
        if len(history) < 5:
            return results

        recent = history[-5:]
        buy_counts = [h.buy_count for h in recent]
        if all(b > 0 for b in buy_counts):
            avg_buys = np.mean(buy_counts)
            if avg_buys > 3:
                results.append(PatternMatch(
                    pattern_type=PatternType.ACCUMULATION,
                    confidence=min(85, 30 + avg_buys * 5),
                    details=f"Consistent buying pattern detected (avg {avg_buys:.0f} buys/period)",
                    indicators={"avg_buys": avg_buys, "periods": 5},
                ))
        return results

    def _check_whale_activity(self, m: TokenMetrics) -> list[PatternMatch]:
        results = []
        if m.top_holder_pct > 50:
            results.append(PatternMatch(
                pattern_type=PatternType.WHALE_ENTRY,
                confidence=min(90, m.top_holder_pct),
                details=f"Top 10 holders control {m.top_holder_pct:.1f}% of supply",
                indicators={"top_holder_pct": m.top_holder_pct},
            ))
        return results

    def _check_rug_setup(self, m: TokenMetrics) -> list[PatternMatch]:
        results = []
        if m.liquidity_bnb < 1.0 and m.top_holder_pct > 80:
            results.append(PatternMatch(
                pattern_type=PatternType.RUG_SETUP,
                confidence=85,
                details="Low liquidity + high holder concentration = potential rug",
                indicators={
                    "liquidity_bnb": m.liquidity_bnb,
                    "top_holder_pct": m.top_holder_pct,
                },
            ))
        return results

    def calculate_fib_targets(
        self, low: float, high: float
    ) -> dict[str, float]:
        diff = high - low
        return {
            f"fib_{level}": low + diff * level
            for level in self.FIB_LEVELS
        }
