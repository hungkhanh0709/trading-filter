# Kết luận Cuối cùng: Dữ liệu Khối Ngoại & Tự Doanh trong vnstock

**Ngày:** 31/01/2026  
**vnstock:** 3.4.0 (VCI, KBS sources)

---

## ❌ KẾT LUẬN: KHÔNG CÓ DATA MUA/BÁN RÒNG

### Dữ liệu vnstock CÓ:

| Field | Nguồn | Ý nghĩa | Hữu ích? |
|-------|-------|---------|----------|
| `foreign_volume` | VCI trading_stats | Tổng volume giao dịch của nước ngoài | ⚠️ **KHÔNG đủ** - không biết mua hay bán |
| `current_holding_ratio` | VCI trading_stats | % sở hữu hiện tại | ✅ Hữu ích - room ngoại |
| `max_holding_ratio` | VCI trading_stats | % tối đa cho phép | ✅ Hữu ích - room ngoại |
| `foreign_room` | VCI trading_stats | Room còn lại (shares) | ✅ Hữu ích |

### Dữ liệu vnstock KHÔNG CÓ:

| Cần | Trạng thái | Note |
|-----|-----------|------|
| `foreign_buy` (Khối ngoại mua) | ❌ Không có | Cần cho sentiment |
| `foreign_sell` (Khối ngoại bán) | ❌ Không có | Cần cho sentiment |
| `foreign_net` (Mua - Bán ròng) | ❌ Không có | **Quan trọng nhất!** |
| `proprietary_buy` (Tự doanh mua) | ❌ Không có | Bonus nếu có |
| `proprietary_sell` (Tự doanh bán) | ❌ Không có | Bonus nếu có |
| `proprietary_net` | ❌ Không có | Bonus nếu có |

---

## 🔍 Chi tiết Kiểm tra

### 1. VCI trading_stats()
```python
# CÓ:
foreign_volume: 3895601  # ← Tổng volume, không biết mua/bán

# KHÔNG CÓ:
foreign_buy: ???
foreign_sell: ???
foreign_net: ???  # ← CẦN CÁI NÀY!
```

### 2. Intraday data
```python
# Có match_type: Buy/Sell
# NHƯNG: Đó là tổng thị trường, không phân biệt investor type
Match types:
Sell: 59 trades
Buy: 40 trades
# ← Không biết trade nào là của foreign/proprietary
```

### 3. Price depth
```python
# Có acc_buy_volume, acc_sell_volume
# NHƯNG: Accumulated volume theo price, không theo investor type
```

### 4. Tất cả APIs khác
- ❌ quote.history() - Chỉ OHLCV cơ bản
- ❌ trading.price_board() - Error, không support
- ❌ company.* - Không có trading flow data
- ❌ KBS source - Giống VCI, không có

---

## ⚠️ VÍ DỤ MINH HỌA (VIC hôm nay)

### Thông tin vnstock cho:
```
VIC:
  foreign_volume: 3,895,601 (55.6% of total)
  current_holding: 3.02%
  
→ Tôi đã kết luận SAI: "Foreign đang tích cực mua!"
```

### Thực tế (theo bạn):
```
VIC:
  Khối ngoại BÁN MẠNH hôm nay
  
→ foreign_volume cao là do BÁN nhiều, KHÔNG phải mua!
```

### Vấn đề:
```
foreign_volume = foreign_buy + foreign_sell

VD có thể:
- foreign_buy: 500K
- foreign_sell: 3,395K
- foreign_net: -2,895K ← BÁN RÒNG MẠNH!

NHƯNG vnstock chỉ cho: foreign_volume = 3,895K
→ KHÔNG BIẾT CHIỀU MUA HAY BÁN!
```

---

## 💡 GIẢI PHÁP THAY THẾ

### Option 1: Sử dụng Web Scraping ⭐⭐⭐ (Recommended cho retail)

**Nguồn:**
- ✅ **cafe.vn** - Có data foreign buy/sell miễn phí
- ✅ **vietstock.vn** - Có bảng foreign/proprietary
- ✅ **SSI iBoard** (iboard.ssi.com.vn) - Chi tiết nhất
- ✅ **VPS SmartOne** - Có app/web

**Implementation:**
```python
# Example: Scrape từ cafe.vn
import requests
from bs4 import BeautifulSoup

def get_foreign_trading(symbol):
    url = f'http://s.cafef.vn/hose/{symbol}-ctck.chn'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Parse table foreign buy/sell
    # (Cần inspect HTML structure)
    
    return {
        'foreign_buy': ...,
        'foreign_sell': ...,
        'foreign_net': ...
    }
```

**Pros:**
- ✅ Miễn phí
- ✅ Data available
- ✅ Khá real-time (15-30 phút delay)

**Cons:**
- ⚠️ Cần maintain khi website thay đổi
- ⚠️ Legal grey area
- ⚠️ Rate limiting issues
- ⚠️ Có thể bị block

**Effort:** 2-3 ngày  
**Reliability:** 70%

---

### Option 2: Sử dụng SSI iBoard API ⭐⭐⭐⭐ (Best quality)

**Nguồn:** SSI iBoard (https://iboard.ssi.com.vn)

**Cách thức:**
1. Đăng ký tài khoản SSI (miễn phí)
2. Login vào iBoard
3. Inspect network requests → Tìm API endpoints
4. Reverse engineer API

**Data available:**
- ✅ Foreign buy/sell/net
- ✅ Proprietary buy/sell/net
- ✅ Real-time (delay ~5 phút)
- ✅ Historical data

**Pros:**
- ✅ Data chất lượng cao
- ✅ Chính thống từ CTCK lớn
- ✅ API structure ổn định hơn web scraping

**Cons:**
- ⚠️ Cần account SSI
- ⚠️ Unofficial API (có thể thay đổi)
- ⚠️ Rate limiting

**Effort:** 3-5 ngày (reverse engineering)  
**Reliability:** 85%

---

### Option 3: Paid API Service ⭐⭐⭐⭐⭐ (Professional)

**Providers:**
- **FiinTrade API** (~$100-200/month)
- **StockQ API** (~$50-100/month)
- **Vietstock API** (contact for pricing)

**Pros:**
- ✅ Official, documented
- ✅ Reliable
- ✅ Support available
- ✅ Legal

**Cons:**
- ❌ Chi phí hàng tháng
- ⚠️ Overkill cho project nhỏ

**Effort:** 1-2 ngày integration  
**Reliability:** 95%+

---

### Option 4: Manual Input ⭐ (Fallback)

**Cách thức:**
- User tự nhập foreign_buy/sell từ broker platform
- Store trong local database

**Pros:**
- ✅ No coding needed
- ✅ Accurate (if user inputs correctly)

**Cons:**
- ❌ Manual effort
- ❌ Không scalable
- ❌ Error-prone

---

## 🎯 KHUYẾN NGHỊ

### Ngắn hạn (1-2 tuần):

**KHÔNG THỰC HIỆN scoring foreign buy/sell**
- Lý do: Không có data đáng tin cậy từ vnstock
- Alternative: Chỉ dùng `current_holding_ratio` (room ngoại) như bạn đề xuất

**Giữ lại scoring room ngoại:**
```python
# GOOD - Data accurate
def _score_foreign_room(self):
    """
    Score dựa trên room ngoại còn lại
    
    Ý nghĩa: Room nhiều → Tiềm năng tăng trưởng ownership
    """
    ownership_pct = self.foreign_trading.get('current_holding_ratio', 0) * 100
    max_pct = self.foreign_trading.get('max_holding_ratio', 1) * 100
    
    room_pct = (max_pct - ownership_pct) / max_pct * 100 if max_pct > 0 else 0
    
    # Scoring: 5 points max
    if ownership_pct >= 40:
        score = 5  # High foreign confidence
    elif ownership_pct >= 30:
        score = 4
    elif ownership_pct >= 20:
        score = 3
    elif ownership_pct >= 10:
        score = 2
    else:
        score = 1
    
    # Warning nếu room thấp
    if room_pct < 10:
        reason = f"Foreign {ownership_pct:.1f}%, ⚠️ gần hết room"
    elif room_pct < 30:
        reason = f"Foreign {ownership_pct:.1f}%, room vừa phải"
    else:
        reason = f"Foreign {ownership_pct:.1f}%, ✅ room tốt"
    
    return {
        'ownership_pct': ownership_pct,
        'room_pct': room_pct,
        'score': score,
        'reason': reason
    }
```

### Dài hạn (1-2 tháng):

**Nếu cần foreign buy/sell data:**

1. **Evaluate use case:**
   - Bạn trade hàng ngày → Cần data real-time → Consider SSI API
   - Bạn invest dài hạn → Room ngoại đủ → Không cần buy/sell

2. **Nếu quyết định implement:**
   - Try cafe.vn scraping first (quickest)
   - If stable, keep it
   - If breaks often, upgrade to SSI API

3. **Priority:**
   - Phase 1: Fix critical issues (Sentiment, Financial Health)
   - Phase 2: Add room ngoại scoring (easy, data có sẵn)
   - Phase 3: Consider foreign buy/sell (nếu thực sự cần)

---

## 📊 REVISED SCORING MODEL

### Sentiment Analysis - 20 điểm

**WITHOUT foreign buy/sell (Current capability):**

| Component | Points | Data source | Status |
|-----------|--------|-------------|--------|
| Foreign Room | 5 | VCI trading_stats | ✅ Có data |
| News Sentiment | 10 | VCI company.news() | ⚠️ Limited (1 news) |
| Shareholder Structure | 5 | VCI company.shareholders() | ✅ Có data |

**Explanation:**
- **Foreign Room (5pts):** % sở hữu hiện tại vs max → Đo độ tin tưởng của NĐT ngoại
- **News (10pts):** Phân tích title của tin tức → Sentiment thị trường
- **Shareholder (5pts):** Tập trung ownership, institutional investors

**Total:** 20 điểm, achievable với data hiện có

---

## 📝 KẾT LUẬN

### ✅ CÓ THỂ LÀM (với vnstock):
1. **Foreign Room scoring** - Ownership ratio, room availability
2. **News Sentiment** - Title analysis (limited)
3. **Shareholder Analysis** - Major shareholders

### ❌ KHÔNG THỂ LÀM (với vnstock):
1. **Foreign buy/sell ròng** - Cần nguồn khác
2. **Proprietary trading** - Cần nguồn khác
3. **Real-time money flow** - Cần nguồn khác

### 🎯 KHUYẾN NGHỊ:
1. **Implement foreign room scoring** - Easy, data có sẵn, hữu ích
2. **Defer foreign buy/sell** - Chờ evaluate real need
3. **Focus on core issues** - Fix Sentiment, Financial Health trước

---

**Update CRITICAL_ISSUES_PLAN.md:**
- ✅ Giữ foreign room scoring (from trading_stats)
- ❌ Remove foreign buy/sell (không có data)
- ✅ Focus vào news + shareholders cho sentiment

**Expected impact:**
- Score improvement: +4-5 điểm (thay vì +6-7 như dự kiến ban đầu)
- Vẫn đủ để đạt 82-88/100 (S-tier target: 85+)
