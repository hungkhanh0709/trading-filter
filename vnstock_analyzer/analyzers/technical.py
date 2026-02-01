"""
Technical Analyzer - Orchestrator chính cho phân tích kỹ thuật

Refactored: Sử dụng các analyzer chuyên biệt từ thư mục technical_modules/
"""

from .technical_modules.ma_analyzer import MAAnalyzer
from .technical_modules.rsi_analyzer import RSIAnalyzer
from .technical_modules.volume_analyzer import VolumeAnalyzer
from .technical_modules.mfi_analyzer import MFIAnalyzer
from .technical_modules.pattern_analyzer import PatternAnalyzer


class TechnicalAnalyzer:
    """
    Orchestrator cho phân tích kỹ thuật
    
    Delegate work to specialized analyzers:
    - MA: Moving Average analysis
    - RSI: Relative Strength Index
    - Volume: Volume + OBV analysis
    - MFI: Money Flow Index
    - Pattern: Candlestick patterns + Support/Resistance
    """
    
    def __init__(self, df_history):
        """
        Initialize technical analyzer
        
        Args:
            df_history: Historical price dataframe
        """
        self.df = df_history.copy() if df_history is not None else None
        self._calculate_indicators()
        
        # Tạo các specialized analyzers
        if self.df is not None:
            self.ma_analyzer = MAAnalyzer(self.df)
            self.rsi_analyzer = RSIAnalyzer(self.df)
            self.volume_analyzer = VolumeAnalyzer(self.df)
            self.mfi_analyzer = MFIAnalyzer(self.df)
            self.pattern_analyzer = PatternAnalyzer(self.df)
        
    def _calculate_indicators(self):
        """Tính các chỉ báo kỹ thuật - Dùng EMA để match TradingView"""
        if self.df is None or len(self.df) == 0:
            return
        
        # Moving Averages - EMA (Exponential) thay vì SMA (Simple)
        # EMA phản ứng nhanh hơn, match với TradingView default
        self.df['MA5'] = self.df['close'].ewm(span=5, adjust=False).mean()
        self.df['MA10'] = self.df['close'].ewm(span=10, adjust=False).mean()
        self.df['MA20'] = self.df['close'].ewm(span=20, adjust=False).mean()
        self.df['MA50'] = self.df['close'].ewm(span=50, adjust=False).mean()

        # RSI
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        self.df['RSI'] = 100 - (100 / (1 + rs))
        
        # Volume
        self.df['vol_ma20'] = self.df['volume'].rolling(20).mean()
        self.df['vol_ratio'] = self.df['volume'] / self.df['vol_ma20']
        
        # OBV (On Balance Volume)
        self.df['OBV'] = (self.df['volume'] * (~self.df['close'].diff().le(0) * 2 - 1)).cumsum()
        
        # Money Flow Index (MFI)
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        raw_money_flow = typical_price * self.df['volume']
        
        # Positive and negative money flow
        positive_flow = raw_money_flow.where(typical_price.diff() > 0, 0).rolling(14).sum()
        negative_flow = raw_money_flow.where(typical_price.diff() < 0, 0).rolling(14).sum()
        
        # Avoid division by zero
        money_ratio = positive_flow / negative_flow.replace(0, 1)
        self.df['MFI'] = 100 - (100 / (1 + money_ratio))
    
    def score_ma_trend(self):
        """
        Backward compatibility: delegate to MAAnalyzer
        
        Returns:
            tuple: (score, reason_string) - reason_string được join từ array
        """
        if self.df is None or len(self.df) < 50:
            return 0, "Không đủ dữ liệu"
        
        result = self.ma_analyzer.analyze()
        return result['score'], " | ".join(result['reasons'])
    
    def score_rsi(self):
        """Backward compatibility: delegate to RSIAnalyzer"""
        if self.df is None or len(self.df) < 14:
            return 0, "Không đủ dữ liệu"
        
        result = self.rsi_analyzer.analyze()
        return result['score'], "; ".join(result['reasons'])
    
    def score_volume(self):
        """Backward compatibility: delegate to VolumeAnalyzer"""
        if self.df is None or len(self.df) < 20:
            return 0, "Không đủ dữ liệu"
        
        result = self.volume_analyzer.analyze()
        return result['score'], "; ".join(result['reasons'])
    
    def score_money_flow(self):
        """Backward compatibility: delegate to MFIAnalyzer"""
        if self.df is None or len(self.df) < 14:
            return 0, "Không đủ dữ liệu"
        
        result = self.mfi_analyzer.analyze()
        return result['score'], "; ".join(result['reasons'])
    
    def score_pattern_signals(self):
        """Backward compatibility: delegate to PatternAnalyzer"""
        if self.df is None or len(self.df) < 14:
            return 0, "HOLD", "Không đủ dữ liệu"
        
        result = self.pattern_analyzer.analyze()
        return result['score'], result['signal'], "; ".join(result['reasons'])
    
    def get_analysis(self):
        """
        Phân tích toàn diện - OUTPUT MỚI VỚI REASONS DẠNG ARRAY!
        
        Returns:
            dict: {
                'status': str,
                'criteria': {
                    'ma_trend': {
                        'status': str,
                        'reasons': list,  # ARRAY!
                        'details': dict
                    },
                    ...
                },
                'summary': dict,
                'signal': str,
                'component_score': float
            }
        """
        if self.df is None or len(self.df) < 14:
            return {
                'status': 'NA',
                'criteria': {},
                'summary': {},
                'signal': 'HOLD',
                'component_score': 0
            }
        
        # Get analysis từ các specialized analyzers
        ma_result = self.ma_analyzer.analyze()
        rsi_result = self.rsi_analyzer.analyze()
        vol_result = self.volume_analyzer.analyze()
        mfi_result = self.mfi_analyzer.analyze()
        pattern_result = self.pattern_analyzer.analyze()
        
        # Build criteria với reasons dạng array
        criteria = {
            'ma_trend': {
                'status': ma_result['status'],
                'reasons': ma_result['reasons'],  # ARRAY!
                'details': ma_result.get('details', {}),
                'ui_alerts': ma_result.get('ui_alerts', [])  # UI-READY FORMAT!
            },
            'rsi': {
                'status': rsi_result['status'],
                'reasons': rsi_result['reasons'],  # ARRAY!
                'details': rsi_result.get('details', {})
            },
            'volume_obv': {
                'status': vol_result['status'],
                'reasons': vol_result['reasons'],  # ARRAY!
                'details': vol_result.get('details', {})
            },
            'money_flow': {
                'status': mfi_result['status'],
                'reasons': mfi_result['reasons'],  # ARRAY!
                'details': mfi_result.get('details', {})
            },
            'pattern_signal': {
                'status': pattern_result['status'],
                'reasons': pattern_result['reasons'],  # ARRAY!
                'details': pattern_result.get('details', {})
            }
        }
        
        # Calculate overall component status
        from ..core.constants import calculate_component_score, count_criteria_by_status
        
        component_score = calculate_component_score(criteria)
        summary = count_criteria_by_status(criteria)
        
        # Determine overall status
        if component_score >= 0.9:
            overall_status = 'EXCELLENT'
        elif component_score >= 0.7:
            overall_status = 'GOOD'
        elif component_score >= 0.5:
            overall_status = 'ACCEPTABLE'
        elif component_score >= 0.3:
            overall_status = 'WARNING'
        else:
            overall_status = 'POOR'
        
        return {
            'status': overall_status,
            'criteria': criteria,
            'summary': summary,
            'signal': pattern_result['signal'],
            'component_score': component_score
        }
    
    # Backward compatibility methods cho mapping
    def _map_ma_status(self, score):
        """Map MA score to status (backward compatibility)"""
        if score >= 9:
            return 'EXCELLENT'
        elif score >= 7:
            return 'GOOD'
        elif score >= 4:
            return 'ACCEPTABLE'
        elif score >= 2:
            return 'WARNING'
        else:
            return 'POOR'
    
    def _map_rsi_status(self, score):
        """Map RSI score to status"""
        if score == 5:
            return 'EXCELLENT'
        elif score == 4:
            return 'GOOD'
        elif score == 3:
            return 'ACCEPTABLE'
        elif score == 2:
            return 'WARNING'
        else:
            return 'POOR'
    
    def _map_volume_status(self, score):
        """Map Volume score to status"""
        if score >= 8:
            return 'EXCELLENT'
        elif score >= 6:
            return 'GOOD'
        elif score >= 3:
            return 'ACCEPTABLE'
        elif score >= 1:
            return 'WARNING'
        else:
            return 'POOR'
    
    def _map_mfi_status(self, score):
        """Map MFI score to status"""
        if score == 5:
            return 'EXCELLENT'
        elif score == 4:
            return 'GOOD'
        elif score == 3:
            return 'ACCEPTABLE'
        elif score == 2:
            return 'WARNING'
        else:
            return 'POOR'
    
    def _map_pattern_status(self, signal):
        """Map pattern signal to status"""
        if signal == 'STRONG_BUY':
            return 'EXCELLENT'
        elif signal == 'BUY':
            return 'GOOD'
        elif signal == 'HOLD':
            return 'ACCEPTABLE'
        elif signal == 'CAUTION':
            return 'WARNING'
        elif signal in ['SELL', 'STRONG_SELL']:
            return 'POOR'
        else:
            return 'NA'
