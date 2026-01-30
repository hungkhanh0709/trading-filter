# Kế hoạch Khắc phục Các Vấn đề Nghiêm trọng

## Tóm tắt Hiện trạng

**Điểm tối đa hiện tại:** 74-79/100 (không đạt S-tier 85+)

**Vấn đề chính:**
- ❌ SentimentAnalyzer: Chỉ placeholder, thiếu 9-14 điểm
- ❌ FundamentalAnalyzer Financial Health: D/E và Current Ratio không hoạt động, thiếu 5 điểm
- ⚠️ IndustryAnalyzer: Thiếu peer comparison, thiếu ~7 điểm

---

## Phần 1: Xác định Data Availability (HOÀN TẤT)

### ✅ APIs có sẵn trong vnstock 3.4.0:

| API | Trạng thái | Columns | Use Case |
|-----|-----------|---------|----------|
| `company.shareholders()` | ✅ Available | name, update_date, shares_owned, ownership_percentage | Foreign ownership |
| `company.news()` | ✅ Available | head, article_id, title, publish_time, url | News sentiment |
| `finance.ratio()` | ✅ Available | item_id (có `owners_equity`) | Tính toán ratios |
| `finance.balance_sheet()` | ✅ Available | 77 items bao gồm assets, liabilities | Fallback cho D/E |

### ❌ APIs KHÔNG tồn tại:

| API | Status | Impact |
|-----|--------|--------|
| `company.insider_deals()` | ❌ Not available | Không thể phân tích insider trading |
| `company.events()` | ⚠️ Empty (0 rows) | Không có sự kiện doanh nghiệp |

### 📊 Ratio API - Item IDs Available:

```python
# Trong ratio dataframe có:
- owners_equity              # Có thể dùng
- equitydeposits_from_customers  
- equitytotal_assets         # Có thể dùng

# KHÔNG TÌM THẤY:
- debt_equity_ratio
- current_ratio
- total_debt
- total_liabilities
```

### ⚠️ Kết luận:
**Phải dùng `balance_sheet()` để tính D/E ratio thủ công**

---

## Phần 2: Vấn đề Nghiêm trọng #1 - SentimentAnalyzer (Thiếu 9-14 điểm)

### 2.1. Root Cause Analysis

**File:** [vnstock_analyzer/analyzers/sentiment.py](vnstock_analyzer/analyzers/sentiment.py)

**Vấn đề:**
```python
# Current code - PLACEHOLDER ONLY
def _parse_insider_activity(self):
    return {
        'net_buying': 0,
        'recent_purchases': 0,
        'score': 5  # ← HARDCODED, không parse thật
    }
```

**Impact:**
- Insider Activity: 5/10 điểm (default) thay vì 0-10 dựa trên data
- Foreign Ownership: 3/5 điểm (default) thay vì parse thật
- News Sentiment: 3/5 điểm (default) thay vì phân tích
- **Tổng thiếu:** 9-14 điểm tiềm năng

### 2.2. Implementation Plan - DETAILED

#### Task 2.1: Fix Foreign Ownership Scoring (Priority: HIGH)

**Timeline:** 2 hours

**Input:** `shareholders` DataFrame
```python
# Structure confirmed:
columns: ['name', 'update_date', 'shares_owned', 'ownership_percentage']
# Sample:
                     name  ownership_percentage
0             CTCP Sovico                  9.99
1            Phạm Văn Đẩu                  4.28
```

**Algorithm:**
```python
def _parse_foreign_ownership(self, shareholders):
    """
    Điểm số: 5 points max
    - Foreign ownership > 30%: 5 pts (Very positive)
    - 20-30%: 4 pts
    - 10-20%: 3 pts  
    - 5-10%: 2 pts
    - < 5%: 1 pt
    """
    if shareholders is None or len(shareholders) == 0:
        return {'percentage': 0, 'score': 0}
    
    # Keywords to detect foreign investors
    foreign_keywords = [
        'nước ngoài',  # Vietnamese
        'foreign',
        'international',
        'global',
        'fund',
        'capital',
        # Add specific fund names
        'dragon',
        'vfmvn',
        'diamond'
    ]
    
    total_foreign = 0
    foreign_investors = []
    
    for _, row in shareholders.iterrows():
        name_lower = str(row['name']).lower()
        
        # Check if name contains foreign keywords
        if any(keyword in name_lower for keyword in foreign_keywords):
            ownership = float(row['ownership_percentage'])
            total_foreign += ownership
            foreign_investors.append({
                'name': row['name'],
                'ownership': ownership
            })
    
    # Calculate score
    if total_foreign >= 30:
        score = 5
    elif total_foreign >= 20:
        score = 4
    elif total_foreign >= 10:
        score = 3
    elif total_foreign >= 5:
        score = 2
    else:
        score = 1
    
    return {
        'percentage': round(total_foreign, 2),
        'foreign_investors': foreign_investors,
        'score': score
    }
```

**Testing:**
```bash
# Test với HDB (có foreign funds)
python scripts/analyze_stock.py HDB

# Expected: Foreign ownership > 0%, score > 0
```

---

#### Task 2.2: Implement News Sentiment Analysis (Priority: MEDIUM)

**Timeline:** 4 hours (include rate limiting)

**Input:** `news` DataFrame
```python
# Structure confirmed:
columns: ['head', 'article_id', 'title', 'publish_time', 'url']
# Note: Only 1 recent news returned
```

**Challenges:**
- ⚠️ News API chỉ trả về 1 tin gần nhất
- ⚠️ Không có content, chỉ có title
- ⚠️ Cần phân tích sentiment từ title

**Algorithm - Simplified Version:**
```python
def _parse_news_sentiment(self, news):
    """
    Điểm số: 5 points max (giảm từ 10 do data hạn chế)
    
    Chỉ phân tích title do không có content.
    """
    if news is None or len(news) == 0:
        return {'recent_count': 0, 'positive_count': 0, 'score': 0}
    
    # Positive keywords (Vietnamese)
    positive_keywords = [
        'tăng trưởng', 'lợi nhuận', 'tích cực', 'khả quan',
        'thành công', 'mở rộng', 'phát triển', 'đột phá',
        'growth', 'profit', 'positive', 'successful'
    ]
    
    # Negative keywords
    negative_keywords = [
        'giảm', 'sụt giảm', 'thua lỗ', 'tiêu cực', 'khó khăn',
        'rủi ro', 'cảnh báo', 'decline', 'loss', 'negative', 'risk'
    ]
    
    recent_count = len(news)
    positive_count = 0
    negative_count = 0
    
    for _, row in news.iterrows():
        title = str(row['title']).lower()
        
        has_positive = any(kw in title for kw in positive_keywords)
        has_negative = any(kw in title for kw in negative_keywords)
        
        if has_positive and not has_negative:
            positive_count += 1
        elif has_negative and not has_positive:
            negative_count += 1
    
    # Simple scoring: 5 pts if positive, 0 if negative, 2.5 neutral
    if positive_count > negative_count:
        score = 5
    elif negative_count > positive_count:
        score = 0
    else:
        score = 2.5
    
    return {
        'recent_count': recent_count,
        'positive_count': positive_count,
        'negative_count': negative_count,
        'score': score
    }
```

**⚠️ Limitation:**
Do API chỉ trả về 1 news, chúng ta giảm weight từ 10 → 5 điểm.

---

#### Task 2.3: Handle Insider Activity Absence (Priority: HIGH)

**Problem:** API `insider_deals()` không tồn tại

**Solution Options:**

**Option A: REMOVE COMPLETELY** ✅ RECOMMENDED
```python
# Adjust scoring weights:
OLD:
- Insider Activity: 10 points
- Foreign Ownership: 5 points  
- News Sentiment: 5 points
TOTAL: 20 points

NEW:
- Foreign Ownership: 10 points (tăng từ 5)
- News Sentiment: 10 points (tăng từ 5)
TOTAL: 20 points
```

**Option B: Use Shareholder Changes (Complex)**
```python
# Phân tích thay đổi ownership qua thời gian
# Cần cache historical data
# ⚠️ Phức tạp, chưa cần thiết
```

**Decision:** Chọn Option A - đơn giản, minh bạch

**Implementation:**
```python
# vnstock_analyzer/analyzers/sentiment.py

def get_total_score(self):
    """Calculate total sentiment score: 20 points max"""
    
    # REMOVED: insider activity
    foreign_score = self.foreign_ownership.get('score', 0) * 2  # x2 to scale 5→10
    news_score = self.news_sentiment.get('score', 0) * 2       # x2 to scale 5→10
    
    total = foreign_score + news_score
    
    return {
        'total_score': total,
        'max_score': 20,
        'breakdown': {
            'foreign_ownership': foreign_score,  # 0-10
            'news_sentiment': news_score         # 0-10
        }
    }
```

---

### 2.3. Testing Strategy for Sentiment

```bash
# Test 1: Foreign ownership detection
python -c "
from vnstock_analyzer import StockScorer
scorer = StockScorer('HDB')
result = scorer.analyze()
print(f'Foreign score: {result[\"sentiment\"][\"breakdown\"][\"foreign_ownership\"]}/10')
"

# Expected: > 0 (HDB có foreign funds)

# Test 2: Multiple stocks
for symbol in HDB VNM VCB FPT; do
    echo "=== $symbol ==="
    python scripts/analyze_stock.py $symbol | grep -A 5 "SENTIMENT"
done
```

---

## Phần 3: Vấn đề Nghiêm trọng #2 - Financial Health (Thiếu 5 điểm)

### 3.1. Root Cause Analysis

**File:** [vnstock_analyzer/analyzers/fundamental.py](vnstock_analyzer/analyzers/fundamental.py#L120-L135)

**Current Code:**
```python
def _score_financial_health(self):
    # D/E ratio
    de_ratio = self.ratios.get('debt_equity_ratio', None)  # ← Always None
    
    # Current ratio
    current_ratio = self.ratios.get('current_ratio', None) # ← Always None
    
    # Result: 0/5 points always
```

**Debug Results:**
```python
# ratio API có:
- owners_equity
- equitytotal_assets
# KHÔNG CÓ:
- debt_equity_ratio ❌
- current_ratio ❌
```

### 3.2. Solution: Use Balance Sheet

**Data Available in `balance_sheet()`:**
```
assets                              # A. TÀI SẢN
liabilities                         # B. NỢ PHẢI TRẢ  
owners_equity                       # C. VỐN CHỦ SỞ HỮU
current_assets                      # Tài sản ngắn hạn
current_liabilities                 # Nợ ngắn hạn
```

**Implementation:**

```python
# vnstock_analyzer/core/data_fetcher.py

def fetch_all_data(self):
    """Add balance_sheet to fetched data"""
    data = {
        # ... existing fields ...
        'balance_sheet': self._fetch_balance_sheet()  # ← NEW
    }
    return data

def _fetch_balance_sheet(self):
    """Fetch balance sheet data"""
    try:
        bs = self.stock.finance.balance_sheet(period='quarter')
        return self._parse_balance_sheet_to_dict(bs)
    except Exception as e:
        print(f"Error fetching balance sheet: {e}")
        return {}

def _parse_balance_sheet_to_dict(self, bs_df):
    """
    Parse balance sheet pivot format to dict.
    Structure: item_id as keys, latest quarter as values
    """
    if bs_df is None or len(bs_df) == 0:
        return {}
    
    result = {}
    latest_quarter_col = bs_df.columns[-1]  # Last column = latest data
    
    for _, row in bs_df.iterrows():
        item_id = row['item_id']
        value = row[latest_quarter_col]
        
        # Convert to float
        try:
            result[item_id] = float(value) if pd.notna(value) else None
        except:
            result[item_id] = None
    
    return result
```

**Update FundamentalAnalyzer:**

```python
# vnstock_analyzer/analyzers/fundamental.py

class FundamentalAnalyzer:
    def __init__(self, overview, ratios, balance_sheet):  # ← Add param
        self.overview = overview
        self.ratios = ratios
        self.balance_sheet = balance_sheet  # ← NEW
        
    def _calculate_debt_equity_ratio(self):
        """
        Calculate D/E from balance sheet.
        D/E = Total Liabilities / Owners Equity
        """
        liabilities = self.balance_sheet.get('liabilities')
        equity = self.balance_sheet.get('owners_equity')
        
        if liabilities and equity and equity != 0:
            return liabilities / equity
        return None
    
    def _calculate_current_ratio(self):
        """
        Calculate Current Ratio from balance sheet.
        Current Ratio = Current Assets / Current Liabilities
        """
        current_assets = self.balance_sheet.get('current_assets')
        current_liabilities = self.balance_sheet.get('current_liabilities')
        
        if current_assets and current_liabilities and current_liabilities != 0:
            return current_assets / current_liabilities
        return None
    
    def _score_financial_health(self):
        """
        Score financial health: 5 points max
        - D/E Ratio: 2.5 points (lower is better)
        - Current Ratio: 2.5 points (higher is better)
        """
        score = 0
        
        # D/E Ratio scoring
        de_ratio = self._calculate_debt_equity_ratio()
        if de_ratio is not None:
            if de_ratio < 0.5:
                score += 2.5  # Excellent
            elif de_ratio < 1.0:
                score += 2.0  # Good
            elif de_ratio < 1.5:
                score += 1.5  # Fair
            elif de_ratio < 2.0:
                score += 1.0  # Concerning
            else:
                score += 0.5  # High risk
        
        # Current Ratio scoring
        current_ratio = self._calculate_current_ratio()
        if current_ratio is not None:
            if current_ratio >= 2.0:
                score += 2.5  # Excellent
            elif current_ratio >= 1.5:
                score += 2.0  # Good
            elif current_ratio >= 1.0:
                score += 1.5  # Fair
            elif current_ratio >= 0.8:
                score += 1.0  # Concerning
            else:
                score += 0.5  # Poor liquidity
        
        return {
            'de_ratio': de_ratio,
            'current_ratio': current_ratio,
            'score': score
        }
```

**Update scorer.py:**

```python
# vnstock_analyzer/scorer.py

def analyze(self):
    # Fetch data
    data = self.data_fetcher.fetch_all_data()
    
    # Initialize analyzers with balance_sheet
    fundamental = FundamentalAnalyzer(
        data['overview'],
        data['ratios'],
        data['balance_sheet']  # ← Add parameter
    )
```

### 3.3. Testing

```python
# Test balance sheet parsing
from vnstock import Vnstock

stock = Vnstock().stock('HDB', source='KBS')
bs = stock.finance.balance_sheet(period='quarter')

print('Latest quarter:', bs.columns[-1])
print('Liabilities:', bs[bs['item_id'] == 'liabilities'].iloc[0][bs.columns[-1]])
print('Equity:', bs[bs['item_id'] == 'owners_equity'].iloc[0][bs.columns[-1]])
```

**Expected output:**
```
D/E Ratio: 8.5 (banks typically high)
Current Ratio: N/A (banks don't have traditional current assets)
Score: 0.5-1.0/5 for banks
```

---

## Phần 4: Vấn đề Trung bình - Industry Comparison (Thiếu ~7 điểm)

### 4.1. Current State

**File:** [vnstock_analyzer/analyzers/industry.py](vnstock_analyzer/analyzers/industry.py#L50-L60)

```python
def _score_industry_performance(self):
    # PLACEHOLDER
    return {
        'industry_avg_score': 50,
        'relative_performance': 0,
        'score': 5  # ← HARDCODED
    }
```

### 4.2. Implementation Complexity

**Challenge:**
- Cần fetch data cho TẤT CẢ stocks trong cùng industry
- Risk: Rate limiting (VD: Ngân hàng có 30+ stocks)
- Time consuming: ~30 API calls × 2-3s = 1-2 phút

**Solution Options:**

**Option A: DEFER TO LATER** ✅ RECOMMENDED
- Priority thấp hơn Sentiment và Financial Health
- Chỉ thiếu ~7 điểm, ít impact hơn
- Cần caching strategy phức tạp

**Option B: Implement với Sampling**
```python
# Chỉ compare với top 10 stocks trong industry by market cap
# Reduces API calls từ 30+ → 10
```

**Decision:** DEFER - focus vào 2 issues nghiêm trọng hơn trước

---

## Phần 5: Timeline & Priority

### Phase 1: Critical Fixes (Week 1-2) ⚡ HIGH PRIORITY

**Week 1:**
- ✅ [DONE] Data investigation
- [ ] Task 2.1: Foreign Ownership parsing (2h)
- [ ] Task 2.2: News Sentiment parsing (4h)
- [ ] Task 2.3: Remove Insider Activity, adjust weights (1h)
- [ ] Update constants.py weights (30min)

**Week 2:**
- [ ] Task 3: Balance Sheet integration (3h)
- [ ] Task 3: D/E and Current Ratio calculation (2h)
- [ ] Testing với 10 stocks (HDB, VCB, FPT, VNM, HPG, etc.) (4h)
- [ ] Fix bugs phát hiện (2-4h)

**Deliverable:** Score tăng từ 74-79 → 85-90 (đạt S-tier)

### Phase 2: Enhancement (Week 3) - OPTIONAL

- [ ] Industry Comparison với sampling approach
- [ ] Cache strategy cho industry data
- [ ] Tune thresholds dựa trên backtesting

### Phase 3: Validation (Week 4)

- [ ] Backtest với 50-100 stocks
- [ ] Compare với market performance
- [ ] Document edge cases

---

## Phần 6: Expected Score Improvement

### Before Fixes:
```
Technical:     20-25/25  ✅ Working
Fundamental:   15-20/25  ⚠️ Missing 5 (Financial Health)
Sentiment:      6-11/20  ❌ Mostly placeholder
Liquidity:     13-15/15  ✅ Working
Industry:       8-10/15  ⚠️ Missing 5-7 (Comparison)
─────────────────────────
TOTAL:         62-81/100 (avg ~74)
MAX TIER:      B (55-69) or A (70-84)
```

### After Critical Fixes (Phase 1):
```
Technical:     20-25/25  ✅ Working
Fundamental:   20-25/25  ✅ FIXED (Balance Sheet)
Sentiment:     14-18/20  ✅ FIXED (Foreign + News, no insider)
Liquidity:     13-15/15  ✅ Working
Industry:       8-10/15  ⚠️ Still missing comparison
─────────────────────────
TOTAL:         75-93/100 (avg ~85)
MAX TIER:      S (85-100) ✅ ACHIEVABLE
```

### After All Enhancements (Phase 2+3):
```
TOTAL:         85-98/100
TIER:          S consistently
```

---

## Phần 7: Risk Mitigation

### Risk 1: API Rate Limiting
**Mitigation:**
- Add delays between API calls (1-2s)
- Cache data aggressively
- Batch processing với retry logic

### Risk 2: Data Quality Issues
**Mitigation:**
- Extensive null checking
- Fallback values
- Log warnings cho missing data

### Risk 3: Balance Sheet Format Changes
**Mitigation:**
- Test với multiple stocks
- Handle missing item_ids gracefully
- Document assumptions

---

## Phần 8: Implementation Checklist

### SentimentAnalyzer Fix:
- [ ] Update `_parse_foreign_ownership()` với keyword detection
- [ ] Implement `_parse_news_sentiment()` với title analysis
- [ ] Remove `_parse_insider_activity()`
- [ ] Update `get_total_score()` với new weights (10+10)
- [ ] Update constants.py SENTIMENT_WEIGHTS
- [ ] Test với 5 stocks

### FundamentalAnalyzer Fix:
- [ ] Add `balance_sheet` parameter to `__init__()`
- [ ] Implement `_calculate_debt_equity_ratio()`
- [ ] Implement `_calculate_current_ratio()`
- [ ] Update `_score_financial_health()` với new calculations
- [ ] Update DataFetcher với `_fetch_balance_sheet()`
- [ ] Update StockScorer to pass balance_sheet
- [ ] Test với bank stocks (HDB, VCB) - high D/E expected
- [ ] Test với non-bank (FPT, VNM) - normal D/E expected

### Documentation:
- [ ] Update README.md với new scoring breakdown
- [ ] Document API limitations (no insider_deals, limited news)
- [ ] Add examples cho edge cases
- [ ] Update STOCK_ANALYSIS_STRATEGY.md với revised approach

---

## Phần 9: Success Criteria

**Must Have (Phase 1):**
- ✅ Foreign ownership parsing hoạt động với accuracy > 90%
- ✅ D/E và Current Ratio tính toán đúng (validate bằng manual check)
- ✅ Sentiment score khác nhau giữa các stocks (không phải hardcoded)
- ✅ Đạt S-tier cho stocks chất lượng cao (VD: VNM, VCB)

**Nice to Have (Phase 2+):**
- Industry comparison với top 10 peers
- News sentiment phân tích content (nếu API support)
- Historical trend analysis

---

## Tổng kết

**Ưu tiên:**
1. **CRITICAL:** Fix Financial Health (5 điểm) - Week 1
2. **CRITICAL:** Fix Sentiment Analysis (9-14 điểm) - Week 1-2
3. **MEDIUM:** Industry Comparison (7 điểm) - Week 3+

**Timeline:** 2-3 tuần cho Phase 1 (critical fixes)

**Impact:** Tăng điểm từ 74 → 85+ (đạt S-tier)

**Risk:** Thấp - đã xác định data availability, implementation straightforward
