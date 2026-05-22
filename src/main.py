import sys
from loguru import logger
from src.bot.auto_trader import AutoTrader

HELP_TEXT = """
=========================================
🥞 PancakeSwap Prediction Bot Backend 🐰
=========================================

Description:
PancakeSwap Prediction Game Bot's (UP/DOWN prediction and auto-betting engine) main entry point. 
Connects to Binance Smart Chain (BSC) via Web3, starts the `AutoTrader` loop, and automatically signs `betBull` or `betBear` transactions through your wallet based on the strategy engine's analysis.

Usage:
`python -m src.main` -> Starts the bot and enters the real-time betting loop.
`python -m src.main -h` -> Shows this help message.

Features:
- Fully automated BSC betting engine (Smart Contract Integration).
- Secure transaction signing via Web3 RPC and Private Key.
- Follows 5-minute rounds (epochs) seamlessly.
=========================================
"""

def print_help():
    print(HELP_TEXT.strip())

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "-h":
        print_help()
        sys.exit(0)
        
    logger.info("Starting PancakeSwap Prediction Bot Backend...")
    trader = AutoTrader()
    try:
        trader.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        trader.stop()
