"""
MA Analyzer - Phân tích Moving Average (Đường trung bình động)

Uses EMA (Exponential Moving Average) to match TradingView default.
EMA reacts faster to recent price changes compared to SMA.
"""

class MAAnalyzer:
    """
    Chuyên phân tích Moving Average
    
    Hỗ trợ phương pháp đầu tư theo MA (KHÔNG dùng MA5 - quá ngắn hạn):
    - Perfect Order (MA10>MA20>MA50)
    - MA Convergence (tích luỹ trước breakout)
    - MA Expansion (xoè ra - xu hướng mạnh)
    - Golden Cross (MA10xMA20, MA20xMA50)
    - Sell Warnings (cảnh báo bán sớm)
    
    Note: Dùng EMA (Exponential) thay vì SMA (Simple) để:
    - Match với TradingView default
    - Phản ứng nhanh hơn với price changes
    - Chính xác hơn trong trend detection
    """
    
    def __init__(self, df):
        """
        Args:
            df: DataFrame đã tính sẵn các MA (MA10, MA20, MA50)
            Note: MA5 không được dùng vì quá nhạy với noise ngắn hạn
                  Dùng EMA (Exponential MA) để match TradingView
        """
        self.df = df
    
    def _detect_convergence(self):
        """
        Phát hiện MA convergence (các đường MA xoắn vào nhau) - Dấu hiệu tích luỹ
        
        Returns:
            dict: {
                'is_converging': bool,
                'convergence_strength': float (0-100),
                'avg_distance': float,
                'message': str
            }
        """
        if self.df is None or len(self.df) < 50:
            return {
                'is_converging': False,
                'convergence_strength': 0,
                'avg_distance': 0,
                'message': 'Không đủ dữ liệu'
            }
        
        latest = self.df.iloc[-1]
        
        # Tính khoảng cách % giữa các MA (KHÔNG dùng MA5 - quá nhạy)
        ma10 = latest['MA10']
        ma20 = latest['MA20']
        ma50 = latest['MA50']
        
        if ma50 == 0:
            return {
                'is_converging': False,
                'convergence_strength': 0,
                'avg_distance': 0,
                'message': 'MA50 = 0'
            }
        
        # Khoảng cách % so với MA50 (chỉ MA10 và MA20)
        dist_10_50 = abs((ma10 - ma50) / ma50 * 100)
        dist_20_50 = abs((ma20 - ma50) / ma50 * 100)
        
        # Khoảng cách trung bình (2 MA thay vì 3)
        avg_distance = (dist_10_50 + dist_20_50) / 2
        
        # Convergence strength: 100 khi các MA xoắn sát nhau (< 1%)
        # 0 khi các MA cách xa (> 8%)
        convergence_strength = max(0, min(100, (8 - avg_distance) / 8 * 100))
        
        is_converging = avg_distance < 4  # Các MA xoắn vào nhau khi cách nhau < 4% (tighter threshold)
        
        if avg_distance < 1.5:
            message = f"⚡ MA siêu xoắn (TB: {avg_distance:.1f}%) - Breakout sắp xảy ra!"
        elif avg_distance < 4:
            message = f"🔄 MA đang tích luỹ (TB: {avg_distance:.1f}%) - Theo dõi breakout"
        elif avg_distance < 8:
            message = f"➕ MA gần nhau (TB: {avg_distance:.1f}%)"
        else:
            message = f"↔️ MA cách xa (TB: {avg_distance:.1f}%)"
        
        return {
            'is_converging': is_converging,
            'convergence_strength': convergence_strength,
            'avg_distance': avg_distance,
            'message': message
        }
    
    def _detect_expansion(self):
        """
        Phát hiện MA expansion (các đường MA xoè ra) - Xác nhận uptrend mạnh
        
        Returns:
            dict: {
                'is_expanding': bool,
                'expansion_quality': str (PERFECT/GOOD/WEAK),
                'ma50_slope': float,
                'distances': dict,
                'message': str
            }
        """
        if self.df is None or len(self.df) < 50:
            return {
                'is_expanding': False,
                'expansion_quality': 'WEAK',
                'ma50_slope': 0,
                'distances': {},
                'message': 'Không đủ dữ liệu'
            }
        
        latest = self.df.iloc[-1]
        
        # Kiểm tra Perfect Order (MA10 > MA20 > MA50, KHÔNG dùng MA5)
        perfect_order = (latest['MA10'] > latest['MA20'] > latest['MA50'])
        
        if not perfect_order:
            return {
                'is_expanding': False,
                'expansion_quality': 'WEAK',
                'ma50_slope': 0,
                'distances': {},
                'message': '❌ Không có Perfect Order'
            }
        
        # Tính khoảng cách giữa các MA (% so với MA50, KHÔNG dùng MA5)
        ma50 = latest['MA50']
        if ma50 == 0:
            return {
                'is_expanding': False,
                'expansion_quality': 'WEAK',
                'ma50_slope': 0,
                'distances': {},
                'message': 'MA50 = 0'
            }
        
        dist_10_50 = (latest['MA10'] - ma50) / ma50 * 100
        dist_20_50 = (latest['MA20'] - ma50) / ma50 * 100
        
        distances = {
            'ma10_ma50': dist_10_50,
            'ma20_ma50': dist_20_50
        }
        
        # Tính độ nghiêng (slope) của MA50 trong 10 ngày gần nhất
        if len(self.df) >= 10:
            ma50_10_days_ago = self.df.iloc[-10]['MA50']
            ma50_slope = ((ma50 - ma50_10_days_ago) / ma50_10_days_ago * 100) if ma50_10_days_ago > 0 else 0
        else:
            ma50_slope = 0
        
        # Đánh giá expansion quality (dựa vào MA10 thay vì MA5)
        if dist_10_50 > 6 and dist_20_50 > 3 and ma50_slope > 2:
            expansion_quality = 'PERFECT'
            message = f"🚀 Perfect Expansion! MA xoè rộng (MA10 +{dist_10_50:.1f}%, MA20 +{dist_20_50:.1f}%) | MA50 slope +{ma50_slope:.1f}%"
        elif dist_10_50 > 4 and dist_20_50 > 2 and ma50_slope > 1:
            expansion_quality = 'GOOD'
            message = f"✅ MA đang xoè ra (MA10 +{dist_10_50:.1f}%, MA20 +{dist_20_50:.1f}%) | MA50 slope +{ma50_slope:.1f}%"
        elif dist_10_50 > 2:
            expansion_quality = 'WEAK'
            message = f"➕ MA xoè yếu (MA10 +{dist_10_50:.1f}%, MA20 +{dist_20_50:.1f}%) | MA50 slope +{ma50_slope:.1f}%"
        else:
            expansion_quality = 'WEAK'
            message = f"⚠️ Perfect Order nhưng MA chưa xoè rõ (MA10 +{dist_10_50:.1f}%)"
        
        return {
            'is_expanding': expansion_quality in ['PERFECT', 'GOOD'],
            'expansion_quality': expansion_quality,
            'ma50_slope': ma50_slope,
            'distances': distances,
            'message': message
        }
    
    def _detect_golden_cross(self):
        """
        Phát hiện và đánh giá chất lượng Golden Cross (các mức độ uy tín khác nhau)
        
        Returns:
            dict: {
                'crosses': list of dicts,
                'best_cross': dict or None,
                'message': str
            }
        """
        if self.df is None or len(self.df) < 50:
            return {
                'crosses': [],
                'best_cross': None,
                'message': 'Không đủ dữ liệu'
            }
        
        crosses = []
        latest = self.df.iloc[-1]
        
        if len(self.df) >= 2:
            prev = self.df.iloc[-2]
            
            # MA10 x MA20 (Golden Cross ngắn hạn - 6 điểm)
            if prev['MA10'] <= prev['MA20'] and latest['MA10'] > latest['MA20']:
                crosses.append({
                    'type': 'MA10_MA20',
                    'label': 'Golden Cross ngắn hạn',
                    'score': 6,
                    'icon': '🟠'
                })
            
            # MA20 x MA50 (Golden Cross UY TÍN - 10 điểm) - QUAN TRỌNG NHẤT
            if prev['MA20'] <= prev['MA50'] and latest['MA20'] > latest['MA50']:
                crosses.append({
                    'type': 'MA20_MA50',
                    'label': 'Golden Cross UY TÍN',
                    'score': 10,
                    'icon': '🏆'
                })
        
        # Tìm cross uy tín nhất
        best_cross = None
        if crosses:
            best_cross = max(crosses, key=lambda x: x['score'])
        
        # Tạo message
        if not crosses:
            message = "Không có Golden Cross gần đây"
        else:
            message = f"{best_cross['icon']} {best_cross['label']} vừa xảy ra!"
        
        return {
            'crosses': crosses,
            'best_cross': best_cross,
            'message': message
        }
    
    def _detect_tight_convergence(self, convergence, sell_warning):
        """
        Phát hiện MA SIÊU XOẮN - Dấu hiệu breakout sắp xảy ra
        
        Đây là insight quan trọng: khi MA xoắn rất sát nhau, chỉ cần 1 phiên
        breakout là có thể chuyển sang Perfect Order hoặc tăng mạnh.
        
        Điều kiện:
        - Convergence strength > 75% (MA siêu xoắn)
        - Giá > MA50 (đang trong xu hướng tăng)
        - Perfect Order = True HOẶC gần đạt (MA10 > MA20 gần bằng MA50)
        - KHÔNG có sell warning CRITICAL (death cross thật sự)
        
        Args:
            convergence: Kết quả từ _detect_convergence()
            sell_warning: Kết quả từ _detect_sell_warning()
            
        Returns:
            dict: {
                'is_tight': bool,
                'strength': float,
                'message': str,
                'suggested_action': str
            }
        """
        if self.df is None or len(self.df) < 50:
            return {
                'is_tight': False,
                'strength': 0,
                'message': '',
                'suggested_action': 'WAIT'
            }
        
        latest = self.df.iloc[-1]
        price = latest['close']
        ma10 = latest['MA10']
        ma20 = latest['MA20']
        ma50 = latest['MA50']
        
        # Điều kiện 1: Convergence strength > 75% (siêu xoắn)
        strength = convergence.get('convergence_strength', 0)
        if strength < 75:
            return {'is_tight': False, 'strength': strength, 'message': '', 'suggested_action': 'WAIT'}
        
        # Điều kiện 2: Giá > MA50 (trong uptrend)
        if price <= ma50:
            return {'is_tight': False, 'strength': strength, 'message': '', 'suggested_action': 'WAIT'}
        
        # Điều kiện 3: Perfect Order HOẶC gần đạt HOẶC convergence CỰC mạnh
        # Khi convergence > 95%, MA đã xoắn CỰC sát → không cần Perfect Order
        # VD: TPB với strength 97.6%, avg_dist 0.19% = MA gần như chạm nhau!
        perfect_order = (ma10 > ma20 > ma50)
        near_perfect_order = (ma10 > ma20 and ma20 >= ma50 * 0.998)  # MA20 gần MA50 trong 0.2%
        ultra_tight = (strength >= 95)  # Convergence CỰC mạnh, không cần PO
        
        if not (perfect_order or near_perfect_order or ultra_tight):
            return {'is_tight': False, 'strength': strength, 'message': '', 'suggested_action': 'WAIT'}
        
        # Điều kiện 4: KHÔNG có death cross (CRITICAL sell warning)
        has_critical_warning = sell_warning.get('has_warning') and sell_warning.get('warning_level') == 'CRITICAL'
        if has_critical_warning:
            return {'is_tight': False, 'strength': strength, 'message': '', 'suggested_action': 'WAIT'}
        
        # Passed all conditions!
        avg_dist = convergence.get('avg_distance', 0)
        
        # Message based on strength
        if strength >= 90:
            message = f"⚡⚡ MA SIÊU SIÊU XOẮN ({strength:.0f}%, TB: {avg_dist:.2f}%) - Breakout CỰC GẦN!"
            suggested_action = 'WATCH_CLOSELY'
        else:
            message = f"⚡ MA SIÊU XOẮN ({strength:.0f}%, TB: {avg_dist:.1f}%) - Breakout sắp xảy ra"
            suggested_action = 'WATCH'
        
        return {
            'is_tight': True,
            'strength': strength,
            'avg_distance': avg_dist,
            'message': message,
            'suggested_action': suggested_action
        }
    
    def _analyze_ma_momentum(self):
        """
        Phân tích momentum (tốc độ thay đổi) của từng MA để dự đoán xu hướng tương lai
        
        Momentum = slope của MA trong N ngày gần nhất (% change per day)
        - MA10: 5 ngày (ngắn hạn, phản ứng nhanh)
        - MA20: 10 ngày (trung hạn)
        - MA50: 20 ngày (dài hạn, xu hướng chính)
        
        Returns:
            dict: {
                'ma10': {'slope': float, 'trend': str, 'strength': str},
                'ma20': {'slope': float, 'trend': str, 'strength': str},
                'ma50': {'slope': float, 'trend': str, 'strength': str},
                'alignment': str (BULLISH_ALIGNED/MIXED/BEARISH_ALIGNED),
                'summary': str
            }
        """
        if self.df is None or len(self.df) < 50:
            return {
                'ma10': {'slope': 0, 'trend': 'NEUTRAL', 'strength': 'WEAK'},
                'ma20': {'slope': 0, 'trend': 'NEUTRAL', 'strength': 'WEAK'},
                'ma50': {'slope': 0, 'trend': 'NEUTRAL', 'strength': 'WEAK'},
                'alignment': 'NEUTRAL',
                'summary': 'Không đủ dữ liệu'
            }
        
        latest = self.df.iloc[-1]
        
        def calc_ma_slope(ma_name, lookback_days):
            """Tính slope của MA trong N ngày gần nhất"""
            if len(self.df) < lookback_days:
                return 0
            
            ma_current = latest[ma_name]
            ma_past = self.df.iloc[-lookback_days][ma_name]
            
            if ma_past == 0:
                return 0
            
            # % change per day
            total_change_pct = (ma_current - ma_past) / ma_past * 100
            slope = total_change_pct / lookback_days
            
            return slope
        
        # Tính slope cho từng MA
        ma10_slope = calc_ma_slope('MA10', 5)
        ma20_slope = calc_ma_slope('MA20', 10)
        ma50_slope = calc_ma_slope('MA50', 20)
        
        def interpret_slope(slope, ma_name):
            """Diễn giải slope"""
            # Trend
            if slope > 0.3:
                trend = 'UPTREND'
            elif slope > 0.1:
                trend = 'MILD_UPTREND'
            elif slope > -0.1:
                trend = 'NEUTRAL'
            elif slope > -0.3:
                trend = 'MILD_DOWNTREND'
            else:
                trend = 'DOWNTREND'
            
            # Strength
            abs_slope = abs(slope)
            if abs_slope > 0.5:
                strength = 'VERY_STRONG'
            elif abs_slope > 0.3:
                strength = 'STRONG'
            elif abs_slope > 0.15:
                strength = 'MODERATE'
            else:
                strength = 'WEAK'
            
            return {
                'slope': slope,
                'slope_pct_per_day': slope,
                'trend': trend,
                'strength': strength
            }
        
        ma10_analysis = interpret_slope(ma10_slope, 'MA10')
        ma20_analysis = interpret_slope(ma20_slope, 'MA20')
        ma50_analysis = interpret_slope(ma50_slope, 'MA50')
        
        # Kiểm tra alignment (tất cả MA cùng hướng)
        uptrend_count = sum([
            1 if ma10_slope > 0.1 else 0,
            1 if ma20_slope > 0.1 else 0,
            1 if ma50_slope > 0.1 else 0
        ])
        
        downtrend_count = sum([
            1 if ma10_slope < -0.1 else 0,
            1 if ma20_slope < -0.1 else 0,
            1 if ma50_slope < -0.1 else 0
        ])
        
        if uptrend_count == 3:
            alignment = 'BULLISH_ALIGNED'
            summary = f"🚀 TẤT CẢ MA đang tăng - Xu hướng tăng mạnh (MA10: +{ma10_slope:.2f}%/ngày, MA50: +{ma50_slope:.2f}%/ngày)"
        elif uptrend_count >= 2:
            alignment = 'MOSTLY_BULLISH'
            summary = f"📈 Đa số MA đang tăng - Xu hướng tăng ({uptrend_count}/3 MA tăng)"
        elif downtrend_count == 3:
            alignment = 'BEARISH_ALIGNED'
            summary = f"📉 TẤT CẢ MA đang giảm - Xu hướng giảm mạnh (MA10: {ma10_slope:.2f}%/ngày, MA50: {ma50_slope:.2f}%/ngày)"
        elif downtrend_count >= 2:
            alignment = 'MOSTLY_BEARISH'
            summary = f"⚠️ Đa số MA đang giảm - Xu hướng giảm ({downtrend_count}/3 MA giảm)"
        else:
            alignment = 'MIXED'
            summary = f"➕ MA hướng hỗn hợp - Thị trường sideway/tích luỹ"
        
        return {
            'ma10': ma10_analysis,
            'ma20': ma20_analysis,
            'ma50': ma50_analysis,
            'alignment': alignment,
            'summary': summary
        }
    
    def _forecast_scenarios(self, momentum):
        """
        Dự đoán kịch bản tương lai dựa trên momentum của MA
        
        Kịch bản:
        1. STRONG_UPTREND: Tất cả MA tăng mạnh → tiếp tục tăng trong 5-10 phiên
        2. UPTREND_CONSOLIDATION: MA tăng nhưng chậm lại → có thể tích luỹ
        3. BREAKOUT_SOON: MA convergence + momentum tăng → breakout sắp xảy ra
        4. DOWNTREND_WARNING: MA bắt đầu giảm → có thể điều chỉnh
        5. STRONG_DOWNTREND: Tất cả MA giảm → tiếp tục giảm
        
        Args:
            momentum: Kết quả từ _analyze_ma_momentum()
            
        Returns:
            dict: {
                'scenario': str,
                'probability': str (HIGH/MEDIUM/LOW),
                'timeframe': str (1-3 days / 5-10 days / etc),
                'key_levels': dict,
                'action_plan': str,
                'description': str
            }
        """
        if self.df is None or len(self.df) < 50:
            return {
                'scenario': 'UNKNOWN',
                'probability': 'LOW',
                'timeframe': 'N/A',
                'key_levels': {},
                'action_plan': 'Chờ đủ dữ liệu',
                'description': 'Không đủ dữ liệu để dự đoán'
            }
        
        latest = self.df.iloc[-1]
        price = latest['close']
        ma10 = latest['MA10']
        ma20 = latest['MA20']
        ma50 = latest['MA50']
        
        ma10_slope = momentum['ma10']['slope']
        ma20_slope = momentum['ma20']['slope']
        ma50_slope = momentum['ma50']['slope']
        alignment = momentum['alignment']
        
        # Tính convergence để phát hiện breakout
        convergence = self._detect_convergence()
        is_converging = convergence.get('is_converging', False)
        conv_strength = convergence.get('convergence_strength', 0)
        
        # Perfect Order
        perfect_order = (ma10 > ma20 > ma50)
        
        # SCENARIO 1: STRONG UPTREND
        if alignment == 'BULLISH_ALIGNED' and ma50_slope > 0.3 and perfect_order:
            return {
                'scenario': 'STRONG_UPTREND',
                'probability': 'HIGH',
                'timeframe': '5-10 phiên',
                'key_levels': {
                    'support': ma20,
                    'strong_support': ma50,
                    'target': price * (1 + ma10_slope / 100 * 10)  # Dự đoán giá sau 10 phiên
                },
                'action_plan': '✅ GIỮ - Để giá chạy, chỉ bán nếu giá phá xuống MA20',
                'description': f'🚀 Xu hướng tăng MẠN MẼ - Tất cả MA đang tăng (MA50: +{ma50_slope:.2f}%/ngày). Dự kiến tiếp tục tăng trong 5-10 phiên tới.'
            }
        
        # SCENARIO 2: UPTREND CONSOLIDATION
        if alignment in ['BULLISH_ALIGNED', 'MOSTLY_BULLISH'] and 0.1 < ma50_slope < 0.3 and perfect_order:
            return {
                'scenario': 'UPTREND_CONSOLIDATION',
                'probability': 'MEDIUM',
                'timeframe': '3-7 phiên',
                'key_levels': {
                    'support': ma10,
                    'strong_support': ma20,
                    'resistance': price * 1.03  # Kháng cự gần
                },
                'action_plan': '➕ GIỮ hoặc CHỐT LỜI 30% - Uptrend chậm lại, có thể tích luỹ',
                'description': f'📈 Xu hướng tăng CHẬM LẠI - MA50 slope giảm ({ma50_slope:.2f}%/ngày). Có thể tích luỹ 3-7 phiên trước khi tăng tiếp hoặc điều chỉnh.'
            }
        
        # SCENARIO 3: BREAKOUT SOON
        if is_converging and conv_strength > 70 and price > ma50 and ma50_slope > 0:
            timeframe = '1-3 phiên' if conv_strength > 85 else '3-5 phiên'
            probability = 'HIGH' if conv_strength > 85 else 'MEDIUM'
            
            return {
                'scenario': 'BREAKOUT_SOON',
                'probability': probability,
                'timeframe': timeframe,
                'key_levels': {
                    'breakout_level': max(ma10, ma20, ma50) * 1.01,  # Breakout khi vượt MA cao nhất + 1%
                    'support': ma50,
                    'target': price * 1.05  # Target +5% sau breakout
                },
                'action_plan': f'⚡ THEO DÕI SÁT - MA siêu xoắn ({conv_strength:.0f}%), sẵn sàng mua khi breakout',
                'description': f'⚡ BREAKOUT SẮP XẢY RA - MA convergence {conv_strength:.0f}%, giá đang tích luỹ trên MA50. Dự kiến breakout trong {timeframe}.'
            }
        
        # SCENARIO 4: DOWNTREND WARNING
        if ma10_slope < -0.1 or (ma20_slope < -0.1 and price < ma20):
            return {
                'scenario': 'DOWNTREND_WARNING',
                'probability': 'MEDIUM',
                'timeframe': '2-5 phiên',
                'key_levels': {
                    'resistance': ma20,
                    'support': ma50,
                    'stop_loss': ma50 * 0.97  # Cắt lỗ nếu giá phá MA50 -3%
                },
                'action_plan': '⚠️ BÁN 50% - Momentum giảm, bảo vệ lợi nhuận',
                'description': f'⚠️ CẢNH BÁO GIẢM - MA10/MA20 bắt đầu giảm (MA10: {ma10_slope:.2f}%/ngày). Có thể điều chỉnh 2-5 phiên tới.'
            }
        
        # SCENARIO 5: STRONG DOWNTREND
        if alignment in ['BEARISH_ALIGNED', 'MOSTLY_BEARISH'] and ma50_slope < -0.1:
            return {
                'scenario': 'STRONG_DOWNTREND',
                'probability': 'HIGH',
                'timeframe': '5-10 phiên',
                'key_levels': {
                    'resistance': ma50,
                    'support': price * (1 + ma10_slope / 100 * 10),  # Dự đoán giá sau 10 phiên
                    'stop_loss': price  # Cắt lỗ ngay
                },
                'action_plan': '❌ BÁN NGAY - Xu hướng giảm mạnh',
                'description': f'📉 Xu hướng GIẢM MẠNH - Tất cả MA đang giảm (MA50: {ma50_slope:.2f}%/ngày). Dự kiến tiếp tục giảm 5-10 phiên.'
            }
        
        # SCENARIO 6: NEUTRAL / SIDEWAY
        return {
            'scenario': 'SIDEWAY',
            'probability': 'MEDIUM',
            'timeframe': '3-7 phiên',
            'key_levels': {
                'support': min(ma10, ma20, ma50),
                'resistance': max(ma10, ma20, ma50),
                'price_range': f"{min(ma10, ma20, ma50):.1f} - {max(ma10, ma20, ma50):.1f}"
            },
            'action_plan': '➕ THEO DÕI - Thị trường sideway, chờ tín hiệu rõ hơn',
            'description': f'➕ Thị trường SIDEWAY - MA hướng hỗn hợp, giá dao động quanh MA. Chờ breakout hoặc breakdown.'
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
        
        # Kiểm tra Perfect Order trước (KHÔNG dùng MA5)
        was_in_perfect_order = (latest['MA10'] > latest['MA20'] > latest['MA50'])
        
        if len(self.df) >= 2:
            prev = self.df.iloc[-2]
            
            # CRITICAL: MA20 cắt xuống MA50 (Death Cross uy tín)
            if prev['MA20'] >= prev['MA50'] and latest['MA20'] < latest['MA50']:
                warnings.append('🔴 DEATH CROSS MA20/MA50 - TÍN HIỆU BÁN MẠNH!')
                warning_level = 'CRITICAL'
                suggested_action = 'SELL_ALL'
            
            # HIGH: MA10 cắt xuống MA20 (Death Cross ngắn hạn - đáng tin hơn MA5xMA10)
            elif prev['MA10'] >= prev['MA20'] and latest['MA10'] < latest['MA20']:
                warnings.append('⚠️ MA10 cắt xuống MA20 - Cân nhắc bán 50%')
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
    
    def analyze(self):
        """
        Phân tích toàn diện MA và trả về kết quả với reasons dạng array
        
        Returns:
            dict: {
                'score': float (0-10),
                'status': str,
                'reasons': list of str,  # ARRAY FORMAT!
                'details': {
                    'perfect_order': bool,
                    'expansion': dict,
                    'convergence': dict,
                    'golden_cross': dict,
                    'sell_warning': dict,
                    'price_position': dict
                }
            }
        """
        if self.df is None or len(self.df) < 50:
            return {
                'score': 0,
                'status': 'NA',
                'reasons': ['Không đủ dữ liệu'],
                'details': {}
            }
        
        latest = self.df.iloc[-1]
        price = latest['close']
        score = 0
        reasons = []
        
        # === 1. PHÂN TÍCH PERFECT ORDER & MA EXPANSION ===
        # Perfect Order KHÔNG dùng MA5 (quá nhạy với noise)
        perfect_order = (latest['MA10'] > latest['MA20'] > latest['MA50'])
        expansion = self._detect_expansion()
        
        if perfect_order:
            if expansion['expansion_quality'] == 'PERFECT':
                score += 6
                reasons.append(expansion['message'])
            elif expansion['expansion_quality'] == 'GOOD':
                score += 5
                reasons.append(expansion['message'])
            else:
                score += 3
                reasons.append("✅ Perfect Order nhưng MA chưa xoè rõ")
        elif (latest['MA10'] > latest['MA20']):
            score += 2
            reasons.append("➕ MA ngắn hạn tích cực (MA10>MA20)")
        else:
            reasons.append("⚠️ Chưa có Perfect Order")
        
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
        
        price_position = {
            'vs_ma50': dist_to_ma50,
            'vs_ma20': dist_to_ma20,
            'vs_ma10': dist_to_ma10
        }
        
        if price > latest['MA50']:
            score += 2
            reasons.append(f"✅ Giá trên MA50 (+{dist_to_ma50:.1f}%)")
        elif price > latest['MA20']:
            score += 1
            reasons.append(f"➕ Giá trên MA20 (+{dist_to_ma20:.1f}%)")
        elif price > latest['MA10']:
            score += 0.5
            reasons.append(f"⚠️ Giá chỉ trên MA10 (+{dist_to_ma10:.1f}%)")
        else:
            reasons.append("❌ Giá dưới MA10")
        
        # === 3. PHÂN TÍCH GOLDEN CROSS ===
        golden_cross = self._detect_golden_cross()
        
        if golden_cross['best_cross']:
            best = golden_cross['best_cross']
            score += best['score'] * 0.3
            reasons.append(golden_cross['message'])
        
        # === 4. PHÂN TÍCH MA CONVERGENCE (TÍCH LUỸ) ===
        convergence = self._detect_convergence()
        
        if convergence['is_converging'] and convergence['convergence_strength'] > 70:
            score += 1
            reasons.append(convergence['message'])
        elif convergence['is_converging']:
            reasons.append(convergence['message'])
        
        # === 5. CẢNH BÁO BÁN ===
        sell_warning = self._detect_sell_warning()
        
        # === 5.5. TIGHT CONVERGENCE (MA siêu xoắn) ===
        tight_convergence = self._detect_tight_convergence(convergence, sell_warning)
        
        if tight_convergence['is_tight']:
            # MA siêu xoắn là dấu hiệu tích cực - OVERRIDE sell warning MEDIUM
            # Vì giá tạm xuống MA10/MA20 trong lúc tích luỹ là bình thường
            if sell_warning.get('warning_level') in ['MEDIUM', 'LOW']:
                score += 2  # Bonus cho tight convergence
                reasons.append(tight_convergence['message'])
                reasons.append(f"👀 Đề xuất: {tight_convergence['suggested_action']} - Theo dõi breakout!")
                # Override sell warning
                sell_warning = {
                    'has_warning': False,
                    'warning_level': 'LOW',
                    'warnings': [],
                    'suggested_action': 'WATCH'
                }
            else:
                # Có tight convergence nhưng cũng có HIGH/CRITICAL warning
                reasons.append(tight_convergence['message'])
        
        if sell_warning['has_warning']:
            # Giảm điểm nếu có cảnh báo
            if sell_warning['warning_level'] == 'CRITICAL':
                score = max(0, score - 5)
            elif sell_warning['warning_level'] == 'HIGH':
                score = max(0, score - 3)
            elif sell_warning['warning_level'] == 'MEDIUM':
                score = max(0, score - 1)
            
            # Thêm cảnh báo vào reasons
            for warning in sell_warning['warnings']:
                reasons.append(warning)
            
            reasons.append(f"👉 Đề xuất: {sell_warning['suggested_action']}")
        
        # === 6. PHÂN TÍCH MOMENTUM & FORECAST ===
        momentum = self._analyze_ma_momentum()
        forecast = self._forecast_scenarios(momentum)
        
        # Thêm momentum summary vào reasons
        if momentum['alignment'] in ['BULLISH_ALIGNED', 'MOSTLY_BULLISH']:
            reasons.append(momentum['summary'])
        
        # Đảm bảo score không vượt quá 10
        final_score = min(score, 10)
        
        # Map score to status
        if final_score >= 9:
            status = 'EXCELLENT'
        elif final_score >= 7:
            status = 'GOOD'
        elif final_score >= 4:
            status = 'ACCEPTABLE'
        elif final_score >= 2:
            status = 'WARNING'
        else:
            status = 'POOR'
        
        return {
            'score': final_score,
            'status': status,
            'reasons': reasons,  # ARRAY FORMAT!
            'details': {
                'perfect_order': perfect_order,
                'expansion': expansion,
                'convergence': convergence,
                'golden_cross': golden_cross,
                'sell_warning': sell_warning,
                'tight_convergence': tight_convergence,
                'price_position': price_position
            },
            # FORECAST - Dự đoán tương lai (NEW!)
            'forecast': {
                'momentum': momentum,
                'scenario': forecast
            },
            # UI-READY FORMAT (Backend-driven UI pattern)
            'ui_alerts': self._format_ui_alerts(sell_warning, convergence, golden_cross, expansion, tight_convergence)
        }
    
    def _format_ui_alerts(self, sell_warning, convergence, golden_cross, expansion, tight_convergence):
        """
        Format MA alerts for UI rendering (Backend-driven pattern)
        UI chỉ cần v-for loop qua array này, không cần business logic
        
        CRITICAL RULES (UPDATED v2):
        1. Alerts phải phản ánh chính xác trạng thái thị trường
        2. Convergence CHỈ tích cực KHI đang trong uptrend (giá > MA50)
        3. Tránh mâu thuẫn: Sell Warning → loại bỏ tín hiệu mua
        4. TIGHT CONVERGENCE (MA siêu xoắn) override sell_warning MEDIUM - đây là insight quan trọng!
        5. Priority: Sell Warning CRITICAL > Tight Convergence > Expansion > Weak Uptrend > Golden Cross > Convergence
        
        Args:
            sell_warning: Sell warning detection result
            convergence: Convergence detection result
            golden_cross: Golden cross detection result
            expansion: Expansion detection result
            tight_convergence: Tight convergence detection result
            
        Returns:
            list: Array of UI-ready alert objects sorted by priority
        """
        alerts = []
        has_critical_warning = sell_warning.get('has_warning') and sell_warning.get('warning_level') in ['CRITICAL', 'HIGH']
        
        # Get current market state from self.df
        in_uptrend = False
        perfect_order = False
        price_above_ma50_pct = 0
        
        if hasattr(self, 'df') and self.df is not None and len(self.df) > 0:
            latest = self.df.iloc[-1]
            price = latest['close']
            ma50 = latest['MA50']
            
            # Perfect Order KHÔNG dùng MA5 (quá nhạy)
            perfect_order = (latest['MA10'] > latest['MA20'] > latest['MA50'])
            in_uptrend = price > ma50  # Uptrend = giá trên MA50
            price_above_ma50_pct = (price - ma50) / ma50 * 100 if ma50 > 0 else 0
        
        # 1. SELL WARNING - Highest priority (action required!)
        # NOTE: MEDIUM level có thể bị override bởi tight_convergence ở analyze()
        if sell_warning.get('has_warning'):
            level = sell_warning.get('warning_level', 'MEDIUM')
            
            warnings_html = '<br>'.join([f'• {w}' for w in sell_warning.get('warnings', [])])
            tooltip = (
                f"<strong>🚨 CẢNH BÁO BÁN ({level})</strong><br>"
                f"<div style='color: #ff5252;'>{warnings_html}</div>"
                f"<div style='font-weight: 600; margin-top: 4px;'>👉 Đề xuất: {sell_warning.get('suggested_action', '')}</div>"
            )
            
            alerts.append({
                'type': 'sell_warning',
                'priority': 1,
                'icon': 'mdi-alert',
                'color': 'error' if level in ['CRITICAL', 'HIGH'] else 'warning',
                'size': 'default' if level in ['CRITICAL', 'HIGH'] else 'small',
                'animation': 'pulse-animation' if level in ['CRITICAL', 'HIGH'] else '',
                'tooltip': tooltip
            })
        
        # 1.5. TIGHT CONVERGENCE - MA siêu xoắn, insight quan trọng!
        # Priority cao hơn expansion vì đây là DỰ BÁO về breakout sắp xảy ra
        if tight_convergence.get('is_tight'):
            strength = tight_convergence.get('strength', 0)
            avg_dist = tight_convergence.get('avg_distance', 0)
            action = tight_convergence.get('suggested_action', 'WATCH')
            
            # Emoji based on strength
            emoji = '⚡⚡⚡' if strength >= 95 else '⚡⚡' if strength >= 85 else '⚡'
            
            tooltip = (
                f"<strong>{emoji} MA SIÊU XOẮN - Breakout sắp xảy ra!</strong><br>"
                f"<span style='color: #FF6F00; font-weight: 600;'>Độ mạnh: {strength:.0f}/100</span><br>"
                f"Khoảng cách TB: {avg_dist:.2f}%<br>"
                f"<div style='margin-top: 4px; color: #FFA726;'>👀 Theo dõi sát, chỉ cần 1 phiên breakout!</div>"
                f"<div style='font-weight: 600; margin-top: 4px;'>📊 Đề xuất: {action}</div>"
            )
            
            alerts.append({
                'type': 'tight_convergence',
                'priority': 1.5,
                'icon': 'mdi-flash-alert',
                'color': 'deep-orange',
                'size': 'default' if strength >= 90 else 'small',
                'animation': 'pulse-animation' if strength >= 90 else '',
                'tooltip': tooltip
            })
        
        # 2. EXPANSION - Strong uptrend (explain S/A tier)
        if expansion.get('is_expanding'):
            quality = expansion.get('expansion_quality', 'WEAK')
            distances = expansion.get('distances', {})
            ma50_slope = expansion.get('ma50_slope', 0)
            
            tooltip = (
                f"<strong>🚀 MA EXPANSION - Uptrend mạnh</strong><br>"
                f"<span style='color: #4CAF50; font-weight: 600;'>Mức độ: {quality}</span><br>"
                f"MA10 cách MA50: +{distances.get('ma10_ma50', 0):.1f}%<br>"
                f"MA20 cách MA50: +{distances.get('ma20_ma50', 0):.1f}%<br>"
                f"MA50 slope: +{ma50_slope:.1f}%<br>"
                f"<div style='margin-top: 4px; color: #66BB6A;'>✅ Xu hướng tăng rõ ràng, có thể giữ tiếp</div>"
            )
            
            alerts.append({
                'type': 'expansion',
                'priority': 2,
                'icon': 'mdi-trending-up',
                'color': 'success' if quality == 'PERFECT' else 'green',
                'size': 'default' if quality == 'PERFECT' else 'small',
                'animation': '',
                'tooltip': tooltip
            })
        
        # 3. WEAK UPTREND - Price > MA50 but not Perfect Order (explain A/B tier)
        # Chỉ hiển thị nếu chưa có expansion và đang trong uptrend
        if len(alerts) == 0 and in_uptrend and not perfect_order:
            tooltip = (
                f"<strong>📈 UPTREND YẾU - Giá trên MA50</strong><br>"
                f"<span style='color: #2196F3; font-weight: 600;'>Giá cách MA50: +{price_above_ma50_pct:.1f}%</span><br>"
                f"⚠️ Chưa có Perfect Order<br>"
                f"<div style='margin-top: 4px; color: #42A5F5;'>➕ Xu hướng tăng yếu, theo dõi tiếp</div>"
            )
            
            alerts.append({
                'type': 'weak_uptrend',
                'priority': 3,
                'icon': 'mdi-chevron-triple-up',
                'color': 'blue',
                'size': 'small',
                'animation': '',
                'tooltip': tooltip
            })
        
        # 4. GOLDEN CROSS - Buy signal (only if no critical warning)
        if golden_cross.get('best_cross') and not has_critical_warning:
            cross = golden_cross['best_cross']
            tooltip = (
                f"<strong>⭐ GOLDEN CROSS - Tín hiệu mua</strong><br>"
                f"{cross.get('icon', '')} {cross.get('label', '')}<br>"
                f"Điểm uy tín: {cross.get('score', 0)}/10<br>"
                f"<div style='margin-top: 4px; color: #FFA726;'>✅ Có thể mua, theo dõi tiếp</div>"
            )
            
            alerts.append({
                'type': 'golden_cross',
                'priority': 4,
                'icon': 'mdi-star-circle',
                'color': 'amber',
                'size': 'small',
                'animation': '',
                'tooltip': tooltip
            })
        
        # 5. CONVERGENCE - CHỈ có ý nghĩa tích cực KHI trong uptrend NHƯNG chưa Perfect Order
        # KHÔNG hiển thị nếu:
        # - Có critical warning (mâu thuẫn)
        # - KHÔNG trong uptrend (convergence trong sideway/downtrend = không rõ hướng)
        # - ĐÃ có Perfect Order (mâu thuẫn - Perfect Order nghĩa là MA đã xếp rõ, không còn converging)
        if (convergence.get('is_converging') and 
            not has_critical_warning and 
            in_uptrend and 
            not perfect_order):
            
            avg_dist = convergence.get('avg_distance', 0)
            strength = convergence.get('convergence_strength', 0)
            
            tooltip = (
                f"<strong>🔄 MA CONVERGENCE - Tích luỹ trong uptrend</strong><br>"
                f"<span style='color: #9C27B0; font-weight: 600;'>Độ mạnh: {strength:.0f}/100</span><br>"
                f"Khoảng cách TB: {avg_dist:.1f}%<br>"
                f"<div style='margin-top: 4px; color: #AB47BC;'>⚡ Tích luỹ, chuẩn bị breakout lên</div>"
            )
            
            alerts.append({
                'type': 'convergence',
                'priority': 5,
                'icon': 'mdi-arrow-collapse',
                'color': 'purple',
                'size': 'small',
                'animation': '',
                'tooltip': tooltip
            })
        
        # 6. PERFECT ORDER - Default positive signal (explain S/A/B tier)
        # Hiển thị nếu:
        # - Chưa có alert nào HOẶC
        # - Có Perfect Order nhưng chỉ có convergence (mâu thuẫn, ưu tiên Perfect Order)
        show_perfect_order = (len(alerts) == 0 and perfect_order) or \
                             (perfect_order and len(alerts) == 1 and alerts[0]['type'] == 'convergence')
        
        if show_perfect_order:
            # Xóa convergence nếu có (mâu thuẫn với Perfect Order)
            alerts = [a for a in alerts if a['type'] != 'convergence']
            tooltip = (
                f"<strong>✅ PERFECT ORDER - Xu hướng tốt</strong><br>"
                f"MA10 > MA20 > MA50<br>"
                f"Giá cách MA50: +{price_above_ma50_pct:.1f}%<br>"
                f"<div style='margin-top: 4px; color: #2196F3;'>📈 Xu hướng tăng, theo dõi tiếp</div>"
            )
            
            alerts.append({
                'type': 'perfect_order',
                'priority': 6,
                'icon': 'mdi-check-circle',
                'color': 'blue',
                'size': 'small',
                'animation': '',
                'tooltip': tooltip
            })
        
        # Sort by priority
        alerts.sort(key=lambda x: x['priority'])
        
        return alerts
