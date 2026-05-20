"""
BSC RPC Client with failover support.
Connects to real BSC nodes via QuickNode, ANKR, or public endpoints.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

import httpx
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware

from src.utils.config import get_settings
from src.utils.logging_setup import get_logger
from src.utils.retry import rpc_retry

logger = get_logger("bsc_client")


class BSCClient:
    """Async BSC RPC client with automatic failover."""

    # Standard ERC-20 ABI for balance & transfer queries
    ERC20_ABI = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "totalSupply",
            "outputs": [{"name": "", "type": "uint256"}],
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "symbol",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "name",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "owner",
            "outputs": [{"name": "", "type": "address"}],
            "type": "function",
        },
    ]

    def __init__(self) -> None:
        self._settings = get_settings()
        self._w3: Optional[AsyncWeb3] = None
        self._current_endpoint: str = ""
        self._http_client = httpx.AsyncClient(timeout=30.0)

    async def connect(self) -> None:
        """Connect to the best available BSC RPC endpoint."""
        endpoints = self._settings.get_rpc_endpoints()

        for endpoint in endpoints:
            try:
                provider = AsyncHTTPProvider(endpoint)
                w3 = AsyncWeb3(provider)
                w3.middleware_onion.inject(
                    ExtraDataToPOAMiddleware, layer=0
                )

                if await w3.is_connected():
                    self._w3 = w3
                    self._current_endpoint = endpoint
                    block = await w3.eth.block_number
                    logger.info(
                        "Connected to BSC at %s (block: %d)",
                        endpoint[:40] + "...",
                        block,
                    )
                    return
            except Exception as exc:
                logger.warning(
                    "Failed to connect to %s: %s", endpoint[:40], exc
                )
                continue

        raise ConnectionError("Could not connect to any BSC RPC endpoint")

    @property
    def w3(self) -> AsyncWeb3:
        """Get the Web3 instance, raising if not connected."""
        if self._w3 is None:
            raise RuntimeError("BSCClient not connected. Call connect() first.")
        return self._w3

    @rpc_retry(max_attempts=3)
    async def get_block_number(self) -> int:
        """Get current block number."""
        return await self.w3.eth.block_number

    @rpc_retry(max_attempts=3)
    async def get_bnb_balance(self, address: str) -> float:
        """Get BNB balance of an address in ether units."""
        checksum = self.w3.to_checksum_address(address)
        balance_wei = await self.w3.eth.get_balance(checksum)
        return float(self.w3.from_wei(balance_wei, "ether"))

    @rpc_retry(max_attempts=3)
    async def get_token_info(self, token_address: str) -> dict[str, Any]:
        """Get basic token information (name, symbol, decimals, totalSupply)."""
        checksum = self.w3.to_checksum_address(token_address)
        contract = self.w3.eth.contract(address=checksum, abi=self.ERC20_ABI)

        try:
            name = await contract.functions.name().call()
            symbol = await contract.functions.symbol().call()
            decimals = await contract.functions.decimals().call()
            total_supply = await contract.functions.totalSupply().call()

            return {
                "address": token_address,
                "name": name,
                "symbol": symbol,
                "decimals": decimals,
                "total_supply": total_supply / (10**decimals),
            }
        except Exception as exc:
            logger.error("Failed to get token info for %s: %s", token_address, exc)
            return {
                "address": token_address,
                "name": "Unknown",
                "symbol": "???",
                "decimals": 18,
                "total_supply": 0,
            }

    @rpc_retry(max_attempts=3)
    async def get_token_balance(
        self, token_address: str, holder_address: str
    ) -> float:
        """Get token balance of a holder."""
        token_cs = self.w3.to_checksum_address(token_address)
        holder_cs = self.w3.to_checksum_address(holder_address)
        contract = self.w3.eth.contract(address=token_cs, abi=self.ERC20_ABI)

        balance = await contract.functions.balanceOf(holder_cs).call()
        decimals = await contract.functions.decimals().call()
        return balance / (10**decimals)

    @rpc_retry(max_attempts=3)
    async def get_transaction(self, tx_hash: str) -> dict:
        """Get transaction details."""
        return dict(await self.w3.eth.get_transaction(tx_hash))

    @rpc_retry(max_attempts=3)
    async def get_block(self, block_number: int | str = "latest") -> dict:
        """Get block details."""
        return dict(await self.w3.eth.get_block(block_number, full_transactions=True))

    async def get_contract_source(self, address: str) -> Optional[dict]:
        """Fetch contract source code from BSCScan API."""
        if not self._settings.bscscan_api_key:
            logger.warning("BSCScan API key not set, skipping source fetch")
            return None

        url = (
            f"https://api.bscscan.com/api"
            f"?module=contract&action=getsourcecode"
            f"&address={address}"
            f"&apikey={self._settings.bscscan_api_key}"
        )

        try:
            resp = await self._http_client.get(url)
            data = resp.json()
            if data.get("status") == "1" and data.get("result"):
                return data["result"][0]
            return None
        except Exception as exc:
            logger.error("BSCScan API error for %s: %s", address, exc)
            return None

    async def get_top_holders(
        self, token_address: str, limit: int = 10
    ) -> list[dict]:
        """
        Get top token holders via BSCScan API.
        Falls back to empty list if API key not available.
        """
        if not self._settings.bscscan_api_key:
            return []

        url = (
            f"https://api.bscscan.com/api"
            f"?module=token&action=tokenholderlist"
            f"&contractaddress={token_address}"
            f"&page=1&offset={limit}"
            f"&apikey={self._settings.bscscan_api_key}"
        )

        try:
            resp = await self._http_client.get(url)
            data = resp.json()
            if data.get("status") == "1":
                return data.get("result", [])
            return []
        except Exception:
            return []

    async def close(self) -> None:
        """Close HTTP client and cleanup."""
        await self._http_client.aclose()
        logger.info("BSC client closed")
