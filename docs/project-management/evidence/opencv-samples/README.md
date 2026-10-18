# Mẫu báo cáo vision — dữ liệu giả

Sinh bằng `.document-tools/verify_opencv.py` trên DB tạm: login/CSRF,3ảnh texture đăng ký,
scan chỉ PENDING, staff confirm, retry, manual fallback, uniform và close.
Chỉ detector dương được mock; LBPH/HSV, service, transaction, quyền và xuất file thật.
Không phải kết quả camera/người thật hoặc đo độ chính xác.

- 3roster;2PRESENT/1ABSENT;1VISION/1MANUAL.
- 1đúng giờ/1muộn;1đồng phục đạt/1không đạt.
- JSON chi tiết/tổng hợp, XLSX và CSV đã được mở lại/đối chiếu.
- VISION có giờ đến bằng giờ quét server. Không có crop/frame/password/token.

Các UUID sinh ngẫu nhiên chỉ định danh dữ liệu giả trong DB tạm đã dọn.
Chạy lại script sẽ sinh mẫu/ngày/UUID mới. Nguồn backend/db.sqlite3 được giữ nguyên.
