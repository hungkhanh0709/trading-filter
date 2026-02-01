"""
MA Analyzer - Main orchestrator (Simplified after refactor)

Import pure functions from modules:
- ma_detector: detect_convergence, detect_expansion, detect_golden_cross, detect_sell_warning, detect_tight_convergence
- ma_momentum: analyze_momentum
- ma_forecaster: forecast_scenarios

Uses EMA (Exponential Moving Average) to match TradingView default.
"""

from .ma_detector import (
    detect_convergence,
    detect_expansion,
    detect_golden_cross,
    detect_death_cross,
    detect_tight_convergence
)
from .ma_momentum import analyze_momentum
from .ma_signal_formatter import format_ma_signals


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
        convergence = detect_convergence(self.df)
        golden_cross = detect_golden_cross(self.df)
        death_cross = detect_death_cross(self.df)
        tight_convergence = detect_tight_convergence(self.df, convergence, death_cross)
        
        # === 2. RUN MOMENTUM ANALYSIS ===
        momentum = analyze_momentum(self.df)
        
        
        # === 3. FORMAT FACTUAL MA SIGNALS (NO ADVICE) ===
        ma_signals = format_ma_signals(
            df=self.df,
            golden_cross=golden_cross,
            death_cross=death_cross,
            convergence=convergence,
            expansion=expansion,
            momentum=momentum,
            tight_convergence=tight_convergence
        )
        
        # === 4. CALCULATE SCORE ===
        score, status, reasons = self._calculate_score(
            expansion, convergence, golden_cross,
            death_cross, tight_convergence, momentum
        )
        
        # === 5. RETURN COMPREHENSIVE RESULT ===
        latest = self.df.iloc[-1]
        perfect_order = (latest['MA10'] > latest['MA20'] > latest['MA50'])
        
        return {
            'score': score,
            'status': status,
            'reasons': reasons,
            'details': {
                'perfect_order': perfect_order,
                'expansion': expansion,
                'convergence': convergence,
                'golden_cross': golden_cross,
                'death_cross': death_cross,
                'tight_convergence': tight_convergence,
                'momentum': momentum,
                'price_position': self._get_price_position()
            },
            'ma_signals': ma_signals  # Factual signals only - NO advice
        }
    
    def _calculate_score(self, expansion, convergence, golden_cross,
                         death_cross, tight_convergence, momentum):
        """
        Calculate score from all signals
        
        Args:
            expansion: Result from detect_expansion()
            convergence: Result from detect_convergence()
            golden_cross: Result from detect_golden_cross()
            death_cross: Result from detect_death_cross()
            tight_convergence: Result from detect_tight_convergence()
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
        if convergence['is_converging'] and convergence['convergence_strength'] > 70:
            score += 1
            reasons.append(convergence['message'])
        elif convergence['is_converging']:
            reasons.append(convergence['message'])
        
        # === 5. TIGHT CONVERGENCE (MA siêu xoắn) ===
        if tight_convergence['is_tight']:
            score += 2
            reasons.append(tight_convergence['message'])
        
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
