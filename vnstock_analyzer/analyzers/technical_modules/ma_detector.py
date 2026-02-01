"""
MA Detector Module - Pure detection functions

Phát hiện các patterns trong Moving Averages:
- Convergence (MA xoắn vào nhau)
- Expansion (MA xoè ra - Perfect Order)
- Golden Cross (MA cắt lên)
- Sell Warning (Death Cross)
- Tight Convergence (MA siêu xoắn - breakout sắp xảy ra)

All functions are PURE - no side effects, easy to test.
"""


def detect_convergence(df):
    """
    Phát hiện MA convergence (các đường MA xoắn vào nhau) - Dấu hiệu tích luỹ
    
    Args:
        df: DataFrame with MA10, MA20, MA50 columns
        
    Returns:
        dict: {
            'is_converging': bool,
            'convergence_strength': float (0-100),
            'avg_distance': float,
            'message': str
        }
    """
    if df is None or len(df) < 50:
        return {
            'is_converging': False,
            'convergence_strength': 0,
            'avg_distance': 0,
            'message': 'Không đủ dữ liệu'
        }
    
    latest = df.iloc[-1]
    
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
    
    is_converging = avg_distance < 4  # Các MA xoắn vào nhau khi cách nhau < 4%
    
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


def detect_expansion(df):
    """
    Phát hiện MA expansion (các đường MA xoè ra) - Xác nhận uptrend mạnh
    
    Args:
        df: DataFrame with MA10, MA20, MA50 columns
        
    Returns:
        dict: {
            'is_expanding': bool,
            'expansion_quality': str (PERFECT/GOOD/WEAK),
            'ma50_slope': float,
            'distances': dict,
            'message': str
        }
    """
    if df is None or len(df) < 50:
        return {
            'is_expanding': False,
            'expansion_quality': 'WEAK',
            'ma50_slope': 0,
            'distances': {},
            'message': 'Không đủ dữ liệu'
        }
    
    latest = df.iloc[-1]
    
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
    if len(df) >= 10:
        ma50_10_days_ago = df.iloc[-10]['MA50']
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
    else:
        message = f"{best_cross['icon']} {best_cross['label']} vừa xảy ra!"
    
    return {
        'crosses': crosses,
        'best_cross': best_cross,
        'message': message
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
    
    return {
        'has_death_cross': has_death_cross,
        'crosses': crosses,
        'strongest_cross': strongest_cross,
        'price_below_ma': price_below_ma
    }


def detect_tight_convergence(df, convergence, death_cross):
    """
    Phát hiện MA SIÊU XOẮN - Dấu hiệu breakout sắp xảy ra
    
    Đây là insight quan trọng: khi MA xoắn rất sát nhau, chỉ cần 1 phiên
    breakout là có thể chuyển sang Perfect Order hoặc tăng mạnh.
    
    Điều kiện:
    - Convergence strength > 75% (MA siêu xoắn)
    - Giá > MA50 (đang trong xu hướng tăng)
    - Perfect Order = True HOẶC gần đạt (MA10 > MA20 gần bằng MA50)
    - KHÔNG có death cross CRITICAL
    
    Args:
        df: DataFrame with close, MA10, MA20, MA50
        convergence: Result from detect_convergence()
        death_cross: Result from detect_death_cross()
        
    Returns:
        dict: {
            'is_tight': bool,
            'strength': float,
            'avg_distance': float,
            'message': str
        }
    """
    if df is None or len(df) < 50:
        return {
            'is_tight': False,
            'strength': 0,
            'message': ''
        }
    
    latest = df.iloc[-1]
    price = latest['close']
    ma10 = latest['MA10']
    ma20 = latest['MA20']
    ma50 = latest['MA50']
    
    # Điều kiện 1: Convergence strength > 75% (siêu xoắn)
    strength = convergence.get('convergence_strength', 0)
    if strength < 75:
        return {'is_tight': False, 'strength': strength, 'message': ''}
    
    # Điều kiện 2: Giá > MA50 (trong uptrend)
    if price <= ma50:
        return {'is_tight': False, 'strength': strength, 'message': ''}
    
    # Điều kiện 3: Perfect Order HOẶC gần đạt HOẶC convergence CỰC mạnh
    perfect_order = (ma10 > ma20 > ma50)
    near_perfect_order = (ma10 > ma20 and ma20 >= ma50 * 0.998)
    ultra_tight = (strength >= 95)
    
    if not (perfect_order or near_perfect_order or ultra_tight):
        return {'is_tight': False, 'strength': strength, 'message': ''}
    
    # Điều kiện 4: KHÔNG có death cross CRITICAL
    has_critical_death_cross = (death_cross.get('has_death_cross') and 
                                death_cross.get('strongest_cross', {}).get('severity') == 'CRITICAL')
    if has_critical_death_cross:
        return {'is_tight': False, 'strength': strength, 'message': ''}
    
    # Passed all conditions!
    avg_dist = convergence.get('avg_distance', 0)
    
    # Message - FACTUAL only
    if strength >= 90:
        message = f"⚡⚡ MA siêu siêu xoắn: {strength:.0f}%, khoảng cách {avg_dist:.2f}%"
    else:
        message = f"⚡ MA siêu xoắn: {strength:.0f}%, khoảng cách {avg_dist:.1f}%"
    
    return {
        'is_tight': True,
        'strength': strength,
        'avg_distance': avg_dist,
        'message': message
    }
