"""
Stock Scorer - Main orchestrator for stock analysis
"""

import sys
from datetime import datetime

from .core import DataFetcher, TIERS, TIER_LABELS, TIER_RECOMMENDATIONS
from .analyzers import (
    TechnicalAnalyzer,
    FundamentalAnalyzer,
    SentimentAnalyzer,
    LiquidityAnalyzer,
    IndustryAnalyzer
)


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
        
    def _calculate_tier(self, total_score):
        """
        Determine tier based on total score
        
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
        
    def analyze(self):
        """
        Phân tích toàn diện
        
        Returns:
            dict: Complete analysis result
        """
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"🎯 PHÂN TÍCH CỔ PHIẾU: {self.symbol}", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)
        
        # Fetch data
        if not self.fetcher.fetch_all_data():
            return None
        
        # Get cached data
        df_history = self.fetcher.get_data('history')
        df_ratio = self.fetcher.get_data('ratio')
        insider = self.fetcher.get_data('insider')
        shareholders = self.fetcher.get_data('shareholders')
        overview = self.fetcher.get_data('overview')
        
        # Run analyzers
        print(f"🔍 Đang phân tích...\n", file=sys.stderr)
        
        technical = TechnicalAnalyzer(df_history)
        fundamental = FundamentalAnalyzer(df_ratio)
        sentiment = SentimentAnalyzer(insider, shareholders)
        liquidity = LiquidityAnalyzer(df_history)
        
        # Get current price for industry analyzer
        current_price = df_history.iloc[-1]['close'] if df_history is not None and len(df_history) > 0 else None
        industry = IndustryAnalyzer(self.symbol, self.source)
        
        # Calculate scores
        tech_result = technical.get_total_score()
        fund_result = fundamental.get_total_score()
        sent_result = sentiment.get_total_score()
        liq_result = liquidity.get_total_score()
        industry_result = industry.get_total_score(overview, current_price)
        
        # Total score
        total_score = (
            tech_result['total'] + 
            fund_result['total'] + 
            sent_result['total'] + 
            liq_result['total'] + 
            industry_result['total']
        )
        
        # Determine tier
        tier, tier_label, recommendation = self._calculate_tier(total_score)
        
        # Extract technical signal (if available)
        tech_signal = tech_result.get('signal', 'HOLD')
        
        result = {
            'symbol': self.symbol,
            'analyzed_at': datetime.now().isoformat(),
            'total_score': total_score,
            'max_score': 100,
            'tier': tier,
            'tier_label': tier_label,
            'recommendation': recommendation,
            'technical_signal': tech_signal,
            'scores': {
                'technical': tech_result,
                'fundamental': fund_result,
                'sentiment': sent_result,
                'liquidity': liq_result,
                'industry': industry_result
            }
        }
        
        return result
