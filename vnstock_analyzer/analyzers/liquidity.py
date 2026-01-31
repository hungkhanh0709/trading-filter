"""
Liquidity Analyzer - Phân tích thanh khoản (15 điểm)
"""


class LiquidityAnalyzer:
    """Phân tích thanh khoản - 15 điểm"""
    
    def __init__(self, df_history):
        """
        Initialize liquidity analyzer
        
        Args:
            df_history: Historical price dataframe
        """
        self.df = df_history
    
    def get_analysis(self):
        """
        Status-based Liquidity Analysis
        
        Returns status for each criterion:
        - EXCELLENT 🔥: Outstanding
        - GOOD ✅: Pass
        - ACCEPTABLE ➕: OK
        - WARNING ⚠️: Caution
        - POOR ❌: Fail
        - NA ⚪: No data
        
        Returns:
            dict: {
                'status': 'GOOD',
                'criteria': {...},
                'summary': {'excellent': 1, 'good': 1, ...}
            }
        """
        if self.df is None or len(self.df) < 20:
            return {
                'status': 'NA',
                'criteria': {
                    'avg_volume': {'status': 'NA', 'reason': 'Không đủ dữ liệu'},
                    'volatility': {'status': 'NA', 'reason': 'Không đủ dữ liệu'}
                },
                'summary': {'na': 2},
                'component_score': 0
            }
        
        criteria = {}
        
        # Average Volume
        avg_vol = self.df['volume'].mean()
        if avg_vol > 1_000_000:
            criteria['avg_volume'] = {
                'status': 'EXCELLENT',
                'reason': f"🔥 Thanh khoản rất cao ({avg_vol/1e6:.1f}M cp/ngày)"
            }
        elif avg_vol > 500_000:
            criteria['avg_volume'] = {
                'status': 'GOOD',
                'reason': f"✅ Thanh khoản tốt ({avg_vol/1e3:.0f}K cp/ngày)"
            }
        elif avg_vol > 200_000:
            criteria['avg_volume'] = {
                'status': 'ACCEPTABLE',
                'reason': f"➕ Thanh khoản chấp nhận ({avg_vol/1e3:.0f}K cp/ngày)"
            }
        elif avg_vol > 100_000:
            criteria['avg_volume'] = {
                'status': 'WARNING',
                'reason': f"⚠️  Thanh khoản thấp ({avg_vol/1e3:.0f}K cp/ngày)"
            }
        else:
            criteria['avg_volume'] = {
                'status': 'POOR',
                'reason': f"❌ Thanh khoản rất thấp ({avg_vol/1e3:.0f}K cp/ngày)"
            }
        
        # Volatility
        volatility = self.df['close'].pct_change().std() * 100
        if volatility < 2:
            criteria['volatility'] = {
                'status': 'EXCELLENT',
                'reason': f"✅ Biến động thấp ({volatility:.1f}%)"
            }
        elif 2 <= volatility < 3:
            criteria['volatility'] = {
                'status': 'GOOD',
                'reason': f"✅ Biến động hợp lý ({volatility:.1f}%)"
            }
        elif 3 <= volatility < 5:
            criteria['volatility'] = {
                'status': 'ACCEPTABLE',
                'reason': f"➕ Biến động trung bình ({volatility:.1f}%)"
            }
        elif 5 <= volatility < 7:
            criteria['volatility'] = {
                'status': 'WARNING',
                'reason': f"⚠️  Biến động cao ({volatility:.1f}%)"
            }
        else:
            criteria['volatility'] = {
                'status': 'POOR',
                'reason': f"❌ Biến động rất cao ({volatility:.1f}%)"
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
            'component_score': component_score
        }
