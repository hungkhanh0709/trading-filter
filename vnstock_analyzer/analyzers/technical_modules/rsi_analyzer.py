"""
RSI Analyzer - Phân tích Relative Strength Index
"""

class RSIAnalyzer:
    """Chuyên phân tích RSI"""
    
    def __init__(self, df):
        """
        Args:
            df: DataFrame đã tính sẵn RSI
        """
        self.df = df
    
    def analyze(self):
        """
        Phân tích RSI và trả về kết quả với reasons dạng array
        
        Returns:
            dict: {
                'score': float (0-5),
                'status': str,
                'reasons': list of str,
                'details': {
                    'rsi_value': float,
                    'zone': str (OVERSOLD/BALANCED/OVERBOUGHT)
                }
            }
        """
        if self.df is None or len(self.df) < 14:
            return {
                'score': 0,
                'status': 'NA',
                'reasons': ['Không đủ dữ liệu'],
                'details': {}
            }
        
        rsi = self.df.iloc[-1]['RSI']
        score = 0
        reasons = []
        
        # Xác định zone
        if rsi < 30:
            zone = 'OVERSOLD'
        elif rsi > 70:
            zone = 'OVERBOUGHT'
        else:
            zone = 'BALANCED'
        
        # Scoring logic
        if 40 <= rsi <= 60:
            score = 5
            reasons.append(f"✅ RSI ở vùng cân bằng ({rsi:.1f})")
            reasons.append("Tiềm năng tốt cho cả xu hướng tăng và giảm")
        elif 30 <= rsi < 40:
            score = 4
            reasons.append(f"🔥 RSI oversold recovery ({rsi:.1f})")
            reasons.append("Cơ hội mua - giá có thể phục hồi")
        elif 60 < rsi <= 70:
            score = 3
            reasons.append(f"➕ RSI tích cực ({rsi:.1f})")
            reasons.append("Xu hướng tăng nhưng cần thận trọng")
        elif rsi > 70:
            score = 2
            reasons.append(f"⚠️ RSI overbought ({rsi:.1f})")
            reasons.append("Cảnh báo - giá có thể điều chỉnh")
        else:  # rsi < 30
            score = 3
            reasons.append(f"💎 RSI quá bán ({rsi:.1f})")
            reasons.append("Có thể rebound mạnh nếu có xúc tác")
        
        # Map score to status
        if score == 5:
            status = 'EXCELLENT'
        elif score == 4:
            status = 'GOOD'
        elif score == 3:
            status = 'ACCEPTABLE'
        elif score == 2:
            status = 'WARNING'
        else:
            status = 'POOR'
        
        return {
            'score': score,
            'status': status,
            'reasons': reasons,
            'details': {
                'rsi_value': rsi,
                'zone': zone
            }
        }
