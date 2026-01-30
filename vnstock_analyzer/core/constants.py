"""
Constants and thresholds for stock scoring system
"""

# Scoring weights (total = 100)
WEIGHTS = {
    'technical': 25,
    'fundamental': 25,
    'sentiment': 20,
    'liquidity': 15,
    'industry': 15
}

# Tier thresholds and labels
TIERS = {
    'S': (85, 100),
    'A': (70, 84),
    'B': (55, 69),
    'C': (40, 54),
    'D': (0, 39)
}

TIER_LABELS = {
    'S': '🏆 CHIẾN THẦN',
    'A': '⭐ RẤT TỐT',
    'B': '✅ TỐT',
    'C': '⚠️  TRUNG BÌNH',
    'D': '❌ YẾU'
}

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

EPS_RANGES = {
    'high': 3000,
    'good': 1000
}

DEBT_EQUITY_RANGES = {
    'very_low': 0.5,
    'reasonable': 1,
    'high': 2
}

CURRENT_RATIO_RANGES = {
    'good': 1.5,
    'acceptable': 1
}

# Liquidity thresholds
VOLUME_RANGES = {
    'very_high': 1_000_000,
    'high': 500_000,
    'acceptable': 200_000
}

VOLATILITY_RANGES = {
    'reasonable': (1, 3),
    'medium': (3, 5)
}

# Technical analysis sub-weights
TECHNICAL_WEIGHTS = {
    'ma_trend': 10,
    'rsi': 5,
    'volume': 10
}

# Fundamental analysis sub-weights
FUNDAMENTAL_WEIGHTS = {
    'valuation': 10,
    'profitability': 10,
    'financial_health': 5
}

# Sentiment analysis sub-weights
SENTIMENT_WEIGHTS = {
    'insider': 10,
    'foreign': 5,
    'news': 5
}

# Liquidity analysis sub-weights
LIQUIDITY_WEIGHTS = {
    'volume': 10,
    'volatility': 5
}

# Industry analysis sub-weights
INDUSTRY_WEIGHTS = {
    'relative_strength': 10,
    'market_position': 5
}
