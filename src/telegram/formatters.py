"""
Telegram message formatters for prediction alerts.
"""

from __future__ import annotations

from typing import Any


DIRECTION_EMOJI = {
    "BULLISH": "🟢",
    "BEARISH": "🔴",
    "NEUTRAL": "⚪",
}

ALERT_EMOJI = {
    "INFO": "ℹ️",
    "SIGNAL": "📊",
    "URGENT": "🚨",
}

RISK_EMOJI = {
    "LOW": "🟢",
    "MEDIUM": "🟡",
    "HIGH": "🟠",
    "CRITICAL": "🔴",
    "UNKNOWN": "⚪",
}


def format_prediction_alert(prediction: dict[str, Any]) -> str:
    """Format a prediction into a Telegram message."""
    direction = prediction.get("direction", "NEUTRAL")
    alert_level = prediction.get("alert_level", "INFO")
    risk_level = prediction.get("risk_level", "UNKNOWN")

    d_emoji = DIRECTION_EMOJI.get(direction, "⚪")
    a_emoji = ALERT_EMOJI.get(alert_level, "ℹ️")
    r_emoji = RISK_EMOJI.get(risk_level, "⚪")

    lines = [
        f"{a_emoji} <b>BSC Prediction Alert</b> {a_emoji}",
        "",
        f"🪙 <b>Token:</b> {prediction.get('token_symbol', '???')}",
        f"📍 <code>{prediction.get('token_address', '')}</code>",
        "",
        f"{d_emoji} <b>Direction:</b> {direction}",
        f"🎯 <b>Confidence:</b> {prediction.get('confidence', 0):.0f}%",
        f"⏱ <b>Time Window:</b> {prediction.get('time_window', 'N/A')}",
        "",
        f"💰 <b>Price:</b> {prediction.get('price_bnb', 0):.10f} BNB",
    ]

    if prediction.get("target_price"):
        lines.append(f"🎯 <b>Target:</b> {prediction['target_price']:.10f} BNB")
    if prediction.get("stop_loss"):
        lines.append(f"🛑 <b>Stop Loss:</b> {prediction['stop_loss']:.10f} BNB")

    lines.extend([
        "",
        f"{r_emoji} <b>Risk:</b> {risk_level} ({prediction.get('risk_score', 'N/A')}/100)",
    ])

    patterns = prediction.get("patterns", [])
    if patterns:
        lines.append("")
        lines.append("📋 <b>Patterns:</b>")
        for p in patterns[:5]:
            lines.append(f"  • {p['type']}: {p['details']}")

    reasoning = prediction.get("reasoning", [])
    if reasoning:
        lines.append("")
        lines.append("💡 <b>Reasoning:</b>")
        for r in reasoning[:5]:
            lines.append(f"  • {r}")

    lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━",
        f"<a href='https://bscscan.com/token/{prediction.get('token_address', '')}'>BSCScan</a> | "
        f"<a href='https://poocoin.app/tokens/{prediction.get('token_address', '')}'>PooCoin</a>",
    ])

    return "\n".join(lines)


def format_scan_summary(pairs: list[dict[str, Any]]) -> str:
    """Format a scan summary message."""
    if not pairs:
        return "🔍 <b>Scan Complete</b>\n\nNo new pairs found."

    lines = [
        f"🔍 <b>Scan Complete</b> - {len(pairs)} new pairs found",
        "",
    ]

    for pair in pairs[:10]:
        t0 = pair.get("token0", {})
        t1 = pair.get("token1", {})
        liq = pair.get("liquidity_bnb", 0)
        lines.append(
            f"• {t0.get('symbol', '?')}/{t1.get('symbol', '?')} "
            f"| Liq: {liq:.2f} BNB"
        )

    if len(pairs) > 10:
        lines.append(f"\n... and {len(pairs) - 10} more")

    return "\n".join(lines)
