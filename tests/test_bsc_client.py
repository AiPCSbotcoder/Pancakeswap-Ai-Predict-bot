"""Tests for the BSC client module."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.blockchain.bsc_client import BSCClient


class TestBSCClient:
    """Test suite for BSCClient."""

    def test_initialization(self):
        """Test that BSCClient initializes without errors."""
        with patch("src.blockchain.bsc_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                bsc_rpc_url="https://bsc-dataseed1.binance.org/",
                bsc_quicknode_url=None,
                bsc_ankr_url="https://rpc.ankr.com/bsc",
            )
            client = BSCClient()
            assert client._w3 is None
            assert client._current_endpoint == ""

    def test_w3_property_raises_when_not_connected(self):
        """Test that accessing w3 before connect raises RuntimeError."""
        with patch("src.blockchain.bsc_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                bsc_rpc_url="https://bsc-dataseed1.binance.org/",
                bsc_quicknode_url=None,
                bsc_ankr_url="https://rpc.ankr.com/bsc",
            )
            client = BSCClient()
            with pytest.raises(RuntimeError, match="not connected"):
                _ = client.w3

    def test_erc20_abi_structure(self):
        """Verify ERC20 ABI contains expected functions."""
        abi_names = [item["name"] for item in BSCClient.ERC20_ABI]
        assert "balanceOf" in abi_names
        assert "totalSupply" in abi_names
        assert "decimals" in abi_names
        assert "symbol" in abi_names
        assert "name" in abi_names

    @pytest.mark.asyncio
    async def test_get_contract_source_without_api_key(self):
        """Test that contract source fetch returns None without API key."""
        with patch("src.blockchain.bsc_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                bsc_rpc_url="https://bsc-dataseed1.binance.org/",
                bsc_quicknode_url=None,
                bsc_ankr_url="https://rpc.ankr.com/bsc",
                bscscan_api_key="",
            )
            client = BSCClient()
            result = await client.get_contract_source("0x1234")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_top_holders_without_api_key(self):
        """Test that top holders returns empty list without API key."""
        with patch("src.blockchain.bsc_client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                bsc_rpc_url="https://bsc-dataseed1.binance.org/",
                bsc_quicknode_url=None,
                bsc_ankr_url="https://rpc.ankr.com/bsc",
                bscscan_api_key="",
            )
            client = BSCClient()
            result = await client.get_top_holders("0x1234")
            assert result == []
