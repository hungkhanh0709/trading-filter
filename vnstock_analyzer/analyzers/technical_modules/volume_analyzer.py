"""
Volume Analyzer - Analyze volume trends

Phân tích xu hướng volume để phối hợp với convergence analysis:
- Volume đang tăng hay giảm
- Volume trung bình vs hiện tại
- Convergence + Volume giảm = tích luỹ tốt
"""

from vnstock_analyzer.core.constants import VN_COLORS, VN_ICONS


def analyze_volume_trend(df, lookback_days=20):
    """
    Phân tích xu hướng volume với UI metadata
    
    Args:
        df: DataFrame with 'volume' column
        lookback_days: Số ngày để tính volume trung bình
        
    Returns:
        dict: {
            'current_volume': float,
            'avg_volume': float,
            'volume_ratio': float (current/avg),
            'trend': str (INCREASING/DECREASING/STABLE),
            'is_decreasing': bool,
            'message': str,
            'icon': str,
            'color': str,
            'label': str,
            'tooltip': str
        }
    """
    if df is None or len(df) < lookback_days or 'volume' not in df.columns:
        return {
            'current_volume': 0,
            'avg_volume': 0,
            'volume_ratio': 0,
            'trend': 'NA',
            'is_decreasing': False,
            'message': 'Không đủ dữ liệu volume',
            'icon': 'mdi-volume-off',
            'color': 'grey',
            'label': 'No Data',
            'tooltip': '<strong>📊 Volume</strong><br>Không đủ dữ liệu'
        }
    
    # Get recent volume data
    recent_df = df.tail(lookback_days)
    current_volume = df.iloc[-1]['volume']
    avg_volume = recent_df['volume'].mean()
    
    if avg_volume == 0:
        return {
            'current_volume': current_volume,
            'avg_volume': 0,
            'volume_ratio': 0,
            'trend': 'NA',
            'is_decreasing': False,
            'message': 'Volume = 0',
            'icon': 'mdi-volume-off',
            'color': 'grey',
            'label': 'No Vol',
            'tooltip': '<strong>📊 Volume</strong><br>Volume = 0'
        }
    
    # Calculate ratio
    volume_ratio = current_volume / avg_volume
    
    # Determine trend and UI metadata
    if volume_ratio < 0.7:
        trend = 'DECREASING'
        is_decreasing = True
        message = f"📉 Volume giảm ({volume_ratio:.1%} vs TB {lookback_days} ngày)"
        icon = VN_ICONS['STRONG_DOWN']
        color = VN_COLORS['FLOOR']  # Cyan - Tốt cho tích luỹ
        label = f"{volume_ratio:.1%} 📉"
        tooltip = f"<strong>📊 Volume Trend</strong><br>Xu hướng: DECREASING 📉<br>Volume hiện tại: {current_volume:,.0f}<br>Volume TB 20 ngày: {avg_volume:,.0f}<br>Tỉ lệ: {volume_ratio:.1%}<br><em>Volume giảm - Dấu hiệu tích luỹ</em>"
    elif volume_ratio > 1.3:
        trend = 'INCREASING'
        is_decreasing = False
        message = f"📈 Volume tăng ({volume_ratio:.1%} vs TB {lookback_days} ngày)"
        icon = VN_ICONS['STRONG_UP']
        color = VN_COLORS['CEILING']  # Purple - Xuất sắc (breakout)
        label = f"{volume_ratio:.1%} 📈"
        tooltip = f"<strong>📊 Volume Trend</strong><br>Xu hướng: INCREASING 📈<br>Volume hiện tại: {current_volume:,.0f}<br>Volume TB 20 ngày: {avg_volume:,.0f}<br>Tỉ lệ: {volume_ratio:.1%}<br><em>Volume tăng - Quan sát breakout</em>"
    else:
        trend = 'STABLE'
        is_decreasing = False
        message = f"➡️ Volume ổn định ({volume_ratio:.1%} vs TB {lookback_days} ngày)"
        icon = VN_ICONS['NEUTRAL']
        color = VN_COLORS['REFERENCE']  # Yellow - Trung tính
        label = f"{volume_ratio:.1%} ➡️"
        tooltip = f"<strong>📊 Volume Trend</strong><br>Xu hướng: STABLE ➡️<br>Volume hiện tại: {current_volume:,.0f}<br>Volume TB 20 ngày: {avg_volume:,.0f}<br>Tỉ lệ: {volume_ratio:.1%}<br><em>Volume ổn định</em>"
    
    return {
        'current_volume': current_volume,
        'avg_volume': avg_volume,
        'volume_ratio': round(volume_ratio, 2),
        'trend': trend,
        'is_decreasing': is_decreasing,
        'message': message,
        'icon': icon,
        'color': color,
        'label': label,
        'tooltip': tooltip
    }


def check_convergence_volume_signal(convergence, volume_trend):
    """
    Kiểm tra tín hiệu tích luỹ: Convergence + Volume giảm
    
    Đây là tín hiệu tốt: MA đang xoắn lại, volume giảm (không có áp lực bán),
    chuẩn bị cho breakout.
    
    Args:
        convergence: Result from detect_convergence()
        volume_trend: Result from analyze_volume_trend()
        
    Returns:
        dict: {
            'has_signal': bool,
            'quality': str (STRONG/GOOD/WEAK),
            'message': str
        }
    """
    if not convergence or not volume_trend:
        return {
            'has_signal': False,
            'quality': 'NA',
            'message': ''
        }
    
    # Check conditions
    is_converging = convergence.get('is_converging', False)
    convergence_level = convergence.get('level', 'LOOSE')
    volume_decreasing = volume_trend.get('is_decreasing', False)
    volume_ratio = volume_trend.get('volume_ratio', 1.0)
    
    # No signal if not converging
    if not is_converging:
        return {
            'has_signal': False,
            'quality': 'NA',
            'message': ''
        }
    
    # No signal if volume increasing
    if not volume_decreasing:
        return {
            'has_signal': False,
            'quality': 'NA',
            'message': ''
        }
    
    # Determine quality
    if convergence_level == 'SUPER_TIGHT' and volume_ratio < 0.5:
        quality = 'STRONG'
        message = "🔥 Tích luỹ MẠNH: Convergence SUPER TIGHT + Volume giảm sâu!"
    elif convergence_level == 'SUPER_TIGHT' or (convergence_level == 'TIGHT' and volume_ratio < 0.5):
        quality = 'GOOD'
        message = "✅ Tích luỹ TỐT: Convergence chặt + Volume giảm"
    else:
        quality = 'WEAK'
        message = "➕ Tích luỹ YẾU: Convergence + Volume giảm nhẹ"
    
    return {
        'has_signal': True,
        'quality': quality,
        'message': message
    }
