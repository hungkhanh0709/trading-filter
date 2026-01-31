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
        
        # Money Flow Index (MFI)
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        raw_money_flow = typical_price * self.df['volume']
        
        # Positive and negative money flow
        positive_flow = raw_money_flow.where(typical_price.diff() > 0, 0).rolling(14).sum()
        negative_flow = raw_money_flow.where(typical_price.diff() < 0, 0).rolling(14).sum()
        
        # Avoid division by zero
        money_ratio = positive_flow / negative_flow.replace(0, 1)
        self.df['MFI'] = 100 - (100 / (1 + money_ratio))
    
    def _detect_support_resistance(self, window=30, n_levels=3):
        """
        Phát hiện vùng hỗ trợ/kháng cự
        
        Args:
            window: Số ngày gần nhất để phân tích
            n_levels: Số mức hỗ trợ/kháng cự cần tìm
            
        Returns:
            dict: {'supports': [...], 'resistances': [...], 'near_support': bool, 'near_resistance': bool}
        """
        if self.df is None or len(self.df) < window:
            return {'supports': [], 'resistances': [], 'near_support': False, 'near_resistance': False}
        
        recent = self.df.tail(window)
        current_price = self.df.iloc[-1]['close']
        
        # Support levels (local minimums)
        supports = recent.nsmallest(n_levels, 'low')['low'].values
        
        # Resistance levels (local maximums)
        resistances = recent.nlargest(n_levels, 'high')['high'].values
        
        # Check nếu giá gần support/resistance (trong vòng 2%)
        dist_to_support = min([abs(current_price - s) / current_price * 100 for s in supports]) if len(supports) > 0 else 100
        dist_to_resistance = min([abs(current_price - r) / current_price * 100 for r in resistances]) if len(resistances) > 0 else 100
        
        return {
            'supports': supports.tolist(),
            'resistances': resistances.tolist(),
            'near_support': dist_to_support < 2,
            'near_resistance': dist_to_resistance < 2,
            'dist_to_support': dist_to_support,
            'dist_to_resistance': dist_to_resistance
        }
    
    def _detect_candlestick_patterns(self):
        """
        Phát hiện các mẫu nến đảo chiều
        
        Returns:
            dict: {'patterns': [...], 'is_bullish': bool, 'is_bearish': bool}
        """
        if self.df is None or len(self.df) < 2:
            return {'patterns': [], 'is_bullish': False, 'is_bearish': False}
        
        latest = self.df.iloc[-1]
        prev = self.df.iloc[-2]
        
        patterns = []
        is_bullish = False
        is_bearish = False
        
        # Candlestick measurements
        body = abs(latest['close'] - latest['open'])
        upper_shadow = latest['high'] - max(latest['open'], latest['close'])
        lower_shadow = min(latest['open'], latest['close']) - latest['low']
        total_range = latest['high'] - latest['low']
        
        if total_range == 0:  # Tránh chia cho 0
            return {'patterns': patterns, 'is_bullish': is_bullish, 'is_bearish': is_bearish}
        
        # 1. Hammer (bullish reversal)
        if (lower_shadow >= 2 * body and 
            upper_shadow < body * 0.3 and 
            body < total_range * 0.3):
            patterns.append('Hammer')
            is_bullish = True
        
        # 2. Shooting Star (bearish reversal)
        if (upper_shadow >= 2 * body and 
            lower_shadow < body * 0.3 and 
            body < total_range * 0.3):
            patterns.append('Shooting Star')
            is_bearish = True
        
        # 3. Doji (indecision)
        if body < total_range * 0.1:
            patterns.append('Doji')
        
        # 4. Bullish Engulfing
        if (prev['close'] < prev['open'] and  # prev red
            latest['close'] > latest['open'] and  # current green
            latest['open'] < prev['close'] and  # opens below prev close
            latest['close'] > prev['open']):  # closes above prev open
            patterns.append('Bullish Engulfing')
            is_bullish = True
        
        # 5. Bearish Engulfing
        if (prev['close'] > prev['open'] and  # prev green
            latest['close'] < latest['open'] and  # current red
            latest['open'] > prev['close'] and  # opens above prev close
            latest['close'] < prev['open']):  # closes below prev open
            patterns.append('Bearish Engulfing')
            is_bearish = True
        
        return {
            'patterns': patterns,
            'is_bullish': is_bullish,
            'is_bearish': is_bearish
        }
    
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
        """Chấm điểm volume + money flow - 10 điểm"""
        if self.df is None or len(self.df) < 20:
            return 0, "Không đủ dữ liệu"
        
        latest = self.df.iloc[-1]
        score = 0
        reasons = []
        
        # Volume breakout (so với trung bình 20 ngày) - 7 điểm max
        vol_ratio = latest['vol_ratio']
        if vol_ratio > 2:
            score += 4
            reasons.append(f"🚀 Volume đột biến ({vol_ratio:.1f}x TB)")
        elif vol_ratio > 1.5:
            score += 3
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
            score += 3
            reasons.append("✅ Tích lũy mạnh (giá tăng + volume cao)")
        elif price_up_days >= 2 and vol_up_days >= 2:
            score += 2
            reasons.append("➕ Có tích lũy")
        
        # OBV Trend Analysis - 3 điểm max (NEW)
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
            elif obv_trend_up and not price_trend_up:
                score += 2
                reasons.append("🟢 OBV tăng khi giá giảm (tích lũy)")
            elif not obv_trend_up and price_trend_up:
                score += 0
                reasons.append("⚠️  Giá tăng nhưng OBV giảm (divergence)")
            else:
                score += 0
                reasons.append("⚠️  OBV + Giá cùng giảm")
        
        return min(score, 10), "; ".join(reasons)
    
    def score_money_flow(self):
        """
        Chấm điểm Money Flow Index - 5 điểm
        
        MFI = RSI + Volume, đo lường dòng tiền thực tế
        """
        if self.df is None or len(self.df) < 14:
            return 0, "Không đủ dữ liệu"
        
        latest = self.df.iloc[-1]
        mfi = latest['MFI']
        rsi = latest['RSI']
        score = 0
        reasons = []
        
        # MFI scoring (similar to RSI)
        if 40 <= mfi <= 60:
            score = 5
            reasons.append(f"✅ MFI cân bằng ({mfi:.1f})")
        elif 20 <= mfi < 40:
            score = 4
            reasons.append(f"🔥 MFI oversold recovery ({mfi:.1f})")
        elif 60 < mfi <= 80:
            score = 3
            reasons.append(f"➕ MFI tích cực ({mfi:.1f})")
        elif mfi > 80:
            score = 2
            reasons.append(f"⚠️  MFI overbought ({mfi:.1f})")
        else:  # mfi < 20
            score = 3
            reasons.append(f"💎 MFI oversold ({mfi:.1f})")
        
        # MFI vs RSI divergence analysis
        mfi_rsi_diff = abs(mfi - rsi)
        if mfi_rsi_diff > 15:
            if mfi > rsi:
                reasons.append("Volume mạnh support giá")
            else:
                reasons.append("⚠️  Volume yếu, cảnh báo divergence")
        
        return score, "; ".join(reasons)
    
    def score_pattern_signals(self):
        """
        Chấm điểm Pattern + Support/Resistance - Bonus 0-10 điểm
        
        Tín hiệu mạnh:
        - RSI quá bán + gần hỗ trợ + Hammer = +8-10 điểm (BUY)
        - RSI quá mua + gần kháng cự + Shooting Star = -5 điểm (SELL warning)
        - Bullish/Bearish Engulfing + vùng giá = +5/-3 điểm
        
        Returns:
            tuple: (bonus_score, signal, explanation)
        """
        if self.df is None or len(self.df) < 14:
            return 0, "HOLD", "Không đủ dữ liệu"
        
        # Get current indicators
        latest = self.df.iloc[-1]
        rsi = latest['RSI']
        
        # Detect patterns & levels
        sr_data = self._detect_support_resistance()
        pattern_data = self._detect_candlestick_patterns()
        
        score = 0
        signal = "HOLD"
        reasons = []
        
        # === BULLISH SIGNALS (BUY) ===
        if rsi <= 30 and sr_data['near_support']:
            if 'Hammer' in pattern_data['patterns']:
                score += 10
                signal = "STRONG_BUY"
                reasons.append("🔥 RSI quá bán + gần hỗ trợ + Hammer")
            elif pattern_data['is_bullish']:
                score += 7
                signal = "BUY"
                reasons.append("✅ RSI quá bán + gần hỗ trợ + nến đảo chiều tăng")
            else:
                score += 5
                signal = "BUY"
                reasons.append("➕ RSI quá bán + gần hỗ trợ")
        
        elif rsi <= 40 and sr_data['near_support'] and pattern_data['is_bullish']:
            score += 6
            signal = "BUY"
            reasons.append("✅ RSI thấp + gần hỗ trợ + nến tích cực")
        
        elif 'Hammer' in pattern_data['patterns'] and sr_data['near_support']:
            score += 5
            signal = "BUY"
            reasons.append("✅ Hammer tại vùng hỗ trợ")
        
        elif 'Bullish Engulfing' in pattern_data['patterns']:
            score += 4
            signal = "BUY" if sr_data['near_support'] else "HOLD"
            reasons.append("➕ Bullish Engulfing")
        
        # === BEARISH SIGNALS (SELL) ===
        elif rsi >= 70 and sr_data['near_resistance']:
            if 'Shooting Star' in pattern_data['patterns']:
                score -= 5
                signal = "STRONG_SELL"
                reasons.append("⚠️  RSI quá mua + gần kháng cự + Shooting Star")
            elif pattern_data['is_bearish']:
                score -= 3
                signal = "SELL"
                reasons.append("⚠️  RSI quá mua + gần kháng cự + nến đảo chiều giảm")
            else:
                score -= 2
                signal = "CAUTION"
                reasons.append("⚠️  RSI quá mua + gần kháng cự")
        
        elif rsi >= 60 and sr_data['near_resistance'] and pattern_data['is_bearish']:
            score -= 3
            signal = "SELL"
            reasons.append("⚠️  RSI cao + gần kháng cự + nến tiêu cực")
        
        elif 'Shooting Star' in pattern_data['patterns'] and sr_data['near_resistance']:
            score -= 3
            signal = "SELL"
            reasons.append("⚠️  Shooting Star tại vùng kháng cự")
        
        elif 'Bearish Engulfing' in pattern_data['patterns']:
            score -= 2
            signal = "SELL" if sr_data['near_resistance'] else "CAUTION"
            reasons.append("⚠️  Bearish Engulfing")
        
        # === NEUTRAL PATTERNS ===
        elif 'Doji' in pattern_data['patterns']:
            reasons.append("⚪ Doji - chờ xác nhận")
        
        # Không có pattern đặc biệt
        if not reasons:
            reasons.append("Không có pattern đặc biệt")
        
        # Add pattern info to reasons
        if pattern_data['patterns']:
            patterns_str = ", ".join(pattern_data['patterns'])
            reasons.append(f"Patterns: {patterns_str}")
        
        explanation = "; ".join(reasons)
        
        # Đảm bảo score không âm (tối thiểu 0)
        bonus_score = max(score, 0)
        
        return bonus_score, signal, explanation
    
    def get_total_score(self):
        """
        Tổng điểm Technical - 30 điểm (base) + bonus 0-10 điểm
        
        Base scoring (30 điểm):
        - MA Trend: 10 điểm
        - RSI: 5 điểm  
        - Volume + OBV: 10 điểm
        - Money Flow (MFI): 5 điểm
        
        Bonus (0-10 điểm):
        - Pattern + Support/Resistance signals
        
        Returns:
            dict: Score breakdown with signal
        """
        ma_score, ma_reason = self.score_ma_trend()
        rsi_score, rsi_reason = self.score_rsi()
        vol_score, vol_reason = self.score_volume()
        mfi_score, mfi_reason = self.score_money_flow()
        pattern_bonus, signal, pattern_reason = self.score_pattern_signals()
        
        base_total = ma_score + rsi_score + vol_score + mfi_score
        final_total = min(base_total + pattern_bonus, 30)  # Cap tại 30 điểm
        
        return {
            'total': final_total,
            'max': 30,
            'signal': signal,  # STRONG_BUY, BUY, HOLD, CAUTION, SELL, STRONG_SELL
            'breakdown': {
                'ma_trend': {'score': ma_score, 'max': 10, 'reason': ma_reason},
                'rsi': {'score': rsi_score, 'max': 5, 'reason': rsi_reason},
                'volume_obv': {'score': vol_score, 'max': 10, 'reason': vol_reason},
                'money_flow': {'score': mfi_score, 'max': 5, 'reason': mfi_reason},
                'pattern_bonus': {'score': pattern_bonus, 'max': 10, 'reason': pattern_reason, 'signal': signal}
            }
        }
