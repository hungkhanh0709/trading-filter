"""
Utility functions for stock analysis
"""

import json


def print_report(result):
    """
    In báo cáo đẹp
    
    Args:
        result: Analysis result dictionary
    """
    if result is None:
        print("❌ Không thể phân tích được")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 BÁO CÁO ĐÁNH GIÁ CỔ PHIẾU: {result['symbol']}")
    print(f"{'='*60}\n")
    
    # Overall score
    print(f"🎯 TỔNG ĐIỂM: {result['total_score']}/{result['max_score']}")
    print(f"🏅 XẾP HẠNG: {result['tier_label']}")
    print(f"💡 KHUYẾN NGHỊ: {result['recommendation']}\n")
    
    print(f"{'─'*60}")
    print(f"CHI TIẾT ĐIỂM SỐ:")
    print(f"{'─'*60}\n")
    
    # Technical
    tech = result['scores']['technical']
    print(f"1️⃣  PHÂN TÍCH KỸ THUẬT: {tech['total']}/{tech['max']} điểm")
    for key, val in tech['breakdown'].items():
        print(f"   • {key.upper()}: {val['score']}/{val['max']} - {val['reason']}")
    print()
    
    # Fundamental
    fund = result['scores']['fundamental']
    print(f"2️⃣  PHÂN TÍCH CƠ BẢN: {fund['total']}/{fund['max']} điểm")
    for key, val in fund['breakdown'].items():
        print(f"   • {key.upper()}: {val['score']}/{val['max']} - {val['reason']}")
    print()
    
    # Sentiment
    sent = result['scores']['sentiment']
    print(f"3️⃣  TÂM LÝ THỊ TRƯỜNG: {sent['total']}/{sent['max']} điểm")
    for key, val in sent['breakdown'].items():
        print(f"   • {key.upper()}: {val['score']}/{val['max']} - {val['reason']}")
    print()
    
    # Liquidity
    liq = result['scores']['liquidity']
    print(f"4️⃣  THANH KHOẢN: {liq['total']}/{liq['max']} điểm")
    for key, val in liq['breakdown'].items():
        print(f"   • {key.upper()}: {val['score']}/{val['max']} - {val['reason']}")
    print()
    
    # Industry
    ind = result['scores']['industry']
    print(f"5️⃣  PHÂN TÍCH NGÀNH: {ind['total']}/{ind['max']} điểm")
    print(f"   • NGÀNH: {ind['breakdown']['industry']['info']}")
    for key, val in ind['breakdown'].items():
        if key != 'industry':
            print(f"   • {key.upper()}: {val['score']}/{val['max']} - {val['reason']}")
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
