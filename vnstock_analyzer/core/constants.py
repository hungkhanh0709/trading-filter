"""
Constants and thresholds for stock scoring system
"""

# ============================================================================
# VIETNAMESE STOCK MARKET COLOR SCHEME
# ============================================================================
# Theo quy ước thị trường chứng khoán Việt Nam:
# - Tím (Purple): Tăng kịch trần / Rất tốt
# - Xanh lá (Green): Tăng / Tốt  
# - Vàng (Yellow): Tham chiếu / Trung tính
# - Đỏ (Red): Giảm / Xấu
# - Xanh lơ (Cyan): Giảm kịch sàn / Rất xấu
# ============================================================================

VN_COLORS = {
    'CEILING': 'purple',        # Tím - Tăng kịch trần / Excellent
    'UP': 'success',            # Xanh lá - Tăng / Good (Vuetify: success = green)
    'REFERENCE': 'warning',     # Vàng - Tham chiếu / Neutral (Vuetify: warning = yellow/amber)
    'DOWN': 'error',            # Đỏ - Giảm / Bad (Vuetify: error = red)
    'FLOOR': 'cyan',            # Xanh lơ - Giảm kịch sàn / Very Bad
    'NEUTRAL': 'grey'           # Xám - Không xác định
}

# Icon set theo Material Design Icons (mdi)
VN_ICONS = {
    'EXCELLENT': 'mdi-star-circle',           # Xuất sắc - Ngôi sao
    'VERY_STRONG_UP': 'mdi-arrow-up-bold-circle',  # Tăng rất mạnh
    'STRONG_UP': 'mdi-arrow-up-bold',         # Tăng mạnh
    'UP': 'mdi-arrow-up',                     # Tăng
    'NEUTRAL': 'mdi-minus-circle',            # Trung tính
    'DOWN': 'mdi-arrow-down',                 # Giảm
    'STRONG_DOWN': 'mdi-arrow-down-bold',     # Giảm mạnh
    'VERY_STRONG_DOWN': 'mdi-arrow-down-bold-circle',  # Giảm rất mạnh
    'EXPAND': 'mdi-arrow-expand-all',         # Xoè
    'CONTRACT': 'mdi-arrow-collapse-all',     # Co lại
    'ALERT': 'mdi-alert-circle',              # Cảnh báo
    'STAR': 'mdi-star-circle',                # Ngôi sao (Golden Cross)
    'TREND_UP': 'mdi-trending-up',            # Xu hướng tăng
    'TREND_DOWN': 'mdi-trending-down'         # Xu hướng giảm
}

# Status-based evaluation system (using English labels as requested)
STATUS_LEVELS = {
    'EXCELLENT': {'icon': '🔥', 'label': 'EXCELLENT', 'weight': 1.0},
    'GOOD': {'icon': '✅', 'label': 'GOOD', 'weight': 1.0},
    'ACCEPTABLE': {'icon': '➕', 'label': 'ACCEPTABLE', 'weight': 0.7},
    'WARNING': {'icon': '⚠️', 'label': 'WARNING', 'weight': 0.3},
    'POOR': {'icon': '❌', 'label': 'POOR', 'weight': 0.0},
    'NA': {'icon': '⚪', 'label': 'NA', 'weight': None}
}

# Component weights for tier calculation (total = 1.0)
COMPONENT_WEIGHTS = {
    'technical': 0.40,      # 40% - most important
    'fundamental': 0.35,    # 35%
    'liquidity': 0.25       # 25%
    # Sentiment and Industry are disabled
}

# Legacy scoring weights (kept for backward compatibility)
WEIGHTS = {
    'technical': 25,
    'fundamental': 25,
    'sentiment': 20,
    'liquidity': 15,
    'industry': 15
}

# Tier thresholds and labels
TIER_RECOMMENDATIONS = {
    'S': 'MUA MẠNH - Tiềm năng bứt phá rất cao',
    'A': 'MUA - Cổ phiếu chất lượng cao',
    'B': 'XEM XÉT MUA - Có tiềm năng',
    'C': 'THẬN TRỌNG - Cần theo dõi thêm',
    'D': 'TRÁNH - Rủi ro cao'
}

# Market cap tiers (billion VND)
MARKET_CAP_TIERS = {
    'large': 100_000,        # > 100 trillion
    'mid_large': 20_000,     # 20-100 trillion
    'mid': 5_000,            # 5-20 trillion
    'small_mid': 1_000       # 1-5 trillion
    # < 1 trillion = small cap
}

# Technical indicators thresholds
RSI_ZONES = {
    'balanced': (40, 60),           # Best zone
    'oversold_recovery': (30, 40),  # Opportunity
    'positive': (60, 70),           # Good
    'overbought': (70, 100),        # Warning
    'oversold': (0, 30)             # Potential rebound
}

# Fundamental ratios ranges
PE_RANGES = {
    'excellent': (5, 8),
    'good': (8, 15),
    'acceptable': (15, 25)
}

PB_RANGES = {
    'excellent': (0, 0.8),
    'good': (0.8, 2),
    'high': (2, 999)
}

ROE_RANGES = {
    'excellent': 15,
    'good': 10,
    'acceptable': 5
}

ROA_RANGES = {
    'excellent': 8,
    'good': 5
}

