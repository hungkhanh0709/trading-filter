"""
MFI Analyzer - Phân tích Money Flow Index
"""

class MFIAnalyzer:
    """Chuyên phân tích Money Flow Index (RSI kết hợp Volume)"""
    
    def __init__(self, df):
        """
        Args:
            df: DataFrame đã tính sẵn MFI và RSI
        """
        self.df = df
    
    def analyze(self):
        """
        Phân tích MFI và trả về kết quả với reasons dạng array
        
        Returns:
            dict: {
                'score': float (0-5),
                'status': str,
                'reasons': list of str,
                'details': {
                    'mfi_value': float,
                    'rsi_value': float,
                    'divergence': float,
                    'zone': str
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
        
        latest = self.df.iloc[-1]
        mfi = latest['MFI']
        rsi = latest['RSI']
        score = 0
        reasons = []
        
        # Xác định zone
        if mfi < 20:
            zone = 'OVERSOLD'
        elif mfi > 80:
            zone = 'OVERBOUGHT'
        else:
            zone = 'BALANCED'
        
        # === 1. MFI SCORING ===
        if 40 <= mfi <= 60:
            score = 5
            reasons.append(f"✅ MFI cân bằng ({mfi:.1f})")
            reasons.append("Dòng tiền ổn định - điều kiện tốt")
        elif 20 <= mfi < 40:
            score = 4
            reasons.append(f"🔥 MFI oversold recovery ({mfi:.1f})")
            reasons.append("Dòng tiền bắt đầu quay lại")
        elif 60 < mfi <= 80:
            score = 3
            reasons.append(f"➕ MFI tích cực ({mfi:.1f})")
            reasons.append("Dòng tiền tích cực nhưng cần theo dõi")
        elif mfi > 80:
            score = 2
            reasons.append(f"⚠️ MFI overbought ({mfi:.1f})")
            reasons.append("Dòng tiền quá mạnh - có thể điều chỉnh")
        else:  # mfi < 20
            score = 3
            reasons.append(f"💎 MFI oversold ({mfi:.1f})")
            reasons.append("Dòng tiền rất yếu - tiềm năng phục hồi")
        
        # === 2. MFI vs RSI DIVERGENCE ===
        mfi_rsi_diff = abs(mfi - rsi)
        
        if mfi_rsi_diff > 15:
            if mfi > rsi:
                reasons.append(f"✅ Volume mạnh support giá (MFI-RSI: +{mfi_rsi_diff:.1f})")
                reasons.append("Dòng tiền thực mạnh hơn chỉ báo giá")
            else:
                reasons.append(f"⚠️ Volume yếu, cảnh báo divergence (MFI-RSI: -{mfi_rsi_diff:.1f})")
                reasons.append("Giá tăng nhưng dòng tiền không theo kịp")
        
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
                'mfi_value': mfi,
                'rsi_value': rsi,
                'divergence': mfi_rsi_diff,
                'zone': zone
            }
        }
