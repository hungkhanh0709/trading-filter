"""Small SQLite store for reproducible Oracle inputs and immutable forecasts."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pandas as pd


DEFAULT_PATH = Path(__file__).parents[1] / "data" / "oracle.db"


class OracleStore:
    def __init__(self, path=None):
        configured = os.environ.get("ORACLE_DB_PATH")
        self.path = Path(path or configured or DEFAULT_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=20)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=20000")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS price_history (
                symbol TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                source TEXT,
                captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, trading_date)
            );
            CREATE TABLE IF NOT EXISTS forecasts (
                symbol TEXT NOT NULL,
                as_of TEXT NOT NULL,
                model_version TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, as_of, model_version)
            );
            """
        )
        return connection

    def save_history(self, symbol, history, source=None):
        if history is None or history.empty:
            return 0
        date_column = "time" if "time" in history.columns else "date" if "date" in history.columns else None
        rows = []
        for index, row in history.iterrows():
            date_value = row[date_column] if date_column else index
            date = pd.to_datetime(date_value, errors="coerce")
            if pd.isna(date):
                continue
            try:
                rows.append((
                    symbol,
                    date.strftime("%Y-%m-%d"),
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    float(row.get("volume", 0)),
                    source,
                ))
            except (KeyError, TypeError, ValueError):
                continue
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO price_history
                    (symbol, trading_date, open, high, low, close, volume, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, trading_date) DO UPDATE SET
                    open=excluded.open, high=excluded.high, low=excluded.low,
                    close=excluded.close, volume=excluded.volume, source=excluded.source,
                    captured_at=CURRENT_TIMESTAMP
                """,
                rows,
            )
        return len(rows)

    def save_forecast(self, symbol, forecast):
        if not forecast or forecast.get("status") != "READY":
            return False
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO forecasts (symbol, as_of, model_version, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(symbol, as_of, model_version) DO NOTHING
                """,
                (
                    symbol,
                    forecast["as_of"],
                    forecast["model_version"],
                    json.dumps(forecast, ensure_ascii=False, separators=(",", ":")),
                ),
            )
        return True

    def latest_forecast(self, symbol):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload FROM forecasts
                WHERE symbol = ? ORDER BY as_of DESC, created_at DESC LIMIT 1
                """,
                (symbol,),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def load_panel_history(self):
        """Return every persisted symbol/date observation for panel models."""
        with self._connect() as connection:
            return pd.read_sql_query(
                """
                SELECT symbol, trading_date, open, high, low, close, volume, source
                FROM price_history
                ORDER BY trading_date, symbol
                """,
                connection,
                parse_dates=["trading_date"],
            )

    def load_model_health(self, model_version, as_of):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS model_health (
                    model_version TEXT NOT NULL,
                    as_of TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (model_version, as_of)
                )
                """
            )
            row = connection.execute(
                "SELECT payload FROM model_health WHERE model_version=? AND as_of=?",
                (model_version, as_of),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def save_model_health(self, model_version, as_of, payload):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS model_health (
                    model_version TEXT NOT NULL,
                    as_of TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (model_version, as_of)
                )
                """
            )
            connection.execute(
                """
                INSERT INTO model_health (model_version, as_of, payload)
                VALUES (?, ?, ?)
                ON CONFLICT(model_version, as_of) DO UPDATE SET
                    payload=excluded.payload, created_at=CURRENT_TIMESTAMP
                """,
                (model_version, as_of, json.dumps(payload, ensure_ascii=False, separators=(",", ":"))),
            )
