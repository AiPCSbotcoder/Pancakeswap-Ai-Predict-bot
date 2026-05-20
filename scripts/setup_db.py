"""
Database setup script.
Creates SQLite tables for prediction history and token metadata cache.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


DB_PATH = Path.home() / ".bsc_prediction" / "predictions.db"


def setup_database(db_path: Path = DB_PATH) -> None:
    """Create database tables."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_address TEXT NOT NULL,
            token_symbol TEXT,
            direction TEXT NOT NULL,
            confidence REAL NOT NULL,
            alert_level TEXT,
            time_window TEXT,
            price_bnb REAL,
            target_price REAL,
            stop_loss REAL,
            risk_score INTEGER,
            risk_level TEXT,
            patterns TEXT,
            reasoning TEXT,
            timestamp REAL NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_predictions_token
            ON predictions(token_address);
        CREATE INDEX IF NOT EXISTS idx_predictions_timestamp
            ON predictions(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_predictions_direction
            ON predictions(direction);

        CREATE TABLE IF NOT EXISTS token_cache (
            address TEXT PRIMARY KEY,
            name TEXT,
            symbol TEXT,
            decimals INTEGER,
            total_supply REAL,
            is_honeypot INTEGER DEFAULT 0,
            risk_score INTEGER DEFAULT 0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pair_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair_address TEXT NOT NULL,
            token0 TEXT,
            token1 TEXT,
            liquidity_bnb REAL,
            discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_pair_history_pair
            ON pair_history(pair_address);
    """)

    conn.commit()
    conn.close()
    print(f"✅ Database created at: {db_path}")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DB_PATH
    setup_database(path)
