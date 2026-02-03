"""
MA Signal Formatter - Format factual signals for UI

CRITICAL: NO TRADING ADVICE
- NO "action_plan"
- NO "suggested_action"  
- NO "recommendation"

Only FACTUAL data:
- Golden Cross (when, where, type)
- Death Cross (when, where, type)
- MA Convergence (strength %)
- MA Expansion (quality, distances)
- Momentum (slope %/day)
- Price Position (% from MA)
"""

from vnstock_analyzer.core.constants import VN_COLORS, VN_ICONS


def format_ma_signals(df, golden_cross, death_cross, convergence, expansion, momentum, tight_convergence):
    """
    Format MA signals for UI - FACTUAL DATA ONLY
    
    Args:
        df: DataFrame
        golden_cross: Result from detect_golden_cross()
        death_cross: Result from detect_death_cross()
        convergence: Result from detect_convergence()
        expansion: Result from detect_expansion()
        momentum: Result from analyze_momentum()
        tight_convergence: Result from detect_tight_convergence()
        
    Returns:
        list: Array of factual signal objects
    """
    signals = []
    
    if df is None or len(df) < 2:
        return signals
    
    latest = df.iloc[-1]
    price = latest['close']
    
    # 1. GOLDEN CROSS - Factual event
    if golden_cross.get('best_cross'):
        cross = golden_cross['best_cross']
        signals.append({
            'type': 'golden_cross',
            'icon': 'mdi-trending-up',
            'color': 'success',
            'label': cross.get('label', ''),
            'data': {
                'cross_type': cross.get('type'),
                'credibility_score': cross.get('score'),
                'happened_recently': True
            },
            'tooltip': (
                f"<strong>⭐ {cross.get('label')}</strong><br>"
                f"Loại: {cross.get('type')}<br>"
                f"Độ uy tín: {cross.get('score')}/10<br>"
                f"<em style='color: #999; font-size: 0.85em;'>Chỉ là thông tin, không phải lời khuyên</em>"
            )
        })
    
    # 2. DEATH CROSS - Factual event
    if death_cross.get('has_death_cross'):
        dc = death_cross.get('strongest_cross', {})
        signals.append({
            'type': 'death_cross',
            'icon': 'mdi-trending-down',
            'color': 'error',
            'label': dc.get('label', 'Death Cross'),
            'data': {
                'cross_type': dc.get('type'),
                'severity': dc.get('severity'),
                'happened_recently': True
            },
            'tooltip': (
                f"<strong>🔴 {dc.get('label')}</strong><br>"
                f"Loại: {dc.get('type')}<br>"
                f"Mức độ: {dc.get('severity')}<br>"
                f"<em style='color: #999; font-size: 0.85em;'>Chỉ là thông tin, không phải lời khuyên</em>"
            )
        })
    
    # 3. TIGHT CONVERGENCE - Factual pattern
    if tight_convergence.get('is_tight'):
        strength = tight_convergence.get('strength', 0)
        avg_dist = tight_convergence.get('avg_distance', 0)
        
        signals.append({
            'type': 'tight_convergence',
            'icon': 'mdi-arrow-collapse-all',
            'color': 'deep-orange',
            'label': f'MA xoắn {strength:.0f}%',
            'data': {
                'convergence_strength': strength,
                'avg_distance': avg_dist,
                'pattern_type': 'tight_convergence'
            },
            'tooltip': (
                f"<strong>⚡ MA Siêu Xoắn</strong><br>"
                f"Độ mạnh: {strength:.0f}/100<br>"
                f"Khoảng cách TB: {avg_dist:.2f}%<br>"
                f"<em style='color: #999; font-size: 0.85em;'>Pattern tích luỹ - chỉ là thông tin</em>"
            )
        })
    
    # 4. EXPANSION - Factual pattern
    elif expansion.get('is_expanding'):
        quality = expansion.get('expansion_quality', 'WEAK')
        distances = expansion.get('distances', {})
        ma50_slope = expansion.get('ma50_slope', 0)
        
        signals.append({
            'type': 'expansion',
            'icon': 'mdi-arrow-expand-all',
            'color': 'success' if quality == 'PERFECT' else 'green',
            'label': f'MA xoè ({quality})',
            'data': {
                'expansion_quality': quality,
                'ma10_ma50_distance': distances.get('ma10_ma50', 0),
                'ma20_ma50_distance': distances.get('ma20_ma50', 0),
                'ma50_slope': ma50_slope,
                'pattern_type': 'expansion'
            },
            'tooltip': (
                f"<strong>🚀 MA Expansion</strong><br>"
                f"Chất lượng: {quality}<br>"
                f"MA10 cách MA50: +{distances.get('ma10_ma50', 0):.1f}%<br>"
                f"MA20 cách MA50: +{distances.get('ma20_ma50', 0):.1f}%<br>"
                f"MA50 slope: +{ma50_slope:.2f}%/ngày<br>"
                f"<em style='color: #999; font-size: 0.85em;'>Pattern uptrend - chỉ là thông tin</em>"
            )
        })
    
    # 5. MOMENTUM - Factual data
    ma10_slope = momentum['ma10']['slope']
    ma20_slope = momentum['ma20']['slope']
    ma50_slope = momentum['ma50']['slope']
    alignment = momentum['alignment']
    
    # Determine momentum icon color - VN STOCK COLORS
    if alignment in ['BULLISH_ALIGNED', 'MOSTLY_BULLISH']:
        momentum_color = VN_COLORS['UP']  # Green - Bullish
        momentum_icon = VN_ICONS['TREND_UP']
    elif alignment in ['BEARISH_ALIGNED', 'MOSTLY_BEARISH']:
        momentum_color = VN_COLORS['DOWN']  # Red - Bearish
        momentum_icon = VN_ICONS['TREND_DOWN']
    else:
        momentum_color = VN_COLORS['NEUTRAL']  # Grey - Neutral
        momentum_icon = VN_ICONS['NEUTRAL']
    
    signals.append({
        'type': 'momentum',
        'icon': momentum_icon,
        'color': momentum_color,
        'label': f'Momentum {alignment}',
        'data': {
            'ma10_slope': ma10_slope,
            'ma20_slope': ma20_slope,
            'ma50_slope': ma50_slope,
            'alignment': alignment
        },
        'tooltip': (
            f"<strong>📊 Momentum (%/ngày)</strong><br>"
            f"MA10: {ma10_slope:+.2f}<br>"
            f"MA20: {ma20_slope:+.2f}<br>"
            f"MA50: {ma50_slope:+.2f}<br>"
            f"Alignment: {alignment}<br>"
            f"<em style='color: #999; font-size: 0.85em;'>Tốc độ thay đổi - chỉ là thông tin</em>"
        )
    })
    
    # 6. PRICE POSITION - Factual data
    ma50 = latest['MA50']
    ma20 = latest['MA20']
    ma10 = latest['MA10']
    
    if ma50 > 0:
        dist_ma50 = (price - ma50) / ma50 * 100
        dist_ma20 = (price - ma20) / ma20 * 100 if ma20 > 0 else 0
        dist_ma10 = (price - ma10) / ma10 * 100 if ma10 > 0 else 0
        
        signals.append({
            'type': 'price_position',
            'icon': 'mdi-map-marker',
            'color': 'blue' if dist_ma50 > 0 else 'orange',
            'label': f'Giá vs MA50: {dist_ma50:+.1f}%',
            'data': {
                'vs_ma10': dist_ma10,
                'vs_ma20': dist_ma20,
                'vs_ma50': dist_ma50
            },
            'tooltip': (
                f"<strong>📍 Vị trí giá</strong><br>"
                f"vs MA10: {dist_ma10:+.1f}%<br>"
                f"vs MA20: {dist_ma20:+.1f}%<br>"
                f"vs MA50: {dist_ma50:+.1f}%<br>"
                f"<em style='color: #999; font-size: 0.85em;'>Khoảng cách - chỉ là thông tin</em>"
            )
        })
    
    return signals
