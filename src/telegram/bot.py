"""
Telegram alert bot for sending real-time prediction alerts.
Supports rate limiting, alert level filtering, and rich formatting.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from src.utils.config import get_settings
from src.utils.logging_setup import get_logger
from src.telegram.formatters import format_prediction_alert, format_scan_summary

logger = get_logger("telegram_bot")


class TelegramAlertBot:
    """Sends prediction alerts to Telegram with rate limiting."""

    ALERT_LEVELS = {"INFO": 0, "SIGNAL": 1, "URGENT": 2}

    def __init__(self) -> None:
        self._settings = get_settings()
        self._last_alert_times: dict[str, float] = {}
        self._bot = None
        self._enabled = False

    async def initialize(self) -> None:
        """Initialize the Telegram bot."""
        if not self._settings.telegram_bot_token:
            logger.warning("Telegram bot token not set. Alerts disabled.")
            return

        try:
            from telegram import Bot

            self._bot = Bot(token=self._settings.telegram_bot_token)
            me = await self._bot.get_me()
            self._enabled = True
            logger.info("Telegram bot initialized: @%s", me.username)
        except Exception as exc:
            logger.error("Failed to initialize Telegram bot: %s", exc)

    async def send_prediction(self, prediction: dict[str, Any]) -> bool:
        """Send a prediction alert if it meets threshold and rate limit."""
        if not self._enabled:
            return False

        alert_level = prediction.get("alert_level", "INFO")
        min_level = self._settings.telegram_alert_level
        if self.ALERT_LEVELS.get(alert_level, 0) < self.ALERT_LEVELS.get(min_level, 0):
            return False

        confidence = prediction.get("confidence", 0)
        if confidence < self._settings.alert_min_confidence:
            return False

        token = prediction.get("token_address", "")
        if not self._check_rate_limit(token):
            return False

        message = format_prediction_alert(prediction)
        return await self._send_message(message)

    async def send_scan_report(self, pairs: list[dict]) -> bool:
        """Send a scan summary."""
        if not self._enabled:
            return False
        message = format_scan_summary(pairs)
        return await self._send_message(message)

    async def send_raw(self, text: str) -> bool:
        """Send a raw text message."""
        if not self._enabled:
            return False
        return await self._send_message(text)

    async def _send_message(self, text: str) -> bool:
        if not self._bot or not self._settings.telegram_chat_id:
            return False
        try:
            await self._bot.send_message(
                chat_id=self._settings.telegram_chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            return True
        except Exception as exc:
            logger.error("Failed to send Telegram message: %s", exc)
            return False

    def _check_rate_limit(self, token_address: str) -> bool:
        now = time.time()
        last = self._last_alert_times.get(token_address, 0)
        if now - last < self._settings.alert_rate_limit:
            return False
        self._last_alert_times[token_address] = now
        return True
