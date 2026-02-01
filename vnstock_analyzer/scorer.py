"""
Stock Scorer - Main orchestrator for stock analysis
"""

import sys
from datetime import datetime

from .core import DataFetcher
from .analyzers import (
    TechnicalAnalyzer,
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
        
    def analyze(self):
        """
        Phân tích toàn diện - FACTUAL DATA ONLY (NO ADVICE)
        
        Returns:
            dict: Complete analysis result with factual signals
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
        
        # Get MA-focused analysis
        tech_result = technical.get_analysis()
        
        # Extract MA analysis details
        ma_status = tech_result.get('ma_analysis', {}).get('status', 'NA')
        tech_signal = tech_result.get('signal', 'HOLD')
        
        # Extract current state with factual signals
        ma_analysis = tech_result.get('ma_analysis', {})
        current_state = {
            'status': ma_status,
            'signal': tech_signal,
            'score': ma_analysis.get('score', 0),
            'reasons': ma_analysis.get('reasons', []),
            'details': ma_analysis.get('details', {}),
            'ma_signals': ma_analysis.get('ma_signals', [])  # Factual signals only
        }
        
        self.logger.success(f"Analysis complete", status=ma_status, signal=tech_signal)
        
        result = {
            'symbol': self.symbol,
            'analyzed_at': datetime.now().isoformat(),
            'signal': tech_signal,
            
            # Current state - Hiện trạng (FACTUAL DATA ONLY)
            'current_state': current_state,
            
            # Full components (for advanced users)
            'components': {
                'technical': tech_result,
            }
        }
        
        return result
