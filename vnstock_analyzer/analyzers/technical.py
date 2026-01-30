"""
Technical Analyzer - Phân tích kỹ thuật (25 điểm)
"""

import pandas as pd
import numpy as np


class TechnicalAnalyzer:
    """Phân tích kỹ thuật - 25 điểm"""
    
    def __init__(self, df_history):
        """
        Initialize technical analyzer
        
        Args:
            df_history: Historical price dataframe
        """
        self.df = df_history.copy() if df_history is not None else None
        self._calculate_indicators()
        
    def _calculate_indicators(self):
        """Tính các chỉ báo kỹ thuật"""
        if self.df is None or len(self.df) == 0:
            return
        
        # Moving Averages
        self.df['MA5'] = self.df['close'].rolling(5).mean()
        self.df['MA10'] = self.df['close'].rolling(10).mean()
        self.df['MA20'] = self.df['close'].rolling(20).mean()
        self.df['MA50'] = self.df['close'].rolling(50).mean()
        
        # RSI
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        self.df['RSI'] = 100 - (100 / (1 + rs))
        
        # Volume
        self.df['vol_ma20'] = self.df['volume'].rolling(20).mean()
        self.df['vol_ratio'] = self.df['volume'] / self.df['vol_ma20']
        
        # OBV (On Balance Volume)
        self.df['OBV'] = (self.df['volume'] * (~self.df['close'].diff().le(0) * 2 - 1)).cumsum()
    
    def score_ma_trend(self):
        """Chấm điểm xu hướng MA - 10 điểm"""
        if self.df is None or len(self.df) < 50:
            return 0, "Không đủ dữ liệu"
        
        latest = self.df.iloc[-1]
        price = latest['close']
        score = 0
        reasons = []
        
        # MA5 > MA10 > MA20 > MA50 = Perfect uptrend
        if (latest['MA5'] > latest['MA10'] > latest['MA20'] > latest['MA50']):
            score += 5
            reasons.append("✅ MA hoàn hảo (MA5>MA10>MA20>MA50)")
        elif (latest['MA5'] > latest['MA10'] > latest['MA20']):
            score += 3
            reasons.append("✅ MA tốt (MA5>MA10>MA20)")
        elif (latest['MA5'] > latest['MA10']):
            score += 1
            reasons.append("➕ MA ngắn hạn tích cực")
        
        # Giá > các MA
        if price > latest['MA50']:
            score += 3
            reasons.append("✅ Giá trên MA50")
        elif price > latest['MA20']:
            score += 2
            reasons.append("➕ Giá trên MA20")
        elif price > latest['MA10']:
            score += 1
            reasons.append("➕ Giá trên MA10")
        else:
            reasons.append("⚠️  Giá dưới MA10")
        
        # Cross over gần đây (bullish)
        if len(self.df) >= 2:
            prev = self.df.iloc[-2]
            if prev['MA5'] <= prev['MA10'] and latest['MA5'] > latest['MA10']:
                score += 2
                reasons.append("🚀 MA5 vừa cắt lên MA10 (Golden Cross ngắn hạn)")
        
        return min(score, 10), "; ".join(reasons)
    
    def score_rsi(self):
        """Chấm điểm RSI - 5 điểm"""
        if self.df is None or len(self.df) < 14:
            return 0, "Không đủ dữ liệu"
        
        rsi = self.df.iloc[-1]['RSI']
        score = 0
        reason = ""
        
        if 40 <= rsi <= 60:
            score = 5
            reason = f"✅ RSI ở vùng cân bằng ({rsi:.1f}) - Tiềm năng tốt"
        elif 30 <= rsi < 40:
            score = 4
            reason = f"🔥 RSI oversold recovery ({rsi:.1f}) - Cơ hội mua"
        elif 60 < rsi <= 70:
            score = 3
            reason = f"➕ RSI tích cực ({rsi:.1f})"
        elif rsi > 70:
            score = 2
            reason = f"⚠️  RSI overbought ({rsi:.1f}) - Cảnh báo"
        else:  # rsi < 30
            score = 3
            reason = f"💎 RSI quá bán ({rsi:.1f}) - Có thể rebound"
        
        return score, reason
    
    def score_volume(self):
        """Chấm điểm volume breakout - 10 điểm (so với trung bình)"""
        if self.df is None or len(self.df) < 20:
            return 0, "Không đủ dữ liệu"
        
        latest = self.df.iloc[-1]
        score = 0
        reasons = []
        
        # Volume breakout (so với trung bình 20 ngày)
        vol_ratio = latest['vol_ratio']
        if vol_ratio > 2:
            score += 5
            reasons.append(f"🚀 Volume đột biến ({vol_ratio:.1f}x TB)")
        elif vol_ratio > 1.5:
            score += 4
            reasons.append(f"✅ Volume tăng mạnh ({vol_ratio:.1f}x TB)")
        elif vol_ratio > 1:
            score += 2
            reasons.append(f"➕ Volume trên TB ({vol_ratio:.1f}x TB)")
        else:
            reasons.append(f"⚠️  Volume thấp hơn TB ({vol_ratio:.1f}x TB)")
        
        # Price + Volume accumulation
        last_5 = self.df.tail(5)
        price_up_days = (last_5['close'].diff() > 0).sum()
        vol_up_days = (last_5['volume'] > last_5['vol_ma20']).sum()
        
        if price_up_days >= 3 and vol_up_days >= 3:
            score += 5
            reasons.append("✅ Tích lũy mạnh (giá tăng + volume cao)")
        elif price_up_days >= 2 and vol_up_days >= 2:
            score += 3
            reasons.append("➕ Có tích lũy")
        
        return min(score, 10), "; ".join(reasons)
    
    def get_total_score(self):
        """
        Tổng điểm Technical - 25 điểm
        
        Returns:
            dict: Score breakdown
        """
        ma_score, ma_reason = self.score_ma_trend()
        rsi_score, rsi_reason = self.score_rsi()
        vol_score, vol_reason = self.score_volume()
        
        total = ma_score + rsi_score + vol_score
        
        return {
            'total': total,
            'max': 25,
            'breakdown': {
                'ma_trend': {'score': ma_score, 'max': 10, 'reason': ma_reason},
                'rsi': {'score': rsi_score, 'max': 5, 'reason': rsi_reason},
                'volume_breakout': {'score': vol_score, 'max': 10, 'reason': vol_reason}
            }
        }
