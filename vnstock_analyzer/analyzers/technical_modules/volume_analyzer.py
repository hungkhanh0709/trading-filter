"""
Volume Analyzer - Phân tích khối lượng giao dịch và OBV
"""

class VolumeAnalyzer:
    """Chuyên phân tích Volume + OBV"""
    
    def __init__(self, df):
        """
        Args:
            df: DataFrame đã tính sẵn volume indicators (vol_ma20, vol_ratio, OBV)
        """
        self.df = df
    
    def analyze(self):
        """
        Phân tích Volume + OBV và trả về kết quả với reasons dạng array
        
        Returns:
            dict: {
                'score': float (0-10),
                'status': str,
                'reasons': list of str,
                'details': {
                    'vol_ratio': float,
                    'accumulation_days': int,
                    'obv_trend': str,
                    'obv_divergence': bool
                }
            }
        """
        if self.df is None or len(self.df) < 20:
            return {
                'score': 0,
                'status': 'NA',
                'reasons': ['Không đủ dữ liệu'],
                'details': {}
            }
        
        latest = self.df.iloc[-1]
        score = 0
        reasons = []
        
        # === 1. VOLUME BREAKOUT ===
        vol_ratio = latest['vol_ratio']
        if vol_ratio > 2:
            score += 4
            reasons.append(f"🚀 Volume đột biến ({vol_ratio:.1f}x trung bình)")
            reasons.append("Có sự kiện quan trọng hoặc breakout")
        elif vol_ratio > 1.5:
            score += 3
            reasons.append(f"✅ Volume tăng mạnh ({vol_ratio:.1f}x trung bình)")
            reasons.append("Sự quan tâm của nhà đầu tư tăng cao")
        elif vol_ratio > 1:
            score += 2
            reasons.append(f"➕ Volume trên trung bình ({vol_ratio:.1f}x)")
        else:
            reasons.append(f"⚠️ Volume thấp hơn trung bình ({vol_ratio:.1f}x)")
            reasons.append("Thiếu sự quan tâm - khó có xu hướng mạnh")
        
        # === 2. PRICE + VOLUME ACCUMULATION ===
        last_5 = self.df.tail(5)
        price_up_days = (last_5['close'].diff() > 0).sum()
        vol_up_days = (last_5['volume'] > last_5['vol_ma20']).sum()
        
        if price_up_days >= 3 and vol_up_days >= 3:
            score += 3
            reasons.append(f"✅ Tích lũy mạnh ({price_up_days} ngày giá tăng + {vol_up_days} ngày volume cao)")
            reasons.append("Tiền vào mạnh - xu hướng tăng bền vững")
            accumulation_days = min(price_up_days, vol_up_days)
        elif price_up_days >= 2 and vol_up_days >= 2:
            score += 2
            reasons.append(f"➕ Có tích lũy ({price_up_days} ngày giá tăng + {vol_up_days} ngày volume cao)")
            accumulation_days = min(price_up_days, vol_up_days)
        else:
            accumulation_days = 0
        
        # === 3. OBV TREND ANALYSIS ===
        obv_trend = 'NEUTRAL'
        obv_divergence = False
        
        if 'OBV' in self.df.columns and len(self.df) >= 20:
            obv_20_ago = self.df.iloc[-20]['OBV']
            obv_now = latest['OBV']
            price_20_ago = self.df.iloc[-20]['close']
            price_now = latest['close']
            
            obv_trend_up = obv_now > obv_20_ago
            price_trend_up = price_now > price_20_ago
            
            if obv_trend_up and price_trend_up:
                score += 3
                reasons.append("✅ OBV + Giá cùng tăng (confirmation)")
                reasons.append("Dòng tiền và giá đồng thuận - tín hiệu mạnh")
                obv_trend = 'UP_WITH_PRICE'
            elif obv_trend_up and not price_trend_up:
                score += 2
                reasons.append("🟢 OBV tăng khi giá giảm (tích lũy âm thầm)")
                reasons.append("Smart money đang mua vào - tiềm năng tăng")
                obv_trend = 'ACCUMULATION'
            elif not obv_trend_up and price_trend_up:
                score += 0
                reasons.append("⚠️ Giá tăng nhưng OBV giảm (divergence)")
                reasons.append("Cảnh báo - xu hướng tăng không bền")
                obv_trend = 'DIVERGENCE_BEARISH'
                obv_divergence = True
            else:
                score += 0
                reasons.append("⚠️ OBV + Giá cùng giảm")
                reasons.append("Dòng tiền rút ra - xu hướng giảm")
                obv_trend = 'DOWN_WITH_PRICE'
        
        # Đảm bảo score không vượt quá 10
        final_score = min(score, 10)
        
        # Map score to status
        if final_score >= 8:
            status = 'EXCELLENT'
        elif final_score >= 6:
            status = 'GOOD'
        elif final_score >= 3:
            status = 'ACCEPTABLE'
        elif final_score >= 1:
            status = 'WARNING'
        else:
            status = 'POOR'
        
        return {
            'score': final_score,
            'status': status,
            'reasons': reasons,
            'details': {
                'vol_ratio': vol_ratio,
                'accumulation_days': accumulation_days,
                'obv_trend': obv_trend,
                'obv_divergence': obv_divergence
            }
        }
