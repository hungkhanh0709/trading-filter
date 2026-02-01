"""
MA Column Formatter - Format MA data into table columns

Converts MA analysis results into UI-ready column format matching ma_result_new.json structure.
Each column has: type, icon, color, label, value, tooltip
"""


def format_ma_columns(expansion, momentum, price_position, convergence=None, golden_cross=None, death_cross=None, tight_convergence=None):
    """
    Format MA analysis into table columns
    
    Args:
        expansion: Result from detect_expansion()
        momentum: Result from analyze_momentum()
        price_position: Price position dict {vs_ma10, vs_ma20, vs_ma50}
        convergence: Optional - Result from detect_convergence()
        golden_cross: Optional - Result from detect_golden_cross()
        death_cross: Optional - Result from detect_death_cross()
        tight_convergence: Optional - Result from detect_tight_convergence()
        price_position: Price position dict {vs_ma10, vs_ma20, vs_ma50}
        convergence: Optional - Result from detect_convergence()
        golden_cross: Optional - Result from detect_golden_cross()
        death_cross: Optional - Result from detect_death_cross()
        
    Returns:
        list: Array of column objects for UI
    """
    columns = []
    
    # 1. EXPANSION Column - MA xoè/co
    if expansion:
        quality = expansion.get('expansion_quality', 'NA')
        ma10_dist = expansion.get('ma10_ma50_distance', 0)
        ma20_dist = expansion.get('ma20_ma50_distance', 0)
        ma50_slope = expansion.get('ma50_slope', 0)
        
        # Color based on quality
        color_map = {
            'PERFECT': 'success',
            'GOOD': 'light-green',
            'WEAK': 'warning',
            'CONTRACTING': 'error'
        }
        
        columns.append({
            'type': 'expansion',
            'icon': 'mdi-arrow-expand-all',
            'color': color_map.get(quality, 'grey'),
            'label': f'MA xoè ({quality})',
            'value': quality,
            'tooltip': (
                f"<strong>🚀 MA Expansion</strong><br>"
                f"Chất lượng: {quality}<br>"
                f"MA10 cách MA50: +{ma10_dist:.1f}%<br>"
                f"MA20 cách MA50: +{ma20_dist:.1f}%<br>"
                f"MA50 slope: +{ma50_slope:.2f}%/ngày<br>"
            )
        })
    
    # 2. MOMENTUM Column - Đà tăng/giảm
    if momentum:
        ma10_slope = momentum.get('ma10', {}).get('slope', 0)
        ma20_slope = momentum.get('ma20', {}).get('slope', 0)
        ma50_slope = momentum.get('ma50', {}).get('slope', 0)
        alignment = momentum.get('alignment', 'NEUTRAL')
        
        # Color based on alignment
        color_map = {
            'BULLISH_ALIGNED': 'success',
            'MOSTLY_BULLISH': 'light-green',
            'NEUTRAL': 'warning',
            'MOSTLY_BEARISH': 'orange',
            'BEARISH_ALIGNED': 'error'
        }
        
        columns.append({
            'type': 'momentum',
            'icon': 'mdi-speedometer',
            'color': color_map.get(alignment, 'grey'),
            'label': f'Momentum {alignment}',
            'value': alignment,
            'tooltip': (
                f"<strong>📊 Momentum (%/ngày)</strong><br>"
                f"MA10: {ma10_slope:+.2f}<br>"
                f"MA20: {ma20_slope:+.2f}<br>"
                f"MA50: {ma50_slope:+.2f}<br>"
                f"Alignment: {alignment}<br>"
            )
        })
    
    # 3. PRICE POSITION Column - Giá so với MA
    if price_position:
        vs_ma10 = price_position.get('vs_ma10', 0)
        vs_ma20 = price_position.get('vs_ma20', 0)
        vs_ma50 = price_position.get('vs_ma50', 0)
        
        # Label: hiển thị vs MA50 (quan trọng nhất)
        label = f"Giá vs MA50: {vs_ma50:+.1f}%"
        
        # Color: xanh nếu trên MA50, vàng nếu trên MA20, đỏ nếu dưới
        if vs_ma50 > 0:
            color = 'blue'
            icon = 'mdi-arrow-up'
        elif vs_ma20 > 0:
            color = 'cyan'
            icon = 'mdi-arrow-bottom-left'
        else:
            color = 'orange'
            icon = 'mdi-arrow-down'
        
        columns.append({
            'type': 'price_position',
            'icon': icon,
            'color': color,
            'label': label,
            'value': f"{vs_ma50:+.1f}%",
            'tooltip': (
                f"<strong>📍 Vị trí giá</strong><br>"
                f"vs MA10: {vs_ma10:+.1f}%<br>"
                f"vs MA20: {vs_ma20:+.1f}%<br>"
                f"vs MA50: {vs_ma50:+.1f}%<br>"
            )
        })
    
    # 4. CONVERGENCE Column - MA hội tụ (ALWAYS show if strength > 70)
    if convergence:
        strength = convergence.get('convergence_strength', 0)
        avg_dist = convergence.get('avg_distance', 0)
        message = convergence.get('message', '')
        
        # Show convergence if strength > 70 (important signal)
        if strength > 70:
            color = 'deep-orange' if strength >= 90 else 'orange'
            icon = 'mdi-flash-alert' if strength >= 90 else 'mdi-arrow-collapse'
            
            # Determine warning based on message content (phân biệt acceleration vs breakout)
            if 'tăng tốc' in message:
                # Perfect Order + Convergence = Trend Acceleration
                warning = '🚀 Xu hướng có thể TĂNG TỐC mạnh!' if strength >= 95 else 'Xu hướng có thể tăng tốc'
            else:
                # No Perfect Order + Convergence = Breakout
                warning = '🔥 Breakout IMMINENT!' if strength >= 95 else 'Breakout có thể xảy ra'
            
            columns.append({
                'type': 'convergence',
                'icon': icon,
                'color': color,
                'label': f'MA hội tụ ({strength:.0f}%)',
                'value': f"{strength:.0f}%",
                'tooltip': (
                    f"<strong>⚡ MA Convergence</strong><br>"
                    f"Độ mạnh: {strength:.0f}%<br>"
                    f"Khoảng cách TB: {avg_dist:.2f}%<br>"
                    f"<em style='color: #FF6F00; font-weight: 600;'>{warning}</em>"
                )
            })
    
    # 4.5. TIGHT CONVERGENCE Column - MA SIÊU XOẮN (Breakout sắp xảy ra!)
    if tight_convergence and tight_convergence.get('is_tight'):
        strength = tight_convergence.get('strength', 0)
        avg_dist = tight_convergence.get('avg_distance', 0)
        message = tight_convergence.get('message', '')
        
        # Always show with RED color (very urgent signal)
        color = 'red' if strength >= 90 else 'deep-orange'
        icon = 'mdi-alert-decagram'  # Star with exclamation
        
        columns.append({
            'type': 'tight_convergence',
            'icon': icon,
            'color': color,
            'label': f'MA SIÊU XOẮN ({strength:.0f}%)',
            'value': f"{strength:.0f}%",
            'tooltip': (
                f"<strong>⚡⚡ TIGHT CONVERGENCE - BREAKOUT SẮP XẢY RA!</strong><br>"
                f"Độ mạnh: {strength:.0f}%<br>"
                f"Khoảng cách TB: {avg_dist:.2f}%<br>"
                f"<em style='color: #D32F2F; font-weight: 700;'>Chỉ cần 1 phiên breakout là có thể tăng mạnh!</em>"
            )
        })
    
    # 5. GOLDEN CROSS Column (Optional)
    if golden_cross and golden_cross.get('best_cross'):
        cross = golden_cross['best_cross']
        
        columns.append({
            'type': 'golden_cross',
            'icon': 'mdi-star-circle',
            'color': 'amber',
            'label': cross.get('label', 'Golden Cross'),
            'value': f"{cross.get('score', 0)}/10",
            'tooltip': (
                f"<strong>⭐ {cross.get('label')}</strong><br>"
                f"Loại: {cross.get('type')}<br>"
                f"Độ uy tín: {cross.get('score')}/10<br>"
            )
        })
    
    # 6. DEATH CROSS Column (Optional)
    if death_cross and death_cross.get('has_death_cross'):
        dc = death_cross.get('strongest_cross', {})
        severity = dc.get('severity', 'MEDIUM')
        
        columns.append({
            'type': 'death_cross',
            'icon': 'mdi-alert-circle',
            'color': 'error',
            'label': f'Death Cross ({severity})',
            'value': severity,
            'tooltip': (
                f"<strong>⚠️ Death Cross</strong><br>"
                f"Loại: {dc.get('type')}<br>"
                f"Mức độ: {severity}<br>"
            )
        })
    
    return columns
