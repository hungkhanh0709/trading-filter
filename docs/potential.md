# Potential — additive star observation

`Potential` hiện là bảng quan sát toàn bộ mã, không phải bộ lọc và không phải tín hiệu mua/bán. Không mã đã phân tích nào bị ẩn. Mã có nhiều tiêu chí thuận lợi hơn chỉ được xếp lên trên.

## Sáu tiêu chí cộng sao

Mỗi tiêu chí đạt được cộng đúng `1★`; không có điểm âm, hệ số, hard gate hay điều kiện loại:

1. Perfect Order: EMA10 > EMA20 > EMA50.
2. Golden Cross EMA20/50 mới xuất hiện trong tối đa 5 phiên.
3. Cụm EMA10/20/50 rất chặt: bandwidth không quá 1%.
4. Giá pullback gần EMA10.
5. Giá pullback đạt tầng EMA20.
6. Giá pullback đạt tầng EMA50.

Pullback là thang cộng dồn. Gần EMA10 nhận một sao; đạt EMA20 nhận cả sao EMA10 và EMA20; đạt EMA50 nhận đủ ba sao EMA10, EMA20 và EMA50. “Gần” nghĩa là giá đóng cửa nằm từ 0,5% dưới đến 1,5% trên EMA tương ứng. EMA được quy về bước giá giao dịch khi so sánh.

Các trường volume, momentum, market breadth, Death Cross, tuổi Perfect Order và trạng thái nến không tham gia cộng/trừ sao ở giai đoạn quan sát này.

Golden Cross EMA10/20 vẫn được hiển thị như dữ liệu chẩn đoán trên bảng, nhưng không cộng sao `Potential`. Chỉ giao cắt EMA20 đi lên EMA50 mới đạt tiêu chí Golden Cross vì đây là xác nhận xu hướng đáng tin cậy hơn.

## Hiển thị và sắp xếp

- Mọi mã từ universe `POTENTIAL` đều hiển thị, kể cả `0★` và mã chưa phân tích.
- Sắp xếp mặc định theo số sao giảm dần.
- Nếu bằng sao, sắp theo mã alphabet; không dùng tiêu chí ngầm để phá hoà.
- Tooltip liệt kê đủ sáu tiêu chí bằng `★/☆`, giúp đối chiếu trực tiếp với chart.

## Kiểm thử

```bash
npm test
.venv/bin/python -m unittest discover -s tests -v
```
