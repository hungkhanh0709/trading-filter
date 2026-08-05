import importlib.metadata
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

from vnstock_analyzer.analyzers.technical import TechnicalAnalyzer
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

    @patch("vnstock_analyzer.core.data_fetcher.Quote")
    def test_fetches_and_caches_history_with_existing_contract(self, quote_class):
        history = _price_history()
        quote_class.return_value.history.return_value = history
        fetcher = DataFetcher("FPT")
        fetcher.max_retries = 1

        self.assertTrue(fetcher.fetch_all_data())
        self.assertIs(fetcher.get_data("history"), history)

        call = quote_class.return_value.history.call_args
        self.assertEqual(call.kwargs, {"count_back": HISTORY_COUNT_BACK})

    @patch("vnstock_analyzer.core.data_fetcher.Quote")
    def test_falls_back_to_kbs_after_vci_retries_are_exhausted(self, quote_class):
        primary_quote = Mock()
        primary_quote.history.side_effect = ConnectionError("read timeout=30")
        fallback_quote = Mock()
        fallback_history = _price_history()
        fallback_quote.history.return_value = fallback_history
        quote_class.side_effect = [primary_quote, fallback_quote]

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


class TechnicalAnalyzerContractTests(unittest.TestCase):
    def test_calculates_only_ma10_ma20_ma50(self):
        analyzer = TechnicalAnalyzer(_price_history(rows=250))

        self.assertIn("MA10", analyzer.df.columns)
        self.assertIn("MA20", analyzer.df.columns)
        self.assertIn("MA50", analyzer.df.columns)
        self.assertNotIn("MA200", analyzer.df.columns)


class StockScorerContractTests(unittest.TestCase):
    @patch("vnstock_analyzer.scorer.DataFetcher")
    def test_analysis_response_keeps_existing_top_level_contract(self, fetcher_class):
        fetcher_class.return_value.fetch_all_data.return_value = True
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
                "oracle",
            },
            set(result) - {"symbol", "analyzed_at"},
        )


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
