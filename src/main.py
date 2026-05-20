"""
BSC Prediction Bot - Main entry point.
CLI interface with Rich console output using Click.

Commands:
    scan     - One-time scan of recent PancakeSwap pairs
    monitor  - Continuous monitoring mode
    backtest - Backtest on a historical pair
    serve    - Start web dashboard
"""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich import box

from src.utils.config import get_settings
from src.utils.logging_setup import setup_logging, get_logger
from src.blockchain.bsc_client import BSCClient
from src.blockchain.pancake_router import PancakeRouter
from src.blockchain.pair_scanner import PairScanner
from src.blockchain.mempool_monitor import MempoolMonitor
from src.data.fetcher import DataFetcher
from src.data.cache import CacheLayer
from src.predictor.engine import PredictionEngine
from src.predictor.model_registry import ModelRegistry
from src.telegram.bot import TelegramAlertBot

console = Console()

BANNER = """
[bold cyan]╔══════════════════════════════════════════════════════════════╗
║           🥞  BSC Prediction Bot  🥞                        ║
║     PancakeSwap On-Chain Pattern Recognition Engine          ║
╚══════════════════════════════════════════════════════════════╝[/bold cyan]
"""


async def init_components() -> dict:
    """Initialize all bot components."""
    settings = get_settings()
    setup_logging("CRITICAL", settings.log_format)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing BSC client...", total=None)

        bsc = BSCClient()
        await bsc.connect()
        progress.update(task, description="BSC client connected ✓")

        router = PancakeRouter(bsc.w3)

        progress.update(task, description="Initializing cache...")
        cache = CacheLayer()
        await cache.initialize()

        progress.update(task, description="Loading prediction engine...")
        model_registry = ModelRegistry()
        await model_registry.initialize()

        fetcher = DataFetcher(bsc, router)
        engine = PredictionEngine(bsc, router, fetcher, model_registry)

        progress.update(task, description="Initializing Telegram bot...")
        telegram = TelegramAlertBot()
        await telegram.initialize()

        scanner = PairScanner(bsc, router)
        await scanner.initialize()

        progress.update(task, description="All systems ready ✓")

    mode = "heuristic" if model_registry.is_heuristic_mode else "model-based"
    console.print(
        Panel(
            f"[green]Engine Mode:[/green] {mode}\n"
            f"[green]Models Loaded:[/green] {len(model_registry.list_models())}\n"
            f"[green]Telegram:[/green] {'enabled' if telegram._enabled else 'disabled'}",
            title="Status",
            border_style="green",
        )
    )

    return {
        "bsc": bsc,
        "router": router,
        "cache": cache,
        "model_registry": model_registry,
        "fetcher": fetcher,
        "engine": engine,
        "telegram": telegram,
        "scanner": scanner,
        "settings": settings,
    }


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """🥞 BSC Prediction Bot - PancakeSwap Pattern Recognition"""
    console.print(BANNER)


@cli.command()
@click.option("--count", default=20, help="Number of recent pairs to scan")
def scan(count: int):
    """One-time scan of recent PancakeSwap pairs."""

    async def _scan():
        components = await init_components()
        engine = components["engine"]
        scanner = components["scanner"]
        telegram = components["telegram"]

        console.print(f"\n[bold]Scanning last {count} pairs...[/bold]\n")

        pairs = await scanner.scan_new_pairs(lookback=count)

        table = Table(
            title="🔍 Recent Pairs",
            box=box.ROUNDED,
            show_lines=True,
            border_style="cyan",
        )
        table.add_column("Token", style="bold white", width=20)
        table.add_column("Pair", style="dim")
        table.add_column("Liq (BNB)", justify="right", style="yellow")
        table.add_column("Direction", justify="center")
        table.add_column("Confidence", justify="right")
        table.add_column("Risk", justify="center")

        predictions = []
        for pair in pairs:
            token = pair.get("token0", {}) if pair.get("is_bnb_pair") else pair.get("token0", {})
            token_addr = token.get("address", "")
            if not token_addr:
                continue

            try:
                pred = await engine.predict(token_addr)
                predictions.append(pred)

                dir_color = {
                    "BULLISH": "green",
                    "BEARISH": "red",
                    "NEUTRAL": "dim",
                }.get(pred.direction.value, "dim")

                risk_color = {
                    "LOW": "green",
                    "MEDIUM": "yellow",
                    "HIGH": "red",
                    "CRITICAL": "bold red",
                }.get(pred.risk_report.risk_level if pred.risk_report else "UNKNOWN", "dim")

                table.add_row(
                    pred.token_symbol,
                    pair.get("pair_address", "")[:10] + "...",
                    f"{pair.get('liquidity_bnb', 0):.2f}",
                    f"[{dir_color}]{pred.direction.value}[/{dir_color}]",
                    f"{pred.confidence:.0f}%",
                    f"[{risk_color}]{pred.risk_report.risk_level if pred.risk_report else 'N/A'}[/{risk_color}]",
                )
            except Exception as exc:
                console.print(f"[red]Error analyzing {token_addr[:10]}: {exc}[/red]")

        console.print(table)

        # Send summary to Telegram
        await telegram.send_scan_report(pairs)

        console.print(f"\n[green]Scan complete. {len(predictions)} tokens analyzed.[/green]")

        # Cleanup
        await components["bsc"].close()
        await components["cache"].close()
        await components["model_registry"].close()

    asyncio.run(_scan())


@cli.command()
@click.option("--interval", default=10, help="Scan interval in seconds")
def monitor(interval: int):
    """Continuous monitoring mode."""

    async def _monitor():
        components = await init_components()
        engine = components["engine"]
        scanner = components["scanner"]
        telegram = components["telegram"]

        console.print(
            f"\n[bold green]Starting continuous monitoring (every {interval}s)...[/bold green]"
        )
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        async def on_new_pair(pair: dict):
            token = pair.get("token0", {}) if pair.get("is_bnb_pair") else pair.get("token0", {})
            addr = token.get("address", "")
            if not addr:
                return

            try:
                pred = await engine.predict(addr)
                _print_prediction(pred)
                await telegram.send_prediction(pred.to_dict())
            except Exception as exc:
                console.print(f"[red]Analysis error: {exc}[/red]")

        try:
            await scanner.continuous_scan(interval=interval, callback=on_new_pair)
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped.[/yellow]")
        finally:
            await components["bsc"].close()
            await components["cache"].close()
            await components["model_registry"].close()

    asyncio.run(_monitor())


@cli.command()
@click.option("--pair", required=True, help="Pair/token address to backtest")
def backtest(pair: str):
    """Backtest prediction on a historical pair."""

    async def _backtest():
        components = await init_components()
        engine = components["engine"]

        console.print(f"\n[bold]Backtesting on {pair}...[/bold]\n")

        try:
            pred = await engine.predict(pair)
            _print_prediction(pred)

            # Show detailed analysis
            if pred.risk_report:
                _print_risk_report(pred.risk_report)
        except Exception as exc:
            console.print(f"[red]Backtest error: {exc}[/red]")
        finally:
            await components["bsc"].close()
            await components["cache"].close()
            await components["model_registry"].close()

    asyncio.run(_backtest())


@cli.command()
@click.option("--host", default=None, help="Web server host")
@click.option("--port", default=None, type=int, help="Web server port")
def serve(host: Optional[str], port: Optional[int]):
    """Start the web dashboard."""
    settings = get_settings()
    _host = host or settings.web_host
    _port = port or settings.web_port

    console.print(f"\n[bold green]Starting web dashboard on {_host}:{_port}[/bold green]\n")

    import uvicorn
    uvicorn.run(
        "web.app:app",
        host=_host,
        port=_port,
        reload=False,
        log_level="info",
    )


def _print_prediction(pred) -> None:
    """Print a prediction with rich formatting."""
    dir_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "⚪"}.get(
        pred.direction.value, "⚪"
    )

    panel_color = {"BULLISH": "green", "BEARISH": "red", "NEUTRAL": "dim"}.get(
        pred.direction.value, "dim"
    )

    content = [
        f"[bold]{dir_emoji} {pred.direction.value}[/bold] | Confidence: {pred.confidence:.0f}%",
        f"Price: {pred.price_bnb:.10f} BNB | Window: {pred.time_window}",
    ]

    if pred.target_price:
        content.append(f"Target: {pred.target_price:.10f} BNB")
    if pred.stop_loss:
        content.append(f"Stop Loss: {pred.stop_loss:.10f} BNB")

    if pred.reasoning:
        content.append("")
        for r in pred.reasoning:
            content.append(f"  • {r}")

    console.print(
        Panel(
            "\n".join(content),
            title=f"[bold]{pred.token_symbol}[/bold] ({pred.token_address[:10]}...)",
            subtitle=f"Alert: {pred.alert_level.value}",
            border_style=panel_color,
        )
    )


def _print_risk_report(risk) -> None:
    """Print a risk report with rich formatting."""
    risk_color = {
        "LOW": "green", "MEDIUM": "yellow", "HIGH": "red", "CRITICAL": "bold red"
    }.get(risk.risk_level, "dim")

    lines = [
        f"Score: [{risk_color}]{risk.risk_score}/100[/{risk_color}]",
        f"Level: [{risk_color}]{risk.risk_level}[/{risk_color}]",
        f"Honeypot: {'🚨 YES' if risk.is_honeypot else '✅ No'}",
        f"Ownership Renounced: {'✅ Yes' if risk.is_ownership_renounced else '⚠️ No'}",
        f"LP Locked: {'✅ Yes' if risk.is_lp_locked else '❓ Unknown'}",
    ]

    if risk.flags:
        lines.append("\nFlags:")
        for f in risk.flags:
            lines.append(f"  ⚠️ {f}")

    console.print(
        Panel(
            "\n".join(lines),
            title="Risk Report",
            border_style=risk_color,
        )
    )


if __name__ == "__main__":
    cli()
