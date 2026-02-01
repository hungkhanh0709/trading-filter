"""
Pattern Analyzer - Phân tích mẫu nến và Support/Resistance
"""

class PatternAnalyzer:
    """Chuyên phân tích candlestick patterns và support/resistance"""
    
    def __init__(self, df):
        """
        Args:
            df: DataFrame với price data (open, high, low, close)
        """
        self.df = df
    
    def _detect_support_resistance(self, window=30, n_levels=3):
        """
        Phát hiện vùng hỗ trợ/kháng cự
        
        Returns:
            dict: {
                'supports': list,
                'resistances': list,
                'near_support': bool,
                'near_resistance': bool,
                'dist_to_support': float,
                'dist_to_resistance': float
            }
        """
        if self.df is None or len(self.df) < window:
            return {
                'supports': [],
                'resistances': [],
                'near_support': False,
                'near_resistance': False,
                'dist_to_support': 100,
                'dist_to_resistance': 100
            }
        
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
            dict: {
                'patterns': list,
                'is_bullish': bool,
                'is_bearish': bool
            }
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
        
        if total_range == 0:
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
        if (prev['close'] < prev['open'] and
            latest['close'] > latest['open'] and
            latest['open'] < prev['close'] and
            latest['close'] > prev['open']):
            patterns.append('Bullish Engulfing')
            is_bullish = True
        
        # 5. Bearish Engulfing
        if (prev['close'] > prev['open'] and
            latest['close'] < latest['open'] and
            latest['open'] > prev['close'] and
            latest['close'] < prev['open']):
            patterns.append('Bearish Engulfing')
            is_bearish = True
        
        return {
            'patterns': patterns,
            'is_bullish': is_bullish,
            'is_bearish': is_bearish
        }
    
    def analyze(self):
        """
        Phân tích pattern + support/resistance và trả về kết quả với reasons dạng array
        
        Returns:
            dict: {
                'score': float (0-10),
                'signal': str (STRONG_BUY, BUY, HOLD, CAUTION, SELL, STRONG_SELL),
                'status': str,
                'reasons': list of str,
                'details': {
                    'patterns': list,
                    'support_resistance': dict,
                    'is_bullish': bool,
                    'is_bearish': bool
                }
            }
        """
        if self.df is None or len(self.df) < 14:
            return {
                'score': 0,
                'signal': 'HOLD',
                'status': 'NA',
                'reasons': ['Không đủ dữ liệu'],
                'details': {}
            }
        
        # Get current indicators
        latest = self.df.iloc[-1]
        rsi = latest['RSI'] if 'RSI' in self.df.columns else 50
        
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
                reasons.append("Tín hiệu mua mạnh - đảo chiều tăng")
            elif pattern_data['is_bullish']:
                score += 7
                signal = "BUY"
                reasons.append("✅ RSI quá bán + gần hỗ trợ + nến đảo chiều tăng")
                reasons.append("Tín hiệu mua tốt - phục hồi có thể xảy ra")
            else:
                score += 5
                signal = "BUY"
                reasons.append("➕ RSI quá bán + gần hỗ trợ")
                reasons.append("Có tiềm năng phục hồi")
        
        elif rsi <= 40 and sr_data['near_support'] and pattern_data['is_bullish']:
            score += 6
            signal = "BUY"
            reasons.append("✅ RSI thấp + gần hỗ trợ + nến tích cực")
            reasons.append("Điểm mua tốt")
        
        elif 'Hammer' in pattern_data['patterns'] and sr_data['near_support']:
            score += 5
            signal = "BUY"
            reasons.append("✅ Hammer tại vùng hỗ trợ")
            reasons.append("Tín hiệu đảo chiều tăng")
        
        elif 'Bullish Engulfing' in pattern_data['patterns']:
            score += 4
            signal = "BUY" if sr_data['near_support'] else "HOLD"
            reasons.append("➕ Bullish Engulfing")
            if sr_data['near_support']:
                reasons.append("Mẫu tăng tại vùng hỗ trợ")
            else:
                reasons.append("Mẫu tăng - chờ xác nhận")
        
        # === BEARISH SIGNALS (SELL) ===
        elif rsi >= 70 and sr_data['near_resistance']:
            if 'Shooting Star' in pattern_data['patterns']:
                score = 0  # Negative signal
                signal = "STRONG_SELL"
                reasons.append("⚠️ RSI quá mua + gần kháng cự + Shooting Star")
                reasons.append("Tín hiệu bán mạnh - đảo chiều giảm")
            elif pattern_data['is_bearish']:
                score = 0
                signal = "SELL"
                reasons.append("⚠️ RSI quá mua + gần kháng cự + nến đảo chiều giảm")
                reasons.append("Cảnh báo điều chỉnh")
            else:
                score = 0
                signal = "CAUTION"
                reasons.append("⚠️ RSI quá mua + gần kháng cự")
                reasons.append("Thận trọng - có thể điều chỉnh")
        
        elif rsi >= 60 and sr_data['near_resistance'] and pattern_data['is_bearish']:
            score = 0
            signal = "SELL"
            reasons.append("⚠️ RSI cao + gần kháng cự + nến tiêu cực")
            reasons.append("Cân nhắc chốt lời")
        
        elif 'Shooting Star' in pattern_data['patterns'] and sr_data['near_resistance']:
            score = 0
            signal = "SELL"
            reasons.append("⚠️ Shooting Star tại vùng kháng cự")
            reasons.append("Cảnh báo đảo chiều giảm")
        
        elif 'Bearish Engulfing' in pattern_data['patterns']:
            score = 0
            signal = "SELL" if sr_data['near_resistance'] else "CAUTION"
            reasons.append("⚠️ Bearish Engulfing")
            if sr_data['near_resistance']:
                reasons.append("Mẫu giảm tại vùng kháng cự")
            else:
                reasons.append("Mẫu giảm - theo dõi sát")
        
        # === NEUTRAL PATTERNS ===
        elif 'Doji' in pattern_data['patterns']:
            reasons.append("⚪ Doji - phân vân thị trường")
            reasons.append("Chờ xác nhận hướng đi tiếp theo")
        
        # Không có pattern đặc biệt
        if not reasons:
            reasons.append("Không có pattern đặc biệt")
            reasons.append("Theo dõi các chỉ báo khác")
        
        # Add pattern info
        if pattern_data['patterns']:
            patterns_str = ", ".join(pattern_data['patterns'])
            reasons.append(f"Patterns phát hiện: {patterns_str}")
        
        # Add S/R info if near
        if sr_data['near_support']:
            reasons.append(f"📍 Gần vùng hỗ trợ ({sr_data['dist_to_support']:.1f}% khoảng cách)")
        if sr_data['near_resistance']:
            reasons.append(f"📍 Gần vùng kháng cự ({sr_data['dist_to_resistance']:.1f}% khoảng cách)")
        
        # Đảm bảo score >= 0
        final_score = max(score, 0)
        
        # Map signal to status
        if signal == 'STRONG_BUY':
            status = 'EXCELLENT'
        elif signal == 'BUY':
            status = 'GOOD'
        elif signal == 'HOLD':
            status = 'ACCEPTABLE'
        elif signal == 'CAUTION':
            status = 'WARNING'
        elif signal in ['SELL', 'STRONG_SELL']:
            status = 'POOR'
        else:
            status = 'NA'
        
        return {
            'score': final_score,
            'signal': signal,
            'status': status,
            'reasons': reasons,
            'details': {
                'patterns': pattern_data['patterns'],
                'support_resistance': sr_data,
                'is_bullish': pattern_data['is_bullish'],
                'is_bearish': pattern_data['is_bearish']
            }
        }
