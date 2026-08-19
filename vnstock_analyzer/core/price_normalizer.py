"""Normalize Vietnamese equity prices to exchange quotation ticks."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import pandas as pd


PRICE_COLUMNS = ("open", "high", "low", "close")


def normalize_exchange(exchange):
    value = str(exchange or "HOSE").upper()
    return value if value in {"HOSE", "HNX", "UPCOM"} else "HOSE"


def price_tick(price, exchange="HOSE"):
    """Return the quotation tick in thousand-VND price units."""
    numeric = Decimal(str(price))
    venue = normalize_exchange(exchange)
    if venue in {"HNX", "UPCOM"}:
        return 0.1
    if numeric < Decimal("10"):
        return 0.01
    if numeric < Decimal("50"):
        return 0.05
    return 0.1


def round_price_to_tick(price, exchange="HOSE"):
    """Round one fetched price to the nearest legal quotation tick."""
    if price is None or pd.isna(price):
        return float("nan")
    try:
        numeric = Decimal(str(price))
        tick = Decimal(str(price_tick(numeric, exchange)))
    except (InvalidOperation, ValueError):
        return float("nan")
    units = (numeric / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return float(units * tick)


def normalize_price_history(history, exchange="HOSE"):
    """Normalize all fetched OHLC values before any indicator calculation."""
    if history is None or history.empty:
        return history
    result = history.copy()
    for column in PRICE_COLUMNS:
        if column not in result.columns:
            continue
        numeric = pd.to_numeric(result[column], errors="coerce")
        result[column] = numeric.map(lambda value: round_price_to_tick(value, exchange))
    return result
