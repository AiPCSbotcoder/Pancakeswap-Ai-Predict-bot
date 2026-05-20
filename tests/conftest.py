"""Test fixtures and configuration."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_token_metrics():
    """Sample token metrics for testing."""
    from src.data.fetcher import TokenMetrics
    return TokenMetrics(
        address="0x1234567890abcdef1234567890abcdef12345678",
        symbol="TEST",
        name="Test Token",
        price_bnb=0.0001,
        liquidity_bnb=10.5,
        holder_count=50,
        top_holder_pct=35.0,
        price_change_5m=5.0,
        price_change_1h=15.0,
        buy_count=10,
        sell_count=3,
    )


@pytest.fixture
def high_risk_metrics():
    """Token metrics indicating high risk."""
    from src.data.fetcher import TokenMetrics
    return TokenMetrics(
        address="0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        symbol="SCAM",
        name="Scam Token",
        price_bnb=0.000001,
        liquidity_bnb=0.3,
        holder_count=5,
        top_holder_pct=95.0,
        price_change_5m=-30.0,
        price_change_1h=-60.0,
        buy_count=0,
        sell_count=15,
    )


@pytest.fixture
def pump_metrics():
    """Token metrics indicating a pump."""
    from src.data.fetcher import TokenMetrics
    return TokenMetrics(
        address="0xaabbccddaabbccddaabbccddaabbccddaabbccdd",
        symbol="PUMP",
        name="Pump Token",
        price_bnb=0.001,
        liquidity_bnb=50.0,
        holder_count=200,
        top_holder_pct=20.0,
        price_change_5m=45.0,
        price_change_1h=120.0,
        buy_count=50,
        sell_count=2,
    )
