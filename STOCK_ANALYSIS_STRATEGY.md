# CHIẾN LƯỢC PHÂN TÍCH VÀ ĐÁNH GIÁ CỔ PHIẾU "CHIẾN THẦN"

> **Mục tiêu**: Từ danh sách cổ phiếu thô (đã filter cơ bản), xây dựng hệ thống đánh giá đa chiều để tìm ra những cổ phiếu "mạnh nhất" - có khả năng bứt phá cao trong tương lai, đang ở chân sóng.

---

## 📊 I. TÌNH HÌNH HIỆN TẠI

### ✅ Đã có:
- **Lấy giá và % thay đổi**: `fetch_prices.py` - chỉ sử dụng `Quote.history()` để lấy OHLC cơ bản
- **Nguồn dữ liệu**: vnstock 3.x với source KBS
- **Filter cơ bản**: Có thể lọc theo các tiêu chí đơn giản

### ⚠️ Hạn chế:
- **Chỉ khai thác ~5% khả năng của vnstocks**
- Chưa có phân tích kỹ thuật (technical analysis)
- Chưa có phân tích cơ bản (fundamental analysis)
- Chưa có đánh giá động lực thị trường (market sentiment)
- Chưa có so sánh ngành và đối thủ

---

## 🎯 II. CÁC NGUỒN DỮ LIỆU VNSTOCK CÓ THỂ KHAI THÁC

### 1. **Quote Data** (Dữ liệu giá - Đã dùng một phần)
```python
stock = Vnstock().stock('ACB', source='KBS')
quote = stock.quote

# Những gì CÓ THỂ làm:
- quote.history()         # ✅ Đã dùng - OHLC lịch sử
- quote.intraday()        # ⭐ Chưa dùng - Giao dịch trong ngày
- quote.price_depth()     # ⭐ Chưa dùng - Sổ lệnh bid/ask
```

**Ứng dụng mới:**
- **Intraday**: Phân tích volume breakout trong ngày, money flow
- **Price depth**: Đo độ "khỏe" của giá - áp lực mua/bán thực tế

---

### 2. **Company Data** (Thông tin công ty - CHƯA dùng)
```python
company = stock.company

- company.overview()      # ⭐ Tổng quan công ty
- company.profile()       # ⭐ Thông tin chi tiết
- company.shareholders()  # ⭐ Cổ đông lớn - quan trọng!
- company.insider_deals() # ⭐ Giao dịch nội bộ - tín hiệu mạnh!
- company.officers()      # ⭐ Ban lãnh đạo
- company.news()          # ⭐ Tin tức công ty
- company.events()        # ⭐ Sự kiện quan trọng
```

**Ứng dụng mới:**
- **Insider deals**: Nội bộ mua vào = tín hiệu tích cực mạnh
- **Shareholders**: Sở hữu nước ngoài tăng = xu hướng tốt
- **Events**: Trả cổ tức, tăng vốn, họp ĐHCĐ = catalyst tăng giá

---

### 3. **Finance Data** (Báo cáo tài chính - CHƯA dùng)
```python
finance = stock.finance

- finance.balance_sheet()    # ⭐ Bảng cân đối kế toán
- finance.income_statement() # ⭐ Báo cáo kết quả KD
- finance.cash_flow()        # ⭐ Báo cáo lưu chuyển tiền tệ
- finance.ratio()            # ⭐ Chỉ số tài chính (PE, PB, ROE, ROA, EPS...)
```

**Ứng dụng mới:**
- **Ratio**: So sánh PE/PB với trung bình ngành → Tìm cổ phiếu undervalued
- **EPS growth**: Tăng trưởng lợi nhuận → Tiềm năng dài hạn
- **ROE/ROA**: Hiệu quả sử dụng vốn → Công ty chất lượng
- **Cash flow**: Dòng tiền dương mạnh → Bền vững

---

### 4. **Trading Data** (Dữ liệu giao dịch - CHƯA dùng)
```python
trading = stock.trading

- trading.price_board()   # ⭐ Bảng giá realtime nhiều mã
- trading.intraday_ohlc() # ⭐ OHLC trong ngày
```

**Ứng dụng mới:**
- **Volume pattern**: Khối lượng tăng đột biến = dòng tiền vào
- **Foreign trading**: Khối ngoại mua ròng = xu hướng tốt

---

### 5. **Listing Data** (Danh sách & phân nhóm)
```python
listing = Listing(source='KBS')

- listing.all_symbols()          # ⭐ Tất cả mã
- listing.symbols_by_industries() # ⭐ Theo ngành
- listing.symbols_by_exchange()   # ⭐ Theo sàn
- listing.symbols_by_group()      # ⭐ VN30, HNX30...
```

**Ứng dụng mới:**
- So sánh cổ phiếu với trung bình ngành
- Tìm leader trong từng ngành

---

### 6. **Screener** (TCBS - có thể bị giới hạn)
```python
from vnstock import Screener
screener = Screener(source='TCBS')
```
*Lưu ý: TCBS API có thể thay đổi, cân nhắc dùng*

---

## 🏆 III. CHIẾN LƯỢC ĐÁNH GIÁ CỔ PHIẾU "CHIẾN THẦN"

### A. MÔ HÌNH ĐÁNH GIÁ ĐA CHIỀU (Multi-Factor Scoring)

Mỗi cổ phiếu được chấm điểm trên **5 trụ cột chính**:

---

### **1. TECHNICAL STRENGTH (Kỹ thuật - 25 điểm)**

#### a. **Momentum & Trend (10đ)**
- **Xu hướng giá** (5đ):
  - MA crossover: MA5 > MA10 > MA20 > MA50 = +5
  - Giá > tất cả MA = +3
  - Giá > MA20 = +1
  
- **RSI & Oscillators** (5đ):
  - RSI 40-60 (oversold recovery zone) = +5
  - RSI 30-40 (strong oversold) = +3
  - RSI > 70 (overbought - cảnh báo) = +1

**Công thức tính từ `quote.history()`:**
```python
df['MA5'] = df['close'].rolling(5).mean()
df['MA10'] = df['close'].rolling(10).mean()
df['MA20'] = df['close'].rolling(20).mean()
df['MA50'] = df['close'].rolling(50).mean()

# RSI calculation
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))
```

---

#### b. **Volume Analysis (10đ)**
- **Volume breakout** (5đ):
  - Volume hôm nay > 1.5x trung bình 20 ngày = +5
  - Volume > trung bình 20 ngày = +3
  
- **Money Flow (Dòng tiền)** (5đ):
  - Tích lũy 5 ngày: Volume tăng + giá tăng = +5
  - OBV (On Balance Volume) tăng = +3

**Công thức:**
```python
df['vol_ma20'] = df['volume'].rolling(20).mean()
df['vol_ratio'] = df['volume'] / df['vol_ma20']

# OBV
df['OBV'] = (df['volume'] * (~df['close'].diff().le(0) * 2 - 1)).cumsum()
```

---

#### c. **Support & Resistance (5đ)**
- Giá đang ở vùng hỗ trợ mạnh = +5
- Vừa break khỏi resistance = +5
- Đang consolidate = +3

**Xác định:**
```python
# Tìm các pivot points (high/low gần nhất)
# Nếu giá gần pivot low (trong 5%) = support zone
# Nếu giá vừa vượt pivot high = breakout
```

---

### **2. FUNDAMENTAL QUALITY (Cơ bản - 25 điểm)**

#### a. **Valuation (Định giá - 10đ)**
```python
ratio = finance.ratio(period='quarter')

# PE Ratio
pe_industry_avg = get_industry_average_pe(symbol)  # Cần tính
if pe < pe_industry_avg * 0.8:  # Rẻ hơn ngành 20%
    score += 5
elif pe < pe_industry_avg:
    score += 3

# PB Ratio  
if pb < 1.5 and pb > 0.5:  # Sweet spot
    score += 5
```

**Tiêu chí:**
- PE < trung bình ngành = +5
- PB < 1.5 (không quá cao) = +3
- Dividend yield > 3% = +2

---

#### b. **Profitability (Khả năng sinh lời - 10đ)**
```python
# ROE - Return on Equity
if roe > 15:  # ROE tốt
    score += 5
elif roe > 10:
    score += 3

# ROA - Return on Assets
if roa > 8:
    score += 3

# EPS Growth (so với cùng kỳ năm trước)
eps_growth = (eps_current - eps_last_year) / eps_last_year
if eps_growth > 0.2:  # Tăng 20%
    score += 7
elif eps_growth > 0.1:
    score += 4
```

**Tiêu chí:**
- ROE > 15% = +5
- EPS tăng trưởng > 20% YoY = +7
- Profit margin cải thiện = +3

---

#### c. **Financial Health (Sức khỏe tài chính - 5đ)**
```python
# Debt to Equity
if debt_to_equity < 1:  # Nợ thấp
    score += 3

# Current Ratio
if current_ratio > 1.5:  # Thanh khoản tốt
    score += 2
```

**Tiêu chí:**
- Debt/Equity < 1 = +3
- Current ratio > 1.5 = +2

---

### **3. MARKET SENTIMENT (Tâm lý thị trường - 20 điểm)**

#### a. **Insider Activity (10đ)**
```python
insider = company.insider_deals()

# Nội bộ mua ròng trong 3 tháng gần nhất
if insider_net_buy > 0:
    score += 10  # Tín hiệu Cực mạnh!
```

**Tiêu chí:**
- Lãnh đạo/HĐQT mua vào = +10 (rất quan trọng!)
- Không có bán tháo nội bộ = +5

---

#### b. **Foreign Ownership (5đ)**
```python
shareholders = company.shareholders()

# Sở hữu nước ngoài
foreign_ownership = get_foreign_ownership(shareholders)
if foreign_ownership_increasing:  # Tăng so với quý trước
    score += 5
```

**Tiêu chí:**
- Tỷ lệ sở hữu NN tăng = +5
- Tổ chức lớn mua vào = +3

---

#### c. **News & Events (5đ)**
```python
news = company.news()
events = company.events()

# Tin tích cực gần đây (30 ngày)
if positive_news_count > negative_news_count:
    score += 3

# Sự kiện sắp tới (trả cổ tức, tăng vốn...)
if upcoming_dividend or upcoming_stock_split:
    score += 5
```

**Tiêu chí:**
- Tin tích cực > tin tiêu cực = +3
- Có sự kiện catalyst sắp tới = +5

---

### **4. LIQUIDITY & TRADING (Thanh khoản - 15 điểm)**

#### a. **Volume Consistency (10đ)**
```python
# Volume trung bình 3 tháng
avg_vol_3m = df['volume'].tail(60).mean()

if avg_vol_3m > 500_000:  # 500k shares/day
    score += 10
elif avg_vol_3m > 200_000:
    score += 6
```

**Tiêu chí:**
- Volume trung bình > 500k cp/ngày = +10
- Không có ngày volume = 0 trong 20 ngày = +5

---

#### b. **Spread & Volatility (5đ)**
```python
# Độ biến động hợp lý
volatility_20d = df['close'].pct_change().tail(20).std()

if 0.02 < volatility_20d < 0.05:  # 2-5% volatility
    score += 5
```

**Tiêu chí:**
- Volatility vừa phải (2-5%) = +5
- Spread bid/ask < 1% = +3

---

### **5. SECTOR & RELATIVE STRENGTH (So sánh ngành - 15 điểm)**

#### a. **Industry Performance (10đ)**
```python
# So sánh performance với ngành
industry_symbols = listing.symbols_by_industries()
industry_return = calculate_industry_avg_return(industry_symbols)
stock_return = calculate_stock_return(symbol)

if stock_return > industry_return * 1.2:  # Outperform 20%
    score += 10
elif stock_return > industry_return:
    score += 6
```

**Tiêu chí:**
- Outperform ngành > 20% (3 tháng) = +10
- Leader trong ngành (top 3 về growth) = +5

---

#### b. **Market Cap Position (5đ)**
```python
# Ưu tiên mid-cap có tiềm năng
market_cap = get_market_cap(symbol)

if 1_000 < market_cap < 20_000:  # 1-20 tỷ USD (mid-cap)
    score += 5
elif market_cap > 20_000:  # Large cap - ổn định nhưng ít growth
    score += 3
```

**Tiêu chí:**
- Mid-cap (1-20B) với growth cao = +5
- Large-cap ổn định = +3

---

## 📈 IV. HỆ THỐNG PHÂN CẤP & ĐIỂM SỐ

### **Tổng điểm tối đa: 100 điểm**

| Hạng        | Điểm        | Đánh giá                           |
|-------------|-------------|------------------------------------|
| **S Tier**  | 85-100      | 🏆 CHIẾN THẦN - Mua ngay           |
| **A Tier**  | 70-84       | ⭐ RẤT TỐT - Ưu tiên cao            |
| **B Tier**  | 55-69       | ✅ TỐT - Xem xét                    |
| **C Tier**  | 40-54       | ⚠️  TRUNG BÌNH - Thận trọng         |
| **D Tier**  | < 40        | ❌ YẾU - Tránh xa                   |

---

## 🛠️ V. KẾ HOẠCH THỰC HIỆN

### **Phase 1: Core Data Collection (Tuần 1)**
✅ **Module 1: Enhanced Quote Analysis**
```python
# File: services/technical_analyzer.py
class TechnicalAnalyzer:
    def calculate_ma_score(df)
    def calculate_rsi_score(df)
    def calculate_volume_score(df)
    def calculate_support_resistance_score(df)
```

✅ **Module 2: Financial Analysis**
```python
# File: services/fundamental_analyzer.py
class FundamentalAnalyzer:
    def get_valuation_score(symbol)
    def get_profitability_score(symbol)
    def get_financial_health_score(symbol)
```

---

### **Phase 2: Sentiment & Market Data (Tuần 2)**
✅ **Module 3: Market Sentiment**
```python
# File: services/sentiment_analyzer.py
class SentimentAnalyzer:
    def get_insider_score(symbol)
    def get_foreign_ownership_score(symbol)
    def get_news_events_score(symbol)
```

✅ **Module 4: Liquidity & Trading**
```python
# File: services/liquidity_analyzer.py
class LiquidityAnalyzer:
    def get_volume_score(symbol)
    def get_volatility_score(symbol)
```

---

### **Phase 3: Comparative Analysis (Tuần 3)**
✅ **Module 5: Industry Comparison**
```python
# File: services/industry_analyzer.py
class IndustryAnalyzer:
    def get_industry_performance_score(symbol)
    def get_relative_strength_score(symbol)
    def get_market_position_score(symbol)
```

---

### **Phase 4: Integration & Scoring (Tuần 4)**
✅ **Main Scoring Engine**
```python
# File: services/stock_scorer.py
class StockScorer:
    def __init__(self):
        self.technical = TechnicalAnalyzer()
        self.fundamental = FundamentalAnalyzer()
        self.sentiment = SentimentAnalyzer()
        self.liquidity = LiquidityAnalyzer()
        self.industry = IndustryAnalyzer()
    
    def calculate_total_score(self, symbol):
        """Tính tổng điểm từ 5 trụ cột"""
        scores = {
            'technical': self.technical.get_total_score(symbol),      # 25đ
            'fundamental': self.fundamental.get_total_score(symbol),  # 25đ
            'sentiment': self.sentiment.get_total_score(symbol),      # 20đ
            'liquidity': self.liquidity.get_total_score(symbol),      # 15đ
            'industry': self.industry.get_total_score(symbol)         # 15đ
        }
        return sum(scores.values()), scores
```

---

### **Phase 5: API & Frontend (Tuần 5)**
✅ **Enhanced API Endpoints**
```javascript
// server.js mở rộng
app.post('/api/analyze-stocks', async (req, res) => {
    const { symbols } = req.body;
    const results = [];
    
    for (const symbol of symbols) {
        const score = await stockScorer.calculate_total_score(symbol);
        results.push({
            symbol,
            totalScore: score.total,
            breakdown: score.details,
            tier: getTier(score.total),
            recommendation: getRecommendation(score.total)
        });
    }
    
    // Sắp xếp theo điểm
    results.sort((a, b) => b.totalScore - a.totalScore);
    res.json(results);
});
```

✅ **Enhanced Frontend**
```html
<!-- public/index.html - Thêm tab mới -->
<div id="champion-stocks">
    <h2>🏆 Danh Sách Chiến Thần</h2>
    <table>
        <thead>
            <tr>
                <th>Hạng</th>
                <th>Mã CP</th>
                <th>Điểm</th>
                <th>Kỹ Thuật</th>
                <th>Cơ Bản</th>
                <th>Tâm Lý</th>
                <th>Thanh Khoản</th>
                <th>So Sánh</th>
                <th>Khuyến Nghị</th>
            </tr>
        </thead>
        <tbody id="champion-list"></tbody>
    </table>
</div>
```

---

## 🎯 VI. MỤC TIÊU CUỐI CÙNG

### **Input:**
Danh sách 50-100 mã cổ phiếu đã qua filter cơ bản

### **Output:**
```json
[
    {
        "symbol": "ACB",
        "totalScore": 92,
        "tier": "S",
        "breakdown": {
            "technical": 23,
            "fundamental": 22,
            "sentiment": 18,
            "liquidity": 14,
            "industry": 15
        },
        "highlights": [
            "RSI đang ở vùng oversold recovery (45)",
            "Nội bộ mua ròng 2M cổ phiếu trong 3 tháng",
            "EPS tăng 35% YoY",
            "Volume breakout 2.5x trung bình"
        ],
        "recommendation": "MUA MẠNH - Tiềm năng breakout cao",
        "risk_level": "Trung bình",
        "target_price": 28500,
        "stop_loss": 23000
    },
    // ... top 20 chiến thần
]
```

---

## 📊 VII. CHỈ SỐ THEO DÕI HIỆU QUẢ

Sau khi triển khai, theo dõi:

1. **Accuracy Rate**: % cổ phiếu S/A tier thực sự tăng sau 1-3 tháng
2. **False Positive**: % cổ phiếu được đánh giá cao nhưng giảm
3. **Correlation**: Tương quan giữa điểm số và performance thực tế

**Target KPI:**
- Accuracy > 70% cho S tier (3 tháng)
- Accuracy > 60% cho A tier

---

## 🔄 VIII. CẢI TIẾN LIÊN TỤC

### **Học máy & AI (Phase 6 - Tương lai)**
- Sử dụng ML để tối ưu trọng số các yếu tố
- Phân tích sentiment từ tin tức tự động (NLP)
- Pattern recognition cho chart analysis
- Backtest chiến lược với dữ liệu lịch sử

---

## 📝 IX. LƯU Ý QUAN TRỌNG

1. **Không có chiến lược nào 100% chính xác**
   - Luôn đa dạng hóa danh mục
   - Quản lý rủi ro: không all-in 1 mã
   
2. **Kết hợp phân tích thủ công**
   - Hệ thống là công cụ hỗ trợ, không thay thế quyết định
   - Đọc báo cáo tài chính thực tế của top picks
   
3. **Cập nhật dữ liệu thường xuyên**
   - Chạy phân tích hàng tuần
   - Cập nhật ngưỡng điểm dựa trên kết quả thực tế

4. **Tuân thủ kỷ luật giao dịch**
   - Set stop-loss rõ ràng
   - Take profit theo kế hoạch
   - Không FOMO khi bỏ lỡ

---

## 🚀 X. KẾT LUẬN

Chiến lược này kết hợp:
- ✅ **Technical Analysis** (20+ chỉ báo)
- ✅ **Fundamental Analysis** (10+ ratio tài chính)
- ✅ **Market Sentiment** (insider, foreign flow, news)
- ✅ **Liquidity & Trading** (volume, volatility)
- ✅ **Relative Strength** (so sánh ngành)

→ **Tạo ra một hệ thống đánh giá toàn diện, khoa học, có thể backtest và cải tiến liên tục.**

**Next Steps:**
1. ✅ Review và approve chiến lược này
2. 🔨 Bắt đầu code Module 1: TechnicalAnalyzer
3. 🧪 Test với 10 mã cổ phiếu mẫu
4. 📊 Đánh giá kết quả và điều chỉnh

---

*Được tạo bởi GitHub Copilot - Phân tích dựa trên vnstock 3.x capabilities*
*Ngày: 31/01/2026*
