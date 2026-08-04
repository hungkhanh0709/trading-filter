"""
Data fetcher module - Fetch và cache data từ vnstock API với error handling
"""

import sys
import time
from datetime import datetime, timedelta
# Direct import to bypass Company component error
from vnstock.explorer.vci.quote import Quote


class DataFetcher:
    """Fetch và cache data với retry logic và graceful degradation"""
    
    def __init__(self, symbol, source='VCI'):
        """
        Initialize data fetcher
        
        Args:
            symbol: Stock symbol (e.g., 'HDB', 'FPT')
            source: Data source (default: 'VCI')
            
        Note: Direct Quote initialization to bypass VCI Company component error
        """
        self.symbol = symbol
        self.source = source
        
        # Direct initialization to avoid Company component error in VCI
        try:
            if source == 'VCI':
                self.quote = Quote(symbol)
            else:
                # Fallback to legacy method for other sources
                from vnstock import Vnstock
                self.stock = Vnstock().stock(symbol=symbol, source=source)
                self.quote = self.stock.quote
        except Exception as e:
            raise RuntimeError(f"Failed to initialize data fetcher for {symbol}: {e}")
        
        self.data_cache = {}
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.timeout = 30  # seconds per request
        
    def _retry_with_backoff(self, func, description, *args, **kwargs):
        """
        Execute function with exponential backoff retry
        
        Args:
            func: Function to execute
            description: Description for logging
            *args, **kwargs: Arguments to pass to func
            
        Returns:
            Result from func or None on failure
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                
                # Validate result
                if result is None or (hasattr(result, 'empty') and result.empty):
                    if attempt < self.max_retries:
                        print(f"  ⚠️  {description}: Dữ liệu rỗng, thử lại {attempt}/{self.max_retries}...", file=sys.stderr)
                        time.sleep(self.retry_delay * attempt)
                        continue
                    return None
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                
                # Check if it's a network/API error
                if any(keyword in error_msg.lower() for keyword in ['502', 'bad gateway', 'timeout', 'connection', 'network']):
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay * (2 ** (attempt - 1))  # exponential backoff
                        print(f"  ⚠️  {description}: Lỗi network ({error_msg[:50]}...), thử lại sau {wait_time}s ({attempt}/{self.max_retries})", file=sys.stderr)
                        time.sleep(wait_time)
                        continue
                
                # Non-retryable error or last attempt
                if attempt == self.max_retries:
                    print(f"  ❌ {description}: {error_msg}", file=sys.stderr)
                    return None
                else:
                    print(f"  ⚠️  {description}: Lỗi, thử lại ({attempt}/{self.max_retries})...", file=sys.stderr)
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
            # 1. Historical price data - Request 2 years for better EMA accuracy
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
            
            print(f"  ⏳ Lấy lịch sử giá ({start_date} -> {end_date})...", file=sys.stderr)
            
            history = self._retry_with_backoff(
                self.quote.history,
                "Lịch sử giá",
                start=start_date,
                end=end_date
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
