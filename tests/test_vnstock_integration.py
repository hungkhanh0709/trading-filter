import importlib.metadata
import importlib.util
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pandas as pd

from vnstock_analyzer.analyzers.technical import TechnicalAnalyzer
from vnstock_analyzer.analyzers.technical_modules.ma_detector import detect_convergence
from vnstock_analyzer.analyzers.technical_modules.volume_analyzer import analyze_volume_trend
from vnstock_analyzer.core.data_fetcher import DataFetcher, HISTORY_COUNT_BACK
from vnstock_analyzer.scorer import StockScorer


def _price_history(rows=60):
    close = [100.0 + index for index in range(rows)]
    return pd.DataFrame(
        {
            "time": pd.date_range("2026-01-01", periods=rows, freq="D"),
            "open": [value - 0.5 for value in close],
            "high": [value + 1.0 for value in close],
            "low": [value - 1.0 for value in close],
            "close": close,
            "volume": [1_000_000 + index * 1_000 for index in range(rows)],
        }
    )


class DataFetcherContractTests(unittest.TestCase):
    @patch("vnstock_analyzer.core.data_fetcher.Quote")
    def test_initializes_public_quote_with_requested_source(self, quote_class):
        fetcher = DataFetcher("FPT", source="VCI")

        quote_class.assert_called_once_with(symbol="FPT", source="VCI")
        self.assertIs(fetcher.quote, quote_class.return_value)

    @patch("vnstock_analyzer.core.data_fetcher.Reference")
    @patch("vnstock_analyzer.core.data_fetcher.Quote")
    def test_fetches_and_caches_history_with_existing_contract(self, quote_class, reference_class):
        history = _price_history()
        quote_class.return_value.history.return_value = history
        reference_class.return_value.events.return_value.calendar.return_value = pd.DataFrame()
        fetcher = DataFetcher("FPT")
        fetcher.max_retries = 1

        self.assertTrue(fetcher.fetch_all_data())
        self.assertIs(fetcher.get_data("history"), history)

        call = quote_class.return_value.history.call_args
        self.assertEqual(call.kwargs, {"count_back": HISTORY_COUNT_BACK})

    @patch("vnstock_analyzer.core.data_fetcher.Reference")
    @patch("vnstock_analyzer.core.data_fetcher.Quote")
    def test_falls_back_to_kbs_after_vci_retries_are_exhausted(self, quote_class, reference_class):
        primary_quote = Mock()
        primary_quote.history.side_effect = ConnectionError("read timeout=30")
        fallback_quote = Mock()
        fallback_history = _price_history()
        fallback_quote.history.return_value = fallback_history
        quote_class.side_effect = [primary_quote, fallback_quote]
        reference_class.return_value.events.return_value.calendar.return_value = pd.DataFrame()

        fetcher = DataFetcher("VCB", source="VCI")

        self.assertTrue(fetcher.fetch_all_data())
        self.assertIs(fetcher.get_data("history"), fallback_history)
        self.assertEqual(fetcher.active_source, "KBS")
        self.assertIs(fetcher.quote, fallback_quote)
        self.assertEqual(
            quote_class.call_args_list[-1].kwargs,
            {"symbol": "VCB", "source": "KBS"},
        )
        self.assertEqual(
            fallback_quote.history.call_args.kwargs,
            {"count_back": HISTORY_COUNT_BACK},
        )

    def test_restores_unadjusted_cash_dividend_prices_for_tradingview(self):
        history = pd.DataFrame({
            "time": pd.to_datetime(["2026-06-24", "2026-06-25", "2026-06-26"]),
            "open": [56.6, 56.5, 56.8],
            "high": [56.8, 56.7, 56.8],
            "low": [56.2, 56.3, 55.9],
            "close": [56.45, 56.45, 56.3],
            "volume": [1_000_000] * 3,
        })
        events = pd.DataFrame({
            "category": ["DIVIDEND"],
            "exright_date": ["2026-06-26"],
            "value_per_share": [1850.0],
        })

        restored, adjustments = DataFetcher._restore_unadjusted_cash_dividends(
            history, events
        )

        self.assertAlmostEqual(restored.iloc[1]["close"], 58.3)
        self.assertEqual(restored.iloc[2]["close"], 56.3)
        self.assertEqual(adjustments[0]["cash_dividend_vnd"], 1850.0)


class TechnicalAnalyzerContractTests(unittest.TestCase):
    def test_ema_uses_sma_seed_documented_by_tradingview(self):
        values = pd.Series([10.0, 11.0, 15.0, 12.0, 14.0])

        result = TechnicalAnalyzer._tradingview_ema(values, 3)

        self.assertTrue(pd.isna(result.iloc[0]))
        self.assertTrue(pd.isna(result.iloc[1]))
        self.assertEqual(result.iloc[2], 12.0)
        self.assertEqual(result.iloc[3], 12.0)
        self.assertEqual(result.iloc[4], 13.0)

    def test_calculates_only_ma10_ma20_ma50(self):
        analyzer = TechnicalAnalyzer(_price_history(rows=250))

        self.assertIn("MA10", analyzer.df.columns)
        self.assertIn("MA20", analyzer.df.columns)
        self.assertIn("MA50", analyzer.df.columns)
        self.assertNotIn("MA200", analyzer.df.columns)

    def test_convergence_distinguishes_a_contracting_base_from_expansion(self):
        contracting = pd.DataFrame(
            {
                "MA10": [103.0] * 44 + [103.0, 102.5, 102.0, 101.5, 101.0, 100.5],
                "MA20": [102.0] * 44 + [102.0, 101.8, 101.6, 101.4, 101.2, 100.3],
                "MA50": [100.0] * 50,
            }
        )
        expanding = pd.DataFrame(
            {
                "MA10": [100.5] * 44 + [100.5, 101.0, 101.5, 102.0, 102.5, 103.0],
                "MA20": [100.3] * 44 + [100.3, 100.6, 100.9, 101.2, 101.6, 102.0],
                "MA50": [100.0] * 50,
            }
        )

        contracting_result = detect_convergence(contracting)
        expanding_result = detect_convergence(expanding)

        self.assertTrue(contracting_result["is_contracting"])
        self.assertLess(contracting_result["bandwidth_change_5d"], 0)
        self.assertFalse(expanding_result["is_contracting"])
        self.assertGreater(expanding_result["bandwidth_change_5d"], 0)

    def test_analysis_exposes_additive_potential_context(self):
        result = TechnicalAnalyzer(_price_history(rows=250)).get_analysis()["ma_analysis"]

        self.assertIn("perfect_order_days", result["expansion"])
        self.assertIn("is_contracting", result["convergence"])
        self.assertIn("bandwidth_change_5d", result["convergence"])
        self.assertEqual(result["price_position"]["close"], 349.0)
        self.assertEqual(result["price_position"]["ma_type"], "EMA")
        self.assertEqual(result["price_position"]["ma_source"], "close")
        self.assertEqual(result["price_position"]["ema_seed"], "SMA")
        self.assertIn("EMA50: 324.5", result["price_position"]["tooltip"])
        for key in ("ma10", "ma20", "ma50"):
            self.assertGreater(result["price_position"][key], 0)

    def test_volume_ratio_uses_twenty_prior_sessions_as_baseline(self):
        history = _price_history(rows=21)
        history.loc[:19, "volume"] = 1_000_000
        history.loc[20, "volume"] = 2_000_000

        result = analyze_volume_trend(history)

        self.assertEqual(result["avg_volume"], 1_000_000)
        self.assertEqual(result["volume_ratio"], 2.0)


class StockScorerContractTests(unittest.TestCase):
    def test_uses_previous_daily_bar_while_today_session_is_unfinished(self):
        history = _price_history(rows=2)
        history.loc[0, "time"] = "2026-08-10"
        history.loc[1, "time"] = "2026-08-11"
        during_session = datetime(2026, 8, 11, 10, 30, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))

        completed = StockScorer._completed_daily_history(history, now=during_session)

        self.assertEqual(len(completed), 1)
        self.assertEqual(str(completed.iloc[-1]["time"])[:10], "2026-08-10")

    def test_uses_today_daily_bar_after_the_session_is_complete(self):
        history = _price_history(rows=2)
        history.loc[0, "time"] = "2026-08-10"
        history.loc[1, "time"] = "2026-08-11"
        after_session = datetime(2026, 8, 11, 15, 1, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))

        completed = StockScorer._completed_daily_history(history, now=after_session)

        self.assertEqual(len(completed), 2)

    @patch("vnstock_analyzer.scorer.DataFetcher")
    def test_analysis_response_keeps_existing_top_level_contract(self, fetcher_class):
        fetcher_class.return_value.fetch_all_data.return_value = True
        fetcher_class.return_value.active_source = "VCI"
        fetcher_class.return_value.get_data.side_effect = lambda data_type: (
            _price_history() if data_type == "history" else None
        )

        result = StockScorer("FPT").analyze()

        self.assertNotIn("error", result)
        self.assertEqual(result["symbol"], "FPT")
        self.assertEqual(result["price"]["current"], 159.0)
        self.assertEqual(
            {
                "perfect_order",
                "price",
                "expansion",
                "convergence",
                "golden_cross",
                "death_cross",
                "momentum",
                "price_position",
                "volume_analysis",
            },
            set(result) - {
                "symbol", "analyzed_at", "data_as_of", "data_source",
                "data_price_mode", "cash_dividend_adjustments",
            },
        )
        self.assertEqual(result["data_as_of"], "2026-03-01")
        self.assertEqual(result["data_source"], "VCI")


class FetchPricesContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        script_path = Path(__file__).parents[1] / "scripts" / "fetch_prices.py"
        spec = importlib.util.spec_from_file_location("fetch_prices", script_path)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_price_response_shape_and_calculation_are_unchanged(self):
        history = _price_history(rows=2)
        quote = Mock()
        quote.history.return_value = history

        with patch.object(self.module, "Quote", return_value=quote) as quote_class:
            result = self.module.fetch_prices(["FPT"])

        quote_class.assert_called_once_with(symbol="FPT", source="VCI")
        quote.history.assert_called_once_with(count_back=2)
        self.assertEqual(
            result,
            {"FPT": {"price": 101.0, "changePercent": 1.0}},
        )

    def test_price_fetch_falls_back_to_kbs_when_vci_has_no_data(self):
        primary_quote = Mock()
        primary_quote.history.return_value = None
        fallback_quote = Mock()
        fallback_quote.history.return_value = _price_history(rows=2)

        with patch.object(
            self.module,
            "Quote",
            side_effect=[primary_quote, fallback_quote],
        ) as quote_class:
            result = self.module.fetch_prices(["VCB"])

        self.assertEqual(
            [call.kwargs for call in quote_class.call_args_list],
            [
                {"symbol": "VCB", "source": "VCI"},
                {"symbol": "VCB", "source": "KBS"},
            ],
        )
        self.assertEqual(
            result,
            {"VCB": {"price": 101.0, "changePercent": 1.0}},
        )


class DependencyContractTests(unittest.TestCase):
    def test_verified_vnstock_version_is_installed(self):
        self.assertEqual(importlib.metadata.version("vnstock"), "4.0.5")


if __name__ == "__main__":
    unittest.main()
