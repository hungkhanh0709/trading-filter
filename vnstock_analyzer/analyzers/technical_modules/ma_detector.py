"""
MA Detector Module - Pure detection functions

Phát hiện các patterns trong Moving Averages:
- Convergence (MA xoắn vào nhau)
- Expansion (MA xoè ra - Perfect Order)
- Golden Cross (MA cắt lên)
- Death Cross (MA cắt xuống)

All functions are PURE - no side effects, easy to test.
"""

from vnstock_analyzer.core.constants import VN_COLORS, VN_ICONS


def detect_convergence(df, perfect_order=False):
    """
    Phát hiện MA convergence (các đường MA xoắn vào nhau) - Dấu hiệu tích luỹ
    
    Sử dụng Bandwidth % = (MAX - MIN) / MIN * 100
    
    Args:
        df: DataFrame with MA10, MA20, MA50 columns
        perfect_order: bool - Có Perfect Order không? (MA10 > MA20 > MA50)
        
    Returns:
        dict: {
            'is_converging': bool,
            'convergence_pct': float (bandwidth %),
            'level': str (SUPER_TIGHT/TIGHT/LOOSE),
            'slope': str (UP/DOWN/NEUTRAL),
            'message': str
        }
    """
    if df is None or len(df) < 50:
        return {
            'is_converging': False,
            'convergence_pct': 0,
            'level': 'NA',
            'slope': 'NA',
            'message': 'Không đủ dữ liệu'
        }
    
    latest = df.iloc[-1]
    
    # Tính Bandwidth % = (MAX - MIN) / MIN * 100
    ma10 = latest['MA10']
    ma20 = latest['MA20']
    ma50 = latest['MA50']
    
    max_ma = max(ma10, ma20, ma50)
    min_ma = min(ma10, ma20, ma50)
    
    if min_ma == 0:
        return {
            'is_converging': False,
            'convergence_pct': 0,
            'level': 'NA',
            'slope': 'NA',
            'message': 'MA = 0'
        }
    
    # Bandwidth % công thức mới
    convergence_pct = (max_ma - min_ma) / min_ma * 100
    
    # Phân loại level
    if convergence_pct < 1.5:
        level = 'SUPER_TIGHT'
    elif convergence_pct < 3.0:
        level = 'TIGHT'
    else:
        level = 'LOOSE'
    
    is_converging = convergence_pct < 3.0  # Tight hoặc Super Tight
    
    # Tính slope (hướng) - dùng MA50 làm chuẩn
    if len(df) >= 10:
        ma50_10_days_ago = df.iloc[-10]['MA50']
        if ma50_10_days_ago > 0:
            slope_pct = (ma50 - ma50_10_days_ago) / ma50_10_days_ago * 100
            if slope_pct > 0.5:
                slope = 'UP'
            elif slope_pct < -0.5:
                slope = 'DOWN'
            else:
                slope = 'NEUTRAL'
        else:
            slope = 'NA'
    else:
        slope = 'NA'
    
    # MESSAGE: Phân biệt Perfect Order vs Non-Perfect Order
    slope_emoji = '📈' if slope == 'UP' else ('📉' if slope == 'DOWN' else '➡️')
    
    # Icon & Color based on level - VIETNAMESE STOCK MARKET COLORS
    icon_map = {
        'SUPER_TIGHT': VN_ICONS['EXCELLENT'],      # Ngôi sao - Xuất sắc
        'TIGHT': VN_ICONS['STRONG_UP'],           # Mũi tên lên đậm - Tốt
        'LOOSE': VN_ICONS['NEUTRAL']              # Trung tính
    }
    color_map = {
        'SUPER_TIGHT': VN_COLORS['CEILING'],      # Purple - Xuất sắc (sắp breakout)
        'TIGHT': VN_COLORS['UP'],                 # Green - Tốt
        'LOOSE': VN_COLORS['REFERENCE']           # Yellow - Trung tính
    }
    
    if perfect_order:
        # Perfect Order + Convergence = Xu hướng TĂNG TỐC (trend acceleration)
        if level == 'SUPER_TIGHT':
            message = f"🚀 {slope_emoji} Convergence {convergence_pct:.1f}% (SUPER TIGHT, {slope}) - Xu hướng có thể tăng tốc mạnh!"
        elif level == 'TIGHT':
            message = f"📈 {slope_emoji} Convergence {convergence_pct:.1f}% (TIGHT, {slope}) - Xu hướng có thể tăng tốc"
        else:
            message = f"➕ {slope_emoji} Convergence {convergence_pct:.1f}% (LOOSE, {slope})"
    else:
        # Không Perfect Order + Convergence = BREAKOUT (trend change)
        if level == 'SUPER_TIGHT':
            message = f"⚡ {slope_emoji} Convergence {convergence_pct:.1f}% (SUPER TIGHT, {slope}) - Breakout sắp xảy ra!"
        elif level == 'TIGHT':
            message = f"🔄 {slope_emoji} Convergence {convergence_pct:.1f}% (TIGHT, {slope}) - Theo dõi breakout"
        else:
            message = f"↔️ {slope_emoji} Convergence {convergence_pct:.1f}% (LOOSE, {slope})"
    
    return {
        'is_converging': is_converging,
        'convergence_pct': convergence_pct,
        'level': level,
        'slope': slope,
        'message': message,
        # UI metadata
        'icon': icon_map.get(level, 'mdi-circle-outline'),
        'color': color_map.get(level, 'grey'),
        'label': f'{convergence_pct:.1f}% {slope_emoji}',
        'tooltip': (
            f"<strong>⚡ MA Convergence</strong><br>"
            f"Convergence: {convergence_pct:.2f}%<br>"
            f"Level: {level}<br>"
            f"Slope: {slope} {slope_emoji}<br>"
            f"<em>{message}</em>"
        )
    }


def detect_expansion(df):
    """
    Phát hiện MA expansion (độ xoè của MA) - KHÔNG phụ thuộc vào Perfect Order
    
    Expansion đo khoảng cách giữa các MA và slope của MA50:
    - EXPANDING: MAs đang xoè ra (distances lớn, slope dương)
    - NEUTRAL: MAs ổn định
    - CONTRACTING: MAs đang co lại (distances nhỏ, slope âm hoặc gần 0)
    
    Args:
        df: DataFrame with MA10, MA20, MA50 columns
        
    Returns:
        dict: {
            'is_expanding': bool,
            'quality': str (STRONG/MODERATE/WEAK/NEUTRAL/CONTRACTING),
            'ma50_slope': float,
            'ma10_ma50_distance': float,
            'ma20_ma50_distance': float,
            'message': str,
            'icon': str,
            'color': str,
            'label': str,
            'tooltip': str
        }
    """
    if df is None or len(df) < 50:
        return {
            'is_expanding': False,
            'quality': 'NEUTRAL',
            'ma50_slope': 0,
            'ma10_ma50_distance': 0,
            'ma20_ma50_distance': 0,
            'message': 'Không đủ dữ liệu',
            'icon': 'mdi-alert-circle',
            'color': 'grey',
            'label': 'No Data',
            'tooltip': '<strong>📊 MA Expansion</strong><br>Không đủ dữ liệu'
        }
    
    latest = df.iloc[-1]
    ma50 = latest['MA50']
    
    if ma50 == 0:
        return {
            'is_expanding': False,
            'quality': 'NEUTRAL',
            'ma50_slope': 0,
            'ma10_ma50_distance': 0,
            'ma20_ma50_distance': 0,
            'message': 'MA50 = 0',
            'icon': 'mdi-alert-circle',
            'color': 'grey',
            'label': 'Error',
            'tooltip': '<strong>📊 MA Expansion</strong><br>MA50 = 0'
        }
    
    # Tính khoảng cách giữa các MA (% so với MA50)
    dist_10_50 = (latest['MA10'] - ma50) / ma50 * 100
    dist_20_50 = (latest['MA20'] - ma50) / ma50 * 100
    
    # Tính slope của MA50 (10 ngày gần nhất)
    if len(df) >= 10:
        ma50_10_days_ago = df.iloc[-10]['MA50']
        ma50_slope = ((ma50 - ma50_10_days_ago) / ma50_10_days_ago * 100) if ma50_10_days_ago > 0 else 0
    else:
        ma50_slope = 0
    
    # Đánh giá expansion quality (KHÔNG phụ thuộc Perfect Order)
    # Expansion = khoảng cách + slope
    
    # STRONG EXPANSION: Distances lớn + slope dương mạnh
    if dist_10_50 > 6 and dist_20_50 > 3 and ma50_slope > 2:
        quality = 'STRONG'
        message = f"🚀 MA xoè mạnh (MA10 {dist_10_50:+.1f}%, MA20 {dist_20_50:+.1f}%, Slope {ma50_slope:+.1f}%)"
        icon = VN_ICONS['EXPAND']
        color = VN_COLORS['CEILING']  # Purple - Xuất sắc
        label = 'Xoè MẠNH'
        is_expanding = True
    
    # MODERATE EXPANSION: Distances trung bình + slope dương
    elif dist_10_50 > 3 and dist_20_50 > 1.5 and ma50_slope > 0.5:
        quality = 'MODERATE'
        message = f"✅ MA đang xoè (MA10 {dist_10_50:+.1f}%, MA20 {dist_20_50:+.1f}%, Slope {ma50_slope:+.1f}%)"
        icon = VN_ICONS['STRONG_UP']
        color = VN_COLORS['UP']  # Green - Tốt
        label = 'Xoè VỪA'
        is_expanding = True
    
    # WEAK EXPANSION: Distances nhỏ hoặc slope yếu
    elif dist_10_50 > 1 and ma50_slope > 0:
        quality = 'WEAK'
        message = f"➕ MA xoè yếu (MA10 {dist_10_50:+.1f}%, MA20 {dist_20_50:+.1f}%, Slope {ma50_slope:+.1f}%)"
        icon = VN_ICONS['UP']
        color = VN_COLORS['REFERENCE']  # Yellow - Trung tính
        label = 'Xoè YẾU'
        is_expanding = False
    
    # CONTRACTING: MAs đang co lại (distances âm hoặc slope âm)
    elif dist_10_50 < -1 or ma50_slope < -0.5:
        quality = 'CONTRACTING'
        message = f"📉 MA đang co lại (MA10 {dist_10_50:+.1f}%, MA20 {dist_20_50:+.1f}%, Slope {ma50_slope:+.1f}%)"
        icon = VN_ICONS['CONTRACT']
        color = VN_COLORS['DOWN']  # Red - Xấu
        label = 'Đang CO'
        is_expanding = False
    
    # NEUTRAL: Không rõ xu hướng
    else:
        quality = 'NEUTRAL'
        message = f"➡️ MA trung tính (MA10 {dist_10_50:+.1f}%, MA20 {dist_20_50:+.1f}%, Slope {ma50_slope:+.1f}%)"
        icon = VN_ICONS['NEUTRAL']
        color = VN_COLORS['REFERENCE']  # Yellow - Trung tính
        label = 'Trung tính'
        is_expanding = False
    
    return {
        'is_expanding': is_expanding,
        'quality': quality,
        'ma50_slope': round(ma50_slope, 2),
        'ma10_ma50_distance': round(dist_10_50, 2),
        'ma20_ma50_distance': round(dist_20_50, 2),
        'message': message,
        # UI metadata
        'icon': icon,
        'color': color,
        'label': label,
        'tooltip': (
            f"<strong>📊 MA Expansion</strong><br>"
            f"Quality: {quality}<br>"
            f"MA10 vs MA50: {dist_10_50:+.1f}%<br>"
            f"MA20 vs MA50: {dist_20_50:+.1f}%<br>"
            f"MA50 slope: {ma50_slope:+.2f}%/ngày<br>"
            f"<em>{message}</em>"
        )
    }


def detect_golden_cross(df):
    """
    Phát hiện và đánh giá chất lượng Golden Cross (các mức độ uy tín khác nhau)
    
    Args:
        df: DataFrame with MA10, MA20, MA50 columns
        
    Returns:
        dict: {
            'crosses': list of dicts,
            'best_cross': dict or None,
            'message': str
        }
    """
    if df is None or len(df) < 50:
        return {
            'crosses': [],
            'best_cross': None,
            'message': 'Không đủ dữ liệu'
        }
    
    crosses = []
    latest = df.iloc[-1]
    
    if len(df) >= 2:
        prev = df.iloc[-2]
        
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
        tooltip = "<strong>⭐ Golden Cross</strong><br>Không có Golden Cross trong 2 ngày gần đây"
        label = "No GC"
    else:
        message = f"{best_cross['icon']} {best_cross['label']} vừa xảy ra!"
        tooltip = (
            f"<strong>⭐ {best_cross['label']}</strong><br>"
            f"Loại: {best_cross['type']}<br>"
        )
        label = f"{best_cross['icon']} {best_cross['label']}"
    
    return {
        'crosses': crosses,
        'best_cross': best_cross,
        'has_cross': len(crosses) > 0,
        'message': message,
        # UI metadata
        'icon': 'mdi-star-circle',
        'color': 'amber' if best_cross else 'grey',
        'label': label,
        'tooltip': tooltip
    }


def detect_death_cross(df):
    """
    Phát hiện Death Cross - FACTUAL DATA ONLY, NO ADVICE
    
    Death Cross = MA cắt xuống nhau (bearish signal)
    - MA10 cắt xuống MA20
    - MA20 cắt xuống MA50 (uy tín hơn)
    
    Args:
        df: DataFrame with close, MA10, MA20, MA50 columns
        
    Returns:
        dict: {
            'has_death_cross': bool,
            'crosses': list of dicts,
            'strongest_cross': dict or None,
            'price_below_ma': dict
        }
    """
    if df is None or len(df) < 50:
        return {
            'has_death_cross': False,
            'crosses': [],
            'strongest_cross': None,
            'price_below_ma': {}
        }
    
    latest = df.iloc[-1]
    price = latest['close']
    crosses = []
    
    # Kiểm tra Perfect Order trước
    was_in_perfect_order = (latest['MA10'] > latest['MA20'] > latest['MA50'])
    
    if len(df) >= 2:
        prev = df.iloc[-2]
        
        # CRITICAL: MA20 cắt xuống MA50 (Death Cross uy tín)
        if prev['MA20'] >= prev['MA50'] and latest['MA20'] < latest['MA50']:
            crosses.append({
                'type': 'MA20_MA50',
                'label': 'Death Cross MA20/MA50',
                'severity': 'CRITICAL',
                'credibility_score': 10
            })
        
        # HIGH: MA10 cắt xuống MA20 (Death Cross ngắn hạn)
        elif prev['MA10'] >= prev['MA20'] and latest['MA10'] < latest['MA20']:
            crosses.append({
                'type': 'MA10_MA20',
                'label': 'Death Cross MA10/MA20',
                'severity': 'HIGH',
                'credibility_score': 6
            })
    
    # Check price breaking below MA
    price_below_ma = {
        'below_ma10': price < latest['MA10'],
        'below_ma20': price < latest['MA20'] and was_in_perfect_order,
        'below_ma50': price < latest['MA50']
    }
    
    # Find strongest cross
    strongest_cross = None
    if crosses:
        strongest_cross = max(crosses, key=lambda x: x['credibility_score'])
    
    has_death_cross = len(crosses) > 0
    
    # UI metadata
    if has_death_cross:
        dc = strongest_cross
        severity = dc.get('severity', 'MEDIUM')
        tooltip = (
            f"<strong>⚠️ Death Cross</strong><br>"
            f"Loại: {dc.get('type')}<br>"
            f"Mức độ: {severity}<br>"
        )
        label = f"Death Cross ({severity})"
        # Death Cross severity colors
        if severity == 'CRITICAL':
            color = VN_COLORS['FLOOR']  # Cyan - Rất xấu
        else:
            color = VN_COLORS['DOWN']   # Red - Xấu
    else:
        tooltip = "<strong>⚠️ Death Cross</strong><br>Không có Death Cross gần đây"
        label = "No DC"
        color = VN_COLORS['NEUTRAL']  # Grey
    
    return {
        'has_death_cross': has_death_cross,
        'crosses': crosses,
        'strongest_cross': strongest_cross,
        'price_below_ma': price_below_ma,
        # UI metadata
        'icon': 'mdi-alert-circle',
        'color': color,
        'label': label,
        'tooltip': tooltip
    }

