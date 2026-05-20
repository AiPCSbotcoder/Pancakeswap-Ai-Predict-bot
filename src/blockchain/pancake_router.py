"""
PancakeSwap V2/V3 Router and Factory contract interactions.
Handles pair queries, price calculations, and swap decoding.
"""

from __future__ import annotations

from typing import Any, Optional

from web3 import AsyncWeb3

from src.utils.config import get_settings
from src.utils.logging_setup import get_logger
from src.utils.retry import rpc_retry

logger = get_logger("pancake_router")

# PancakeSwap V2 Factory ABI (PairCreated event + getPair)
FACTORY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "token0", "type": "address"},
            {"indexed": True, "name": "token1", "type": "address"},
            {"indexed": False, "name": "pair", "type": "address"},
            {"indexed": False, "name": "", "type": "uint256"},
        ],
        "name": "PairCreated",
        "type": "event",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "tokenA", "type": "address"},
            {"name": "tokenB", "type": "address"},
        ],
        "name": "getPair",
        "outputs": [{"name": "pair", "type": "address"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "allPairsLength",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "", "type": "uint256"}],
        "name": "allPairs",
        "outputs": [{"name": "pair", "type": "address"}],
        "type": "function",
    },
]

# PancakeSwap V2 Pair ABI
PAIR_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"name": "_reserve0", "type": "uint112"},
            {"name": "_reserve1", "type": "uint112"},
            {"name": "_blockTimestampLast", "type": "uint32"},
        ],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token0",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token1",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
]

# PancakeSwap V2 Router ABI (swap functions)
ROUTER_ABI = [
    {
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "type": "function",
    },
    {
        "inputs": [
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactETHForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "type": "function",
    },
    {
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactTokensForETH",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "type": "function",
    },
]

# WBNB address on BSC
WBNB_ADDRESS = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"


class PancakeRouter:
    """Interface for PancakeSwap V2/V3 contracts."""

    def __init__(self, w3: AsyncWeb3) -> None:
        self._w3 = w3
        self._settings = get_settings()

        self._factory = self._w3.eth.contract(
            address=self._w3.to_checksum_address(self._settings.pancake_factory_v2),
            abi=FACTORY_ABI,
        )
        self._router = self._w3.eth.contract(
            address=self._w3.to_checksum_address(self._settings.pancake_router_v2),
            abi=ROUTER_ABI,
        )

    @rpc_retry(max_attempts=3)
    async def get_pair_address(self, token_a: str, token_b: str) -> Optional[str]:
        """Get LP pair address for two tokens."""
        addr_a = self._w3.to_checksum_address(token_a)
        addr_b = self._w3.to_checksum_address(token_b)
        pair = await self._factory.functions.getPair(addr_a, addr_b).call()
        if pair == "0x0000000000000000000000000000000000000000":
            return None
        return pair

    @rpc_retry(max_attempts=3)
    async def get_reserves(self, pair_address: str) -> dict[str, Any]:
        """Get reserves and token addresses for a pair."""
        pair_cs = self._w3.to_checksum_address(pair_address)
        pair_contract = self._w3.eth.contract(address=pair_cs, abi=PAIR_ABI)

        reserves = await pair_contract.functions.getReserves().call()
        token0 = await pair_contract.functions.token0().call()
        token1 = await pair_contract.functions.token1().call()

        return {
            "reserve0": reserves[0],
            "reserve1": reserves[1],
            "block_timestamp": reserves[2],
            "token0": token0,
            "token1": token1,
            "pair": pair_address,
        }

    async def get_token_price_bnb(self, token_address: str) -> float:
        """Get token price in BNB using pair reserves."""
        pair = await self.get_pair_address(token_address, WBNB_ADDRESS)
        if not pair:
            return 0.0

        reserves = await self.get_reserves(pair)
        token_cs = self._w3.to_checksum_address(token_address)

        if reserves["token0"].lower() == token_cs.lower():
            if reserves["reserve0"] == 0:
                return 0.0
            return reserves["reserve1"] / reserves["reserve0"]
        else:
            if reserves["reserve1"] == 0:
                return 0.0
            return reserves["reserve0"] / reserves["reserve1"]

    async def get_liquidity_bnb(self, token_address: str) -> float:
        """Get total BNB liquidity for a token pair."""
        pair = await self.get_pair_address(token_address, WBNB_ADDRESS)
        if not pair:
            return 0.0

        reserves = await self.get_reserves(pair)
        wbnb_cs = self._w3.to_checksum_address(WBNB_ADDRESS)

        if reserves["token0"].lower() == wbnb_cs.lower():
            bnb_reserve = reserves["reserve0"]
        else:
            bnb_reserve = reserves["reserve1"]

        return float(self._w3.from_wei(bnb_reserve, "ether"))

    @rpc_retry(max_attempts=3)
    async def get_total_pairs(self) -> int:
        """Get total number of pairs created on PancakeSwap."""
        return await self._factory.functions.allPairsLength().call()

    @rpc_retry(max_attempts=3)
    async def get_pair_by_index(self, index: int) -> str:
        """Get pair address by index."""
        return await self._factory.functions.allPairs(index).call()

    async def get_recent_pairs(self, count: int = 20) -> list[dict]:
        """Get the most recently created pairs."""
        total = await self.get_total_pairs()
        start = max(0, total - count)

        pairs = []
        for i in range(total - 1, start - 1, -1):
            try:
                pair_addr = await self.get_pair_by_index(i)
                reserves = await self.get_reserves(pair_addr)
                pairs.append({"index": i, "pair_address": pair_addr, **reserves})
            except Exception as exc:
                logger.warning("Failed to fetch pair #%d: %s", i, exc)
                continue
        return pairs

    def decode_swap_input(self, input_data: str) -> Optional[dict]:
        """Decode PancakeSwap router swap transaction input data."""
        try:
            decoded = self._router.decode_function_input(input_data)
            return {"function": decoded[0].fn_name, "params": dict(decoded[1])}
        except Exception:
            return None
