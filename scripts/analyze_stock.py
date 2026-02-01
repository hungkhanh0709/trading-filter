#!/usr/bin/env python3
"""
CLI tool for stock analysis

Usage: 
    python scripts/analyze_stock.py <SYMBOL>
    
Example:
    python scripts/analyze_stock.py HDB
    
Output:
    - Progress logs to stderr (with professional formatting)
    - JSON result to stdout (for programmatic use)
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vnstock_analyzer import StockScorer, export_json
from vnstock_analyzer.utils import get_logger, LogLevel


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_stock.py <SYMBOL>", file=sys.stderr)
        print("Example: python scripts/analyze_stock.py HDB", file=sys.stderr)
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    logger = get_logger('CLI', LogLevel.INFO)
    
    logger.info(f"Starting analysis for {symbol}")
    
    # Analyze stock
    scorer = StockScorer(symbol)
    result = scorer.analyze()
    
    if result:
        logger.success(f"Analysis completed successfully")
        
        # Output JSON to stdout (for programmatic use / UI integration)
        print(export_json(result))
    else:
        logger.error(f"Analysis failed for {symbol}")
        error_result = {
            'error': f'Không thể phân tích {symbol}',
            'symbol': symbol
        }
        print(export_json(error_result))
        sys.exit(1)


if __name__ == '__main__':
    main()
