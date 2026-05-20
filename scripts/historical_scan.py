"""
Historical scan script.
Scans historical PancakeSwap pairs and runs prediction engine on them.
"""

from __future__ import annotations

import asyncio
import sys

from rich.console import Console
from rich.table import Table
from rich import box

from src.utils.config import get_settings
from src.utils.logging_setup import setup_logging
from src.blockchain.bsc_client import BSCClient
from src.blockchain.pancake_router import PancakeRouter
from src.data.fetcher import DataFetcher
from src.predictor.engine import PredictionEngine
from src.predictor.model_registry import ModelRegistry

console = Console()


async def historical_scan(pair_count: int = 50) -> None:
    """Scan historical pairs and generate predictions."""
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)

    console.print("\n[bold cyan]Historical Pair Scanner[/bold cyan]\n")

    bsc = BSCClient()
    await bsc.connect()

    router = PancakeRouter(bsc.w3)
    model_registry = ModelRegistry()
    await model_registry.initialize()

    fetcher = DataFetcher(bsc, router)
    engine = PredictionEngine(bsc, router, fetcher, model_registry)

    total_pairs = await router.get_total_pairs()
    console.print(f"Total pairs on PancakeSwap: [bold]{total_pairs:,}[/bold]")

    start = max(0, total_pairs - pair_count)
    console.print(f"Scanning pairs {start} to {total_pairs}...\n")

    table = Table(
        title=f"Historical Scan Results (last {pair_count} pairs)",
        box=box.ROUNDED,
        border_style="cyan",
    )
    table.add_column("#", style="dim", width=6)
    table.add_column("Token", style="bold")
    table.add_column("Direction", justify="center")
    table.add_column("Confidence", justify="right")
    table.add_column("Risk", justify="center")
    table.add_column("Liq (BNB)", justify="right")

    analyzed = 0
    for i in range(total_pairs - 1, start - 1, -1):
        try:
            pair_addr = await router.get_pair_by_index(i)
            reserves = await router.get_reserves(pair_addr)

            # Pick non-WBNB token
            wbnb = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c".lower()
            if reserves["token0"].lower() == wbnb:
                token_addr = reserves["token1"]
                bnb_reserve = reserves["reserve0"]
            elif reserves["token1"].lower() == wbnb:
                token_addr = reserves["token0"]
                bnb_reserve = reserves["reserve1"]
            else:
                continue

            liquidity = float(bsc.w3.from_wei(bnb_reserve, "ether"))
            if liquidity < 0.1:
                continue

            pred = await engine.predict(token_addr)
            analyzed += 1

            dir_color = {"BULLISH": "green", "BEARISH": "red"}.get(
                pred.direction.value, "dim"
            )
            risk_color = {
                "LOW": "green", "MEDIUM": "yellow",
                "HIGH": "red", "CRITICAL": "bold red"
            }.get(pred.risk_report.risk_level if pred.risk_report else "", "dim")

            table.add_row(
                str(i),
                pred.token_symbol,
                f"[{dir_color}]{pred.direction.value}[/{dir_color}]",
                f"{pred.confidence:.0f}%",
                f"[{risk_color}]{pred.risk_report.risk_level if pred.risk_report else 'N/A'}[/{risk_color}]",
                f"{liquidity:.2f}",
            )
        except Exception as exc:
            console.print(f"[dim]Pair #{i}: {exc}[/dim]")
            continue

    console.print(table)
    console.print(f"\n[green]Scan complete. {analyzed} tokens analyzed.[/green]")

    await bsc.close()
    await model_registry.close()


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    asyncio.run(historical_scan(count))
