# Thiết kế MVP điểm danh học sinh — Python/Django + OpenCV

**Phiên bản 1.4 — 18/10/2026.** Người dùng đã duyệt YuNet + SFace FP32 thay Haar/LBPH; [v1.3](archive/thiet-ke-he-thong-diem-danh-v1.3.md) và Word v1.3 được giữ nguyên làm lịch sử. Nguồn chuẩn theo yêu cầu thay QR bằng nhận diện mặt và gợi ý đồng phục, đã được người dùng cho triển khai (“làm đi”). Bản [v1.2](archive/thiet-ke-he-thong-diem-danh-v1.2.md) được lưu nguyên trạng để đối chiếu. Đề xuất [OpenCV](de-xuat-opencv-demo.md) là quyết định phạm vi, không phải bằng chứng chạy thành công. API_Gate = **NOT_APPROVED**; không tự đánh dấu Finish?. Ngoại lệ ngày18/10/2026: người dùng yêu cầu rõ “làm luôn UI để demo”, cho phép UI local trước gate. Đây không phải phê duyệt PM API; API_Gate vẫn NOT_APPROVED và Finish? không tự thay đổi.

## 1. Mục tiêu và giới hạn

GVCN/giám thị chọn buổi học thuộc quyền, gửi ảnh một người, xem ứng viên nhận diện và gợi ý đồng phục, xác minh trực tiếp rồi xác nhận. Chỉ bước xác nhận hợp lệ mới ghi PRESENT qua service attendance. Có đường nhập thủ công khi camera lỗi, không có mẫu hoặc thuật toán không chắc chắn. Không tự nhận diện để cấp quyền đăng nhập hay kết luận học sinh vi phạm.

Giữ tài khoản/session/CSRF; khối/lớp/một GVCN; học sinh/mã/họ tên/ảnh private; lịch tuần và buổi sáng/chiều; giờ bắt đầu/cutoff/đồng phục snapshot; roster khi mở buổi; manual/PRESENT/ABSENT/UNMARKED; đồng phục; version/idempotency/log; báo cáo và XLSX/CSV tối đa 5.000 dòng. Giáo viên chỉ lớp hiện tại được giao, giám thị toàn bộ; học sinh chỉ đọc phạm vi bản thân, không enroll/analyze/confirm/reject. Danh tính học sinh đăng nhập luôn lấy từ session, không body.

OpenCV cục bộ là ngoại lệ mới được cho phép so với giới hạn không camera/nhận diện của v1.2. Không có liveness/khả năng chống ảnh giả được bảo đảm. Không thêm nhận diện cloud, dịch vụ AI ngoài, video liên tục, SMS, phụ huynh, workers, queues, cloud storage, module duyệt sửa, nhiều trường hoặc tải toàn trường. Hàng đợi scan là danh sách proposal DB đồng bộ, không phải worker queue.

## 2. Kiến trúc và phân công

Một project Django, Python 3.12/Django 5.2, ORM/Auth/Forms/JsonResponse, SQLite demo nhỏ, Pillow/OpenCV contrib headless/NumPy/openpyxl. Không DRF; phiên cookie HttpOnly, CSRF cho mọi request ghi; UUID; timezone Asia/Ho_Chi_Minh, lưu UTC. Phiên bản dependency khóa tại backend/requirements.txt.

| Owner | Phạm vi |
| --- | --- |
| mem1 | accounts, academics, students, ảnh hồ sơ, reports/export; review scope và đăng ký/xóa mẫu của học sinh |
| mem2 | schedules, attendance, vision (mẫu private/proposal/engine), QR legacy |
| Phối hợp | core/config/enums/contracts và migration chéo trước khi đổi interface; xem kế hoạch OpenCV |

Giữ schema/migrations/dữ liệu QR cũ, không xóa lịch sử. QR không còn là đường đi demo hoạt động: QR_ENABLED=false mặc định; bật tương thích có chủ ý chỉ cho regression QR lịch sử. AttendanceSource bổ sung VISION cùng MANUAL và QR lịch sử. Hợp đồng chi tiết ở [api-contract.md](api-contract.md); trình tự migration/kiểm chứng ở [kế hoạch](superpowers/plans/2026-10-18-opencv-demo.md).

## 3. Mẫu nhận diện và ảnh

Ảnh hồ sơ không tự trở thành mẫu sinh trắc. Nhân sự có quyền đăng ký 3–10 ảnh bằng field multipart `images` lặp; thay toàn bộ nguyên tử, lỗi một ảnh giữ bộ cũ. Mỗi ảnh tối đa 2MiB/4MP, tổng enrollment tối đa 15MiB; phải có đúng một mặt, đủ độ nét. Lưu crop màu BGR căn chỉnh112x112 dạng PNG và embedding chuẩn hóa128float32 little-endian (512byte), model_key=sface-2021dec-fp32 trong BinaryField DB private, không endpoint byte, không public media URL, không log ảnh/base64. GET trả metadata/student_id/sample_count/usable_sample_count/requires_reenrollment/model_key, không byte mẫu (sample revision là nội bộ), DELETE xóa mẫu. Không lưu frame phân tích/video; proposal chỉ metadata và phiên bản liên quan. Bản sao lưu DB chứa mẫu private cũng phải được kiểm soát và xóa theo quy trình dữ liệu cục bộ.

Thuật toán demo: YuNet2023mar phát hiện5landmark, SFace2021dec FP32 căn chỉnh mặt màu112x112, embedding128chiều và so cosine trong đúng roster. MODEL_KEY=sface-2021dec-fp32; VISION_FACE_MIN_COSINE=0.45, VISION_FACE_MIN_COSINE_MARGIN=0.10, VISION_MIN_SHARPNESS=50. Cosine càng cao càng giống, không phải xác suất; metric=cosine và distance=1-cosine. Lịch sử LBPH vẫn metric=lbph_distance, không so trực tiếp hai metric. Mẫu grayscale128x128 cũ cần đăng ký lại3–10ảnh màu, không tự chuyển đổi hoặc nạp ảnh mạng. Metadata usable_sample_count chỉ số mẫu đúng model; requires_reenrollment báo bộ cũ chưa đủ3mẫu dùng được. Cần hiệu chỉnh bằng bộ ảnh đánh giá tách bộ đăng ký. Không có mặt/nhiều mặt/mờ/người lạ/ứng viên sát nhau → không có proposal đủ điều kiện xác nhận danh tính; chụp lại hoặc manual.

Models pin revision/SHA-256, chuẩn bị bằng `manage.py prepare_vision_models` trước các lệnh chạy nhận diện hoặc launcher tự chuẩn bị; request không tải network. Thiếu/hỏng model báo VISION_UNAVAILABLE503. Giữ license/ghi công YuNet MIT và SFace Apache2.0 tại backend/third_party/opencv_zoo; không tuyên bố tự huấn luyện model. Nâng DB local có backup và migrate, không seed lại tài khoản/dữ liệu hiện tại; đăng nhập tài khoản cũ và enrollment lại ít nhất3ảnh.

HSV trên vùng áo chỉ gợi ý SHIRT/SPORTS/UNKNOWN theo dải màu cấu hình (mặc định trắng SHIRT, xanh SPORTS). Đây là heuristic màu, không nhận biết logo/chất liệu/đồng phục thật. Áo bị che, crop thiếu thân, nền nhiễu hoặc màu không trội → UNKNOWN. Nhân sự quyết định kết quả đồng phục và lý do; không tự chuyển UNKNOWN thành COMPLIANT/NON_COMPLIANT.

## 4. Luồng nghiệp vụ và đồng thời

1. Nhân sự đăng nhập; chọn session OPEN đúng ngày và `start_at <= now <= close_at` (kể cả hai biên), đúng lớp thuộc quyền; roster tối đa 50 học sinh cho phân tích demo.
2. Gửi một multipart `image` cùng Idempotency-Key. Kiểm tra quyền, dữ liệu ảnh và rate limit 20 analysis/phút/actor theo phút cố định trong cache từng process trước phân tích (không rolling/global). Trả PENDING hoặc kết quả cần chụp lại/chuyển manual; tuyệt đối không ghi PRESENT khi scan.
3. Proposal lưu scanned_at server, hết hạn sau 120 giây, ràng buộc sample revision và attendance version. Client không gửi student_id để chọn danh tính scan.
4. Nhân sự xem người thực tế, bắt buộc `identity_confirmed=true`, gửi expected_scan_version và expected_attendance_version; có thể kèm uniform theo contract. Service kiểm tra lại scope, session, roster, thời hạn, mẫu còn hợp lệ và version rồi ghi attendance source VISION, arrived_at từ scanned_at. Uniform không hợp lệ phải rollback toàn bộ xác nhận.
5. Retry cùng key/payload trả kết quả đã lưu, không nhân đôi attendance/log; key cũ với payload khác phải conflict. Proposal stale/hết hạn/rejected/superseded không được xác nhận. Manual sửa attendance, đóng buổi, chuyển lớp, đăng ký lại/xóa mẫu làm proposal cũ không còn hợp lệ.
6. Reject chỉ đổi proposal với version/key và reason; không ghi PRESENT. Khi không thể xác nhận chắc chắn, nhập thủ công với scope/version/idempotency hiện có. Chốt buổi, xem báo cáo/export đối soát chỉ attendance đã ghi.

UNMARKED/ABSENT không có arrived_at/source/observed_uniform; PRESENT không mặc nhiên COMPLIANT. Đến muộn suy từ arrived_at và late_cutoff_at snapshot. Roster bất biến bảo vệ báo cáo lịch sử khi hồ sơ đổi lớp/tên. CLOSED không cho vision ghi mới; chỉnh thủ công sau chốt theo quy tắc giám thị/lý do hiện có.

## 5. API gate, demo và bằng chứng

[Tracker](project-management/README.md) giữ hai người và 40 ID để truy vết; các task QR hoạt động đã đổi thành vision. Lịch/giờ cũ là ước lượng tạm, cần đánh giá lại sau thử nghiệm mặt thật, không cam kết fit lịch QR. PM phải review quyền/mẫu/ảnh, thuật toán, retry/version/expiry/rollback, migrate DB mới và nâng cấp, report/XLSX/CSV, cùng regression backend trước khi duyệt gate. Test backend QR cũ (126 test lịch sử) không chứng minh vision đạt.

UI demo cục bộ đã triển khai theo ngoại lệ được người dùng cho phép: Django shell tại `/` và CSS/JS trong app demo_ui, đăng nhập staff, tổng quan/điểm danh/học sinh/báo cáo; lịch và tạo/mở/chốt buổi; camera/upload → gợi ý → xác nhận bắt buộc → manual fallback; enrollment3–10ảnh, đồng phục và export qua API hiện có. STUDENT không dùng console và không được tăng quyền API. Chưa tuyên bố browser/full-suite/thiết bị thật đã đạt; evidence UI do lượt kiểm chứng riêng cung cấp. API giữ đường dẫn và scope, mở rộng metadata/metric có version. Chuẩn bị tương thích Vercel SQLite tạm được cho phép, chưa triển khai hosting. Kế hoạch [local demo UI](superpowers/plans/2026-10-18-local-demo-ui.md) ghi quyết định ngoại lệ; pha FRONTEND_LATER trong tracker là baseline lịch sử. [Hướng dẫn demo](huong-dan-demo-opencv.md) và [slide thuyết trình](thuyet-trinh-opencv.pptx) cung cấp setup, API requests, thuyết trình 5–7 phút và checklist thiết bị thật. Chưa có kết quả đo camera thực tế/độ chính xác/chống giả; các mục đó phải có log và người review trước khi đánh dấu hoàn tất. Không deploy, chia sẻ ngoài hoặc gửi lời mời/email.
