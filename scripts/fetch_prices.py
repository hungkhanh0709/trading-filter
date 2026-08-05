#!/usr/bin/env python3
"""
Fetch stock prices for Vietnamese stocks using vnstock
"""
import json
import os
import sys

# Add parent directory to path for the side-effect-safe vnstock adapter.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vnstock_analyzer.core.vnstock_client import Quote

# Force unbuffered output for real-time logging
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

def fetch_prices(symbols):
    """
    Fetch current prices and percent changes for a list of symbols
    
    Args:
        symbols: List of stock symbols (e.g., ['ACB', 'VNM', 'HPG'])
    
    Returns:
        Dictionary with symbol as key and {price, changePercent} as value
    """
    results = {}
    
    import time
    
    total = len(symbols)
    success_count = 0
    sources = ('VCI', 'KBS')
    
    for idx, symbol in enumerate(symbols, 1):
        try:
            df = None
            active_source = None

            for source in sources:
                try:
                    quote = Quote(symbol=symbol, source=source)
                    df = quote.history(count_back=2)
                except Exception as source_error:
                    df = None
                    if source == 'VCI':
                        print(
                            f"⚠️  {symbol}: VCI lỗi ({str(source_error)[:50]}...), "
                            f"chuyển sang KBS...",
                            file=sys.stderr
                        )
                        continue
                    raise

                if df is not None and not df.empty:
                    active_source = source
                    break
                if source == 'VCI':
                    print(f"⚠️  {symbol}: VCI không phản hồi, chuyển sang KBS...", file=sys.stderr)
            
            if df is not None and not df.empty and len(df) > 0:
                # Get the latest data
                latest = df.iloc[-1]
                close_price = float(latest['close'])
                
                # Calculate percent change if we have previous close
                if len(df) > 1:
                    prev_close = float(df.iloc[-2]['close'])
                    change_percent = ((close_price - prev_close) / prev_close) * 100
                else:
                    change_percent = 0.0
                
                results[symbol] = {
                    'price': round(close_price, 2),
                    'changePercent': round(change_percent, 2)
                }
                success_count += 1
                print(
                    f"✅ Progress: {idx}/{total} - {symbol}: "
                    f"{close_price:.2f} ({change_percent:+.1f}%, {active_source})",
                    file=sys.stderr
                )
            else:
                results[symbol] = {
                    'price': None,
                    'changePercent': None,
                    'error': 'No data available'
                }
                print(f"⚠️  Progress: {idx}/{total} - {symbol}: No data", file=sys.stderr)
        except Exception as e:
            results[symbol] = {
                'price': None,
                'changePercent': None,
                'error': str(e)
            }
            print(f"❌ Progress: {idx}/{total} - {symbol}: Error - {str(e)}", file=sys.stderr)
        
        # Delay to avoid rate limit: 20 requests/minute = 1 request per 3 seconds
        # Add 0.5s buffer for safety
        if idx < total:  # Don't sleep after last symbol
            time.sleep(3.5)
    
    return results

if __name__ == '__main__':
    # Read symbols from command line arguments or stdin
    if len(sys.argv) > 1:
        # Symbols passed as command line arguments
        symbols = sys.argv[1:]
    else:
        # Read from stdin (one symbol per line or comma-separated)
        input_data = sys.stdin.read().strip()
        if ',' in input_data:
            symbols = [s.strip() for s in input_data.split(',')]
        else:
            symbols = input_data.split()
    
    if not symbols:
        print(json.dumps({'error': 'No symbols provided'}))
        sys.exit(1)
    
    # Fetch prices
    print(f"🚀 Starting to fetch prices for {len(symbols)} symbols...", file=sys.stderr)
    results = fetch_prices(symbols)
    
    # Count successes
    success_count = sum(1 for r in results.values() if r.get('price') is not None)
    print(f"\n🎯 Completed: {success_count}/{len(symbols)} symbols fetched successfully", file=sys.stderr)
    
    # Output as JSON
    print(json.dumps(results, ensure_ascii=False))
