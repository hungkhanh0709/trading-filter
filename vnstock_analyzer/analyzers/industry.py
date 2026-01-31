"""
Industry Analyzer - Phân tích ngành (10 điểm)
"""


class IndustryAnalyzer:
    """Phân tích ngành - 10 điểm"""
    
    def __init__(self, symbol, source='KBS'):
        """
        Initialize industry analyzer
        
        Args:
            symbol: Stock symbol
            source: Data source (default: 'KBS')
        """
        self.symbol = symbol
        self.source = source
        
    def _get_industry_info(self):
        """Lấy thông tin ngành từ Listing API"""
        try:
            from vnstock import Listing
            listing = Listing(source=self.source)
            industries = listing.symbols_by_industries()
            match = industries[industries['symbol'] == self.symbol]
            if len(match) > 0:
                return match.iloc[0]['industry_name']
        except:
            pass
        return None
    
    def _calculate_market_cap_tier(self, overview, current_price):
        """
        Tính market cap và xếp hạng
        
        Args:
            overview: Company overview dataframe
            current_price: Current stock price
            
        Returns:
            tuple: (score, description)
        """
        if overview is None or len(overview) == 0:
            return 2, "Unknown"
        
        row = overview.iloc[0]
        outstanding = row.get('outstanding_shares')
        
        if outstanding and current_price:
            market_cap = (outstanding * current_price) / 1e9
            
            if market_cap > 100_000:
                return 2, f"Large-cap ({market_cap/1000:.0f} nghìn tỷ)"
            elif market_cap > 20_000:
                return 3, f"Mid-large cap ({market_cap/1000:.0f} nghìn tỷ)"
            elif market_cap > 5_000:
                return 3, f"Mid-cap ({market_cap/1000:.0f} nghìn tỷ)"
            elif market_cap > 1_000:
                return 2, f"Small-mid cap ({market_cap/1000:.0f} nghìn tỷ)"
            else:
                return 1, f"Small-cap ({market_cap:.0f} tỷ)"
        
        return 2, "Unknown market cap"
    
    def get_total_score(self, overview, current_price):
        """
        Tổng điểm Industry - 10 điểm
        
        Args:
            overview: Company overview dataframe
            current_price: Current stock price
            
        Returns:
            dict: Score breakdown
        """
        industry_name = self._get_industry_info()
        market_cap_score, market_cap_desc = self._calculate_market_cap_tier(overview, current_price)
        
        return {
            'total': 5 + market_cap_score,
            'max': 10,
            'breakdown': {
                'industry': {'info': industry_name or 'Unknown'},
                'relative_strength': {'score': 5, 'max': 7, 'reason': 'Cần data toàn ngành để so sánh'},
                'market_position': {'score': market_cap_score, 'max': 3, 'reason': market_cap_desc}
            }
        }
