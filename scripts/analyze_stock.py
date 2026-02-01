#!/usr/bin/env python3
"""
CLI tool for stock analysis

Usage: 
    python scripts/analyze_stock.py <SYMBOL>
    
Example:
    python scripts/analyze_stock.py HDB
    
Output:
    - Progress logs to stderr
    - JSON result to stdout (for programmatic use)
"""

import sys
import os

# Force unbuffered output for real-time logging
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vnstock_analyzer import StockScorer, print_report, export_json


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_stock.py <SYMBOL>", file=sys.stderr)
        print("Example: python scripts/analyze_stock.py HDB", file=sys.stderr)
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    
    # Log to stderr (for UI progress) - similar to fetch_prices.py
    print(f"🚀 Analyzing {symbol}...", file=sys.stderr)
    
    # Analyze stock
    scorer = StockScorer(symbol)
    result = scorer.analyze()
    
    if result:
        print(f"✅ Completed analysis for {symbol}", file=sys.stderr)
        
        # Output JSON to stdout (for programmatic use / UI integration)
        print(export_json(result))
    else:
        print(f"❌ Failed to analyze {symbol}", file=sys.stderr)
        error_result = {
            'error': f'Không thể phân tích {symbol}',
            'symbol': symbol
        }
        print(export_json(error_result))
        sys.exit(1)


if __name__ == '__main__':
    main()
