#!/usr/bin/env python3
"""
CLI tool for stock analysis

Usage: 
    python scripts/analyze_stock.py <SYMBOL>
    
Example:
    python scripts/analyze_stock.py HDB
    .venv/bin/python scripts/analyze_stock.py HDB
    
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
    
    try:
        # Analyze stock với error handling
        scorer = StockScorer(symbol)
        result = scorer.analyze()
        
        # Check if result contains error
        if result and 'error' not in result:
            logger.success(f"Analysis completed successfully")
            print(export_json(result))
            sys.exit(0)
        elif result and 'error' in result:
            # Có kết quả nhưng có lỗi
            logger.error(f"Analysis failed: {result['error']}")
            print(export_json(result))
            sys.exit(1)
        else:
            # Không có kết quả gì
            logger.error(f"Analysis failed for {symbol}")
            error_result = {
                'error': f'Không thể phân tích {symbol} (unknown error)',
                'symbol': symbol
            }
            print(export_json(error_result))
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.error("Analysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        error_result = {
            'error': f'Lỗi không mong đợi: {str(e)}',
            'symbol': symbol
        }
        print(export_json(error_result))
        sys.exit(1)


if __name__ == '__main__':
    main()
