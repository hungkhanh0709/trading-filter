"""
Technical Analyzer - Phân tích kỹ thuật
"""
class TechnicalAnalyzer:
    """Phân tích kỹ thuật"""
    
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
    
    def _detect_ma_convergence(self):
        """
        Phát hiện MA convergence (các đường MA xoắn vào nhau) - Dấu hiệu tích luỹ
        
        Returns:
            dict: {
                'is_converging': bool,
                'convergence_strength': float (0-100),
                'description': str
            }
        """
        if self.df is None or len(self.df) < 50:
            return {'is_converging': False, 'convergence_strength': 0, 'description': 'Không đủ dữ liệu'}
        
        latest = self.df.iloc[-1]
        
        # Tính khoảng cách % giữa các MA
        ma5 = latest['MA5']
        ma10 = latest['MA10']
        ma20 = latest['MA20']
        ma50 = latest['MA50']
        
        if ma50 == 0:
            return {'is_converging': False, 'convergence_strength': 0, 'description': 'MA50 = 0'}
        
        # Khoảng cách % so với MA50
        dist_5_50 = abs((ma5 - ma50) / ma50 * 100)
        dist_10_50 = abs((ma10 - ma50) / ma50 * 100)
        dist_20_50 = abs((ma20 - ma50) / ma50 * 100)
        
        # Khoảng cách trung bình
        avg_distance = (dist_5_50 + dist_10_50 + dist_20_50) / 3
        
        # Convergence strength: 100 khi các MA xoắn sát nhau (< 1%)
        # 0 khi các MA cách xa (> 10%)
        convergence_strength = max(0, min(100, (10 - avg_distance) / 10 * 100))
        
        is_converging = avg_distance < 5  # Các MA xoắn vào nhau khi cách nhau < 5%
        
        if avg_distance < 2:
            description = f"⚡ MA siêu xoắn (TB: {avg_distance:.1f}%) - Breakout sắp xảy ra!"
        elif avg_distance < 5:
            description = f"🔄 MA đang tích luỹ (TB: {avg_distance:.1f}%) - Theo dõi breakout"
        elif avg_distance < 10:
            description = f"➕ MA gần nhau (TB: {avg_distance:.1f}%)"
        else:
            description = f"↔️ MA cách xa (TB: {avg_distance:.1f}%)"
        
        return {
            'is_converging': is_converging,
            'convergence_strength': convergence_strength,
            'avg_distance': avg_distance,
            'description': description
        }
    
    def _detect_ma_expansion(self):
        """
        Phát hiện MA expansion (các đường MA xoè ra) - Xác nhận uptrend mạnh
        
        Returns:
            dict: {
                'is_expanding': bool,
                'expansion_quality': str (PERFECT/GOOD/WEAK),
                'description': str
            }
        """
        if self.df is None or len(self.df) < 50:
            return {'is_expanding': False, 'expansion_quality': 'WEAK', 'description': 'Không đủ dữ liệu'}
        
        latest = self.df.iloc[-1]
        
        # Kiểm tra Perfect Order
        perfect_order = (latest['MA5'] > latest['MA10'] > latest['MA20'] > latest['MA50'])
        
        if not perfect_order:
            return {
                'is_expanding': False,
                'expansion_quality': 'WEAK',
                'description': '❌ Không có Perfect Order'
            }
        
        # Tính khoảng cách giữa các MA (% so với MA50)
        ma50 = latest['MA50']
        if ma50 == 0:
            return {'is_expanding': False, 'expansion_quality': 'WEAK', 'description': 'MA50 = 0'}
        
        dist_5_50 = (latest['MA5'] - ma50) / ma50 * 100
        dist_10_50 = (latest['MA10'] - ma50) / ma50 * 100
        dist_20_50 = (latest['MA20'] - ma50) / ma50 * 100
        
        # Tính độ nghiêng (slope) của MA50 trong 10 ngày gần nhất
        if len(self.df) >= 10:
            ma50_10_days_ago = self.df.iloc[-10]['MA50']
            ma50_slope = ((ma50 - ma50_10_days_ago) / ma50_10_days_ago * 100) if ma50_10_days_ago > 0 else 0
        else:
            ma50_slope = 0
        
        # Đánh giá expansion quality
        if dist_5_50 > 8 and dist_20_50 > 3 and ma50_slope > 2:
            expansion_quality = 'PERFECT'
            description = f"🚀 Perfect Expansion! MA xoè rộng (MA5 +{dist_5_50:.1f}%, MA20 +{dist_20_50:.1f}%) | MA50 slope +{ma50_slope:.1f}%"
        elif dist_5_50 > 5 and dist_20_50 > 2 and ma50_slope > 1:
            expansion_quality = 'GOOD'
            description = f"✅ MA đang xoè ra (MA5 +{dist_5_50:.1f}%, MA20 +{dist_20_50:.1f}%) | MA50 slope +{ma50_slope:.1f}%"
        elif dist_5_50 > 3:
            expansion_quality = 'WEAK'
            description = f"➕ MA xoè yếu (MA5 +{dist_5_50:.1f}%, MA20 +{dist_20_50:.1f}%) | MA50 slope +{ma50_slope:.1f}%"
        else:
            expansion_quality = 'WEAK'
            description = f"⚠️ Perfect Order nhưng MA chưa xoè rõ (MA5 +{dist_5_50:.1f}%)"
        
        return {
            'is_expanding': expansion_quality in ['PERFECT', 'GOOD'],
            'expansion_quality': expansion_quality,
            'ma50_slope': ma50_slope,
            'description': description
        }
    
    def _detect_golden_cross_quality(self):
        """
        Phát hiện và đánh giá chất lượng Golden Cross (các mức độ uy tín khác nhau)
        
        Returns:
            dict: {
                'crosses': list of dicts,
                'best_cross': str,
                'description': str
            }
        """
        if self.df is None or len(self.df) < 50:
            return {'crosses': [], 'best_cross': None, 'description': 'Không đủ dữ liệu'}
        
        crosses = []
        latest = self.df.iloc[-1]
        
        if len(self.df) >= 2:
            prev = self.df.iloc[-2]
            
            # MA5 x MA10 (Golden Cross ngắn hạn - 3 điểm)
            if prev['MA5'] <= prev['MA10'] and latest['MA5'] > latest['MA10']:
                crosses.append({
                    'type': 'MA5_MA10',
                    'label': 'Golden Cross ngắn hạn',
                    'score': 3,
                    'icon': '🟡'
                })
            
            # MA10 x MA20 (Golden Cross trung hạn - 5 điểm)
            if prev['MA10'] <= prev['MA20'] and latest['MA10'] > latest['MA20']:
                crosses.append({
                    'type': 'MA10_MA20',
                    'label': 'Golden Cross trung hạn',
                    'score': 5,
                    'icon': '🟠'
                })
            
            # MA20 x MA50 (Golden Cross uy tín - 7 điểm) - QUAN TRỌNG NHẤT
            if prev['MA20'] <= prev['MA50'] and latest['MA20'] > latest['MA50']:
                crosses.append({
                    'type': 'MA20_MA50',
                    'label': 'Golden Cross UY TÍN',
                    'score': 7,
                    'icon': '🏆'
                })
        
        # Tìm cross uy tín nhất
        best_cross = None
        if crosses:
            best_cross = max(crosses, key=lambda x: x['score'])
        
        # Tạo description
        if not crosses:
            description = "Không có Golden Cross gần đây"
        else:
            desc_parts = [f"{c['icon']} {c['label']}" for c in crosses]
            description = "; ".join(desc_parts)
        
        return {
            'crosses': crosses,
            'best_cross': best_cross,
            'description': description
        }
    
    def _detect_sell_warning(self):
        """
        Phát hiện tín hiệu cảnh báo bán (để tối ưu điểm bán, không bán quá muộn)
        
        Returns:
            dict: {
                'has_warning': bool,
                'warning_level': str (CRITICAL/HIGH/MEDIUM/LOW),
                'warnings': list of str,
                'suggested_action': str
            }
        """
        if self.df is None or len(self.df) < 50:
            return {
                'has_warning': False,
                'warning_level': 'LOW',
                'warnings': [],
                'suggested_action': 'HOLD'
            }
        
        latest = self.df.iloc[-1]
        price = latest['close']
        warnings = []
        warning_level = 'LOW'
        suggested_action = 'HOLD'
        
        # Kiểm tra Perfect Order trước
        was_in_perfect_order = (latest['MA5'] > latest['MA10'] > latest['MA20'] > latest['MA50'])
        
        if len(self.df) >= 2:
            prev = self.df.iloc[-2]
            
            # CRITICAL: MA20 cắt xuống MA50 (Death Cross uy tín)
            if prev['MA20'] >= prev['MA50'] and latest['MA20'] < latest['MA50']:
                warnings.append('🔴 DEATH CROSS MA20/MA50 - TÍN HIỆU BÁN MẠNH!')
                warning_level = 'CRITICAL'
                suggested_action = 'SELL_ALL'
            
            # HIGH: MA5 cắt xuống MA10 (Death Cross ngắn hạn)
            elif prev['MA5'] >= prev['MA10'] and latest['MA5'] < latest['MA10']:
                warnings.append('⚠️ MA5 cắt xuống MA10 - Cân nhắc bán 50%')
                if warning_level == 'LOW':
                    warning_level = 'HIGH'
                    suggested_action = 'SELL_HALF'
        
        # MEDIUM: Giá giảm xuống dưới MA20 (trong uptrend)
        if was_in_perfect_order and price < latest['MA20']:
            warnings.append('⚠️ Giá phá xuống MA20 - Theo dõi sát, có thể bán 30%')
            if warning_level == 'LOW':
                warning_level = 'MEDIUM'
                suggested_action = 'SELL_PARTIAL'
        
        # MEDIUM: Giá giảm xuống dưới MA10 (sau uptrend mạnh)
        if was_in_perfect_order and price < latest['MA10']:
            warnings.append('⚠️ Giá phá xuống MA10 - Cảnh báo điều chỉnh')
            if warning_level == 'LOW':
                warning_level = 'MEDIUM'
        
        # Kiểm tra momentum giảm (MA50 bắt đầu đi ngang hoặc giảm)
        if len(self.df) >= 10:
            ma50_10_days_ago = self.df.iloc[-10]['MA50']
            ma50_slope = ((latest['MA50'] - ma50_10_days_ago) / ma50_10_days_ago * 100) if ma50_10_days_ago > 0 else 0
            
            if ma50_slope < 0.5 and was_in_perfect_order:
                warnings.append(f'⚠️ MA50 đi ngang/giảm (slope {ma50_slope:.1f}%) - Xu hướng suy yếu')
        
        has_warning = len(warnings) > 0
        
        return {
            'has_warning': has_warning,
            'warning_level': warning_level,
            'warnings': warnings,
            'suggested_action': suggested_action
        }
    
    def score_ma_trend(self):
        """
        Chấm điểm xu hướng MA - 10 điểm
        
        Phân tích toàn diện theo phương pháp đầu tư MA:
        - Perfect Order (MA5>MA10>MA20>MA50)
        - MA Convergence (tích luỹ) - mua sớm
        - MA Expansion (xoè ra) - xác nhận uptrend
        - Golden Cross (nhiều mức độ uy tín)
        - Sell Warnings (bán sớm khi cần)
        """
        if self.df is None or len(self.df) < 50:
            return 0, "Không đủ dữ liệu"
        
        latest = self.df.iloc[-1]
        price = latest['close']
        score = 0
        reasons = []
        
        # === 1. PHÂN TÍCH PERFECT ORDER & MA EXPANSION ===
        perfect_order = (latest['MA5'] > latest['MA10'] > latest['MA20'] > latest['MA50'])
        
        if perfect_order:
            # Kiểm tra chất lượng expansion
            expansion = self._detect_ma_expansion()
            
            if expansion['expansion_quality'] == 'PERFECT':
                score += 6
                reasons.append(expansion['description'])
            elif expansion['expansion_quality'] == 'GOOD':
                score += 5
                reasons.append(expansion['description'])
            else:
                score += 3
                reasons.append("✅ Perfect Order nhưng MA chưa xoè rõ")
        
        elif (latest['MA5'] > latest['MA10'] > latest['MA20']):
            score += 3
            reasons.append("✅ MA tốt (MA5>MA10>MA20)")
        elif (latest['MA5'] > latest['MA10']):
            score += 1
            reasons.append("➕ MA ngắn hạn tích cực")
        
        # === 2. PHÂN TÍCH VỊ TRÍ GIÁ SO VỚI MA ===
        ma50 = latest['MA50']
        ma20 = latest['MA20']
        ma10 = latest['MA10']
        
        if ma50 > 0:
            dist_to_ma50 = (price - ma50) / ma50 * 100
            dist_to_ma20 = (price - ma20) / ma20 * 100 if ma20 > 0 else 0
            dist_to_ma10 = (price - ma10) / ma10 * 100 if ma10 > 0 else 0
        else:
            dist_to_ma50 = dist_to_ma20 = dist_to_ma10 = 0
        
        if price > latest['MA50']:
            score += 2
            reasons.append(f"✅ Giá trên MA50 (+{dist_to_ma50:.1f}%)")
        elif price > latest['MA20']:
            score += 1
            reasons.append(f"➕ Giá trên MA20 (+{dist_to_ma20:.1f}%)")
        elif price > latest['MA10']:
            score += 0.5
            reasons.append(f"⚠️ Giá chỉ trên MA10 ({dist_to_ma10:.1f}%)")
        else:
            reasons.append("❌ Giá dưới MA10")
        
        # === 3. PHÂN TÍCH GOLDEN CROSS (UY TÍN) ===
        golden_cross = self._detect_golden_cross_quality()
        
        if golden_cross['best_cross']:
            best = golden_cross['best_cross']
            score += best['score'] * 0.3  # Scale down để không vượt 10
            reasons.append(f"{best['icon']} {best['label']} vừa xảy ra!")
        
        # === 4. PHÂN TÍCH MA CONVERGENCE (TÍCH LUỸ) - DỰ ĐOÁN SỚM ===
        convergence = self._detect_ma_convergence()
        
        if convergence['is_converging'] and convergence['convergence_strength'] > 70:
            score += 1
            reasons.append(convergence['description'])
        elif convergence['is_converging']:
            reasons.append(convergence['description'])
        
        # === 5. CẢNH BÁO BÁN (QUAN TRỌNG CHO EXIT) ===
        sell_warning = self._detect_sell_warning()
        
        if sell_warning['has_warning']:
            # Giảm điểm nếu có cảnh báo
            if sell_warning['warning_level'] == 'CRITICAL':
                score = max(0, score - 5)  # Giảm mạnh
            elif sell_warning['warning_level'] == 'HIGH':
                score = max(0, score - 3)
            elif sell_warning['warning_level'] == 'MEDIUM':
                score = max(0, score - 1)
            
            # Thêm cảnh báo vào reasons
            for warning in sell_warning['warnings']:
                reasons.append(warning)
            
            reasons.append(f"👉 Đề xuất: {sell_warning['suggested_action']}")
        
        # Đảm bảo score không vượt quá 10
        final_score = min(score, 10)
        
        return final_score, " | ".join(reasons)
    
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
    
    def get_analysis(self):
        """
        Status-based Technical Analysis
        
        Returns status for each criterion:
        - EXCELLENT 🔥: Outstanding
        - GOOD ✅: Pass
        - ACCEPTABLE ➕: OK  
        - WARNING ⚠️: Caution
        - POOR ❌: Fail
        - NA ⚪: No data
        
        Returns:
            dict: {
                'status': 'GOOD',  # Overall component status
                'criteria': {...},  # Individual criteria with status
                'summary': {'excellent': 2, 'good': 3, ...},  # Count by status
                'signal': 'BUY'  # Trading signal
            }
        """
        # Get individual scores (reuse existing methods)
        ma_score, ma_reason = self.score_ma_trend()
        rsi_score, rsi_reason = self.score_rsi()
        vol_score, vol_reason = self.score_volume()
        mfi_score, mfi_reason = self.score_money_flow()
        pattern_bonus, signal, pattern_reason = self.score_pattern_signals()
        
        # Map scores to status
        criteria = {
            'ma_trend': {
                'status': self._map_ma_status(ma_score),
                'reason': ma_reason
            },
            'rsi': {
                'status': self._map_rsi_status(rsi_score),
                'reason': rsi_reason
            },
            'volume_obv': {
                'status': self._map_volume_status(vol_score),
                'reason': vol_reason
            },
            'money_flow': {
                'status': self._map_mfi_status(mfi_score),
                'reason': mfi_reason
            },
            'pattern_signal': {
                'status': self._map_pattern_status(signal),
                'reason': pattern_reason
            }
        }
        
        # Calculate overall component status
        from ..core.constants import calculate_component_score, count_criteria_by_status
        
        component_score = calculate_component_score(criteria)
        summary = count_criteria_by_status(criteria)
        
        # Determine overall status based on component score
        if component_score >= 0.9:
            overall_status = 'EXCELLENT'
        elif component_score >= 0.7:
            overall_status = 'GOOD'
        elif component_score >= 0.5:
            overall_status = 'ACCEPTABLE'
        elif component_score >= 0.3:
            overall_status = 'WARNING'
        else:
            overall_status = 'POOR'
        
        return {
            'status': overall_status,
            'criteria': criteria,
            'summary': summary,
            'signal': signal,
            'component_score': component_score
        }
    
    def _map_ma_status(self, score):
        """Map MA score (0-10) to status"""
        if score >= 9:  # Perfect MA + Golden Cross
            return 'EXCELLENT'
        elif score >= 7:  # Perfect MA or Good MA + Price > MA50
            return 'GOOD'
        elif score >= 4:  # Good MA or Price > MA20
            return 'ACCEPTABLE'
        elif score >= 2:  # Some positive signals
            return 'WARNING'
        else:
            return 'POOR'
    
    def _map_rsi_status(self, score):
        """Map RSI score (0-5) to status"""
        if score == 5:  # 40-60 balanced
            return 'EXCELLENT'
        elif score == 4:  # 30-40 oversold recovery
            return 'GOOD'
        elif score == 3:  # <30 oversold or 60-70 positive
            return 'ACCEPTABLE'
        elif score == 2:  # >70 overbought
            return 'WARNING'
        else:
            return 'POOR'
    
    def _map_volume_status(self, score):
        """Map Volume+OBV score (0-10) to status"""
        if score >= 8:  # Strong volume + accumulation + OBV confirmation
            return 'EXCELLENT'
        elif score >= 6:  # Good volume + some accumulation
            return 'GOOD'
        elif score >= 3:  # Acceptable volume
            return 'ACCEPTABLE'
        elif score >= 1:
            return 'WARNING'
        else:
            return 'POOR'
    
    def _map_mfi_status(self, score):
        """Map MFI score (0-5) to status"""
        if score == 5:  # 40-60 balanced
            return 'EXCELLENT'
        elif score == 4:  # 20-40 oversold recovery
            return 'GOOD'
        elif score == 3:  # 60-80 positive or <20 oversold
            return 'ACCEPTABLE'
        elif score == 2:  # >80 overbought
            return 'WARNING'
        else:
            return 'POOR'
    
    def _map_pattern_status(self, signal):
        """Map trading signal to status"""
        if signal == 'STRONG_BUY':
            return 'EXCELLENT'
        elif signal == 'BUY':
            return 'GOOD'
        elif signal == 'HOLD':
            return 'ACCEPTABLE'
        elif signal == 'CAUTION':
            return 'WARNING'
        elif signal in ['SELL', 'STRONG_SELL']:
            return 'POOR'
        else:
            return 'NA'
