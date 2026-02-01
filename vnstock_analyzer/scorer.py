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
        
        # Extract MA analysis - FLATTENED STRUCTURE (matching ma_result_new.json)
        ma_analysis = tech_result.get('ma_analysis', {})
        
        self.logger.success(f"Analysis complete", 
                          status=ma_analysis.get('status'), 
                          signal=tech_result.get('signal'))
        
        # Return flattened structure
        result = {
            'symbol': self.symbol,
            'analyzed_at': datetime.now().isoformat(),
            
            # Flatten MA analysis to top level
            'status': ma_analysis.get('status', 'NA'),
            'reasons': ma_analysis.get('reasons', []),
            'perfect_order': ma_analysis.get('perfect_order', False),
            
            # MA components (flattened)
            'expansion': ma_analysis.get('expansion', {}),
            'convergence': ma_analysis.get('convergence', {}),
            'golden_cross': ma_analysis.get('golden_cross', {}),
            'death_cross': ma_analysis.get('death_cross', {}),
            'momentum': ma_analysis.get('momentum', {}),
            'price_position': ma_analysis.get('price_position', {}),
            
            # UI columns (NEW)
            'columns': ma_analysis.get('columns', [])
        }
        
        return result
