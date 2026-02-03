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
    
    def __init__(self, symbol, source='VCI'):
        """
        Initialize stock scorer với safe initialization
        
        Args:
            symbol: Stock symbol (e.g., 'HDB', 'FPT')
            source: Data source (default: 'VCI')
        """
        self.symbol = symbol
        self.source = source
        self.logger = get_logger(symbol, LogLevel.INFO)
        
        # Lazy initialization - không fetch data trong constructor
        # để tránh crash nếu network fail
        self.fetcher = None
        self._initialized = False
        
    def _ensure_initialized(self):
        """Ensure fetcher is initialized"""
        if not self._initialized:
            try:
                self.fetcher = DataFetcher(self.symbol, self.source)
                self._initialized = True
            except Exception as e:
                self.logger.error(f"Failed to initialize data fetcher: {e}")
                return False
        return True
        
    def analyze(self):
        """
        Phân tích toàn diện - FACTUAL DATA ONLY (NO ADVICE)
        Với error handling và graceful degradation
        
        Returns:
            dict: Complete analysis result with factual signals, or error dict if failed
        """
        self.logger.section(f"PHÂN TÍCH CỔ PHIẾU: {self.symbol}")
        
        # Ensure fetcher is initialized
        if not self._ensure_initialized():
            return {
                'error': 'Không thể khởi tạo data fetcher',
                'symbol': self.symbol,
                'analyzed_at': datetime.now().isoformat()
            }
        
        # Fetch data với retry logic
        self.logger.info("Fetching market data...")
        if not self.fetcher.fetch_all_data():
            self.logger.error("Failed to fetch critical data")
            return {
                'error': 'Không thể lấy dữ liệu giá (có thể do lỗi network hoặc API)',
                'symbol': self.symbol,
                'analyzed_at': datetime.now().isoformat(),
                'suggestion': 'Vui lòng thử lại sau vài phút'
            }
        
        # Get cached data
        df_history = self.fetcher.get_data('history')
        df_ratio = self.fetcher.get_data('ratio')
        
        # Validate critical data
        if df_history is None or df_history.empty:
            self.logger.error("No price history available")
            return {
                'error': 'Không có dữ liệu lịch sử giá',
                'symbol': self.symbol,
                'analyzed_at': datetime.now().isoformat()
            }
        
        # Run analyzers
        self.logger.info("Running analysis modules...")
        
        try:
            technical = TechnicalAnalyzer(df_history)
            tech_result = technical.get_analysis()
            
            # Extract MA analysis - FLATTENED STRUCTURE
            ma_analysis = tech_result.get('ma_analysis', {})
            
            self.logger.success(f"Analysis complete", 
                              status=ma_analysis.get('status'), 
                              signal=tech_result.get('signal'))
            
            # Extract price data from df_history (same data used in MA analysis)
            price_data = {}
            if df_history is not None and len(df_history) >= 2:
                latest = df_history.iloc[-1]
                prev = df_history.iloc[-2]
                
                price_data = {
                    'price': round(latest['close'], 2),
                    'open': round(latest['open'], 2),
                    'high': round(latest['high'], 2),
                    'low': round(latest['low'], 2),
                    'changePercent': round((latest['close'] - prev['close']) / prev['close'] * 100, 2) if prev['close'] > 0 else 0
                }
            
            # Return flattened structure
            result = {
                'symbol': self.symbol,
                'analyzed_at': datetime.now().isoformat(),
                'perfect_order': ma_analysis.get('perfect_order', False),
                
                # Price data (from historical data used in MA analysis)
                **price_data,
                
                # MA components (flattened)
                'expansion': ma_analysis.get('expansion', {}),
                'convergence': ma_analysis.get('convergence', {}),
                'golden_cross': ma_analysis.get('golden_cross', {}),
                'death_cross': ma_analysis.get('death_cross', {}),
                'momentum': ma_analysis.get('momentum', {}),
                'price_position': ma_analysis.get('price_position', {}),
                
                # Volume analysis (note: volume field contains analysis data, not raw number)
                'volume_analysis': ma_analysis.get('volume', {}),
            }
            
            return result
            
        except Exception as e:
            import traceback
            import sys
            print("=" * 80, file=sys.stderr)
            print("FULL TRACEBACK:", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            self.logger.error(f"Analysis failed: {e}")
            self.logger.error(traceback.format_exc())
            return {
                'error': f'Lỗi phân tích: {str(e)}',
                'symbol': self.symbol,
                'analyzed_at': datetime.now().isoformat()
            }
