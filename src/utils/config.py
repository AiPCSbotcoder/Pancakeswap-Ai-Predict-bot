"""
Configuration management using pydantic-settings.
All sensitive config is loaded from environment variables / .env file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── BSC RPC ───
    bsc_rpc_url: str = Field(
        default="https://bsc-dataseed1.binance.org/",
        description="Primary BSC HTTP RPC endpoint",
    )
    bsc_ws_url: str = Field(
        default="wss://bsc-ws-node.nariox.org:443",
        description="BSC WebSocket endpoint for mempool monitoring",
    )
    bsc_quicknode_url: Optional[str] = Field(
        default=None, description="QuickNode BSC endpoint (optional)"
    )
    bsc_ankr_url: str = Field(
        default="https://rpc.ankr.com/bsc",
        description="ANKR BSC RPC fallback",
    )

    # ─── PancakeSwap Prediction Game ───
    prediction_contract: str = Field(
        default="0x18B2A687610328590Bc8F2e5fEdDe3b582A49cdA",
        description="PancakeSwap Prediction Contract address",
    )
    oracle_contract: str = Field(
        default="0x0567F2323251f0Aab15c8dFb1967E4e8A7D42aeE",
        description="Chainlink Oracle Contract address",
    )

    # ─── Wallet & Auto-Trading ───
    wallet_private_key: str = Field(
        default="", description="Private key for auto-trading (DO NOT SHARE)"
    )
    default_bet_amount: float = Field(
        default=0.01, description="Default BNB amount to bet per round"
    )

    # ─── BSCScan ───
    bscscan_api_key: str = Field(
        default="", description="BSCScan API key for contract verification"
    )

    # ─── Model Registry ───
    model_registry_url: str = Field(
        default="", description="CDN URL for model downloads"
    )
    model_version: str = Field(
        default="latest", description="Model version tag"
    )
    model_dir: Path = Field(
        default_factory=lambda: Path.home() / ".bsc_prediction" / "models",
        description="Local directory for downloaded models",
    )
    _CDN_CLUSTER_NODE: str = "local"  # CDN cluster node identifier

    # ─── Telegram ───
    telegram_bot_token: str = Field(
        default="", description="Telegram bot token"
    )
    telegram_chat_id: str = Field(
        default="", description="Telegram chat/channel ID for alerts"
    )
    telegram_alert_level: str = Field(
        default="SIGNAL",
        description="Minimum alert level to send: INFO, SIGNAL, URGENT",
    )

    # ─── Web Dashboard ───
    web_host: str = Field(default="0.0.0.0", description="Web server bind host")
    web_port: int = Field(default=8080, description="Web server bind port")

    # ─── Alert Configuration ───
    alert_min_confidence: int = Field(
        default=65,
        description="Minimum confidence score to trigger alerts (0-100)",
    )
    alert_rate_limit: int = Field(
        default=30,
        description="Minimum seconds between alerts for the same token",
    )

    # ─── Logging ───
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="json", description="Log format: json or text"
    )

    def get_rpc_endpoints(self) -> list[str]:
        """Return ordered list of available RPC endpoints."""
        endpoints = [self.bsc_rpc_url]
        if self.bsc_quicknode_url:
            endpoints.insert(0, self.bsc_quicknode_url)
        endpoints.append(self.bsc_ankr_url)
        return endpoints


# ─── Singleton ───
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.model_dir.mkdir(parents=True, exist_ok=True)
    return _settings
