#!/usr/bin/env python3
"""Validate and summarize Oracle V2 against the persisted whole-market panel."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vnstock_analyzer.oracle_store import OracleStore
from vnstock_analyzer.oracle_v2 import MODEL_VERSION, PanelOracle


def main():
    store = OracleStore()
    model = PanelOracle(store.load_panel_history())
    health = model.validate()
    universe = model.forecast_universe(model_health=health)
    forecasts = universe.get("forecasts", {})
    ordered = sorted(
        forecasts.items(),
        key=lambda item: item[1]["relative_rank_percentile"],
        reverse=True,
    )
    result = {
        "model_version": MODEL_VERSION,
        "as_of": universe.get("as_of"),
        "symbol_count": model.symbol_count,
        "model_health": health,
        "market_state": universe.get("market_state"),
        "distribution": {
            key: sum(value["direction"] == key for value in forecasts.values())
            for key in ("BULLISH", "NEUTRAL", "BEARISH")
        },
        "decisions": {
            key: sum(value["decision"] == key for value in forecasts.values())
            for key in ("LONG_SETUP", "RANK_ONLY", "WATCH_LONG", "WAIT", "AVOID_LONG")
        },
        "top_ranked": [{"symbol": symbol, **forecast} for symbol, forecast in ordered[:15]],
        "bottom_ranked": [{"symbol": symbol, **forecast} for symbol, forecast in ordered[-10:]],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
