"""
Utility functions for stock analysis
"""

import json


def print_report(result):
    """
    In báo cáo theo định dạng status-based (không hiển thị điểm số)
    
    Args:
        result: Analysis result dictionary
    """
    if result is None:
        print("❌ Không thể phân tích được")
        return
    
    from .core.constants import STATUS_LEVELS
    
    print(f"\n{'='*60}")
    print(f"📊 Analyze Report: {result['symbol']}")
    print(f"{'='*60}\n")
    
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
    
    # Calculate percentage
    pass_percentage = (passing_criteria / total_criteria * 100) if total_criteria > 0 else 0
    
    # Display tier with count
    tier_icons = {
        'S': '🔥',
        'A': '✅',
        'B': '➕',
        'C': '⚠️',
        'D': '❌'
    }
    tier_icon = tier_icons.get(result['tier'], '⚪')
    
    print(f"{tier_icon} {tier_label.upper()} ({passing_criteria}/{total_criteria} tiêu chí đạt - {pass_percentage:.0f}%)")
    print(f"💡 {result['recommendation']}")
    
    # Technical signal
    if 'technical_signal' in result:
        signal = result['technical_signal']
        signal_icons = {
            'STRONG_BUY': '🟢🟢',
            'BUY': '🟢',
            'HOLD': '⚪',
            'CAUTION': '🟡',
            'SELL': '🔴',
            'STRONG_SELL': '🔴🔴'
        }
        icon = signal_icons.get(signal, '⚪')
        print(f"{icon} Tín hiệu kỹ thuật: {signal}")
    
    print()
    print(f"{'─'*60}")
    print(f"CHI TIẾT PHÂN TÍCH:")
    print(f"{'─'*60}\n")
    
    # 1. Technical Analysis
    if 'technical' in components:
        tech = components['technical']
        status = tech.get('status', 'NA')
        status_info = STATUS_LEVELS.get(status, STATUS_LEVELS['NA'])
        
        print(f"1️⃣  KỸ THUẬT {status_info['icon']} {status_info['label']}")
        
        criteria = tech.get('criteria', {})
        for criterion_name, criterion_data in criteria.items():
            crit_status = criterion_data.get('status', 'NA')
            crit_info = STATUS_LEVELS.get(crit_status, STATUS_LEVELS['NA'])
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
            
            print(f"   {crit_info['icon']} {display_name}: {reason}")
        print()
    
    # 2. Fundamental Analysis
    if 'fundamental' in components:
        fund = components['fundamental']
        status = fund.get('status', 'NA')
        status_info = STATUS_LEVELS.get(status, STATUS_LEVELS['NA'])
        
        print(f"2️⃣  CƠ BẢN {status_info['icon']} {status_info['label']}")
        
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
            
            print(f"   {crit_info['icon']} {display_name}: {reason}")
        print()
    
    # 3. Liquidity Analysis
    if 'liquidity' in components:
        liq = components['liquidity']
        status = liq.get('status', 'NA')
        status_info = STATUS_LEVELS.get(status, STATUS_LEVELS['NA'])
        
        print(f"3️⃣  THANH KHOẢN {status_info['icon']} {status_info['label']}")
        
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
            
            print(f"   {crit_info['icon']} {display_name}: {reason}")
        print()
    
    print(f"{'='*60}\n")


def export_json(result, filepath=None):
    """
    Export result to JSON
    
    Args:
        result: Analysis result dictionary
        filepath: Optional file path to save JSON
        
    Returns:
        str: JSON string
    """
    json_str = json.dumps(result, indent=2, ensure_ascii=False)
    
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
