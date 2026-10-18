# File mẫu để PM review A15/B15

Các file được tạo bằng request qua Django API thực với CSRF bật, trên SQLite tạm mới và dữ liệu seed hoàn toàn giả. Không dùng database hiện tại hoặc lưu mật khẩu/token QR trong mẫu. Database tạm đã được dọn sau kiểm chứng.

## Mở và đối chiếu

- [attendance-demo.xlsx](attendance-demo.xlsx): ba sheet Chi_tiet, Tong_hop, Thong_tin.
- [attendance-demo.csv](attendance-demo.csv): UTF-8 BOM, cùng 10 dòng chi tiết và giờ Việt Nam như XLSX.
- [summary-demo.json](summary-demo.json): kết quả API tổng hợp.
- [detail-demo.json](detail-demo.json): chi tiết snapshot và metadata API.
- [reconciliation-demo.json](reconciliation-demo.json): kết quả đối soát, danh sách bước và HTTP status; không chứa mật khẩu/token.

Ngày mô phỏng: 12/10/2026, lớp DEMO10A. Giờ được kiểm soát trong kiểm chứng, không đổi đồng hồ hệ thống.

| Chỉ số | Kết quả |
| --- | --- |
| Học sinh-buổi | 10 |
| Có mặt / vắng / chưa ghi nhận | 2 / 8 / 0 |
| Đúng giờ / muộn | 1 / 1 |
| Đồng phục đạt / không đạt / chưa kiểm tra | 1 / 1 / 0 |
| Tỷ lệ có mặt | 20% |
| Tỷ lệ đi muộn trong số có mặt | 50% |
| Vi phạm trong số đã kiểm tra | 50% |
| Độ bao phủ kiểm tra đồng phục | 100% |

Học sinh 01 quét lúc 07:04, nhân sự xác minh lúc 07:08; giờ đến vẫn là 07:04 và ON_TIME. Học sinh 02 ghi thủ công đến 07:10, LATE, có lý do và đồng phục không đạt. Học sinh 03 có scan PENDING nhưng chưa xác minh; chốt chuyển scan EXPIRED, không cộng PRESENT. Tám học sinh UNMARKED chuyển ABSENT.

Đã mở lại XLSX/CSV từ file lưu và đối chiếu **tất cả** dòng chi tiết với API, cùng toàn bộ chỉ số sheet Tong_hop với summary JSON. Học sinh xuất báo cáo bị 403; giáo viên B xuất lớp A bị 403; giám thị thấy tổng đúng; sau logout đọc báo cáo bị 401.

Mẫu này bổ sung bằng chứng A15/B15, không tự phê duyệt API gate. PM xem [API acceptance](../../../api-acceptance.md), nhận xét và xác nhận gate trước A16/B16.
