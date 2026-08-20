#!/usr/bin/env python3
"""Long-lived JSON-lines worker for stock analysis."""

import contextlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vnstock_analyzer import StockAnalyzer
from vnstock_analyzer.core import DataFetcher
from vnstock_analyzer.utils import NumpyEncoder, get_logger


logger = get_logger("WORKER")


def warm_up():
    """Pay vnstock/vnai initialization cost once, before the server is ready."""
    with contextlib.redirect_stdout(sys.stderr):
        DataFetcher("FPT", exchange="HOSE")


def analyze_request(request):
    request_id = request.get("id")
    symbol = str(request.get("symbol", "")).upper()
    exchange = str(request.get("exchange", "HOSE")).upper()

    if not symbol:
        return request_id, {"error": "Missing symbol", "symbol": symbol}

    logger.info(f"Starting analysis for {symbol}")
    started_at = time.monotonic()
    try:
        # Third-party startup/promotional output must never corrupt the JSONL
        # protocol on stdout.
        with contextlib.redirect_stdout(sys.stderr):
            result = StockAnalyzer(symbol, exchange=exchange).analyze()
        logger.info(
            f"Finished analysis for {symbol} in "
            f"{time.monotonic() - started_at:.2f}s"
        )
        return request_id, result
    except Exception as error:
        logger.error(f"Unexpected error for {symbol}: {error}")
        return request_id, {
            "error": f"Lỗi không mong đợi: {error}",
            "symbol": symbol,
        }


def main():
    warmup_started_at = time.monotonic()
    try:
        warm_up()
        logger.info(
            f"Warm-up completed in {time.monotonic() - warmup_started_at:.2f}s"
        )
    except Exception as error:
        # A failed warm-up must not make the worker unusable. The real request
        # will return its normal application-level error if initialization fails.
        logger.error(f"Warm-up failed: {error}")

    print(json.dumps({"type": "ready"}), flush=True)

    for line in sys.stdin:
        try:
            request = json.loads(line)
            request_id, result = analyze_request(request)
            print(
                json.dumps(
                    {"type": "result", "id": request_id, "result": result},
                    ensure_ascii=False,
                    cls=NumpyEncoder,
                ),
                flush=True,
            )
        except Exception as error:
            request_id = request.get("id") if "request" in locals() else None
            print(
                json.dumps({
                    "type": "result",
                    "id": request_id,
                    "result": {"error": f"Worker protocol error: {error}"},
                }),
                flush=True,
            )


if __name__ == "__main__":
    main()
