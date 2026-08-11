"""
Technical Analyzer - MA MASTER FOCUS

Simplified to focus 100% on Moving Average analysis.
All complexity removed - pure MA-based trading signals.
"""

import pandas as pd

from .technical_modules.ma_analyzer import MAAnalyzer


class TechnicalAnalyzer:
    """
    MA-focused Technical Analyzer
    
    Delegates ALL analysis to MAAnalyzer for maximum accuracy.
    Uses only Price + EMA10 + EMA20 + EMA50 for trading decisions.
    """
    
    def __init__(self, df_history):
        """
        Initialize technical analyzer
        
        Args:
            df_history: Historical price dataframe
        """
        self.df = df_history.copy() if df_history is not None else None
        self._calculate_indicators()
        
        # Create MA analyzer only
        if self.df is not None:
            self.ma_analyzer = MAAnalyzer(self.df)
        
    def _calculate_indicators(self):
        """Calculate close-based EMA with TradingView-compatible SMA seed."""
        if self.df is None or len(self.df) == 0:
            return
        
        self.df['MA10'] = self._tradingview_ema(self.df['close'], 10)
        self.df['MA20'] = self._tradingview_ema(self.df['close'], 20)
        self.df['MA50'] = self._tradingview_ema(self.df['close'], 50)

    @staticmethod
    def _tradingview_ema(values, length):
        """EMA seeded with the SMA of the first ``length`` valid closes."""
        source = pd.to_numeric(values, errors='coerce')
        result = pd.Series(float('nan'), index=source.index, dtype='float64')
        valid_positions = [position for position, value in enumerate(source) if pd.notna(value)]
        if len(valid_positions) < length:
            return result

        alpha = 2.0 / (length + 1.0)
        seed_position = valid_positions[length - 1]
        seed = source.iloc[valid_positions[:length]].mean()
        result.iloc[seed_position] = seed
        previous = seed
        for position in range(seed_position + 1, len(source)):
            current = source.iloc[position]
            if pd.isna(current):
                result.iloc[position] = previous
                continue
            previous = alpha * current + (1.0 - alpha) * previous
            result.iloc[position] = previous
        return result

    def get_analysis(self):
        """
        MA-focused analysis - Simple and powerful
        
        Returns:
            dict: {
                'status': str,
                'signal': str,
                'ma_analysis': dict (complete MA analysis),
                'component_score': float
            }
        """
        if self.df is None or len(self.df) < 50:
            return {
                'status': 'NA',
                'signal': 'HOLD',
                'ma_analysis': {
                    'status': 'NA',
                    'score': 0,
                    'reasons': ['Không đủ dữ liệu EMA50; cần tối thiểu 50 phiên'],
                    'details': {},
                    'forecast': {}
                },
                'component_score': 0
            }
        
        # Get MA analysis
        ma_result = self.ma_analyzer.analyze()
        
        # Simple status mapping from MA score
        ma_score = ma_result.get('score', 0)
        if ma_score >= 9:
            overall_status = 'EXCELLENT'
        elif ma_score >= 7:
            overall_status = 'GOOD'
        elif ma_score >= 4:
            overall_status = 'ACCEPTABLE'
        elif ma_score >= 2:
            overall_status = 'WARNING'
        else:
            overall_status = 'POOR'
        
        # Determine signal from MA forecast
        forecast_scenario = ma_result.get('forecast', {}).get('scenario', {}).get('scenario', 'SIDEWAY')
        
        if forecast_scenario in ['STRONG_UPTREND', 'BREAKOUT_SOON']:
            signal = 'STRONG_BUY'
        elif forecast_scenario == 'UPTREND_CONSOLIDATION':
            signal = 'BUY'
        elif forecast_scenario in ['DOWNTREND_WARNING', 'STRONG_DOWNTREND']:
            signal = 'SELL'
        else:
            signal = 'HOLD'
        
        # Component score from MA (0-1)
        component_score = ma_score / 10.0
        
        return {
            'status': overall_status,
            'signal': signal,
            'ma_analysis': ma_result,
            'component_score': component_score
        }
