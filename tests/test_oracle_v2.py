import unittest

import numpy as np
import pandas as pd

from vnstock_analyzer.oracle_v2 import MODEL_VERSION, PanelOracle


def _panel(symbols=35, rows=150, seed=19):
    random = np.random.default_rng(seed)
    dates = pd.bdate_range("2025-01-01", periods=rows)
    market = random.normal(0.0005, 0.008, rows)
    records = []
    for number in range(symbols):
        drift = (number / max(symbols - 1, 1) - 0.5) * 0.0015
        returns = market + drift + random.normal(0, 0.007, rows)
        close = (20 + number) * np.cumprod(1 + returns)
        for index, date in enumerate(dates):
            records.append({
                "symbol": f"S{number:03d}",
                "trading_date": date,
                "open": close[index] * 0.997,
                "high": close[index] * 1.012,
                "low": close[index] * 0.988,
                "close": close[index],
                "volume": 500_000 + number * 20_000 + index * 100,
                "source": "TEST",
            })
    return pd.DataFrame(records)


class PanelOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = PanelOracle(_panel())

    def test_panel_adds_market_and_relative_features(self):
        expected = {
            "market_return_5",
            "breadth_above_ema20",
            "relative_strength_20",
            "rs_rank_20",
            "liquidity_rank",
        }
        self.assertTrue(expected.issubset(self.model.panel.columns))
        self.assertEqual(self.model.symbol_count, 35)

    def test_training_context_only_uses_labels_resolved_by_as_of(self):
        labeled = self.model._labeled(10)
        as_of = self.model.panel["trading_date"].iloc[-20]

        context = self.model._training_context(labeled, as_of)

        self.assertIsNotNone(context)
        self.assertTrue((context["candidates"]["label_end_date"] <= as_of).all())

    def test_universe_forecast_is_bidirectional_and_ranked(self):
        result = self.model.forecast_universe(model_health={
            "status": "RANK_PASS",
            "ranking_status": "PASS",
            "direction_status": "REJECT",
        })

        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["model_version"], MODEL_VERSION)
        self.assertEqual(len(result["forecasts"]), 35)
        ranks = [forecast["relative_rank_percentile"] for forecast in result["forecasts"].values()]
        directions = {forecast["direction"] for forecast in result["forecasts"].values()}
        decisions = {forecast["decision"] for forecast in result["forecasts"].values()}
        self.assertAlmostEqual(max(ranks), 100.0)
        self.assertLess(min(ranks), 10.0)
        self.assertGreaterEqual(len(directions), 2)
        self.assertGreaterEqual(len(decisions), 2)
        for forecast in result["forecasts"].values():
            self.assertIn(forecast["direction"], {"BULLISH", "NEUTRAL", "BEARISH"})
            self.assertAlmostEqual(
                forecast["probability_up"] + forecast["probability_down"],
                100.0,
                delta=2.0,
            )

    def test_rank_pass_does_not_claim_validated_long_setup(self):
        result = self.model.forecast_symbol("S034", model_health={
            "status": "RANK_PASS",
            "ranking_status": "PASS",
            "direction_status": "REJECT",
        })

        self.assertEqual(result["status"], "READY")
        self.assertNotEqual(result["forecast"]["decision"], "LONG_SETUP")


if __name__ == "__main__":
    unittest.main()
