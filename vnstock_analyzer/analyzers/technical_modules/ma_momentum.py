"""
MA Momentum Module - Phân tích tốc độ thay đổi của MA

Momentum = slope của MA trong lookback period (% change per day)
- MA10: 5 days lookback (short-term, react nhanh)
- MA20: 10 days lookback (mid-term)
- MA50: 20 days lookback (long-term, xu hướng chính)

Pure functions - no side effects.
"""


def analyze_momentum(df):
    """
    Phân tích momentum (tốc độ thay đổi) của từng MA để dự đoán xu hướng tương lai
    
    Args:
        df: DataFrame with MA10, MA20, MA50 columns
        
    Returns:
        dict: {
            'ma10': {'slope': float, 'trend': str, 'strength': str},
            'ma20': {'slope': float, 'trend': str, 'strength': str},
            'ma50': {'slope': float, 'trend': str, 'strength': str},
            'alignment': str (BULLISH_ALIGNED/MOSTLY_BULLISH/MIXED/MOSTLY_BEARISH/BEARISH_ALIGNED),
            'summary': str
        }
    """
    if df is None or len(df) < 50:
        return {
            'ma10': {'slope': 0, 'trend': 'NEUTRAL', 'strength': 'WEAK'},
            'ma20': {'slope': 0, 'trend': 'NEUTRAL', 'strength': 'WEAK'},
            'ma50': {'slope': 0, 'trend': 'NEUTRAL', 'strength': 'WEAK'},
            'alignment': 'NEUTRAL',
            'summary': 'Không đủ dữ liệu'
        }
    
    latest = df.iloc[-1]
    
    # Tính slope cho từng MA
    ma10_slope = _calc_ma_slope(df, latest, 'MA10', 5)
    ma20_slope = _calc_ma_slope(df, latest, 'MA20', 10)
    ma50_slope = _calc_ma_slope(df, latest, 'MA50', 20)
    
    ma10_analysis = _interpret_slope(ma10_slope)
    ma20_analysis = _interpret_slope(ma20_slope)
    ma50_analysis = _interpret_slope(ma50_slope)
    
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
    
    # UI metadata
    color_map = {
        'BULLISH_ALIGNED': 'success',
        'MOSTLY_BULLISH': 'light-green',
        'NEUTRAL': 'warning',
        'MOSTLY_BEARISH': 'orange',
        'BEARISH_ALIGNED': 'error',
        'MIXED': 'grey'
    }
    
    tooltip = (
        f"<strong>📊 Momentum (%/ngày)</strong><br>"
        f"MA10: {ma10_analysis['slope']:+.2f}<br>"
        f"MA20: {ma20_analysis['slope']:+.2f}<br>"
        f"MA50: {ma50_analysis['slope']:+.2f}<br>"
        f"Alignment: {alignment}<br>"
    )
    
    return {
        'ma10': ma10_analysis,
        'ma20': ma20_analysis,
        'ma50': ma50_analysis,
        'alignment': alignment,
        'summary': summary,
        # UI metadata
        'icon': 'mdi-speedometer',
        'color': color_map.get(alignment, 'grey'),
        'label': f'Momentum {alignment}',
        'tooltip': tooltip
    }


def _calc_ma_slope(df, latest, ma_name, lookback_days):
    """
    Tính slope của MA trong N ngày gần nhất
    
    Args:
        df: DataFrame
        latest: Latest row from df
        ma_name: Name of MA column (MA10/MA20/MA50)
        lookback_days: Number of days to look back
        
    Returns:
        float: % change per day
    """
    if len(df) < lookback_days:
        return 0
    
    ma_current = latest[ma_name]
    ma_past = df.iloc[-lookback_days][ma_name]
    
    if ma_past == 0:
        return 0
    
    # % change per day
    total_change_pct = (ma_current - ma_past) / ma_past * 100
    slope = total_change_pct / lookback_days
    
    return slope


def _interpret_slope(slope):
    """
    Diễn giải slope thành trend + strength
    
    Args:
        slope: MA slope (% change per day)
        
    Returns:
        dict: {
            'slope': float,
            'slope_pct_per_day': float,
            'trend': str,
            'strength': str
        }
    """
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
