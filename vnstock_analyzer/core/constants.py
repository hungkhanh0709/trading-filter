"""
Constants and thresholds for stock scoring system
"""

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
TIERS = {
    'S': (85, 100),
    'A': (70, 85), 
    'B': (55, 70), 
    'C': (40, 55),  
    'D': (0, 40)
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


# Helper functions for status-based evaluation
def calculate_component_score(criteria):
    """
    Calculate component score based on status distribution
    
    Args:
        criteria: Dict of {criterion_name: {'status': 'GOOD', 'reason': '...'}}
        
    Returns:
        float: Score 0-1 representing quality
    """
    if not criteria:
        return 0.0
    
    total_weight = 0.0
    total_criteria = 0
    
    for criterion_data in criteria.values():
        status = criterion_data.get('status') if isinstance(criterion_data, dict) else criterion_data
        weight = STATUS_LEVELS.get(status, {}).get('weight')
        if weight is not None:  # Exclude NA
            total_weight += weight
            total_criteria += 1
    
    return total_weight / total_criteria if total_criteria > 0 else 0.0


def calculate_overall_tier(component_scores, weights=None):
    """
    Calculate overall tier based on weighted component scores
    
    Args:
        component_scores: Dict of {component: score} where score is 0-1
        weights: Dict of {component: weight} (optional, uses COMPONENT_WEIGHTS if not provided)
        
    Returns:
        tuple: (tier, tier_label)
    """
    if weights is None:
        weights = COMPONENT_WEIGHTS
    
    weighted_score = sum(
        score * weights.get(component, 0)
        for component, score in component_scores.items()
    )
    
    # Convert to percentage
    percentage = weighted_score * 100
    
    # Determine tier
    for tier, (min_score, max_score) in TIERS.items():
        if min_score <= percentage <= max_score:
            return tier, TIER_LABELS[tier]
    
    # Fallback
    return 'D', TIER_LABELS['D']


def count_criteria_by_status(criteria_dict):
    """
    Count criteria by status level
    
    Args:
        criteria_dict: Dict of {criterion_name: {'status': '...', ...}}
        
    Returns:
        dict: Status counts
    """
    counts = {
        'total': 0,
        'excellent': 0,
        'good': 0,
        'acceptable': 0,
        'warning': 0,
        'poor': 0,
        'na': 0
    }
    
    for criterion in criteria_dict.values():
        status = criterion.get('status', 'NA')
        counts['total'] += 1
        
        if status == 'EXCELLENT':
            counts['excellent'] += 1
        elif status == 'GOOD':
            counts['good'] += 1
        elif status == 'ACCEPTABLE':
            counts['acceptable'] += 1
        elif status == 'WARNING':
            counts['warning'] += 1
        elif status == 'POOR':
            counts['poor'] += 1
        elif status == 'NA':
            counts['na'] += 1
    
    return counts
