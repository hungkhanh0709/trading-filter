"""
Utility functions for stock analysis
"""

import sys
import json
import numpy as np


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types"""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super(NumpyEncoder, self).default(obj)


# Import logger
try:
    from .utils.logger import get_logger, LogLevel
except ImportError:
    # Fallback if logger not available
    class LogLevel:
        DEBUG = INFO = SUCCESS = WARNING = ERROR = 0
    def get_logger(*args, **kwargs):
        class FallbackLogger:
            def debug(self, *a, **k): pass
            def info(self, *a, **k): pass
            def success(self, *a, **k): pass
            def warning(self, *a, **k): pass
            def error(self, *a, **k): pass
            def section(self, *a, **k): pass
        return FallbackLogger()


def print_report(result, file=sys.stderr):
    """
    In báo cáo theo định dạng status-based (không hiển thị điểm số)
    
    Args:
        result: Analysis result dictionary
        file: Output file (default: sys.stderr for UI integration)
    """
    if result is None:
        print("❌ Không thể phân tích được", file=file)
        return
    
    from .core.constants import STATUS_LEVELS
    
    print(f"\n{'='*60}", file=file)
    print(f"📊 Analyze Report: {result['symbol']}", file=file)
    print(f"{'='*60}\n", file=file)
    
    # Overall tier with criteria count
    tier_label = result['tier_label']
    
    # Count total criteria and passing criteria (excluding NA)
    components = result['components']
    total_criteria = 0
    passing_criteria = 0
    
    for comp_name, comp_data in components.items():
        summary = comp_data.get('summary', {})
        
        # Count non-NA criteria
        non_na_count = (
            summary.get('excellent', 0) +
            summary.get('good', 0) +
            summary.get('acceptable', 0) +
            summary.get('warning', 0) +
            summary.get('poor', 0)
        )
        total_criteria += non_na_count
        
        # Count passing (EXCELLENT + GOOD)
        passing_criteria += summary.get('excellent', 0) + summary.get('good', 0)
    
    print(f"Trạng thái: {result.get('current_state', {}).get('status', 'NA')}", file=file)
    
    # Technical signal
    if 'signal' in result:
        signal = result['signal']
        signal_icons = {
            'STRONG_BUY': '🟢🟢',
            'BUY': '🟢',
            'HOLD': '⚪',
            'CAUTION': '🟡',
            'SELL': '🔴',
            'STRONG_SELL': '🔴🔴'
        }
        icon = signal_icons.get(signal, '⚪')
        print(f"{icon} Tín hiệu: {signal}", file=file)
    
    print(file=file)
    print(f"{'─'*60}", file=file)
    print(f"CHI TIẾT PHÂN TÍCH:", file=file)
    print(f"{'─'*60}\n", file=file)
    
    # 1. Technical Analysis
    if 'technical' in components:
        tech = components['technical']
        status = tech.get('status', 'NA')
        status_info = STATUS_LEVELS.get(status, STATUS_LEVELS['NA'])
        
        print(f"1️⃣  KỸ THUẬT {status_info['icon']} {status_info['label']}", file=file)
        
        criteria = tech.get('criteria', {})
        for criterion_name, criterion_data in criteria.items():
            crit_status = criterion_data.get('status', 'NA')
            crit_info = STATUS_LEVELS.get(crit_status, STATUS_LEVELS['NA'])
            
            # NEW: Support both 'reason' (string) and 'reasons' (array)
            reasons = criterion_data.get('reasons', None)
            reason = criterion_data.get('reason', '')
            
            # Format criterion name
            name_map = {
                'ma_trend': 'MA Trend',
                'rsi': 'RSI',
                'volume_obv': 'Volume + OBV',
                'money_flow': 'Money Flow (MFI)',
                'pattern_signal': 'Pattern Signal'
            }
            display_name = name_map.get(criterion_name, criterion_name.upper())
            
            # NEW: Print reasons as array (multi-line) if available
            if reasons and isinstance(reasons, list):
                print(f"{crit_info['icon']} {display_name}:", file=file)
                for r in reasons:
                    print(f"  • {r}", file=file)
            else:
                # Backward compatibility with old string format
                print(f"{crit_info['icon']} {display_name}: {reason}", file=file)
        print(file=file)
    
    # 2. Fundamental Analysis
    if 'fundamental' in components:
        fund = components['fundamental']
        status = fund.get('status', 'NA')
        status_info = STATUS_LEVELS.get(status, STATUS_LEVELS['NA'])
        
        print(f"2️⃣  CƠ BẢN {status_info['icon']} {status_info['label']}", file=file)
        
        criteria = fund.get('criteria', {})
        for criterion_name, criterion_data in criteria.items():
            crit_status = criterion_data.get('status', 'NA')
            crit_info = STATUS_LEVELS.get(crit_status, STATUS_LEVELS['NA'])
            reason = criterion_data.get('reason', '')
            
            # Format criterion name
            name_map = {
                'pe': 'P/E',
                'pb': 'P/B',
                'roe': 'ROE',
                'roa': 'ROA',
                'eps': 'EPS',
                'debt_equity': 'Debt/Equity',
                'current_ratio': 'Current Ratio'
            }
            display_name = name_map.get(criterion_name, criterion_name.upper())
            
            print(f"{crit_info['icon']} {display_name}: {reason}", file=file)
        print(file=file)
    
    # 3. Liquidity Analysis
    if 'liquidity' in components:
        liq = components['liquidity']
        status = liq.get('status', 'NA')
        status_info = STATUS_LEVELS.get(status, STATUS_LEVELS['NA'])
        
        print(f"3️⃣  THANH KHOẢN {status_info['icon']} {status_info['label']}", file=file)
        
        criteria = liq.get('criteria', {})
        for criterion_name, criterion_data in criteria.items():
            crit_status = criterion_data.get('status', 'NA')
            crit_info = STATUS_LEVELS.get(crit_status, STATUS_LEVELS['NA'])
            reason = criterion_data.get('reason', '')
            
            # Format criterion name
            name_map = {
                'avg_volume': 'Avg Volume',
                'volatility': 'Volatility'
            }
            display_name = name_map.get(criterion_name, criterion_name.upper())
            
            print(f"{crit_info['icon']} {display_name}: {reason}", file=file)
        print(file=file)
    
    print(f"{'='*60}\n", file=file)


def export_json(result, filepath=None):
    """
    Export result to JSON (with numpy support)
    
    Args:
        result: Analysis result dictionary
        filepath: Optional file path to save JSON
        
    Returns:
        str: JSON string
    """
    json_str = json.dumps(result, indent=2, ensure_ascii=False, cls=NumpyEncoder)
    
    if filepath:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json_str)
    
    return json_str


def format_currency(amount, unit='tỷ'):
    """
    Format VND currency
    
    Args:
        amount: Amount in billion VND
        unit: Unit ('tỷ' or 'nghìn tỷ')
        
    Returns:
        str: Formatted string
    """
    if unit == 'nghìn tỷ':
        return f"{amount/1000:.0f} nghìn tỷ"
    return f"{amount:.0f} tỷ"


def format_percentage(value):
    """
    Format percentage
    
    Args:
        value: Percentage value
        
    Returns:
        str: Formatted string
    """
    return f"{value:.1f}%"
