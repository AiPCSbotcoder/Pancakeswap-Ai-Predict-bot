"""Tests for the pattern matcher module."""

from __future__ import annotations

import pytest

from src.predictor.pattern_matcher import PatternMatcher, PatternType


class TestPatternMatcher:
    """Test suite for PatternMatcher."""

    def setup_method(self):
        self.matcher = PatternMatcher()

    def test_detect_pump_pattern(self, pump_metrics):
        """Test that a rapid price increase is detected as PUMP."""
        patterns = self.matcher.detect_patterns(pump_metrics)
        pump_patterns = [p for p in patterns if p.pattern_type == PatternType.PUMP]
        assert len(pump_patterns) > 0
        assert pump_patterns[0].confidence > 50

    def test_detect_dump_pattern(self, high_risk_metrics):
        """Test that a rapid price drop is detected as DUMP."""
        patterns = self.matcher.detect_patterns(high_risk_metrics)
        dump_patterns = [p for p in patterns if p.pattern_type == PatternType.DUMP]
        assert len(dump_patterns) > 0

    def test_detect_whale_activity(self, high_risk_metrics):
        """Test whale activity detection when top holders > 50%."""
        patterns = self.matcher.detect_patterns(high_risk_metrics)
        whale_patterns = [p for p in patterns if p.pattern_type == PatternType.WHALE_ENTRY]
        assert len(whale_patterns) > 0

    def test_detect_rug_setup(self, high_risk_metrics):
        """Test rug pull setup detection."""
        patterns = self.matcher.detect_patterns(high_risk_metrics)
        rug_patterns = [p for p in patterns if p.pattern_type == PatternType.RUG_SETUP]
        assert len(rug_patterns) > 0

    def test_normal_metrics_no_extreme_patterns(self, sample_token_metrics):
        """Normal metrics should not trigger extreme patterns."""
        patterns = self.matcher.detect_patterns(sample_token_metrics)
        pump_patterns = [p for p in patterns if p.pattern_type == PatternType.PUMP]
        dump_patterns = [p for p in patterns if p.pattern_type == PatternType.DUMP]
        assert len(pump_patterns) == 0
        assert len(dump_patterns) == 0

    def test_fibonacci_targets(self):
        """Test Fibonacci target calculation."""
        targets = self.matcher.calculate_fib_targets(100.0, 200.0)
        assert targets["fib_0.0"] == 100.0
        assert targets["fib_1.0"] == 200.0
        assert abs(targets["fib_0.5"] - 150.0) < 0.01
        assert abs(targets["fib_0.618"] - 161.8) < 0.01

    def test_patterns_sorted_by_confidence(self, pump_metrics):
        """Patterns should be returned sorted by confidence (descending)."""
        patterns = self.matcher.detect_patterns(pump_metrics)
        if len(patterns) > 1:
            for i in range(len(patterns) - 1):
                assert patterns[i].confidence >= patterns[i + 1].confidence

    def test_history_management(self, sample_token_metrics):
        """Test that history is properly managed and trimmed."""
        for _ in range(600):
            self.matcher.add_metrics(sample_token_metrics)
        history = self.matcher._history.get(sample_token_metrics.address, [])
        assert len(history) <= 500
