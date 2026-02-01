"""
Stock Scorer - Main orchestrator for stock analysis
"""

import sys
from datetime import datetime

from .core import DataFetcher, TIERS, TIER_LABELS, TIER_RECOMMENDATIONS
from .analyzers import (
    TechnicalAnalyzer,
    FundamentalAnalyzer,
    LiquidityAnalyzer,
)
from .utils import get_logger, LogLevel


class StockScorer:
    """Main scoring engine - orchestrates all analyzers"""
    
    def __init__(self, symbol, source='KBS'):
        """
        Initialize stock scorer
        
        Args:
            symbol: Stock symbol (e.g., 'HDB', 'FPT')
            source: Data source (default: 'KBS')
        """
        self.symbol = symbol
        self.source = source
        self.fetcher = DataFetcher(symbol, source)
        self.logger = get_logger(symbol, LogLevel.INFO)
        
    def _calculate_tier(self, total_score):
        """
        Determine tier based on total score (DEPRECATED - kept for compatibility)
        
        Args:
            total_score: Total score (0-100)
            
        Returns:
            tuple: (tier, tier_label, recommendation)
        """
        for tier, (min_score, max_score) in TIERS.items():
            if min_score <= total_score <= max_score:
                return tier, TIER_LABELS[tier], TIER_RECOMMENDATIONS[tier]
        
        # Fallback
        return 'D', TIER_LABELS['D'], TIER_RECOMMENDATIONS['D']
    
    def _generate_recommendation(self, tier, tech_signal):
        """
        Generate recommendation based on tier and technical signal
        
        Args:
            tier: Overall tier (S, A, B, C, D)
            tech_signal: Technical signal (STRONG_BUY, BUY, HOLD, CAUTION, SELL, STRONG_SELL)
            
        Returns:
            str: Recommendation text
        """
        # Adjust based on technical signal
        if tier in ['S', 'A']:
            if tech_signal in ['STRONG_BUY', 'BUY']:
                return '🔥 MUA MẠNH - Cơ hội tốt'
            elif tech_signal == 'HOLD':
                return '✅ MUA - Nắm giữ dài hạn'
            elif tech_signal == 'CAUTION':
                return '⚠️  THẬN TRỌNG - Chờ tín hiệu tốt hơn'
            else:  # SELL, STRONG_SELL
                return '⚠️  CANH GIẢM - Đợi điều chỉnh'
        
        elif tier == 'B':
            if tech_signal in ['STRONG_BUY', 'BUY']:
                return '✅ MUA - Tiềm năng tốt'
            elif tech_signal == 'HOLD':
                return '➕ THEO DÕI - Cân nhắc mua'
            else:
                return '⚠️  THẬN TRỌNG'
        
        elif tier == 'C':
            if tech_signal in ['STRONG_BUY', 'BUY']:
                return '➕ THEO DÕI - Tín hiệu kỹ thuật tốt nhưng cơ bản yếu'
            else:
                return '⚠️  TRÁNH - Rủi ro cao'
        
        else:  # tier D
            return '❌ TRÁNH - Không nên đầu tư'
        
    def analyze(self):
        """
        Phân tích toàn diện
        
        Returns:
            dict: Complete analysis result
        """
        self.logger.section(f"PHÂN TÍCH CỔ PHIẾU: {self.symbol}")
        
        # Fetch data
        self.logger.info("Fetching market data...")
        if not self.fetcher.fetch_all_data():
            self.logger.error("Failed to fetch data")
            return None
        
        # Get cached data
        df_history = self.fetcher.get_data('history')
        df_ratio = self.fetcher.get_data('ratio')
        
        # Run analyzers
        self.logger.info("Running analysis modules...")
        
        technical = TechnicalAnalyzer(df_history)
        fundamental = FundamentalAnalyzer(df_ratio)
        liquidity = LiquidityAnalyzer(df_history)
        
        # Get status-based analysis (NEW)
        tech_result = technical.get_analysis()
        fund_result = fundamental.get_analysis()
        liq_result = liquidity.get_analysis()
        
        # Calculate overall tier using weighted component scores
        from .core.constants import calculate_overall_tier, COMPONENT_WEIGHTS
        
        component_scores = {
            'technical': tech_result.get('component_score', 0),
            'fundamental': fund_result.get('component_score', 0),
            'liquidity': liq_result.get('component_score', 0)
        }
        
        tier, tier_label = calculate_overall_tier(component_scores, COMPONENT_WEIGHTS)
        
        # Generate recommendation based on tier and technical signal
        tech_signal = tech_result.get('signal', 'HOLD')
        recommendation = self._generate_recommendation(tier, tech_signal)
        
        self.logger.success(f"Analysis complete", tier=tier, signal=tech_signal)
        
        result = {
            'symbol': self.symbol,
            'analyzed_at': datetime.now().isoformat(),
            'tier': tier,
            'tier_label': tier_label,
            'recommendation': recommendation,
            'technical_signal': tech_signal,
            'components': {
                'technical': tech_result,
                'fundamental': fund_result,
                'liquidity': liq_result,
            }
        }
        
        return result
