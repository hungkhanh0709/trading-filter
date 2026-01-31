"""
Fundamental Analyzer - Phân tích cơ bản (25 điểm)
"""


class FundamentalAnalyzer:
    """Phân tích cơ bản - 25 điểm"""
    
    def __init__(self, df_ratio):
        """
        Initialize fundamental analyzer
        
        Args:
            df_ratio: Financial ratio dataframe
        """
        self.df = df_ratio
        self.ratios = self._parse_ratios()
    
    def _parse_ratios(self):
        """Parse ratio data từ format pivot của KBS"""
        if self.df is None or len(self.df) == 0:
            return {}
        
        ratios = {}
        quarter_cols = [col for col in self.df.columns if col not in ['item', 'item_id']]
        if not quarter_cols:
            return {}
        
        latest_quarter = quarter_cols[0]  # Quý gần nhất
        
        # Mapping item_id to friendly names
        ratio_map = {
            'pe': 'P/E',
            'pb': 'P/B',
            'roe': 'ROE',
            'roa': 'ROA',
            'eps': 'EPS',
            'trailing_eps': 'EPS',
            'debtOnEquity': 'Debt/Equity',
            'debt_on_equity': 'Debt/Equity',
            'currentRatio': 'Current Ratio',
            'current_ratio': 'Current Ratio'
        }
        
        for idx, row in self.df.iterrows():
            item_id = str(row['item_id']).lower().strip()
            value = row.get(latest_quarter)
            
            # Match against known ratios
            for key, friendly in ratio_map.items():
                if key in item_id:
                    try:
                        ratios[key] = float(value) if value and value != '' else None
                    except:
                        ratios[key] = None
                    break
        
        return ratios
    
    def get_analysis(self):
        """
        Status-based Fundamental Analysis
        
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
                'summary': {'excellent': 2, 'good': 3, ...}
            }
        """
        if not self.ratios:
            return {
                'status': 'NA',
                'criteria': {
                    'pe': {'status': 'NA', 'reason': 'Không có dữ liệu'},
                    'pb': {'status': 'NA', 'reason': 'Không có dữ liệu'},
                    'roe': {'status': 'NA', 'reason': 'Không có dữ liệu'},
                    'roa': {'status': 'NA', 'reason': 'Không có dữ liệu'},
                    'eps': {'status': 'NA', 'reason': 'Không có dữ liệu'},
                    'debt_equity': {'status': 'NA', 'reason': 'Không có dữ liệu'},
                    'current_ratio': {'status': 'NA', 'reason': 'Không có dữ liệu'}
                },
                'summary': {'na': 7},
                'component_score': 0
            }
        
        # Analyze each criterion
        criteria = {}
        
        # PE Ratio
        pe = self.ratios.get('pe')
        if pe is not None and pe > 0:
            if 5 < pe <= 8:
                criteria['pe'] = {'status': 'EXCELLENT', 'reason': f'💎 PE rất tốt ({pe:.1f})'}
            elif 8 < pe < 15:
                criteria['pe'] = {'status': 'GOOD', 'reason': f'✅ PE hợp lý ({pe:.1f})'}
            elif 15 <= pe < 25:
                criteria['pe'] = {'status': 'ACCEPTABLE', 'reason': f'➕ PE chấp nhận được ({pe:.1f})'}
            elif pe >= 25:
                criteria['pe'] = {'status': 'WARNING', 'reason': f'⚠️  PE cao ({pe:.1f})'}
            else:  # pe <= 5
                criteria['pe'] = {'status': 'POOR', 'reason': f'⚠️  PE quá thấp ({pe:.1f})'}
        else:
            criteria['pe'] = {'status': 'NA', 'reason': 'Không có dữ liệu PE'}
        
        # PB Ratio
        pb = self.ratios.get('pb')
        if pb is not None and pb > 0:
            if pb <= 0.8:
                criteria['pb'] = {'status': 'EXCELLENT', 'reason': f'💎 PB thấp ({pb:.1f})'}
            elif 0.8 < pb < 2:
                criteria['pb'] = {'status': 'GOOD', 'reason': f'✅ PB tốt ({pb:.1f})'}
            elif 2 <= pb < 3:
                criteria['pb'] = {'status': 'ACCEPTABLE', 'reason': f'➕ PB chấp nhận ({pb:.1f})'}
            elif pb >= 3:
                criteria['pb'] = {'status': 'WARNING', 'reason': f'⚠️  PB cao ({pb:.1f})'}
            else:
                criteria['pb'] = {'status': 'POOR', 'reason': f'⚠️  PB bất thường ({pb:.1f})'}
        else:
            criteria['pb'] = {'status': 'NA', 'reason': 'Không có dữ liệu PB'}
        
        # ROE
        roe = self.ratios.get('roe')
        if roe is not None:
            if roe > 15:
                criteria['roe'] = {'status': 'EXCELLENT', 'reason': f'🔥 ROE xuất sắc ({roe:.1f}%)'}
            elif roe > 10:
                criteria['roe'] = {'status': 'GOOD', 'reason': f'✅ ROE tốt ({roe:.1f}%)'}
            elif roe > 5:
                criteria['roe'] = {'status': 'ACCEPTABLE', 'reason': f'➕ ROE chấp nhận ({roe:.1f}%)'}
            elif roe > 0:
                criteria['roe'] = {'status': 'WARNING', 'reason': f'⚠️  ROE thấp ({roe:.1f}%)'}
            else:
                criteria['roe'] = {'status': 'POOR', 'reason': f'❌ ROE âm ({roe:.1f}%)'}
        else:
            criteria['roe'] = {'status': 'NA', 'reason': 'Không có dữ liệu ROE'}
        
        # ROA
        roa = self.ratios.get('roa')
        if roa is not None:
            if roa > 8:
                criteria['roa'] = {'status': 'EXCELLENT', 'reason': f'🔥 ROA xuất sắc ({roa:.1f}%)'}
            elif roa > 5:
                criteria['roa'] = {'status': 'GOOD', 'reason': f'✅ ROA tốt ({roa:.1f}%)'}
            elif roa > 2:
                criteria['roa'] = {'status': 'ACCEPTABLE', 'reason': f'➕ ROA chấp nhận ({roa:.1f}%)'}
            elif roa > 0:
                criteria['roa'] = {'status': 'WARNING', 'reason': f'⚠️  ROA thấp ({roa:.1f}%)'}
            else:
                criteria['roa'] = {'status': 'POOR', 'reason': f'❌ ROA âm ({roa:.1f}%)'}
        else:
            criteria['roa'] = {'status': 'NA', 'reason': 'Không có dữ liệu ROA'}
        
        # EPS
        eps = self.ratios.get('eps') or self.ratios.get('trailing_eps')
        if eps is not None and eps > 0:
            if eps > 3000:
                criteria['eps'] = {'status': 'EXCELLENT', 'reason': f'🔥 EPS cao ({eps:.0f})'}
            elif eps > 1000:
                criteria['eps'] = {'status': 'GOOD', 'reason': f'✅ EPS tốt ({eps:.0f})'}
            elif eps > 500:
                criteria['eps'] = {'status': 'ACCEPTABLE', 'reason': f'➕ EPS chấp nhận ({eps:.0f})'}
            else:
                criteria['eps'] = {'status': 'WARNING', 'reason': f'⚠️  EPS thấp ({eps:.0f})'}
        elif eps is not None and eps <= 0:
            criteria['eps'] = {'status': 'POOR', 'reason': f'❌ EPS âm hoặc 0 ({eps:.0f})'}
        else:
            criteria['eps'] = {'status': 'NA', 'reason': 'Không có dữ liệu EPS'}
        
        # Debt/Equity
        de = self.ratios.get('debtOnEquity') or self.ratios.get('debt_on_equity')
        if de is not None:
            if de < 0.5:
                criteria['debt_equity'] = {'status': 'EXCELLENT', 'reason': f'✅ Nợ rất thấp (D/E: {de:.2f})'}
            elif de < 1:
                criteria['debt_equity'] = {'status': 'GOOD', 'reason': f'✅ Nợ hợp lý (D/E: {de:.2f})'}
            elif de < 2:
                criteria['debt_equity'] = {'status': 'ACCEPTABLE', 'reason': f'➕ Nợ chấp nhận (D/E: {de:.2f})'}
            elif de < 3:
                criteria['debt_equity'] = {'status': 'WARNING', 'reason': f'⚠️  Nợ cao (D/E: {de:.2f})'}
            else:
                criteria['debt_equity'] = {'status': 'POOR', 'reason': f'❌ Nợ quá cao (D/E: {de:.2f})'}
        else:
            criteria['debt_equity'] = {'status': 'NA', 'reason': 'Không có dữ liệu D/E'}
        
        # Current Ratio
        cr = self.ratios.get('currentRatio') or self.ratios.get('current_ratio')
        if cr is not None:
            if cr > 2:
                criteria['current_ratio'] = {'status': 'EXCELLENT', 'reason': f'✅ Thanh khoản rất tốt (CR: {cr:.2f})'}
            elif cr > 1.5:
                criteria['current_ratio'] = {'status': 'GOOD', 'reason': f'✅ Thanh khoản tốt (CR: {cr:.2f})'}
            elif cr > 1:
                criteria['current_ratio'] = {'status': 'ACCEPTABLE', 'reason': f'➕ Thanh khoản OK (CR: {cr:.2f})'}
            elif cr > 0.8:
                criteria['current_ratio'] = {'status': 'WARNING', 'reason': f'⚠️  Thanh khoản yếu (CR: {cr:.2f})'}
            else:
                criteria['current_ratio'] = {'status': 'POOR', 'reason': f'❌ Thanh khoản rất yếu (CR: {cr:.2f})'}
        else:
            criteria['current_ratio'] = {'status': 'NA', 'reason': 'Không có dữ liệu CR'}
        
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
