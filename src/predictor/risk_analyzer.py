"""
Risk analyzer - Contract risk assessment for BSC tokens.
Checks for honeypot patterns, ownership status, LP locks, holder distribution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from src.blockchain.bsc_client import BSCClient
from src.utils.logging_setup import get_logger

logger = get_logger("risk_analyzer")


@dataclass
class RiskReport:
    """Comprehensive risk assessment for a token."""
    token_address: str
    risk_score: int = 0  # 0 (safe) to 100 (dangerous)
    risk_level: str = "UNKNOWN"  # LOW, MEDIUM, HIGH, CRITICAL
    is_honeypot: bool = False
    is_ownership_renounced: bool = False
    is_lp_locked: bool = False
    holder_concentration: float = 0.0
    flags: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def add_flag(self, flag: str, score_impact: int = 10) -> None:
        self.flags.append(flag)
        self.risk_score = min(100, self.risk_score + score_impact)

    def finalize(self) -> None:
        if self.risk_score <= 25:
            self.risk_level = "LOW"
        elif self.risk_score <= 50:
            self.risk_level = "MEDIUM"
        elif self.risk_score <= 75:
            self.risk_level = "HIGH"
        else:
            self.risk_level = "CRITICAL"


# Common honeypot patterns in Solidity source
HONEYPOT_PATTERNS = [
    (r"require\s*\(\s*msg\.sender\s*==\s*owner", "Owner-only transfer restriction"),
    (r"function\s+_transfer.*require.*blacklist", "Blacklist in transfer"),
    (r"maxTxAmount.*=.*0", "Max transaction set to zero"),
    (r"bool\s+public\s+tradingEnabled\s*=\s*false", "Trading disabled by default"),
    (r"function\s+setMaxTx.*onlyOwner", "Owner can restrict max TX"),
    (r"mapping.*isBlacklisted", "Blacklist mapping present"),
    (r"function\s+enableTrading.*onlyOwner", "Owner controls trading enable"),
]

DEAD_ADDRESS = "0x000000000000000000000000000000000000dEaD"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


class RiskAnalyzer:
    """Analyzes token contracts for potential risks."""

    def __init__(self, bsc: BSCClient) -> None:
        self._bsc = bsc

    async def analyze(self, token_address: str) -> RiskReport:
        report = RiskReport(token_address=token_address)

        await self._check_contract_source(report)
        await self._check_ownership(report)
        await self._check_holder_distribution(report)
        await self._check_lp_lock(report)

        report.finalize()
        logger.info(
            "Risk analysis for %s: score=%d level=%s flags=%d",
            token_address[:10],
            report.risk_score,
            report.risk_level,
            len(report.flags),
        )
        return report

    async def _check_contract_source(self, report: RiskReport) -> None:
        source_data = await self._bsc.get_contract_source(report.token_address)
        if not source_data:
            report.add_flag("Contract source not verified", 15)
            return

        source_code = source_data.get("SourceCode", "")
        if not source_code:
            report.add_flag("No source code available", 15)
            return

        report.details["contract_name"] = source_data.get("ContractName", "")
        report.details["compiler"] = source_data.get("CompilerVersion", "")

        for pattern, desc in HONEYPOT_PATTERNS:
            if re.search(pattern, source_code, re.IGNORECASE):
                report.add_flag(f"Honeypot pattern: {desc}", 20)
                report.is_honeypot = True

        if "selfdestruct" in source_code.lower():
            report.add_flag("Self-destruct capability found", 25)
        if "delegatecall" in source_code.lower():
            report.add_flag("Delegatecall usage (upgradeable proxy risk)", 15)

    async def _check_ownership(self, report: RiskReport) -> None:
        try:
            token_info = await self._bsc.get_token_info(report.token_address)
            source = await self._bsc.get_contract_source(report.token_address)
            if source:
                src_code = source.get("SourceCode", "")
                if "renounceOwnership" in src_code:
                    report.details["has_renounce_function"] = True
                owner_addr = None
                try:
                    checksum = self._bsc.w3.to_checksum_address(report.token_address)
                    owner_abi = [
                        {
                            "constant": True,
                            "inputs": [],
                            "name": "owner",
                            "outputs": [{"name": "", "type": "address"}],
                            "type": "function",
                        }
                    ]
                    contract = self._bsc.w3.eth.contract(address=checksum, abi=owner_abi)
                    owner_addr = await contract.functions.owner().call()
                except Exception:
                    pass

                if owner_addr:
                    report.details["owner"] = owner_addr
                    if owner_addr in (DEAD_ADDRESS, ZERO_ADDRESS):
                        report.is_ownership_renounced = True
                    else:
                        report.add_flag("Ownership NOT renounced", 15)
        except Exception as exc:
            logger.warning("Ownership check failed: %s", exc)

    async def _check_holder_distribution(self, report: RiskReport) -> None:
        holders = await self._bsc.get_top_holders(report.token_address, limit=10)
        if not holders:
            report.add_flag("Cannot verify holder distribution", 10)
            return

        token_info = await self._bsc.get_token_info(report.token_address)
        total_supply = token_info.get("total_supply", 0)
        if total_supply == 0:
            return

        top10_pct = 0.0
        for h in holders:
            bal = float(h.get("TokenHolderQuantity", 0))
            decimals = token_info.get("decimals", 18)
            pct = (bal / (10**decimals) / total_supply) * 100
            top10_pct += pct

        report.holder_concentration = top10_pct
        report.details["top10_holder_pct"] = top10_pct

        if top10_pct > 80:
            report.add_flag(f"Top 10 hold {top10_pct:.1f}% (extreme concentration)", 25)
        elif top10_pct > 50:
            report.add_flag(f"Top 10 hold {top10_pct:.1f}% (high concentration)", 15)

    async def _check_lp_lock(self, report: RiskReport) -> None:
        # LP lock check would query UNCX or similar protocols
        # For now, flag as unknown
        report.details["lp_lock_checked"] = False
        report.add_flag("LP lock status unknown (manual check recommended)", 5)
