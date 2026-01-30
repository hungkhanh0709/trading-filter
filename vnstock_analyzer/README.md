# VNStock Analyzer

Hệ thống phân tích và chấm điểm cổ phiếu Việt Nam đa chiều.

## 📊 Cấu trúc

```
vnstock_analyzer/
├── __init__.py              # Package exports
├── scorer.py                # Main orchestrator
├── utils.py                 # Utilities (print_report, export_json)
│
├── core/                    # Core components
│   ├── __init__.py
│   ├── data_fetcher.py      # DataFetcher class
│   └── constants.py         # Constants & thresholds
│
└── analyzers/               # Analysis modules
    ├── __init__.py
    ├── technical.py         # TechnicalAnalyzer (25 điểm)
    ├── fundamental.py       # FundamentalAnalyzer (25 điểm)
    ├── sentiment.py         # SentimentAnalyzer (20 điểm)
    ├── liquidity.py         # LiquidityAnalyzer (15 điểm)
    └── industry.py          # IndustryAnalyzer (15 điểm)

scripts/
├── analyze_stock.py         # CLI tool
└── fetch_prices.py          # Simple price fetcher
```

## 🚀 Usage

### CLI
```bash
python scripts/analyze_stock.py HDB
```

### Python API
```python
from vnstock_analyzer import StockScorer, print_report

# Analyze stock
scorer = StockScorer('HDB')
result = scorer.analyze()

# Print beautiful report
print_report(result)

# Or access raw data
print(f"Total score: {result['total_score']}/100")
print(f"Tier: {result['tier']}")
```

### Advanced Usage
```python
from vnstock_analyzer.core import DataFetcher
from vnstock_analyzer.analyzers import TechnicalAnalyzer

# Use individual components
fetcher = DataFetcher('HDB')
fetcher.fetch_all_data()
df_history = fetcher.get_data('history')

technical = TechnicalAnalyzer(df_history)
tech_score = technical.get_total_score()
print(tech_score)
```

## 📈 Scoring System

Total: **100 điểm**

1. **Technical Analysis (25 điểm)**
   - MA Trend: 10 điểm
   - RSI: 5 điểm
   - Volume: 10 điểm

2. **Fundamental Analysis (25 điểm)**
   - Valuation (PE, PB): 10 điểm
   - Profitability (ROE, ROA, EPS): 10 điểm
   - Financial Health (D/E, Current Ratio): 5 điểm

3. **Sentiment Analysis (20 điểm)**
   - Insider Deals: 10 điểm
   - Foreign Ownership: 5 điểm
   - News Sentiment: 5 điểm

4. **Liquidity Analysis (15 điểm)**
   - Volume: 10 điểm
   - Volatility: 5 điểm

5. **Industry Analysis (15 điểm)**
   - Relative Strength: 10 điểm
   - Market Position: 5 điểm

## 🏅 Tiers

- **S (85-100)**: 🏆 CHIẾN THẦN - MUA MẠNH
- **A (70-84)**: ⭐ RẤT TỐT - MUA
- **B (55-69)**: ✅ TỐT - XEM XÉT MUA
- **C (40-54)**: ⚠️  TRUNG BÌNH - THẬN TRỌNG
- **D (<40)**: ❌ YẾU - TRÁNH

## 🔧 Architecture

### Separation of Concerns
- **Core**: Data fetching & constants
- **Analyzers**: Independent scoring modules
- **Scorer**: Orchestrates all analyzers
- **Utils**: Formatting & output

### Benefits
- ✅ Easy to test each module independently
- ✅ Easy to add new analyzers
- ✅ Clear dependencies
- ✅ Maintainable codebase (~100-200 lines per file)

## 📝 Adding New Analyzer

1. Create new file in `analyzers/`:
```python
# vnstock_analyzer/analyzers/risk.py
class RiskAnalyzer:
    def __init__(self, data):
        self.data = data
    
    def get_total_score(self):
        return {
            'total': 0,
            'max': 10,
            'breakdown': {...}
        }
```

2. Update `analyzers/__init__.py`:
```python
from .risk import RiskAnalyzer
__all__ = [..., 'RiskAnalyzer']
```

3. Use in `scorer.py`:
```python
risk = RiskAnalyzer(data)
risk_result = risk.get_total_score()
```

## 🎯 Future Enhancements

- [ ] Batch analysis (multiple stocks)
- [ ] Industry peer comparison
- [ ] Enhanced sentiment analysis (parse insider deals)
- [ ] News integration
- [ ] Caching layer (Redis/pickle)
- [ ] REST API (Flask/FastAPI)
- [ ] Web dashboard

## 📄 License

See LICENSE file in project root.
