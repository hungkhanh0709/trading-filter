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
    
    def get_total_score(self):
        """
        Tổng điểm Fundamental - 25 điểm
        
        Returns:
            dict: Score breakdown
        """
        if not self.ratios:
            return {
                'total': 0,
                'max': 25,
                'breakdown': {
                    'valuation': {'score': 0, 'max': 10, 'reason': 'Không có dữ liệu'},
                    'profitability': {'score': 0, 'max': 10, 'reason': 'Không có dữ liệu'},
                    'financial_health': {'score': 0, 'max': 5, 'reason': 'Không có dữ liệu'}
                }
            }
        
        # Valuation - 10 điểm
        val_score = 0
        val_reasons = []
        
        pe = self.ratios.get('pe')
        if pe is not None and pe > 0:
            if 8 < pe < 15:
                val_score += 5
                val_reasons.append(f"✅ PE hợp lý ({pe:.1f})")
            elif 5 < pe <= 8:
                val_score += 4
                val_reasons.append(f"💎 PE rất tốt ({pe:.1f})")
            elif 15 <= pe < 25:
                val_score += 2
                val_reasons.append(f"➕ PE chấp nhận được ({pe:.1f})")
            else:
                val_reasons.append(f"⚠️  PE cao/thấp bất thường ({pe:.1f})")
        
        pb = self.ratios.get('pb')
        if pb is not None and pb > 0:
            if 0.8 < pb < 2:
                val_score += 5
                val_reasons.append(f"✅ PB tốt ({pb:.1f})")
            elif pb <= 0.8:
                val_score += 3
                val_reasons.append(f"💎 PB thấp ({pb:.1f})")
            else:
                val_reasons.append(f"⚠️  PB cao ({pb:.1f})")
        
        # Profitability - 10 điểm
        prof_score = 0
        prof_reasons = []
        
        roe = self.ratios.get('roe')
        if roe is not None:
            if roe > 15:
                prof_score += 5
                prof_reasons.append(f"🔥 ROE xuất sắc ({roe:.1f}%)")
            elif roe > 10:
                prof_score += 3
                prof_reasons.append(f"✅ ROE tốt ({roe:.1f}%)")
            elif roe > 5:
                prof_score += 1
                prof_reasons.append(f"➕ ROE chấp nhận ({roe:.1f}%)")
            else:
                prof_reasons.append(f"⚠️  ROE thấp ({roe:.1f}%)")
        
        roa = self.ratios.get('roa')
        if roa is not None:
            if roa > 8:
                prof_score += 3
                prof_reasons.append(f"✅ ROA tốt ({roa:.1f}%)")
            elif roa > 5:
                prof_score += 2
                prof_reasons.append(f"➕ ROA chấp nhận ({roa:.1f}%)")
        
        eps = self.ratios.get('eps') or self.ratios.get('trailing_eps')
        if eps is not None and eps > 0:
            # Đơn giản hóa: nếu có EPS dương là tốt
            if eps > 3000:
                prof_score += 4
                prof_reasons.append(f"✅ EPS cao ({eps:.0f})")
            elif eps > 1000:
                prof_score += 2
                prof_reasons.append(f"➕ EPS tốt ({eps:.0f})")
        
        # Financial Health - 5 điểm
        health_score = 0
        health_reasons = []
        
        de = self.ratios.get('debtOnEquity') or self.ratios.get('debt_on_equity')
        if de is not None:
            if de < 0.5:
                health_score += 3
                health_reasons.append(f"✅ Nợ rất thấp (D/E: {de:.2f})")
            elif de < 1:
                health_score += 2
                health_reasons.append(f"➕ Nợ hợp lý (D/E: {de:.2f})")
            elif de < 2:
                health_score += 1
                health_reasons.append(f"⚠️  Nợ cao (D/E: {de:.2f})")
            else:
                health_reasons.append(f"❌ Nợ quá cao (D/E: {de:.2f})")
        
        cr = self.ratios.get('currentRatio') or self.ratios.get('current_ratio')
        if cr is not None:
            if cr > 1.5:
                health_score += 2
                health_reasons.append(f"✅ Thanh khoản tốt (CR: {cr:.2f})")
            elif cr > 1:
                health_score += 1
                health_reasons.append(f"➕ Thanh khoản OK (CR: {cr:.2f})")
            else:
                health_reasons.append(f"⚠️  Thanh khoản yếu (CR: {cr:.2f})")
        
        return {
            'total': min(val_score, 10) + min(prof_score, 10) + min(health_score, 5),
            'max': 25,
            'breakdown': {
                'valuation': {'score': min(val_score, 10), 'max': 10, 'reason': "; ".join(val_reasons) or "N/A"},
                'profitability': {'score': min(prof_score, 10), 'max': 10, 'reason': "; ".join(prof_reasons) or "N/A"},
                'financial_health': {'score': min(health_score, 5), 'max': 5, 'reason': "; ".join(health_reasons) or "N/A"}
            }
        }
