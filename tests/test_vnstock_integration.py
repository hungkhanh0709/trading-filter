import importlib.metadata
import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pandas as pd

from vnstock_analyzer.analyzers.technical import TechnicalAnalyzer
from vnstock_analyzer.analyzers.technical_modules.ma_detector import detect_golden_cross
from vnstock_analyzer.analyzers.technical_modules.volume_analyzer import analyze_volume_trend
from vnstock_analyzer.core.data_fetcher import DataFetcher, HISTORY_COUNT_BACK
from vnstock_analyzer.core.price_normalizer import (
    normalize_price_history,
    price_tick,
    round_price_to_tick,
)
from vnstock_analyzer.core.vnstock_client import _safe_hosting_service
from vnstock_analyzer.stock_analyzer import StockAnalyzer


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
        self.assertIsNot(fetcher.get_data("history"), history)
        pd.testing.assert_frame_equal(fetcher.get_data("history"), history)
        self.assertEqual(fetcher.get_data("price_normalization"), "EXCHANGE_TICK_HALF_UP")
        self.assertEqual(fetcher.get_data("exchange"), "HOSE")

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
        self.assertIsNot(fetcher.get_data("history"), fallback_history)
        pd.testing.assert_frame_equal(fetcher.get_data("history"), fallback_history)
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

    @patch("vnstock_analyzer.core.data_fetcher.Reference")
    @patch("vnstock_analyzer.core.data_fetcher.Quote")
    def test_normalizes_ohlc_after_cash_dividend_restoration(self, quote_class, reference_class):
        history = pd.DataFrame({
            "time": pd.to_datetime(["2026-06-25", "2026-06-26"]),
            "open": [11.357, 13.208],
            "high": [11.379, 13.274],
            "low": [11.301, 13.181],
            "close": [11.358, 13.208],
            "volume": [1_000_000, 2_000_000],
        })
        reference_class.return_value.events.return_value.calendar.return_value = pd.DataFrame({
            "category": ["DIVIDEND"],
            "exright_date": ["2026-06-26"],
            "value_per_share": [1850.0],
        })
        quote_class.return_value.history.return_value = history

        fetcher = DataFetcher("NVL", exchange="HOSE")
        fetcher.max_retries = 1

        self.assertTrue(fetcher.fetch_all_data())
        normalized = fetcher.get_data("history")
        self.assertEqual(normalized.iloc[0]["close"], 13.2)
        self.assertEqual(normalized.iloc[1]["close"], 13.2)
        self.assertEqual(normalized.iloc[1]["high"], 13.25)
        self.assertEqual(normalized.iloc[1]["volume"], 2_000_000)


class PriceNormalizationTests(unittest.TestCase):
    def test_hose_uses_all_three_quotation_bands(self):
        self.assertEqual(price_tick(9.99, "HOSE"), 0.01)
        self.assertEqual(price_tick(13.2, "HOSE"), 0.05)
        self.assertEqual(price_tick(50.0, "HOSE"), 0.1)
        self.assertEqual(round_price_to_tick(9.994, "HOSE"), 9.99)
        self.assertEqual(round_price_to_tick(13.208, "HOSE"), 13.2)
        self.assertEqual(round_price_to_tick(13.225, "HOSE"), 13.25)
        self.assertEqual(round_price_to_tick(50.04, "HOSE"), 50.0)

    def test_hnx_and_upcom_use_one_hundred_dong_tick(self):
        self.assertEqual(price_tick(13.2, "HNX"), 0.1)
        self.assertEqual(price_tick(13.2, "UPCOM"), 0.1)
        self.assertEqual(round_price_to_tick(13.25, "HNX"), 13.3)

    def test_normalizes_every_ohlc_column_without_mutating_source(self):
        source = pd.DataFrame({
            "open": [13.208],
            "high": [13.274],
            "low": [13.181],
            "close": [13.225],
            "volume": [123456],
        })

        result = normalize_price_history(source, "HOSE")

        self.assertEqual(result.iloc[0][["open", "high", "low", "close"]].tolist(), [13.2, 13.25, 13.2, 13.25])
        self.assertEqual(result.iloc[0]["volume"], 123456)
        self.assertEqual(source.iloc[0]["close"], 13.225)


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

    def test_analysis_exposes_additive_potential_context(self):
        result = TechnicalAnalyzer(_price_history(rows=250)).get_analysis()["ma_analysis"]

        self.assertNotIn("score", result)
        self.assertNotIn("status", result)
        self.assertNotIn("reasons", result)
        self.assertIn("convergence_pct", result["convergence"])
        self.assertIn("recent_crosses", result["golden_cross"])
        self.assertEqual(result["price_position"]["close"], 349.0)
        self.assertEqual(result["price_position"]["ma_type"], "EMA")
        self.assertEqual(result["price_position"]["ma_source"], "close")
        self.assertEqual(result["price_position"]["ema_seed"], "SMA")
        self.assertIn("EMA50: 324.5", result["price_position"]["tooltip"])
        for key in ("ma10", "ma20", "ma50"):
            self.assertGreater(result["price_position"][key], 0)

    def test_golden_cross_exposes_recency_without_changing_today_flag(self):
        frame = pd.DataFrame({
            "MA10": [99.0] * 51 + [101.0] * 3,
            "MA20": [100.0] * 54,
            "MA50": [98.0] * 54,
        })

        result = detect_golden_cross(frame)

        self.assertFalse(result["has_cross"])
        self.assertEqual(result["recent_crosses"][0]["type"], "MA10_MA20")
        self.assertEqual(result["recent_crosses"][0]["days_ago"], 2)

    def test_golden_cross_empty_state_describes_the_actual_lookback(self):
        frame = pd.DataFrame({
            "MA10": [99.0] * 54,
            "MA20": [100.0] * 54,
            "MA50": [101.0] * 54,
        })

        result = detect_golden_cross(frame)

        self.assertFalse(result["has_recent_cross"])
        self.assertIn("10 phiên gần đây", result["tooltip"])

    def test_volume_ratio_uses_twenty_prior_sessions_as_baseline(self):
        history = _price_history(rows=21)
        history.loc[:19, "volume"] = 1_000_000
        history.loc[20, "volume"] = 2_000_000

        result = analyze_volume_trend(history)

        self.assertEqual(result["avg_volume"], 1_000_000)
        self.assertEqual(result["volume_ratio"], 2.0)


class StockAnalyzerContractTests(unittest.TestCase):
    def test_uses_previous_daily_bar_while_today_session_is_unfinished(self):
        history = _price_history(rows=2)
        history.loc[0, "time"] = "2026-08-10"
        history.loc[1, "time"] = "2026-08-11"
        during_session = datetime(2026, 8, 11, 10, 30, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))

        completed = StockAnalyzer._completed_daily_history(history, now=during_session)

        self.assertEqual(len(completed), 1)
        self.assertEqual(str(completed.iloc[-1]["time"])[:10], "2026-08-10")

    def test_uses_today_daily_bar_after_the_session_is_complete(self):
        history = _price_history(rows=2)
        history.loc[0, "time"] = "2026-08-10"
        history.loc[1, "time"] = "2026-08-11"
        after_session = datetime(2026, 8, 11, 15, 1, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))

        completed = StockAnalyzer._completed_daily_history(history, now=after_session)

        self.assertEqual(len(completed), 2)

    @patch("vnstock_analyzer.stock_analyzer.DataFetcher")
    def test_analysis_response_keeps_existing_top_level_contract(self, fetcher_class):
        fetcher_class.return_value.fetch_all_data.return_value = True
        fetcher_class.return_value.active_source = "VCI"
        fetcher_class.return_value.get_data.side_effect = lambda data_type: (
            _price_history() if data_type == "history" else None
        )

        result = StockAnalyzer("FPT").analyze()

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
                "data_exchange", "price_normalization", "data_price_mode",
                "cash_dividend_adjustments",
            },
        )
        self.assertEqual(result["data_as_of"], "2026-03-01")
        self.assertEqual(result["data_source"], "VCI")
        self.assertEqual(result["data_exchange"], "HOSE")
        self.assertEqual(result["price_normalization"], "EXCHANGE_TICK_HALF_UP")
        self.assertEqual(result["price"]["tickSize"], 0.1)


class DependencyContractTests(unittest.TestCase):
    def test_local_hosting_detector_workaround_is_narrow(self):
        def broken_detector():
            raise UnboundLocalError("hosting_service")

        self.assertEqual(
            _safe_hosting_service(broken_detector),
            "Local or Unknown",
        )
        self.assertEqual(_safe_hosting_service(lambda: "Google Colab"), "Google Colab")

    def test_verified_vnstock_ecosystem_versions_are_installed(self):
        self.assertEqual(importlib.metadata.version("vnstock"), "4.0.6")
        self.assertEqual(importlib.metadata.version("vnai"), "2.5.7")


if __name__ == "__main__":
    unittest.main()
