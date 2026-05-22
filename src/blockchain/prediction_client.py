"""
PancakeSwap Prediction Game Web3 Client
Handles connection to the smart contract and executing bets.
"""

import json
from typing import Optional
from web3 import Web3
from web3.middleware import geth_poa_middleware
from loguru import logger
from src.utils.config import get_settings

# Minimal ABI required for the Prediction Game
PREDICTION_ABI = json.loads('''[
    {"inputs":[],"name":"currentEpoch","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"epoch","type":"uint256"}],"name":"betBull","outputs":[],"stateMutability":"payable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"epoch","type":"uint256"}],"name":"betBear","outputs":[],"stateMutability":"payable","type":"function"},
    {"inputs":[{"internalType":"uint256[]","name":"epochs","type":"uint256[]"}],"name":"claim","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"rounds","outputs":[{"internalType":"uint256","name":"epoch","type":"uint256"},{"internalType":"uint256","name":"startTimestamp","type":"uint256"},{"internalType":"uint256","name":"lockTimestamp","type":"uint256"},{"internalType":"uint256","name":"closeTimestamp","type":"uint256"},{"internalType":"int256","name":"lockPrice","type":"int256"},{"internalType":"int256","name":"closePrice","type":"int256"},{"internalType":"uint256","name":"lockOracleId","type":"uint256"},{"internalType":"uint256","name":"closeOracleId","type":"uint256"},{"internalType":"uint256","name":"totalAmount","type":"uint256"},{"internalType":"uint256","name":"bullAmount","type":"uint256"},{"internalType":"uint256","name":"bearAmount","type":"uint256"},{"internalType":"uint256","name":"rewardBaseCalAmount","type":"uint256"},{"internalType":"uint256","name":"rewardAmount","type":"uint256"},{"internalType":"bool","name":"oracleCalled","type":"bool"}],"stateMutability":"view","type":"function"}
]''')

class PredictionClient:
    def __init__(self):
        self.settings = get_settings()
        self.w3 = Web3(Web3.HTTPProvider(self.settings.bsc_rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        if not self.w3.is_connected():
            logger.error("Failed to connect to BSC network!")
            
        self.contract_address = self.w3.to_checksum_address(self.settings.prediction_contract)
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=PREDICTION_ABI)
        
        self.account = None
        if self.settings.wallet_private_key:
            try:
                self.account = self.w3.eth.account.from_key(self.settings.wallet_private_key)
                logger.info(f"Wallet loaded: {self.account.address}")
            except Exception as e:
                logger.error(f"Failed to load wallet from private key: {e}")
        else:
            logger.warning("No WALLET_PRIVATE_KEY found in .env, running in read-only mode.")

    def get_current_epoch(self) -> int:
        """Fetch the current epoch (round) from the contract."""
        try:
            return self.contract.functions.currentEpoch().call()
        except Exception as e:
            logger.error(f"Error fetching current epoch: {e}")
            return 0

    def _send_transaction(self, function_call, value_wei: int = 0) -> Optional[str]:
        """Internal helper to sign and send a transaction."""
        if not self.account:
            logger.error("Cannot send transaction: No wallet loaded.")
            return None
            
        try:
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            gas_price = self.w3.eth.gas_price
            
            # Build transaction
            tx = function_call.build_transaction({
                'chainId': 56, # BSC Mainnet
                'gas': 300000, # Safe gas limit for betting
                'gasPrice': gas_price,
                'nonce': nonce,
                'value': value_wei
            })
            
            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.account.key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hex = self.w3.to_hex(tx_hash)
            logger.info(f"Transaction sent successfully! TX Hash: {tx_hex}")
            return tx_hex
            
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            return None

    def bet_bull(self, epoch: int, amount_bnb: float) -> Optional[str]:
        """Place a UP (Bull) bet for the given epoch."""
        value_wei = self.w3.to_wei(amount_bnb, 'ether')
        logger.info(f"Placing BULL bet on epoch {epoch} with {amount_bnb} BNB")
        func = self.contract.functions.betBull(epoch)
        return self._send_transaction(func, value_wei)

    def bet_bear(self, epoch: int, amount_bnb: float) -> Optional[str]:
        """Place a DOWN (Bear) bet for the given epoch."""
        value_wei = self.w3.to_wei(amount_bnb, 'ether')
        logger.info(f"Placing BEAR bet on epoch {epoch} with {amount_bnb} BNB")
        func = self.contract.functions.betBear(epoch)
        return self._send_transaction(func, value_wei)
