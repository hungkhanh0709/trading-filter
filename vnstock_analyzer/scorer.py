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
        
    def _generate_recommendation(self, ma_status, tech_signal, forecast_scenario):
        """
        Generate recommendation based on MA analysis and forecast
        
        Args:
            ma_status: MA status (EXCELLENT, GOOD, ACCEPTABLE, WARNING, POOR)
            tech_signal: Technical signal from MA analysis
            forecast_scenario: Forecast scenario (STRONG_UPTREND, BREAKOUT_SOON, etc)
            
        Returns:
            str: Recommendation text
        """
        # Priority 1: Strong signals from forecast
        if forecast_scenario == 'STRONG_UPTREND':
            return '🔥 MUA MẠNH - Xu hướng tăng mạnh mẽ'
        elif forecast_scenario == 'BREAKOUT_SOON':
            return '⚡ SẴN SÀNG MUA - Breakout sắp xảy ra'
        elif forecast_scenario == 'STRONG_DOWNTREND':
            return '❌ BÁN NGAY - Xu hướng giảm mạnh'
        elif forecast_scenario == 'DOWNTREND_WARNING':
            return '⚠️ BÁN 50% - Bảo vệ lợi nhuận'
        
        # Priority 2: Based on MA status
        if ma_status == 'EXCELLENT':
            return '✅ MUA - Cơ hội tốt, nắm giữ dài hạn'
        elif ma_status == 'GOOD':
            return '➕ MUA - Theo dõi tiếp'
        elif ma_status == 'ACCEPTABLE':
            if forecast_scenario == 'UPTREND_CONSOLIDATION':
                return '➕ GIỮ - Tích luỹ, có thể chốt lời 30%'
            return '➕ THEO DÕI - Cân nhắc'
        elif ma_status == 'WARNING':
            return '⚠️ THẬN TRỌNG - Rủi ro cao'
        else:  # POOR
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
        
        # Get MA-focused analysis
        tech_result = technical.get_analysis()
        
        # Extract MA analysis details
        ma_status = tech_result.get('ma_analysis', {}).get('status', 'NA')
        tech_signal = tech_result.get('signal', 'HOLD')
        
        # Get forecast for recommendation
        forecast = tech_result.get('ma_analysis', {}).get('forecast', {})
        forecast_scenario = forecast.get('scenario', {}).get('scenario', 'SIDEWAY')
        
        # Generate recommendation based on MA + forecast
        recommendation = self._generate_recommendation(ma_status, tech_signal, forecast_scenario)
        
        # Extract current state and forecast for clear presentation
        ma_analysis = tech_result.get('ma_analysis', {})
        current_state = {
            'status': ma_status,
            'signal': tech_signal,
            'score': ma_analysis.get('score', 0),
            'reasons': ma_analysis.get('reasons', []),
            'details': ma_analysis.get('details', {}),
            'ui_alerts': ma_analysis.get('ui_alerts', [])
        }
        
        self.logger.success(f"Analysis complete", status=ma_status, signal=tech_signal, scenario=forecast_scenario)
        
        result = {
            'symbol': self.symbol,
            'analyzed_at': datetime.now().isoformat(),
            'recommendation': recommendation,
            'signal': tech_signal,
            
            # Current state - Hiện trạng
            'current_state': current_state,
            
            # Forecast - Dự đoán tương lai
            'forecast': forecast,
            
            # Full components (for advanced users)
            'components': {
                'technical': tech_result,
            }
        }
        
        return result
