#!/usr/bin/env python3
"""Run leakage-safe walk-forward diagnostics for one Vietnamese stock."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vnstock_analyzer.core import DataFetcher
from vnstock_analyzer.oracle import HORIZONS, OracleForecaster


def main():
    if len(sys.argv) != 2:
        print("Usage: .venv/bin/python scripts/backtest_oracle.py <SYMBOL>", file=sys.stderr)
        return 2
    symbol = sys.argv[1].upper()
    fetcher = DataFetcher(symbol)
    if not fetcher.fetch_all_data():
        print(json.dumps({"symbol": symbol, "error": "Không lấy được dữ liệu"}, ensure_ascii=False))
        return 1
    forecaster = OracleForecaster(fetcher.get_data("history"))
    result = {
        "symbol": symbol,
        "forecast": forecaster.forecast(),
        "backtests": {str(h): forecaster.walk_forward_backtest(horizon=h) for h in HORIZONS},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

