"""
MA Analyzer - Phân tích Moving Average (Đường trung bình động)
"""

class MAAnalyzer:
    """
    Chuyên phân tích Moving Average
    
    Hỗ trợ phương pháp đầu tư theo MA:
    - Perfect Order (MA5>MA10>MA20>MA50)
    - MA Convergence (tích luỹ trước breakout)
    - MA Expansion (xoè ra - xu hướng mạnh)
    - Golden Cross (nhiều mức độ uy tín)
    - Sell Warnings (cảnh báo bán sớm)
    """
    
    def __init__(self, df):
        """
        Args:
            df: DataFrame đã tính sẵn các MA (MA5, MA10, MA20, MA50)
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
        
        # Tính khoảng cách % giữa các MA
        ma5 = latest['MA5']
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
            message = f"⚡ MA siêu xoắn (TB: {avg_distance:.1f}%) - Breakout sắp xảy ra!"
        elif avg_distance < 5:
            message = f"🔄 MA đang tích luỹ (TB: {avg_distance:.1f}%) - Theo dõi breakout"
        elif avg_distance < 10:
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
        
        # Kiểm tra Perfect Order
        perfect_order = (latest['MA5'] > latest['MA10'] > latest['MA20'] > latest['MA50'])
        
        if not perfect_order:
            return {
                'is_expanding': False,
                'expansion_quality': 'WEAK',
                'ma50_slope': 0,
                'distances': {},
                'message': '❌ Không có Perfect Order'
            }
        
        # Tính khoảng cách giữa các MA (% so với MA50)
        ma50 = latest['MA50']
        if ma50 == 0:
            return {
                'is_expanding': False,
                'expansion_quality': 'WEAK',
                'ma50_slope': 0,
                'distances': {},
                'message': 'MA50 = 0'
            }
        
        dist_5_50 = (latest['MA5'] - ma50) / ma50 * 100
        dist_10_50 = (latest['MA10'] - ma50) / ma50 * 100
        dist_20_50 = (latest['MA20'] - ma50) / ma50 * 100
        
        distances = {
            'ma5_ma50': dist_5_50,
            'ma10_ma50': dist_10_50,
            'ma20_ma50': dist_20_50
        }
        
        # Tính độ nghiêng (slope) của MA50 trong 10 ngày gần nhất
        if len(self.df) >= 10:
            ma50_10_days_ago = self.df.iloc[-10]['MA50']
            ma50_slope = ((ma50 - ma50_10_days_ago) / ma50_10_days_ago * 100) if ma50_10_days_ago > 0 else 0
        else:
            ma50_slope = 0
        
        # Đánh giá expansion quality
        if dist_5_50 > 8 and dist_20_50 > 3 and ma50_slope > 2:
            expansion_quality = 'PERFECT'
            message = f"🚀 Perfect Expansion! MA xoè rộng (MA5 +{dist_5_50:.1f}%, MA20 +{dist_20_50:.1f}%) | MA50 slope +{ma50_slope:.1f}%"
        elif dist_5_50 > 5 and dist_20_50 > 2 and ma50_slope > 1:
            expansion_quality = 'GOOD'
            message = f"✅ MA đang xoè ra (MA5 +{dist_5_50:.1f}%, MA20 +{dist_20_50:.1f}%) | MA50 slope +{ma50_slope:.1f}%"
        elif dist_5_50 > 3:
            expansion_quality = 'WEAK'
            message = f"➕ MA xoè yếu (MA5 +{dist_5_50:.1f}%, MA20 +{dist_20_50:.1f}%) | MA50 slope +{ma50_slope:.1f}%"
        else:
            expansion_quality = 'WEAK'
            message = f"⚠️ Perfect Order nhưng MA chưa xoè rõ (MA5 +{dist_5_50:.1f}%)"
        
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
        perfect_order = (latest['MA5'] > latest['MA10'] > latest['MA20'] > latest['MA50'])
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
                'price_position': price_position
            },
            # UI-READY FORMAT (Backend-driven UI pattern)
            'ui_alerts': self._format_ui_alerts(sell_warning, convergence, golden_cross, expansion)
        }
    
    def _format_ui_alerts(self, sell_warning, convergence, golden_cross, expansion):
        """
        Format MA alerts for UI rendering (Backend-driven pattern)
        UI chỉ cần v-for loop qua array này, không cần business logic
        
        Args:
            sell_warning: Sell warning detection result
            convergence: Convergence detection result
            golden_cross: Golden cross detection result
            expansion: Expansion detection result
            
        Returns:
            list: Array of UI-ready alert objects sorted by priority
        """
        alerts = []
        
        # 1. SELL WARNING - Highest priority (action required!)
        if sell_warning.get('has_warning'):
            level = sell_warning.get('warning_level', 'MEDIUM')
            
            # Build tooltip HTML
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
                'color': 'error' if level == 'HIGH' else 'warning',
                'size': 'default' if level == 'HIGH' else 'small',
                'animation': 'pulse-animation' if level == 'HIGH' else '',
                'tooltip': tooltip
            })
        
        # 2. CONVERGENCE - Breakout signal (prepare to buy!)
        if convergence.get('is_converging'):
            tooltip = (
                f"<strong>🔄 BREAKOUT SẮP XẢY RA (MA Convergence)</strong><br>"
                f"<span style='color: #9c27b0; font-weight: 600;'>⚡ Chuẩn bị điểm mua tốt!</span><br>"
                f"Khoảng cách TB: {convergence.get('avg_distance', 0):.1f}%<br>"
                f"{convergence.get('message', '')}"
            )
            
            alerts.append({
                'type': 'convergence',
                'priority': 2,
                'icon': 'mdi-arrow-collapse',
                'color': 'purple',
                'size': 'small',
                'animation': '',
                'tooltip': tooltip
            })
        
        # 3. GOLDEN CROSS - Buy signal (can buy)
        if golden_cross.get('best_cross'):
            cross = golden_cross['best_cross']
            tooltip = (
                f"<strong>⭐ Golden Cross - Có thể mua</strong><br>"
                f"{cross.get('label', '')}<br>"
                f"Credibility: {cross.get('credibility_points', 0)} pts"
            )
            
            alerts.append({
                'type': 'golden_cross',
                'priority': 3,
                'icon': 'mdi-star-circle',
                'color': 'amber',
                'size': 'small',
                'animation': '',
                'tooltip': tooltip
            })
        
        # 4. EXPANSION - Uptrend confirmation (hold)
        if expansion.get('is_expanding'):
            quality = expansion.get('expansion_quality', 'WEAK')
            tooltip = (
                f"<strong>📈 MA Expansion - Giữ tiếp</strong><br>"
                f"Mức độ: {quality}<br>"
                f"{expansion.get('message', '')}"
            )
            
            alerts.append({
                'type': 'expansion',
                'priority': 4,
                'icon': 'mdi-arrow-expand',
                'color': 'green' if quality == 'STRONG' else 'blue',
                'size': 'small',
                'animation': '',
                'tooltip': tooltip
            })
        
        # Sort by priority
        alerts.sort(key=lambda x: x['priority'])
        
        return alerts
