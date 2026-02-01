"""
VNStock Analyzer - Hệ thống phân tích và chấm điểm cổ phiếu Việt Nam

Package này cung cấp framework để phân tích đa chiều cổ phiếu:
- Technical Analysis (25 điểm)
- Fundamental Analysis (25 điểm)
- Sentiment Analysis (20 điểm)
- Liquidity Analysis (15 điểm)
- Industry Analysis (15 điểm)

Usage:
    from vnstock_analyzer import StockScorer
    
    scorer = StockScorer('HDB')
    result = scorer.analyze()
"""

from .scorer import StockScorer
from .utils import print_report, export_json

__version__ = '1.0.0'
__all__ = ['StockScorer', 'print_report', 'export_json']
