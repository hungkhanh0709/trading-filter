#!/usr/bin/env python3
"""
CLI tool for stock analysis

Usage: 
    python scripts/analyze_stock.py <SYMBOL>
    
Example:
    python scripts/analyze_stock.py HDB
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vnstock_analyzer import StockScorer, print_report, export_json


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_stock.py <SYMBOL>")
        print("Example: python scripts/analyze_stock.py HDB")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    
    # Analyze stock
    scorer = StockScorer(symbol)
    result = scorer.analyze()
    
    if result:
        # Print beautiful report
        print_report(result)
        
        # Output JSON for programmatic use
        print(f"\n📄 JSON Output:")
        print(export_json(result))
    else:
        print(f"❌ Không thể phân tích {symbol}")
        sys.exit(1)


if __name__ == '__main__':
    main()
