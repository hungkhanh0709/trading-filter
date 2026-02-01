"""
Data fetcher module - Fetch và cache data từ vnstock API
"""

import sys
from datetime import datetime, timedelta
from vnstock import Vnstock


class DataFetcher:
    """Fetch và cache data để tránh rate limit"""
    
    def __init__(self, symbol, source='KBS'):
        """
        Initialize data fetcher
        
        Args:
            symbol: Stock symbol (e.g., 'HDB', 'FPT')
            source: Data source (default: 'KBS')
        """
        self.symbol = symbol
        self.source = source
        self.stock = Vnstock().stock(symbol=symbol, source=source)
        self.data_cache = {}
        
    def fetch_all_data(self):
        """
        Fetch toàn bộ data 1 lần, cache lại
        
        Returns:
            bool: True if successful, False otherwise
        """
        print(f"📊 Đang fetch data cho {self.symbol}...", file=sys.stderr)
        
        try:
            # 1. Historical price data (3 tháng)
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            
            print(f"  ⏳ Lấy lịch sử giá ({start_date} -> {end_date})...", file=sys.stderr)
            self.data_cache['history'] = self.stock.quote.history(start=start_date, end=end_date)
            print(f"  ✅ Lấy được {len(self.data_cache['history'])} ngày giao dịch", file=sys.stderr)
            
            # 2. Financial ratios
            print(f"  ⏳ Lấy chỉ số tài chính...", file=sys.stderr)
            try:
                self.data_cache['ratio'] = self.stock.finance.ratio(period='quarter')
                print(f"  ✅ Lấy được {len(self.data_cache['ratio'])} quý dữ liệu tài chính", file=sys.stderr)
            except Exception as e:
                print(f"  ⚠️  Không lấy được ratio: {e}", file=sys.stderr)
                self.data_cache['ratio'] = None
            
            # 3. Company info
            print(f"  ⏳ Lấy thông tin công ty...", file=sys.stderr)
            try:
                self.data_cache['overview'] = self.stock.company.overview()
                print(f"  ✅ Lấy được thông tin công ty", file=sys.stderr)
            except Exception as e:
                print(f"  ⚠️  Không lấy được overview: {e}", file=sys.stderr)
                self.data_cache['overview'] = None
            
            # 4. Shareholders
            print(f"  ⏳ Lấy danh sách cổ đông...", file=sys.stderr)
            try:
                self.data_cache['shareholders'] = self.stock.company.shareholders()
                print(f"  ✅ Lấy được danh sách cổ đông", file=sys.stderr)
            except Exception as e:
                print(f"  ⚠️  Không lấy được shareholders: {e}", file=sys.stderr)
                self.data_cache['shareholders'] = None
            
            # 5. Insider deals
            print(f"  ⏳ Lấy giao dịch nội bộ...", file=sys.stderr)
            try:
                self.data_cache['insider'] = self.stock.company.insider_deals()
                print(f"  ✅ Lấy được giao dịch nội bộ", file=sys.stderr)
            except Exception as e:
                print(f"  ⚠️  Không lấy được insider deals: {e}", file=sys.stderr)
                self.data_cache['insider'] = None
            
            print(f"✅ Hoàn thành fetch data cho {self.symbol}!\n", file=sys.stderr)
            return True
            
        except Exception as e:
            print(f"❌ Lỗi khi fetch data: {e}", file=sys.stderr)
            return False
    
    def get_data(self, data_type):
        """
        Lấy data từ cache
        
        Args:
            data_type: Type of data ('history', 'ratio', 'overview', 'shareholders', 'insider')
            
        Returns:
            Cached dataframe or None
        """
        return self.data_cache.get(data_type)
