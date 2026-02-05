# 📊 Stock Filter - Watch List Tracker

Web app đơn giản hiển thị danh sách mã cổ phiếu theo dõi, với đánh dấu VN30/VN100 và link TradingView.

## ✨ Tính năng

- ✅ Hiển thị danh sách mã cổ phiếu theo ngày
- ✅ Đánh dấu VN30/VN100 bằng icon
- ✅ Link trực tiếp tới TradingView chart
- ✅ Chọn ngày xem data lịch sử
- ✅ UI Material Design hiện đại (Vuetify 3)
- ✅ Tìm kiếm nhanh
- ✅ Thống kê: tổng số mã, số mã VN30/VN100
- ✅ Hỗ trợ cả HOSE và HNX
- ✅ Watch List tùy chỉnh (thêm mã thủ công)

## 🚀 Sử dụng

### Khởi động

```bash
npm start
```

Mở trình duyệt: **http://localhost:3000**

## 📝 Quản lý Watch List

### Thêm mã vào Watch List

Chỉnh sửa file `data/watch-list.json`:

```json
[
  {
    "date": "20260201",
    "HOSE": "ACB,BID,VTP,SAB,HPG,MBB,VCB",
    "HNX": "IDC,PVS"
  }
]
```

**Lưu ý:**
- Format ngày: `YYYYMMDD` (VD: `20260201`)
- Mã HOSE và HNX tách riêng
- Các mã cách nhau bằng dấu phẩy
- File được sort theo ngày giảm dần (mới nhất trên cùng)

### Tabs hiển thị

- **Watch List**: Tất cả mã trong watch-list.json
- **HOSE**: Chỉ mã sàn HOSE
- **HNX**: Chỉ mã sàn HNX
- **VN30**: 30 mã blue-chip HOSE
- **VN100**: 100 mã lớn nhất HOSE

## 📁 Cấu trúc Files

```
trading-filter/
├── server.js              # Express backend
├── package.json           
├── data/
│   ├── vn30.json         # Danh sách VN30 (reference)
│   ├── vn100.json        # Danh sách VN100 (reference)
│   └── watch-list.json   # Watch List - EDIT thủ công
└── public/
    └── index.html         # Vue 3 + Vuetify 3 UI
```

### File Purposes

**`watch-list.json`** - Danh sách theo dõi:
- ✅ SAFE to edit manually
- ✅ Organized by date
- ✅ Hỗ trợ cả HOSE và HNX
- ✅ Có thể thêm mã ngoài VN30/VN100

**`vn30.json` / `vn100.json`** - Reference lists:
- ✅ Danh sách official VN30/VN100
- ✅ Dùng để đánh dấu trong UI
- ❌ Không cần edit thường xuyên

## 🔧 API Endpoints

### `GET /api/stocks?exchange=WATCHLIST`
Trả về data Watch List

### `GET /api/stocks?exchange=VN30`
Trả về data VN30 với status từ watch-list.json

### `GET /api/stocks?exchange=VN100`
Trả về data VN100 với status từ watch-list.json

### `GET /api/analyze/:symbol`
Phân tích kỹ thuật cho một mã

## 💡 Tips

### Theo dõi mã mới:
1. Mở `data/watch-list.json`
2. Thêm mã vào HOSE hoặc HNX
3. Save
4. Refresh page
5. Done! ✅

### Xem lịch sử:
- Matrix table hiển thị lịch sử nhiều ngày
- Mỗi cột là một ngày
- ✅ = có mặt, 🆕 = mới xuất hiện

### Phân tích kỹ thuật:
- Click icon 📊 "Phân tích tất cả"
- Hoặc click "Phân tích" trên từng mã
- Kết quả: MA analysis, convergence, momentum

## 🎨 UI Features

- **Stats cards:** Ngày, Tổng mã, VN30, VN100
- **Matrix view:** Lịch sử nhiều ngày
- **VN30/VN100 badges:** Đánh dấu rõ ràng
- **TradingView link:** Xem chart trực tiếp
- **Analysis:** Phân tích MA, convergence, momentum
- **Search:** Tìm kiếm nhanh theo mã
- **Responsive:** Mobile-friendly

## 🔮 Future Features

- [ ] Calendar view để duyệt lịch sử
- [ ] So sánh giữa các ngày
- [ ] Capture screenshot TradingView
- [ ] Export Excel/PDF
- [ ] Chart xu hướng xuất hiện của mã

---

*Built with Node.js, Express, Vue 3, Vuetify 3*
*Last updated: January 19, 2026*
