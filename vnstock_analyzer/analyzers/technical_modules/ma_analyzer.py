"""
MA Analyzer - Main orchestrator (Simplified after refactor)

Import pure functions from modules:
- ma_detector: detect_convergence, detect_expansion, detect_golden_cross, detect_death_cross
- ma_momentum: analyze_momentum
- volume_analyzer: analyze_volume_trend, check_convergence_volume_signal

Uses EMA (Exponential Moving Average) to match TradingView default.
"""

from vnstock_analyzer.core.constants import VN_COLORS, VN_ICONS
from .ma_detector import (
    detect_convergence,
    detect_expansion,
    detect_golden_cross,
    detect_death_cross
)
from .ma_momentum import analyze_momentum
from .volume_analyzer import analyze_volume_trend, check_convergence_volume_signal


class MAAnalyzer:
    """
    Main orchestrator for MA analysis - Simplified to ~200 lines
    
    Hỗ trợ phương pháp đầu tư theo MA (KHÔNG dùng MA5 - quá ngắn hạn):
    - Perfect Order (MA10>MA20>MA50)
    - MA Convergence (tích luỹ trước breakout)
    - MA Expansion (xoè ra - xu hướng mạnh)
    - Golden Cross (MA10xMA20, MA20xMA50)
    - Sell Warnings (cảnh báo bán sớm)
    """
    
    def __init__(self, df):
        """
        Args:
            df: DataFrame đã tính sẵn các MA (MA10, MA20, MA50)
            Note: Dùng EMA (Exponential MA) để match TradingView
        """
        self.df = df
    
    def analyze(self):
        """
        Main analysis flow - Orchestrates all modules
        
        Flow:
        1. Run all detectors (convergence, expansion, golden_cross, death_cross, tight_convergence)
        2. Run momentum analysis
        3. Format factual signals for UI (NO ADVICE)
        4. Calculate score from all signals
        
        Returns:
            dict: {
                'score': float (0-10),
                'status': str,
                'reasons': list,
                'details': dict,
                'ma_signals': list (factual signals only - NO advice)
            }
        """
        if self.df is None or len(self.df) < 50:
            return {
                'score': 0,
                'status': 'NA',
                'reasons': ['Không đủ dữ liệu'],
                'details': {},
                'ma_signals': []
            }
        
        # === 1. RUN ALL DETECTORS ===
        expansion = detect_expansion(self.df)
        
        # Check Perfect Order first (needed for convergence logic)
        latest = self.df.iloc[-1]
        perfect_order = (latest['MA10'] > latest['MA20'] > latest['MA50'])
        
        convergence = detect_convergence(self.df, perfect_order=perfect_order)
        golden_cross = detect_golden_cross(self.df)
        death_cross = detect_death_cross(self.df)
        
        # === 2. RUN MOMENTUM ANALYSIS ===
        momentum = analyze_momentum(self.df)
        
        # === 2.5. RUN VOLUME ANALYSIS ===
        volume_trend = analyze_volume_trend(self.df)
        convergence_volume_signal = check_convergence_volume_signal(convergence, volume_trend)
        
        # === 3. GET PRICE POSITION WITH UI METADATA ===
        price_position = self._get_price_position_with_ui()
        
        # === 4. CALCULATE SCORE ===
        score, status, reasons = self._calculate_score(
            expansion, convergence, golden_cross,
            death_cross, momentum
        )
        
        # === 5. RETURN STRUCTURE (NO COLUMNS - UI builds from sections) ===
        latest = self.df.iloc[-1]
        perfect_order = (latest['MA10'] > latest['MA20'] > latest['MA50'])
        
        return {
            'score': score,
            'status': status,
            'reasons': reasons,
            'perfect_order': perfect_order,
            
            # Flatten all MA data to top level
            'expansion': {
                'is_expanding': expansion.get('is_expanding'),
                'quality': expansion.get('quality'),
                'ma50_slope': round(expansion.get('ma50_slope', 0), 2),
                'ma10_ma50_distance': round(expansion.get('ma10_ma50_distance', 0), 2),
                'ma20_ma50_distance': round(expansion.get('ma20_ma50_distance', 0), 2),
                'message': expansion.get('message', ''),
                # UI metadata
                'icon': expansion.get('icon', 'mdi-arrow-expand-all'),
                'color': expansion.get('color', 'grey'),
                'label': expansion.get('label', ''),
                'tooltip': expansion.get('tooltip', '')
            },
            'convergence': {
                'is_converging': convergence.get('is_converging'),
                'convergence_pct': round(convergence.get('convergence_pct', 0), 2),
                'level': convergence.get('level', 'NA'),
                'slope': convergence.get('slope', 'NA'),
                'message': convergence.get('message', ''),
                # UI metadata
                'icon': convergence.get('icon', 'mdi-circle-outline'),
                'color': convergence.get('color', 'grey'),
                'label': convergence.get('label', ''),
                'tooltip': self._build_convergence_tooltip(convergence, convergence_volume_signal)
            },
            'golden_cross': {
                'has_cross': golden_cross.get('has_cross', False),
                'crosses': golden_cross.get('crosses', []),
                'message': golden_cross.get('message', ''),
                # UI metadata
                'icon': golden_cross.get('icon', 'mdi-star-circle'),
                'color': golden_cross.get('color', 'grey'),
                'label': golden_cross.get('label', 'No GC'),
                'tooltip': golden_cross.get('tooltip', '')
            },
            'death_cross': {
                'has_cross': death_cross.get('has_death_cross', False),
                'crosses': death_cross.get('crosses', []),
                'price_below_ma10': death_cross.get('price_below_ma', {}).get('below_ma10', False),
                'price_below_ma20': death_cross.get('price_below_ma', {}).get('below_ma20', False),
                'price_below_ma50': death_cross.get('price_below_ma', {}).get('below_ma50', False),
                # UI metadata
                'icon': death_cross.get('icon', 'mdi-alert-circle'),
                'color': death_cross.get('color', 'grey'),
                'label': death_cross.get('label', 'No DC'),
                'tooltip': death_cross.get('tooltip', '')
            },
            'momentum': {
                'ma10': {
                    'slope': round(momentum.get('ma10', {}).get('slope', 0), 2),
                    'trend': momentum.get('ma10', {}).get('trend'),
                    'strength': momentum.get('ma10', {}).get('strength')
                },
                'ma20': {
                    'slope': round(momentum.get('ma20', {}).get('slope', 0), 2),
                    'trend': momentum.get('ma20', {}).get('trend'),
                    'strength': momentum.get('ma20', {}).get('strength')
                },
                'ma50': {
                    'slope': round(momentum.get('ma50', {}).get('slope', 0), 2),
                    'trend': momentum.get('ma50', {}).get('trend'),
                    'strength': momentum.get('ma50', {}).get('strength')
                },
                'alignment': momentum.get('alignment'),
                'summary': momentum.get('summary'),
                # UI metadata
                'icon': momentum.get('icon', 'mdi-speedometer'),
                'color': momentum.get('color', 'grey'),
                'label': momentum.get('label', ''),
                'tooltip': momentum.get('tooltip', '')
            },
            'price_position': {
                'vs_ma10': round(price_position.get('vs_ma10', 0), 2),
                'vs_ma20': round(price_position.get('vs_ma20', 0), 2),
                'vs_ma50': round(price_position.get('vs_ma50', 0), 2),
                # UI metadata
                'icon': price_position.get('icon', 'mdi-arrow-up'),
                'color': price_position.get('color', 'blue'),
                'label': price_position.get('label', ''),
                'tooltip': price_position.get('tooltip', '')
            },
            
            # Volume analysis
            'volume': {
                'current_volume': volume_trend.get('current_volume', 0),
                'avg_volume': volume_trend.get('avg_volume', 0),
                'volume_ratio': volume_trend.get('volume_ratio', 0),
                'trend': volume_trend.get('trend', 'NA'),
                'is_decreasing': volume_trend.get('is_decreasing', False),
                'message': volume_trend.get('message', ''),
                # UI metadata
                'icon': volume_trend.get('icon', 'mdi-volume-high'),
                'color': volume_trend.get('color', 'grey'),
                'label': volume_trend.get('label', ''),
                'tooltip': volume_trend.get('tooltip', '')
            },
        }
    
    def _calculate_score(self, expansion, convergence, golden_cross,
                         death_cross, momentum):
        """
        Calculate score from all signals
        
        Args:
            expansion: Result from detect_expansion()
            convergence: Result from detect_convergence()
            golden_cross: Result from detect_golden_cross()
            death_cross: Result from detect_death_cross()
            momentum: Result from analyze_momentum()
            
        Returns:
            tuple: (score, status, reasons)
        """
        latest = self.df.iloc[-1]
        price = latest['close']
        score = 0
        reasons = []
        
        # === 1. PERFECT ORDER & MA EXPANSION ===
        perfect_order = (latest['MA10'] > latest['MA20'] > latest['MA50'])
        
        if perfect_order:
            if expansion['quality'] == 'STRONG':
                score += 6
                reasons.append(expansion['message'])
            elif expansion['quality'] == 'MODERATE':
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
        
        # === 2. VỊ TRÍ GIÁ SO VỚI MA ===
        price_position = self._get_price_position()
        dist_to_ma50 = price_position.get('vs_ma50', 0)
        dist_to_ma20 = price_position.get('vs_ma20', 0)
        dist_to_ma10 = price_position.get('vs_ma10', 0)
        
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
        
        # === 3. GOLDEN CROSS ===
        if golden_cross['best_cross']:
            best = golden_cross['best_cross']
            score += best['score'] * 0.3
            reasons.append(golden_cross['message'])
        
        # === 4. MA CONVERGENCE ===
        convergence_pct = convergence.get('convergence_pct', 100)
        level = convergence.get('level', 'LOOSE')
        
        if level == 'SUPER_TIGHT':
            score += 2
            reasons.append(convergence['message'])
        elif level == 'TIGHT':
            score += 1
            reasons.append(convergence['message'])
        elif convergence['is_converging']:
            reasons.append(convergence['message'])
        
        # === 6. DEATH CROSS (Factual - not advice) ===
        if death_cross['has_death_cross']:
            # Giảm điểm nếu có death cross
            strongest = death_cross.get('strongest_cross', {})
            severity = strongest.get('severity', 'LOW')
            
            if severity == 'CRITICAL':
                score = max(0, score - 5)
            elif severity == 'HIGH':
                score = max(0, score - 3)
            elif severity == 'MEDIUM':
                score = max(0, score - 1)
            
            # Thêm thông tin factual vào reasons (NO advice)
            cross_type = strongest.get('type', '')
            reasons.append(f"⚠️ Death Cross: {cross_type} (Mức độ: {severity})")
        
        # === 7. MOMENTUM SUMMARY ===
        if momentum['alignment'] in ['BULLISH_ALIGNED', 'MOSTLY_BULLISH']:
            reasons.append(momentum['summary'])
        
        # === 8. FINALIZE SCORE & STATUS ===
        final_score = min(score, 10)
        
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
        
        return final_score, status, reasons
    
    def _get_price_position_with_ui(self):
        """
        Get price position vs MA with UI metadata + Wick Rejection detection
        
        Wick Rejection (Enhanced):
        Bullish MA:
          - Low ≤ MA (test support)
          - Close > MA (rejection successful)
          - (Close-Low)/(High-Low) ≥ 60% (lower wick dominant)
          - Lower shadow ≥ 1.5× body
          - MA slope not steep down
          - Volume low-medium (not spike)
        
        Bearish MA:
          - High ≥ MA (test resistance)
          - Close < MA (rejection down)
          - Upper wick dominant
          - Upper shadow ≥ 1.5× body
          - MA slope not steep up
          - Volume low-medium
        
        Returns:
            dict: {
                'vs_ma50': float,
                'vs_ma20': float,
                'vs_ma10': float,
                'icon': str,
                'color': str,
                'label': str,
                'tooltip': str (bao gồm thông tin wick rejection)
            }
        """
        latest = self.df.iloc[-1]
        price = latest['close']
        open_price = latest['open']
        low = latest['low']
        high = latest['high']
        volume = latest['volume']
        ma50 = latest['MA50']
        ma20 = latest['MA20']
        ma10 = latest['MA10']
        
        if ma50 > 0:
            dist_to_ma50 = (price - ma50) / ma50 * 100
            dist_to_ma20 = (price - ma20) / ma20 * 100 if ma20 > 0 else 0
            dist_to_ma10 = (price - ma10) / ma10 * 100 if ma10 > 0 else 0
        else:
            dist_to_ma50 = dist_to_ma20 = dist_to_ma10 = 0
        
        # Calculate candle components
        body = abs(price - open_price)
        lower_shadow = min(price, open_price) - low
        upper_shadow = high - max(price, open_price)
        total_range = high - low
        
        # Volume check (not abnormal spike)
        if len(self.df) >= 20:
            avg_volume = self.df.iloc[-20:]['volume'].mean()
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1
            is_volume_ok = volume_ratio <= 2.5  # Not more than 2.5x average
        else:
            is_volume_ok = True
        
        # MA slope check
        def get_ma_slope(ma_col, periods=5):
            """Calculate MA slope over last N periods"""
            if len(self.df) < periods + 1:
                return 0
            recent_ma = self.df.iloc[-(periods+1):][ma_col].values
            return (recent_ma[-1] - recent_ma[0]) / recent_ma[0] * 100
        
        ma50_slope = get_ma_slope('MA50', 5)
        ma20_slope = get_ma_slope('MA20', 5)
        
        # Detect Wick Rejection with enhanced criteria
        wick_signals = []
        
        # MA50 Wick Rejection (quan trọng nhất)
        if ma50 > 0 and total_range > 0:
            # Bullish: Low test MA50, close above
            if low <= ma50 and price > ma50:
                wick_ratio = (price - low) / total_range if total_range > 0 else 0
                shadow_body_ratio = lower_shadow / body if body > 0 else 999
                
                # Check all criteria
                if (wick_ratio >= 0.6 and 
                    shadow_body_ratio >= 1.5 and 
                    ma50_slope >= -1.5 and  # MA not steep down
                    is_volume_ok):
                    
                    wick_pct = (ma50 - low) / ma50 * 100
                    wick_signals.append(f"✅ Bullish MA50: Test -{wick_pct:.1f}%; Reject({wick_ratio*100:.0f}%)")
            
            # Bearish: High test MA50, close below
            elif high >= ma50 and price < ma50:
                wick_ratio = (high - price) / total_range if total_range > 0 else 0
                shadow_body_ratio = upper_shadow / body if body > 0 else 999
                
                if (wick_ratio >= 0.6 and 
                    shadow_body_ratio >= 1.5 and 
                    ma50_slope <= 1.5 and  # MA not steep up
                    is_volume_ok):
                    
                    wick_pct = (high - ma50) / ma50 * 100
                    wick_signals.append(f"⚠️ Bearish MA50: Test +{wick_pct:.1f}%; Reject({wick_ratio*100:.0f}%)")
        
        # MA20 Wick Rejection
        if ma20 > 0 and total_range > 0:
            # Bullish: Low test MA20, close above
            if low <= ma20 and price > ma20:
                wick_ratio = (price - low) / total_range if total_range > 0 else 0
                shadow_body_ratio = lower_shadow / body if body > 0 else 999
                
                if (wick_ratio >= 0.6 and 
                    shadow_body_ratio >= 1.5 and 
                    ma20_slope >= -1.5 and 
                    is_volume_ok):
                    
                    wick_pct = (ma20 - low) / ma20 * 100
                    wick_signals.append(f"✅ Bullish MA20: Test -{wick_pct:.1f}%; Reject({wick_ratio*100:.0f}%)")
            
            # Bearish: High test MA20, close below
            elif high >= ma20 and price < ma20:
                wick_ratio = (high - price) / total_range if total_range > 0 else 0
                shadow_body_ratio = upper_shadow / body if body > 0 else 999
                
                if (wick_ratio >= 0.6 and 
                    shadow_body_ratio >= 1.5 and 
                    ma20_slope <= 1.5 and 
                    is_volume_ok):
                    
                    wick_pct = (high - ma20) / ma20 * 100
                    wick_signals.append(f"⚠️ Bearish MA20: Test +{wick_pct:.1f}%; Reject({wick_ratio*100:.0f}%)")
        
        # Determine icon & color - VN STOCK COLORS
        if dist_to_ma50 > 0:
            icon = VN_ICONS['UP']
            color = VN_COLORS['UP']  # Green - Giá trên MA50 (tốt)
        elif dist_to_ma20 > 0:
            icon = VN_ICONS['NEUTRAL']
            color = VN_COLORS['REFERENCE']  # Yellow - Giá giữa MA20-MA50
        else:
            icon = VN_ICONS['DOWN']
            color = VN_COLORS['DOWN']  # Red - Giá dưới MA50 (xấu)
        
        label = f"vs MA50: {dist_to_ma50:+.1f}%"
        
        # Build tooltip with wick signals
        tooltip = (
            f"<strong>📍 Vị trí giá</strong><br>"
            f"vs MA10: {dist_to_ma10:+.1f}%<br>"
            f"vs MA20: {dist_to_ma20:+.1f}%<br>"
            f"vs MA50: {dist_to_ma50:+.1f}%<br>"
        )
        
        # Add wick rejection signals
        if wick_signals:
            tooltip += "<br><strong>🕯️ Wick Rejection:</strong><br>"
            tooltip += "<br>".join(wick_signals)
        
        return {
            'vs_ma50': dist_to_ma50,
            'vs_ma20': dist_to_ma20,
            'vs_ma10': dist_to_ma10,
            'icon': icon,
            'color': color,
            'label': label,
            'tooltip': tooltip
        }
    
    def _get_price_position(self):
        """
        Get price position vs MA (extracted from old analyze())
        
        Returns:
            dict: {
                'vs_ma50': float,
                'vs_ma20': float,
                'vs_ma10': float
            }
        """
        latest = self.df.iloc[-1]
        price = latest['close']
        ma50 = latest['MA50']
        ma20 = latest['MA20']
        ma10 = latest['MA10']
        
        if ma50 > 0:
            dist_to_ma50 = (price - ma50) / ma50 * 100
            dist_to_ma20 = (price - ma20) / ma20 * 100 if ma20 > 0 else 0
            dist_to_ma10 = (price - ma10) / ma10 * 100 if ma10 > 0 else 0
        else:
            dist_to_ma50 = dist_to_ma20 = dist_to_ma10 = 0
        
        return {
            'vs_ma50': dist_to_ma50,
            'vs_ma20': dist_to_ma20,
            'vs_ma10': dist_to_ma10
        }    
    def _build_convergence_tooltip(self, convergence, convergence_volume_signal):
        """
        Build convergence tooltip with volume signal if available
        
        Args:
            convergence: Result from detect_convergence()
            convergence_volume_signal: Result from check_convergence_volume_signal()
            
        Returns:
            str: HTML tooltip
        """
        convergence_pct = convergence.get('convergence_pct', 0)
        level = convergence.get('level', 'NA')
        slope = convergence.get('slope', 'NA')
        slope_emoji = '📈' if slope == 'UP' else ('📉' if slope == 'DOWN' else '➡️')
        message = convergence.get('message', '')
        
        # Base tooltip
        tooltip = (
            f"<strong>⚡ MA Convergence</strong><br>"
            f"Convergence: {convergence_pct:.2f}%<br>"
            f"Level: {level}<br>"
            f"Slope: {slope} {slope_emoji}<br>"
            f"<em>{message}</em>"
        )
        
        # Add volume signal if available
        has_signal = convergence_volume_signal.get('has_signal', False)
        if has_signal:
            quality = convergence_volume_signal.get('quality', 'NA')
            vol_message = convergence_volume_signal.get('message', '')
            tooltip += f"<br><br><strong>🔥 Volume Signal</strong><br>{quality}: {vol_message}"
        
        return tooltip