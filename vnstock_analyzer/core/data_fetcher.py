"""
Data fetcher module - Fetch và cache data từ vnstock API với error handling
"""

import sys
import time
import logging

from .vnstock_client import Quote


HISTORY_COUNT_BACK = 250


class DataFetcher:
    """Fetch và cache data với retry logic và graceful degradation"""
    
    def __init__(self, symbol, source='VCI'):
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
        self.fallback_source = 'KBS' if source.upper() == 'VCI' else None
        
        try:
            self.quote = Quote(symbol=symbol, source=source)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize data fetcher for {symbol}: {e}")
        
        self.data_cache = {}
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.timeout = 30  # seconds per request
        
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
                
                # Check if it's a network/API error
                if any(keyword in error_msg.lower() for keyword in ['502', 'bad gateway', 'timeout', 'connection', 'network']):
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
            
            history = self._retry_with_backoff(
                self.quote.history,
                "Lịch sử giá",
                count_back=HISTORY_COUNT_BACK,
                # Quote.history already retries transient failures internally.
                max_attempts=1,
                report_final_error=not self.fallback_source
            )

            if history is None and self.fallback_source:
                print(
                    f"  ⚠️  {self.source} không phản hồi, chuyển sang "
                    f"{self.fallback_source}...",
                    file=sys.stderr
                )
                try:
                    fallback_quote = Quote(
                        symbol=self.symbol,
                        source=self.fallback_source
                    )
                    history = self._retry_with_backoff(
                        fallback_quote.history,
                        f"Lịch sử giá ({self.fallback_source})",
                        count_back=HISTORY_COUNT_BACK,
                        max_attempts=1
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
                self.data_cache['history'] = history
                print(f"  ✅ Lấy được {len(history)} ngày giao dịch", file=sys.stderr)
                has_critical_data = True
            else:
                print(f"  ❌ CRITICAL: Không lấy được lịch sử giá", file=sys.stderr)
                return False  # Cannot proceed without price history
            
            # 2-5: Non-critical data - fail silently
            # self._fetch_optional_data()
            
            if has_critical_data:
                print(f"✅ Fetch data thành công (có thể thiếu một số data phụ)\n", file=sys.stderr)
            
            return has_critical_data
            
        except Exception as e:
            print(f"❌ Lỗi nghiêm trọng khi fetch data: {e}", file=sys.stderr)
            return False
    
    def _fetch_optional_data(self):
        """Fetch optional data - không ảnh hưởng nếu fail"""
        
        # 2. Financial ratios (OPTIONAL)
        print(f"  ⏳ Lấy chỉ số tài chính...", file=sys.stderr)
        ratio = self._retry_with_backoff(
            self.stock.finance.ratio,
            "Chỉ số tài chính",
            period='quarter'
        )
        
        if ratio is not None:
            self.data_cache['ratio'] = ratio
            print(f"  ✅ Lấy được {len(ratio)} quý dữ liệu tài chính", file=sys.stderr)
        else:
            self.data_cache['ratio'] = None
            print(f"  ⚠️  Bỏ qua ratio (không bắt buộc)", file=sys.stderr)
        
        # 3. Company overview (OPTIONAL)
        print(f"  ⏳ Lấy thông tin công ty...", file=sys.stderr)
        overview = self._retry_with_backoff(
            self.stock.company.overview,
            "Thông tin công ty"
        )
        
        if overview is not None:
            self.data_cache['overview'] = overview
            print(f"  ✅ Lấy được thông tin công ty", file=sys.stderr)
        else:
            self.data_cache['overview'] = None
            print(f"  ⚠️  Bỏ qua overview (không bắt buộc)", file=sys.stderr)
        
        # 4. Shareholders (OPTIONAL)
        print(f"  ⏳ Lấy danh sách cổ đông...", file=sys.stderr)
        shareholders = self._retry_with_backoff(
            self.stock.company.shareholders,
            "Danh sách cổ đông"
        )
        
        if shareholders is not None:
            self.data_cache['shareholders'] = shareholders
            print(f"  ✅ Lấy được danh sách cổ đông", file=sys.stderr)
        else:
            self.data_cache['shareholders'] = None
            print(f"  ⚠️  Bỏ qua shareholders (không bắt buộc)", file=sys.stderr)
        
        # 5. Insider deals (OPTIONAL - often not available)
        print(f"  ⏳ Lấy giao dịch nội bộ...", file=sys.stderr)
        try:
            if hasattr(self.stock.company, 'insider_deals'):
                insider = self._retry_with_backoff(
                    self.stock.company.insider_deals,
                    "Giao dịch nội bộ"
                )
                if insider is not None:
                    self.data_cache['insider'] = insider
                    print(f"  ✅ Lấy được giao dịch nội bộ", file=sys.stderr)
                else:
                    self.data_cache['insider'] = None
                    print(f"  ⚠️  Bỏ qua insider deals (không bắt buộc)", file=sys.stderr)
            else:
                self.data_cache['insider'] = None
                print(f"  ⚠️  API không hỗ trợ insider deals", file=sys.stderr)
        except Exception:
            self.data_cache['insider'] = None
            print(f"  ⚠️  Bỏ qua insider deals (không khả dụng)", file=sys.stderr)
    
    def get_data(self, data_type):
        """
        Lấy data từ cache
        
        Args:
            data_type: Type of data ('history', 'ratio', 'overview', 'shareholders', 'insider')
            
        Returns:
            Cached dataframe or None
        """
        return self.data_cache.get(data_type)
