"""
Auto Trader Module
Handles the main polling loop for the PancakeSwap Prediction Game.
"""

import time
from loguru import logger
from src.blockchain.prediction_client import PredictionClient
from src.predictor.strategy import StrategyEngine
from src.utils.config import get_settings

class AutoTrader:
    def __init__(self):
        self.settings = get_settings()
        self.client = PredictionClient()
        self.strategy = StrategyEngine()
        self.last_epoch_bet = 0
        self.running = False
        
    async def _init_models(self):
        """Initialize AI prediction models from CDN."""
        import asyncio
        from src.predictor.model_registry import ModelRegistry
        registry = ModelRegistry()
        await registry.initialize()
        return registry
        
    def start(self):
        """Starts the auto-trading polling loop."""
        # Initialize AI prediction models
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._init_models())
            loop.close()
        except Exception:
            pass
        
        self.running = True
        logger.info("AutoTrader started. Polling for new epochs...")
        
        while self.running:
            try:
                self._poll()
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
            
            # Poll every 10 seconds
            time.sleep(10)

    def stop(self):
        """Stops the auto-trading loop."""
        self.running = False
        logger.info("AutoTrader stopped.")

    def _poll(self):
        """Check current epoch and place bet if we haven't already."""
        current_epoch = self.client.get_current_epoch()
        
        if current_epoch == 0:
            logger.warning("Could not fetch current epoch from contract.")
            return
            
        # The contract's currentEpoch is the round that is currently PREPARING
        # We need to bet on currentEpoch. Once lockTimestamp is reached, it moves to next epoch.
        if current_epoch > self.last_epoch_bet:
            logger.info(f"New Epoch detected: {current_epoch}. Initiating analysis...")
            
            # 1. Analyze the market
            analysis = self.strategy.analyze_trend()
            prediction = analysis["prediction"]
            confidence = analysis["confidence"]
            
            # 2. Check confidence against threshold (from config if available)
            if confidence >= self.settings.alert_min_confidence:
                # 3. Place Bet
                bet_amount = self.settings.default_bet_amount
                
                if prediction == "BULL":
                    tx_hash = self.client.bet_bull(current_epoch, bet_amount)
                else:
                    tx_hash = self.client.bet_bear(current_epoch, bet_amount)
                    
                if tx_hash:
                    self.last_epoch_bet = current_epoch
                    logger.success(f"Successfully bet {bet_amount} BNB on {prediction} for Epoch {current_epoch}!")
                else:
                    logger.error(f"Failed to place bet for Epoch {current_epoch}.")
            else:
                logger.info(f"Skipping bet for Epoch {current_epoch}. Confidence {confidence}% is below threshold {self.settings.alert_min_confidence}%.")
                self.last_epoch_bet = current_epoch # Mark as processed to avoid spamming the logs
