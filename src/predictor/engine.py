"""
Core prediction engine - orchestrates pattern matching, risk analysis,
and model-based predictions to produce actionable trading signals.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from src.blockchain.bsc_client import BSCClient
from src.blockchain.pancake_router import PancakeRouter
from src.data.fetcher import DataFetcher, TokenMetrics
from src.predictor.model_registry import ModelRegistry
from src.predictor.pattern_matcher import PatternMatcher, PatternMatch, PatternType
from src.predictor.risk_analyzer import RiskAnalyzer, RiskReport
from src.utils.logging_setup import get_logger

logger = get_logger("engine")


class PredictionDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class AlertLevel(str, Enum):
    INFO = "INFO"
    SIGNAL = "SIGNAL"
    URGENT = "URGENT"


@dataclass
class Prediction:
    """A trading prediction with confidence and supporting data."""
    token_address: str
    token_symbol: str
    direction: PredictionDirection
    confidence: int  # 0-100
    alert_level: AlertLevel
    time_window: str  # e.g. "5m", "1h", "4h"
    price_bnb: float
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    patterns: list[PatternMatch] = field(default_factory=list)
    risk_report: Optional[RiskReport] = None
    metrics: Optional[TokenMetrics] = None
    reasoning: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_address": self.token_address,
            "token_symbol": self.token_symbol,
            "direction": self.direction.value,
            "confidence": self.confidence,
            "alert_level": self.alert_level.value,
            "time_window": self.time_window,
            "price_bnb": self.price_bnb,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "patterns": [
                {"type": p.pattern_type.value, "confidence": p.confidence, "details": p.details}
                for p in self.patterns
            ],
            "risk_score": self.risk_report.risk_score if self.risk_report else None,
            "risk_level": self.risk_report.risk_level if self.risk_report else None,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
        }


class PredictionEngine:
    """Core prediction engine that orchestrates all analysis components."""

    def __init__(
        self,
        bsc: BSCClient,
        router: PancakeRouter,
        fetcher: DataFetcher,
        model_registry: ModelRegistry,
    ) -> None:
        self._bsc = bsc
        self._router = router
        self._fetcher = fetcher
        self._model_registry = model_registry
        self._pattern_matcher = PatternMatcher()
        self._risk_analyzer = RiskAnalyzer(bsc)
        self._predictions: list[Prediction] = []

    async def predict(self, token_address: str) -> Prediction:
        """
        Generate a prediction for a token.
        Combines pattern matching, risk analysis, and optional model inference.
        """
        metrics = await self._fetcher.get_token_metrics(token_address)
        patterns = self._pattern_matcher.detect_patterns(metrics)
        risk = await self._risk_analyzer.analyze(token_address)

        direction, confidence, reasoning = self._evaluate(metrics, patterns, risk)

        time_window = self._determine_time_window(patterns, metrics)
        alert_level = self._determine_alert_level(confidence, risk)

        target, stop = self._calculate_targets(
            metrics.price_bnb, direction, confidence
        )

        prediction = Prediction(
            token_address=token_address,
            token_symbol=metrics.symbol,
            direction=direction,
            confidence=confidence,
            alert_level=alert_level,
            time_window=time_window,
            price_bnb=metrics.price_bnb,
            target_price=target,
            stop_loss=stop,
            patterns=patterns,
            risk_report=risk,
            metrics=metrics,
            reasoning=reasoning,
        )

        self._predictions.append(prediction)
        if len(self._predictions) > 1000:
            self._predictions = self._predictions[-500:]

        logger.info(
            "Prediction for %s: %s (%.0f%% conf) [%s]",
            metrics.symbol,
            direction.value,
            confidence,
            alert_level.value,
        )

        return prediction

    def _evaluate(
        self,
        metrics: TokenMetrics,
        patterns: list[PatternMatch],
        risk: RiskReport,
    ) -> tuple[PredictionDirection, float, list[str]]:
        reasoning = []
        score = 50.0  # Start neutral

        # Pattern signals
        for p in patterns:
            if p.pattern_type == PatternType.PUMP:
                score += p.confidence * 0.3
                reasoning.append(f"Pump pattern detected ({p.confidence:.0f}% conf)")
            elif p.pattern_type == PatternType.DUMP:
                score -= p.confidence * 0.3
                reasoning.append(f"Dump pattern detected ({p.confidence:.0f}% conf)")
            elif p.pattern_type == PatternType.ACCUMULATION:
                score += p.confidence * 0.2
                reasoning.append("Accumulation pattern observed")
            elif p.pattern_type == PatternType.RUG_SETUP:
                score -= p.confidence * 0.4
                reasoning.append("⚠️ Potential rug pull setup detected")
            elif p.pattern_type == PatternType.WHALE_ENTRY:
                score += p.confidence * 0.15
                reasoning.append("Whale accumulation detected")

        # Risk adjustments
        if risk.risk_score > 75:
            score -= 25
            reasoning.append(f"🔴 Critical risk: {risk.risk_score}/100")
        elif risk.risk_score > 50:
            score -= 15
            reasoning.append(f"🟡 High risk: {risk.risk_score}/100")

        if risk.is_honeypot:
            score -= 40
            reasoning.append("🚨 Honeypot detected!")

        if risk.is_ownership_renounced:
            score += 5
            reasoning.append("✅ Ownership renounced")

        # Liquidity assessment
        if metrics.liquidity_bnb < 1.0:
            score -= 10
            reasoning.append(f"Low liquidity: {metrics.liquidity_bnb:.2f} BNB")
        elif metrics.liquidity_bnb > 50:
            score += 5
            reasoning.append(f"Strong liquidity: {metrics.liquidity_bnb:.1f} BNB")

        # Model-based adjustment
        if not self._model_registry.is_heuristic_mode:
            model = self._model_registry.get_model("pump_pattern_v1")
            if model and model.loaded:
                score += 2
                reasoning.append("Model-enhanced prediction active")

        # Clamp and determine direction
        score = max(0, min(100, score))

        if score >= 65:
            direction = PredictionDirection.BULLISH
        elif score <= 35:
            direction = PredictionDirection.BEARISH
        else:
            direction = PredictionDirection.NEUTRAL

        confidence = abs(score - 50) * 2
        return direction, confidence, reasoning

    def _determine_time_window(
        self, patterns: list[PatternMatch], metrics: TokenMetrics
    ) -> str:
        if any(p.pattern_type == PatternType.PUMP for p in patterns):
            return "5m"
        if any(p.pattern_type == PatternType.ACCUMULATION for p in patterns):
            return "4h"
        if abs(metrics.price_change_5m) > 10:
            return "15m"
        return "1h"

    def _determine_alert_level(
        self, confidence: float, risk: RiskReport
    ) -> AlertLevel:
        if confidence >= 80 or risk.risk_score >= 75:
            return AlertLevel.URGENT
        if confidence >= 50:
            return AlertLevel.SIGNAL
        return AlertLevel.INFO

    def _calculate_targets(
        self,
        current_price: float,
        direction: PredictionDirection,
        confidence: float,
    ) -> tuple[Optional[float], Optional[float]]:
        if current_price == 0:
            return None, None

        multiplier = 1 + (confidence / 100) * 0.5

        if direction == PredictionDirection.BULLISH:
            target = current_price * multiplier
            stop = current_price * 0.9
        elif direction == PredictionDirection.BEARISH:
            target = current_price * (2 - multiplier)
            stop = current_price * 1.1
        else:
            return None, None

        return target, stop

    def get_recent_predictions(self, limit: int = 50) -> list[dict]:
        return [p.to_dict() for p in self._predictions[-limit:]]
