# API acceptance — OpenCV v1.3

Kiểm chứng UI mới: [153test + browser/desktop/mobile và review](project-management/evidence/ui-demo/README.md). Đã ghi rõ các fixture/sự cố được mô phỏng, không coi đó là kết quả camera vật lý.

**API_Gate = NOT_APPROVED**. Đây là hồ sơ chờ PM/member review; không tự tick Finish?. Ngoại lệ ngày18/10/2026: người dùng yêu cầu rõ “làm luôn UI để demo”, cho phép UI local trước gate. Đây không phải phê duyệt PM API; API_Gate vẫn NOT_APPROVED và Finish? không tự thay đổi. [Acceptance v1.2](archive/api-acceptance-v1.2.md) và 126 test QR cũ là evidence lịch sử, không phải kết quả hiện tại.

Kiểm chứng kỹ thuật mới: [149test + migrate/CSRF/export và review](project-management/evidence/opencv-backend.md), [log tái lập](project-management/evidence/opencv-validation.txt), [XLSX/CSV/JSON vision giả](project-management/evidence/opencv-samples/README.md). Đây là bằng chứng backend tổng hợp; thiết bị thật/accuracy/PM review còn chờ.

| Phạm vi | Evidence phải đọc/chạy |
| --- | --- |
| Auth/scope/CSRF | GVCN khác lớp, STUDENT, tài khoản inactive, logout; ảnh/mẫu/queue/scan/confirm/reject/report/export không vượt quyền |
| Enrollment | 3–10 ảnh nguyên tử, byte/MP/tổng limit, zero/multi/blur, metadata không bytes, DELETE/re-enroll vô hiệu proposal |
| Engine | Real LBPH/HSV trên fixture có kiểm soát, match/unknown/ambiguous, torso clipped; phân biệt mock detector với camera thật |
| Scan | OPEN/đúng ngày/start_at≤now≤close_at (biên inclusive)/roster≤50; multipart một ảnh, limit20/phút cố định/actor/cache từng process; PENDING không PRESENT; expiry120s |
| Confirm/reject | Xác minh người trực tiếp bắt buộc; version/sample revision; key/retry/conflict; invalid uniform rollback; manual/close/transfer vô hiệu |
| Reports/export | VISION arrived_at từ scanned_at; chỉ attendance đã ghi; đối soát JSON/XLSX/CSV cùng bộ lọc và mở lại file |
| Regression/migrations | check, full suite, migrate DB mới và nâng cấp schema v1.2, makemigrations --check, pip check; QR mặc định tắt, legacy bật rõ trong test |
| Demo | Checklist ánh sáng/người lạ/ảnh giả/mạng/camera/manual; kết quả thật có người review, không suy accuracy từ synthetic |

Chạy hướng dẫn [demo](huong-dan-demo-opencv.md) trên DB thử riêng. Ghi command, ngày, exit code, test count, giới hạn synthetic/mocking và file log trong docs/project-management/evidence; root agent cung cấp evidence kỹ thuật mới sau validation. PM đọc implementation và evidence mới, ghi PM Comment/Evidence vào tracker, xác nhận các task API trước khi quyết định gate. Không xem file skeleton hoặc checkbox có sẵn là test đạt.

SQLite/cache local phục vụ demo nhỏ; chưa chứng minh tải nhiều process/toàn trường. HSV chỉ đo màu vùng áo, không nhận dạng đồng phục đầy đủ. Chưa có accuracy/liveness/camera thật được xác nhận. Không deploy/chia sẻ ngoài. UI local tại `/` đã triển khai bằng Django shell/CSS/JS, dùng API hiện có; cần kiểm chứng browser riêng, không coi sự tồn tại template/static là UI đã đạt.

- PM/member review: chờ.
- API_Gate: NOT_APPROVED.
- UI local: được người dùng cho phép trước gate;153test và browser/desktop/mobile đã có evidence riêng; thiết bị thật/accuracy còn chờ.
- Finish?: giữ chưa hoàn tất cho tới khi có đủ implementation + validation + review.
