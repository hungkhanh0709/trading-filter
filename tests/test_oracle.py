import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from vnstock_analyzer.oracle import MODEL_VERSION, OracleForecaster
from vnstock_analyzer.oracle_store import OracleStore


def _history(rows=250, seed=11):
    random = np.random.default_rng(seed)
    returns = 0.0008 + random.normal(0, 0.012, rows)
    close = 100 * np.cumprod(1 + returns)
    return pd.DataFrame({
        "time": pd.bdate_range("2025-01-01", periods=rows),
        "open": close * (1 + random.normal(0, 0.003, rows)),
        "high": close * (1 + random.uniform(0.002, 0.018, rows)),
        "low": close * (1 - random.uniform(0.002, 0.018, rows)),
        "close": close,
        "volume": random.integers(500_000, 3_000_000, rows),
    })


class OracleForecastTests(unittest.TestCase):
    def test_forecast_exposes_three_horizons_and_risk_plan(self):
        result = OracleForecaster(_history()).forecast()

        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["model_version"], MODEL_VERSION)
        self.assertEqual(set(result["horizons"]), {"5", "10", "20"})
        primary = result["primary"]
        self.assertLess(primary["stop"], primary["entry"]["low"])
        self.assertGreater(primary["target"], primary["entry"]["high"])
        self.assertAlmostEqual(
            primary["probability_target"] + primary["probability_stop"] + primary["probability_timeout"],
            100.0,
            delta=0.2,
        )

    def test_same_day_target_and_stop_is_scored_conservatively(self):
        future = pd.DataFrame([{"open": 100, "high": 110, "low": 90, "close": 105, "volume": 1}])

        result = OracleForecaster.evaluate_barriers(future, 100, stop_pct=5, target_pct=8)

        self.assertEqual(result.outcome, "STOP")
        self.assertEqual(result.return_pct, -5)

    def test_analogs_never_use_rows_whose_future_reaches_as_of(self):
        oracle = OracleForecaster(_history())
        as_of = 180
        horizon = 20

        analogs = oracle._analog_indices(as_of, horizon)

        self.assertTrue(analogs)
        self.assertTrue(all(index + horizon <= as_of for index, _ in analogs))

    def test_forecast_at_historical_index_ignores_later_appended_rows(self):
        history = _history()
        index = 180
        full = OracleForecaster(history).forecast(as_of_index=index)
        truncated = OracleForecaster(history.iloc[:index + 1]).forecast()

        for horizon in ("5", "10", "20"):
            keys = ("probability_target", "probability_stop", "expected_r", "sample_size")
            self.assertEqual(
                {key: full["horizons"][horizon][key] for key in keys},
                {key: truncated["horizons"][horizon][key] for key in keys},
            )

    def test_walk_forward_returns_calibration_metrics(self):
        result = OracleForecaster(_history()).walk_forward_backtest(horizon=10)

        self.assertEqual(result["status"], "READY")
        self.assertGreater(result["samples"], 0)
        self.assertGreaterEqual(result["brier_score"], 0)
        self.assertLessEqual(result["brier_score"], 1)

    def test_validation_gate_vetoes_an_actionable_unproven_forecast(self):
        oracle = OracleForecaster(_history())
        with unittest.mock.patch.object(oracle, "forecast") as forecast, unittest.mock.patch.object(
            oracle, "walk_forward_backtest"
        ) as backtest:
            primary = {"horizon": 10, "decision": "SETUP"}
            forecast.return_value = {
                "status": "READY",
                "primary": primary,
                "primary_horizon": 10,
                "horizons": {"10": primary},
                "warnings": [],
            }
            backtest.return_value = {
                "status": "READY",
                "samples": 100,
                "base_rate": 30,
                "brier_score": 0.40,
                "selected_samples": 20,
                "selected_expectancy_r": -0.2,
            }

            result = oracle.forecast_validated()

        self.assertEqual(result["model_health"]["status"], "REJECT")
        self.assertEqual(result["primary"]["decision"], "NO_TRADE")
        self.assertEqual(result["primary"]["raw_decision"], "SETUP")


class OracleStoreTests(unittest.TestCase):
    def test_history_is_upserted_and_forecast_is_immutable_by_version(self):
        with tempfile.TemporaryDirectory() as directory:
            store = OracleStore(Path(directory) / "oracle.db")
            history = _history(rows=90)
            forecast = OracleForecaster(history).forecast()

            self.assertEqual(store.save_history("FPT", history, "VCI"), 90)
            self.assertTrue(store.save_forecast("FPT", forecast))
            latest = store.latest_forecast("FPT")

            self.assertEqual(latest["as_of"], forecast["as_of"])
            self.assertEqual(latest["model_version"], MODEL_VERSION)
            json.dumps(latest)


if __name__ == "__main__":
    unittest.main()
