"""
Liquidity Analyzer - Phân tích thanh khoản (15 điểm)
"""


class LiquidityAnalyzer:
    """Phân tích thanh khoản - 15 điểm"""
    
    def __init__(self, df_history):
        """
        Initialize liquidity analyzer
        
        Args:
            df_history: Historical price dataframe
        """
        self.df = df_history
    
    def get_total_score(self):
        """
        Tổng điểm Liquidity - 15 điểm
        
        Returns:
            dict: Score breakdown
        """
        if self.df is None or len(self.df) < 20:
            return {
                'total': 0,
                'max': 15,
                'breakdown': {
                    'avg_volume': {'score': 0, 'max': 10, 'reason': 'Không đủ dữ liệu'},
                    'volatility': {'score': 0, 'max': 5, 'reason': 'Không đủ dữ liệu'}
                }
            }
        
        # Volume consistency - 10 điểm
        avg_vol = self.df['volume'].mean()
        vol_score = 0
        
        if avg_vol > 1_000_000:
            vol_score = 10
            vol_reason = f"✅ Thanh khoản rất cao ({avg_vol/1e6:.1f}M cp/ngày)"
        elif avg_vol > 500_000:
            vol_score = 8
            vol_reason = f"✅ Thanh khoản tốt ({avg_vol/1e3:.0f}K cp/ngày)"
        elif avg_vol > 200_000:
            vol_score = 5
            vol_reason = f"➕ Thanh khoản chấp nhận ({avg_vol/1e3:.0f}K cp/ngày)"
        else:
            vol_score = 2
            vol_reason = f"⚠️  Thanh khoản thấp ({avg_vol/1e3:.0f}K cp/ngày)"
        
        # Volatility - 5 điểm
        volatility = self.df['close'].pct_change().std() * 100
        vol_score_2 = 0
        
        if 1 < volatility < 3:
            vol_score_2 = 5
            vol_reason_2 = f"✅ Biến động hợp lý ({volatility:.1f}%)"
        elif 3 <= volatility < 5:
            vol_score_2 = 3
            vol_reason_2 = f"➕ Biến động trung bình ({volatility:.1f}%)"
        else:
            vol_score_2 = 1
            vol_reason_2 = f"⚠️  Biến động cao ({volatility:.1f}%)"
        
        return {
            'total': vol_score + vol_score_2,
            'max': 15,
            'breakdown': {
                'avg_volume': {'score': vol_score, 'max': 10, 'reason': vol_reason},
                'volatility': {'score': vol_score_2, 'max': 5, 'reason': vol_reason_2}
            }
        }
