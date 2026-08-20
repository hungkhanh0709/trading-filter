# Triple EMA Potential Monitor

Ứng dụng quan sát cổ phiếu Việt Nam bằng giá và EMA10/20/50. Tab `POTENTIAL` hiển thị toàn bộ universe rồi xếp hạng bằng hệ sao cộng dồn; không lọc hoặc ẩn mã.

## Khởi động

Yêu cầu Python 3.10+ và Node.js.

```bash
npm install
.venv/bin/python -m pip install -r requirements.txt
npm start
```

Mở `http://localhost:3000`.

## Potential

Sáu tiêu chí, mỗi tiêu chí đúng cộng `1★`:

1. Perfect Order: EMA10 > EMA20 > EMA50.
2. Golden Cross EMA20/50 trong tối đa 5 phiên; EMA10/20 chỉ để quan sát.
3. Bandwidth EMA10/20/50 không quá 1%.
4. Perfect Order + pullback gần EMA10.
5. Perfect Order + pullback đạt tầng EMA20.
6. Perfect Order + pullback đạt tầng EMA50.

Ba tầng pullback chỉ cộng sao khi đã có Perfect Order. Hệ thống chọn EMA gần giá nhất rồi cộng dồn theo tầng; đạt EMA50 nhận cả ba sao EMA10/20/50. Chi tiết ngưỡng và contract nằm trong [docs/potential.md](docs/potential.md).

## Dữ liệu và API

- `GET /api/symbols?exchange=POTENTIAL`: toàn bộ mã VN30, VN100, HNX30 và watch list, đã khử trùng lặp.
- `GET /api/symbols?exchange=WATCHLIST|VN30|VN100|HNX30`: universe tương ứng.
- `GET /api/analyze/:symbol`: giá đã chuẩn hoá bước giá và phân tích EMA.
- `GET /api/analyze/:symbol?force=1`: bỏ qua cache phân tích trong bộ nhớ.
- `POST /api/analysis-jobs`: khởi tạo hàng đợi phân tích chạy phía server, không bị dừng khi tab trình duyệt xuống nền.

Mỗi mã có hard timeout mặc định 120 giây để một request bị treo không chặn toàn bộ hàng đợi. Có thể thay đổi bằng biến môi trường `ANALYSIS_TIMEOUT_MS`.

Server dùng một Python worker lâu dài thay vì khởi động lại Python cho từng mã. Chi phí import pandas, khởi tạo `vnstock/vnai` và cache Matplotlib chỉ xảy ra một lần lúc `npm start`.

Mỗi mã tải 250 phiên: đủ để phần ảnh hưởng của SMA seed lên EMA50 giảm xuống dưới 0,1%, đồng thời tránh payload dư thừa của cửa sổ 500 phiên.

Mỗi lần gọi nguồn dữ liệu có timeout mặc định 8 giây (`VNSTOCK_REQUEST_TIMEOUT_SECONDS`). App gọi VCI một lần rồi chuyển sang KBS, tránh lớp retry 30 giây × 3 của `Quote.history` giữ cả hàng đợi quá lâu.

Khi một nguồn lỗi network, worker tạm bỏ qua nguồn đó trong 5 phút (`VNSTOCK_SOURCE_COOLDOWN_SECONDS`) để các mã kế tiếp không lặp lại cùng một timeout.

Watch list có dạng:

```json
{
  "HOSE": "VCB,BID,CTG,TCB",
  "HNX": "IDC,PVS"
}
```

## Kiểm thử

```bash
npm test
.venv/bin/python -m unittest discover -s tests -v
```

Source chính:

- `server.js`: API và cache.
- `public/index.html`: Vue/Vuetify UI.
- `public/potential-ranker.js`: tiêu chí sao và thứ tự hiển thị.
- `vnstock_analyzer/`: lấy dữ liệu, chuẩn hoá bước giá và tính EMA.
