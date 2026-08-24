"""
Data fetcher module - Fetch và cache data từ vnstock API với error handling
"""

import sys
import time
import logging
import os

import pandas as pd

from .vnstock_client import Quote, Reference, fetch_history_once
from .price_normalizer import normalize_exchange, normalize_price_history


# The largest direct lookback is EMA50 plus its 20-session momentum window
# (about 70 bars), but that is not enough for a stable SMA-seeded EMA50.
# At 250 bars the seed's remaining weight is only ~0.0335%, while 500 bars
# doubles the payload for no meaningful signal improvement.
HISTORY_COUNT_BACK = 250
SOURCE_FAILURE_COOLDOWN_SECONDS = float(
    os.environ.get("VNSTOCK_SOURCE_COOLDOWN_SECONDS", "300")
)
_SOURCE_UNAVAILABLE_UNTIL = {}


def _source_is_cooling_down(source):
    return _SOURCE_UNAVAILABLE_UNTIL.get(source.upper(), 0) > time.monotonic()


def _mark_source_unavailable(source):
    _SOURCE_UNAVAILABLE_UNTIL[source.upper()] = (
        time.monotonic() + SOURCE_FAILURE_COOLDOWN_SECONDS
    )


def _mark_source_available(source):
    _SOURCE_UNAVAILABLE_UNTIL.pop(source.upper(), None)


class DataFetcher:
    """Fetch và cache data với retry logic và graceful degradation"""
    
    def __init__(self, symbol, source='VCI', exchange='HOSE'):
        """
        Initialize data fetcher
        
        Args:
            symbol: Stock symbol (e.g., 'HDB', 'FPT')
            source: Data source (default: 'VCI')
            
        Note: Quote is used directly because this analyzer only needs price data.
        """
        self.symbol = symbol
        self.source = source
        self.active_source = source
        self.exchange = normalize_exchange(exchange)
        self.fallback_source = 'KBS' if source.upper() == 'VCI' else None
        
        try:
            self.quote = Quote(symbol=symbol, source=source)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize data fetcher for {symbol}: {e}")
        
        self.data_cache = {}
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self._last_failure_transient = False
        
    def _retry_with_backoff(
        self,
        func,
        description,
        *args,
        max_attempts=None,
        report_final_error=True,
        **kwargs
    ):
        """
        Execute function with exponential backoff retry
        
        Args:
            func: Function to execute
            description: Description for logging
            *args, **kwargs: Arguments to pass to func
            
        Returns:
            Result from func or None on failure
        """
        attempt_limit = max_attempts or self.max_retries
        self._last_failure_transient = False

        for attempt in range(1, attempt_limit + 1):
            try:
                # vnstock logs every internal retry as ERROR. Only surface the
                # final application-level warning after its own retries finish.
                client_logger = logging.getLogger('vnstock.core.utils.client')
                previous_level = client_logger.level
                client_logger.setLevel(logging.CRITICAL)
                try:
                    result = func(*args, **kwargs)
                finally:
                    client_logger.setLevel(previous_level)
                
                # Validate result
                if result is None or (hasattr(result, 'empty') and result.empty):
                    if attempt < attempt_limit:
                        print(f"  ⚠️  {description}: Dữ liệu rỗng, thử lại {attempt}/{attempt_limit}...", file=sys.stderr)
                        time.sleep(self.retry_delay * attempt)
                        continue
                    return None
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                is_transient = any(
                    keyword in error_msg.lower()
                    for keyword in [
                        '502', '503', '504', 'bad gateway', 'timeout',
                        'connection', 'network', 'api request failed',
                        'failed to fetch data',
                    ]
                )
                self._last_failure_transient = is_transient
                
                # Check if it's a network/API error
                if is_transient:
                    if attempt < attempt_limit:
                        wait_time = self.retry_delay * (2 ** (attempt - 1))  # exponential backoff
                        print(f"  ⚠️  {description}: Lỗi network ({error_msg[:50]}...), thử lại sau {wait_time}s ({attempt}/{attempt_limit})", file=sys.stderr)
                        time.sleep(wait_time)
                        continue
                
                # Non-retryable error or last attempt
                if attempt == attempt_limit:
                    if report_final_error:
                        print(f"  ❌ {description}: {error_msg}", file=sys.stderr)
                    return None
                else:
                    print(f"  ⚠️  {description}: Lỗi, thử lại ({attempt}/{attempt_limit})...", file=sys.stderr)
                    time.sleep(self.retry_delay * attempt)
        
        return None
        
    def fetch_all_data(self):
        """
        Fetch toàn bộ data với retry logic và graceful degradation
        
        Returns:
            bool: True if có ít nhất history data, False nếu critical data fail
        """
        print(f"📊 Đang fetch data cho {self.symbol}...", file=sys.stderr)
        
        has_critical_data = False
        
        try:
            # 1. Historical price data - enough for MA10/20/50 with buffer.
            print(
                f"  ⏳ Lấy lịch sử giá ({HISTORY_COUNT_BACK} phiên gần nhất)...",
                file=sys.stderr
            )
            
            primary_started_at = time.monotonic()
            if _source_is_cooling_down(self.source):
                history = None
                print(
                    f"  ⏭️  {self.source} đang tạm nghỉ sau lỗi network; "
                    "chuyển thẳng sang nguồn dự phòng",
                    file=sys.stderr,
                )
            else:
                history = self._retry_with_backoff(
                    fetch_history_once,
                    "Lịch sử giá",
                    self.quote,
                    count_back=HISTORY_COUNT_BACK,
                    # One bounded VCI attempt, followed by explicit KBS fallback.
                    max_attempts=1,
                    report_final_error=not self.fallback_source
                )
                if history is not None:
                    _mark_source_available(self.source)
                elif self._last_failure_transient:
                    _mark_source_unavailable(self.source)
            print(
                f"  ⏱️  {self.source}: "
                f"{time.monotonic() - primary_started_at:.2f}s",
                file=sys.stderr,
            )

            if history is None and self.fallback_source:
                print(
                    f"  ⚠️  {self.source} không lấy được dữ liệu, chuyển sang "
                    f"{self.fallback_source}...",
                    file=sys.stderr
                )
                try:
                    fallback_started_at = time.monotonic()
                    if _source_is_cooling_down(self.fallback_source):
                        print(
                            f"  ⏭️  {self.fallback_source} cũng đang tạm nghỉ "
                            "sau lỗi network",
                            file=sys.stderr,
                        )
                        return False
                    fallback_quote = Quote(
                        symbol=self.symbol,
                        source=self.fallback_source
                    )
                    history = self._retry_with_backoff(
                        fetch_history_once,
                        f"Lịch sử giá ({self.fallback_source})",
                        fallback_quote,
                        count_back=HISTORY_COUNT_BACK,
                        max_attempts=1
                    )
                    if history is not None:
                        _mark_source_available(self.fallback_source)
                    elif self._last_failure_transient:
                        _mark_source_unavailable(self.fallback_source)
                    print(
                        f"  ⏱️  {self.fallback_source}: "
                        f"{time.monotonic() - fallback_started_at:.2f}s",
                        file=sys.stderr,
                    )
                    if history is not None:
                        self.quote = fallback_quote
                        self.active_source = self.fallback_source
                except Exception as e:
                    print(
                        f"  ❌ Không thể khởi tạo nguồn dự phòng "
                        f"{self.fallback_source}: {e}",
                        file=sys.stderr
                    )
            
            if history is not None and not history.empty:
                events_started_at = time.monotonic()
                dividend_events = self._fetch_dividend_events(history)
                print(
                    f"  ⏱️  Sự kiện cổ tức: "
                    f"{time.monotonic() - events_started_at:.2f}s",
                    file=sys.stderr,
                )
                history, adjustments = self._restore_unadjusted_cash_dividends(
                    history,
                    dividend_events,
                )
                history = normalize_price_history(history, self.exchange)
                self.data_cache['history'] = history
                self.data_cache['price_adjustments'] = adjustments
                self.data_cache['price_adjustment_status'] = (
                    'UNADJUSTED_RESTORED'
                    if isinstance(dividend_events, pd.DataFrame)
                    else 'SOURCE_ADJUSTMENT_UNKNOWN'
                )
                self.data_cache['price_normalization'] = 'EXCHANGE_TICK_HALF_UP'
                self.data_cache['exchange'] = self.exchange
                print(f"  ✅ Lấy được {len(history)} ngày giao dịch", file=sys.stderr)
                has_critical_data = True
            else:
                print(f"  ❌ CRITICAL: Không lấy được lịch sử giá", file=sys.stderr)
                return False  # Cannot proceed without price history
            
            if has_critical_data:
                print("✅ Fetch dữ liệu giá thành công\n", file=sys.stderr)
            
            return has_critical_data
            
        except Exception as e:
            print(f"❌ Lỗi nghiêm trọng khi fetch data: {e}", file=sys.stderr)
            return False

    def _fetch_dividend_events(self, history):
        """Fetch cash-dividend events needed to restore unadjusted OHLC."""
        if history is None or history.empty or 'time' not in history.columns:
            return None
        try:
            dates = pd.to_datetime(history['time'], errors='coerce').dropna()
            if dates.empty:
                return None
            events = Reference().events(self.symbol)
            return self._retry_with_backoff(
                events.calendar,
                "Sự kiện cổ tức",
                start=dates.min().date().isoformat(),
                end=dates.max().date().isoformat(),
                event_type='DIVIDEND',
                source='vci',
                max_attempts=1,
                report_final_error=False,
            )
        except Exception:
            return None

    @staticmethod
    def _restore_unadjusted_cash_dividends(history, events):
        """Reverse VCI/KBS back-adjustments to match unadjusted chart prices.

        For a cash dividend D, providers back-adjust all earlier OHLC values by
        ``(previous_close - D) / previous_close``. Events are reversed newest
        first so multiple dividends compose correctly.
        """
        if (
            history is None or history.empty or events is None or
            not isinstance(events, pd.DataFrame) or events.empty or
            'exright_date' not in events.columns or
            'value_per_share' not in events.columns
        ):
            return history, []

        result = history.copy()
        times = pd.to_datetime(result['time'], errors='coerce')
        event_rows = events.copy()
        event_rows['exright_date'] = pd.to_datetime(
            event_rows['exright_date'], errors='coerce'
        )
        event_rows['value_per_share'] = pd.to_numeric(
            event_rows['value_per_share'], errors='coerce'
        )
        event_rows = event_rows.dropna(subset=['exright_date', 'value_per_share'])
        event_rows = event_rows[event_rows['value_per_share'] > 0]
        if 'category' in event_rows.columns:
            event_rows = event_rows[event_rows['category'] == 'DIVIDEND']

        cash_by_date = event_rows.groupby('exright_date')['value_per_share'].sum()
        adjustments = []
        price_columns = [column for column in ('open', 'high', 'low', 'close') if column in result.columns]
        for ex_date, cash_vnd in cash_by_date.sort_index(ascending=False).items():
            prior_mask = times < ex_date
            if not prior_mask.any():
                continue
            adjusted_previous_close = pd.to_numeric(
                result.loc[prior_mask, 'close'], errors='coerce'
            ).dropna()
            if adjusted_previous_close.empty:
                continue

            previous_close = float(adjusted_previous_close.iloc[-1])
            cash_in_price_units = float(cash_vnd) / 1000.0
            raw_previous_close = previous_close + cash_in_price_units
            if previous_close <= 0 or raw_previous_close <= 0:
                continue
            factor = previous_close / raw_previous_close
            result.loc[prior_mask, price_columns] = (
                result.loc[prior_mask, price_columns].astype(float) / factor
            )
            adjustments.append({
                'exright_date': ex_date.date().isoformat(),
                'cash_dividend_vnd': float(cash_vnd),
                'factor': round(factor, 10),
            })

        return result, adjustments
    
    def get_data(self, data_type):
        """
        Lấy data từ cache
        
        Args:
            data_type: Cache key such as ``history`` or price metadata.
            
        Returns:
            Cached dataframe or None
        """
        return self.data_cache.get(data_type)
