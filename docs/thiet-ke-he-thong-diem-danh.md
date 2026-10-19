# Thiết kế MVP điểm danh học sinh — Python/Django + OpenCV

**Phiên bản 1.5 — 19/10/2026.** Người dùng yêu cầu “hoàn thành task theo plan” sau khi chốt đúng mẫu đồng phục trường bằng bộ ảnh riêng. Phạm vi theo [thiết kế](superpowers/specs/2026-10-18-auto-attendance-uniform-crud-design.md) và [plan](superpowers/plans/2026-10-18-auto-attendance-uniform-crud.md). [v1.4](archive/thiet-ke-he-thong-diem-danh-v1.4.md), v1.3 và v1.2 giữ nguyên làm lịch sử. Yêu cầu mới cho phép tự ghi PRESENT khi đủ điều kiện, thay quy tắc bắt buộc xác nhận danh tính của v1.4 ở luồng tự động. **API_Gate=NOT_APPROVED** là phê duyệt PM riêng, không đồng nghĩa quyền triển khai đã được người dùng cấp.

## 1. Mục tiêu và giới hạn

Nhân sự chọn lớp/buổi OPEN, bật camera và lần lượt cho học sinh vào khung thấy mặt cùng phần áo. Server nhận diện mặt đủ điều kiện thì ghi có mặt và giờ đến, không xác nhận từng em. Mục **Đồng phục** riêng dùng chung camera controller, xử lý người đã có mặt; chế độ chỉ kiểm tra áo không tạo điểm danh mới. Giáo viên xử lý danh sách nghi vi phạm, ghi lý do hoặc sửa cảnh báo sai. Không nhận diện được có nhập thủ công.

Giữ tài khoản/session/CSRF, khối/lớp/GVCN, hồ sơ/ảnh private, lịch/buổi sáng chiều, snapshot, attendance, audit/version/idempotency, CSV/XLSX tối đa 5.000 dòng. GVCN chỉ lớp hiện tại được giao, giám thị toàn phạm vi; STUDENT chỉ đọc bản thân, identity từ session. Không thêm đăng nhập bằng mặt, liveness/chống ảnh giả được bảo đảm, AI cloud, SMS, phụ huynh, cloud storage, worker/queue hay module duyệt sửa. Preview camera ở browser, chỉ gửi cặp ảnh rời, không stream/lưu video.

## 2. Kiến trúc và phân công

Python 3.12/Django 5.2, ORM/Auth/Forms/JsonResponse, SQLite demo, Pillow/OpenCV contrib headless/NumPy/openpyxl. Không DRF. Cookie HttpOnly, CSRF mọi request ghi, UUID; Asia/Ho_Chi_Minh và UTC lưu trữ. Dependency runtime khóa tại requirements/pyproject. Torch/torchvision/ONNX chỉ môi trường train offline riêng, không vào runtime Vercel.

| Owner | Phạm vi |
| --- | --- |
| Member 1 | accounts, academics, students/ảnh, CRUD UI, reports/export, UI ghi lý do |
| Member 2 | schedules/roster, attendance, vision/face/uniform/camera, QR legacy |
| Chung | core/config/enums/contracts, migration liên app và review tích hợp |

QR_ENABLED=false mặc định; giữ lịch sử QR/LBPH/CONFIRMED. API mở rộng đọc; PATCH/DELETE lớp/học sinh yêu cầu expected_version. [Contract](api-contract.md) là giao diện dùng chung.

## 3. CRUD lớp và học sinh

Lớp có mã/tên/khối/GVCN, sức chứa 1–50 (mặc định 50), active/version. Sĩ số active và tổng hồ sơ tính từ danh sách thật, không nhận student_count client. Giám thị tạo/sửa/lưu trữ/khôi phục lớp; GVCN đọc lớp được giao. Không giảm sức chứa dưới sĩ số active hoặc lưu trữ lớp còn học sinh active/buổi OPEN.

Học sinh có mã/tên/lớp/active/version, ảnh hồ sơ và enrollment riêng. GVCN tạo/sửa tên/trạng thái trong lớp; giám thị sửa mã/chuyển lớp với kiểm tra nguồn/đích/sức chứa. Xóa là lưu trữ, restore phải kiểm tra active/capacity. Đổi mã/tên/lớp không viết lại snapshot lịch sử; inactive/transfer loại khỏi nhận diện mới và vô hiệu proposal chờ. Ảnh/export/read/write đều kiểm tra role scope server.

Roster tạo khi OPEN từ học sinh active. Học sinh mới mặc định vào buổi mở sau. Giám thị có thao tác riêng bổ sung vào buổi OPEN: thêm duy nhất roster+UNMARKED, version/audit/capacity; không rebuild hay sửa hàng cũ.

## 4. Mẫu mặt và tự điểm danh

Enrollment 3–10 ảnh riêng, đúng một mặt rõ nét. Lưu private crop BGR 112×112 PNG và embedding chuẩn hóa 128 float32 little-endian (512 byte), model_key=sface-2021dec-fp32. Không endpoint byte mẫu mặt. Mỗi ảnh 2 MiB/4 MP, tổng local 15 MiB, Vercel 3 MiB. Mẫu legacy phải đăng ký lại.

YuNet2023mar phát hiện 5 landmark; SFace2021dec FP32 so cosine đúng roster. Cosine không phải xác suất. Model pinned revision/hash, license/ghi công tại backend/third_party/opencv_zoo. Chuẩn bị model trước request; không download lúc nhận diện. Thiếu/hỏng model báo 503. Không tuyên bố tự huấn luyện YuNet/SFace.

Tự động nhận đúng hai ảnh khác nhau cùng request, mỗi ảnh ≤1 MiB/4 MP, tổng ≤2 MiB. Cả hai đúng một mặt rõ và cùng ứng viên. Ngưỡng auto khởi đầu cosine≥0.60, margin≥0.15; cần calibration bằng ảnh ngoài enrollment. Không mặt/nhiều mặt/mờ/người lạ/ứng viên khác nhau thì không ghi. Hai ảnh chỉ kiểm tra nhất quán, không chứng minh người thật.

Preview local liên tục, tối đa một cặp/4 giây, không chồng request; quota 20 cặp/phút/actor trong cache process, 429 có Retry-After. Dừng khi tab ẩn, đổi trang/lớp/buổi/logout/mất camera. Inference ngoài transaction ghi; ngay trước atomic write kiểm tra lại scope, buổi OPEN đúng ngày/giờ, lớp active/version, roster/học sinh active/lớp hiện tại, mẫu/profile snapshot và attendance version. Scope trước idempotency replay; retry không nhân bản bản ghi, không đổi giờ đến đầu, không đè MANUAL/ABSENT/CLOSED.

PRESENT tự động có source=VISION, recognition_mode=AUTO, recorded_by là người vận hành camera; verified_by/verified_at=null. VisionScan AUTO_RECORDED khác CONFIRMED cũ. Luồng proposal/confirm v1.4 vẫn tương thích có chủ ý với ngưỡng 0.45/0.10; không lấy ngưỡng đó dùng cho auto. Không lưu frame/video/ảnh trong audit.

## 5. Đồng phục đúng trường

HSV chỉ gợi ý legacy, không chứng minh mẫu/logo trường. Profile theo lớp có version ONNX bất biến; buổi OPEN đóng băng snapshot, selection mới áp dụng buổi mới. Giám thị quản lý dataset SHIRT/SPORTS/OTHER tách FaceSample. Ảnh gốc có mặt trên ROI áo, chỉ crop áo được lưu private; detector kiểm tra mặt và nhân sự phải xem lại crop vì phát hiện không bảo đảm tuyệt đối. Không dùng tên/ID học sinh làm capture_group. Chia train/val/test theo người/buổi, không rò ảnh augment.

Quy trình offline: export private → kiểm manifest/hash/group split → train/fine-tune model nhẹ → test độc lập/OpenCV ONNX parity/latency → review logo/mẫu, đồng phục trường khác màu tương tự và che logo → import artifact/hash/evidence → chọn profile. Không train trong request, không worker. MobileNetV3-Small là baseline cần đo, không phải model trường có sẵn. Không publish dataset/model/review private lên GitHub. Hiện chưa có bộ ảnh trường; không đánh dấu nghiệm thu model chỉ vì có tooling.

| Kết quả | Trạng thái | Giáo viên |
| --- | --- | --- |
| Hai ảnh rõ, nhất quán đúng yêu cầu buổi, model đủ điều kiện | COMPLIANT, uniform_source=AUTO | Không cần xác nhận |
| Có bằng chứng, model tự tin sai mẫu/loại | REVIEW_REQUIRED | Ghi lý do để NON_COMPLIANT hoặc sửa cảnh báo sai |
| Thiếu model/thân áo, chưa rõ/không nhất quán | NOT_CHECKED, UNKNOWN | Chụp lại hoặc kiểm tra thủ công |

NON_COMPLIANT bắt buộc lý do nhân sự nhập. Không tự tạo lý do như thể giáo viên đã xác nhận. Quyết định thủ công có checked_by/uniform_source=MANUAL, không bị auto đè. Báo cáo tách REVIEW_REQUIRED/NOT_CHECKED khỏi vi phạm đã xác nhận.

## 6. Demo, nghiệm thu và bằng chứng

UI có tổng quan, điểm danh tự động, Đồng phục, lớp, học sinh/enrollment và báo cáo. Vercel demo dùng SQLite /tmp từng instance, có thể mất/lệch dữ liệu giữa request; không cam kết chia sẻ DB hay exactly-once toàn deployment. Vận hành thật cần DB dùng chung trong scope riêng. Model/dataset local không tự xuất hiện trên Vercel; thiếu model giữ Chưa kiểm tra. Người dùng tự deploy, lượt này không deploy.

Nghiệm thu cần test role/CSRF/private ảnh, version/retry/concurrency/rollback, migration DB cũ, lịch sử, browser/camera và ảnh ngoài enrollment. Công bố precision/recall/coverage/UNKNOWN, số test và latency; synthetic/mocked workflow tests không chứng minh độ chính xác. Mục tiêu đề xuất uniform precision≥95% chỉ có ý nghĩa trên tập đã khai báo kèm coverage. Task thiếu bộ ảnh trường phải giữ chưa nghiệm thu. PM/API_Gate và validation kỹ thuật ghi riêng trong tracker/evidence.
