#!/usr/bin/env python3
"""Return the latest cached-data Oracle V2 universe without network requests."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vnstock_analyzer.oracle_store import OracleStore
from vnstock_analyzer.oracle_v2 import MODEL_VERSION, PanelOracle


def main():
    store = OracleStore()
    model = PanelOracle(store.load_panel_history())
    if model.panel.empty:
        print(json.dumps({"status": "INSUFFICIENT_PANEL", "forecasts": {}}))
        return 0
    as_of = model._reliable_as_of().strftime("%Y-%m-%d")
    bucket = (model.symbol_count // 10) * 10
    health = store.load_model_health(MODEL_VERSION, f"{as_of}-n{bucket}")
    if health is None and model.symbol_count >= model.min_symbols:
        health = model.validate()
        store.save_model_health(MODEL_VERSION, f"{as_of}-n{bucket}", health)
    result = model.forecast_universe(model_health=health or {"status": "UNVALIDATED"})
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
