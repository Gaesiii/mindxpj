# OpenCV backend — kiểm chứng và review 18/10/2026

Theo thiết kế v1.3 được người dùng cho triển khai. QR tắt mặc định, giữ lịch sử và migrations. Đã thêm vision/enrollment/analyze/confirm/reject, source VISION, thời gian quét trong report/export, vô hiệu proposal khi manual/close/enrollment thay đổi. Nhân sự xác nhận danh tính trước PRESENT; không tự quyết đồng phục. UI đã được yêu cầu, chưa tạo vì PM API gate còn NOT_APPROVED.

## Bằng chứng chạy lại

Lệnh từ workspace: `backend/.venv/Scripts/python.exe .document-tools/verify_opencv.py`.
Script tái lập dùng DB tạm riêng, không thay backend/db.sqlite3; secret/password sinh trong process và không in vào log. Log cuối: [opencv-validation.txt](opencv-validation.txt).

Sau review bàn giao, bổ sung kiểm tra riêng từng chỉ số nguồn/trạng thái/giờ/đồng phục cho cả XLSX và CSV; chạy lại `verify_opencv.py --demo-only` đạt, log [opencv-demo-validation.txt](opencv-demo-validation.txt). Log full149test được giữ nguyên, các mẫu đầu ra đã được tái sinh bởi lần kiểm tra này.

| Kiểm chứng | Kết quả |
| --- | --- |
| Django check | exit0, không issue |
| Migrate DB rỗng | exit0, toàn graph hiện tại |
| makemigrations --check --dry-run | exit0, No changes detected |
| pip check | exit0, No broken requirements found |
| Full suite | **149 test đạt, 61.078s**, exit0 |
| Nâng schema v1.2 → v1.3 | Fixture legacy Student/QR CONFIRMED/Attendance source QR giữ nguyên ID/nội dung sau migrate; thêm bảng vision không xóa dữ liệu |
| HTTP với CSRF thật | Login/enroll/analyze/confirm/retry/manual/uniform/close/report/export/logout đạt |
| Report JSON/XLSX/CSV | Mở lại từng file, khớp3 roster/2PRESENT/1ABSENT;1VISION/1MANUAL;1đúng giờ/1muộn;1đạt/1không đạt |
| Scope | GVCN khác lớp không đọc sample/queue; STUDENT không export; logout không truy cập được queue |

Mẫu đầu ra mới: [README](opencv-samples/README.md), [XLSX](opencv-samples/attendance-vision-demo.xlsx), [CSV](opencv-samples/attendance-vision-demo.csv), [summary JSON](opencv-samples/summary-vision-demo.json), [detail JSON](opencv-samples/detail-vision-demo.json). Đây là dữ liệu giả, không có crop/frame nhận diện, password hay token đăng nhập.

## Phạm vi test mới

23test mới (test_vision_engine/test_vision_api) cộng126test backend hiện hữu. Các test QR cũ bật QR_ENABLED=True rõ ràng để chứng minh tương thích lịch sử; test riêng chứng minh cấu hình mặc định trả410 QR_RETIRED.

- Engine: ảnh sai/nặng/quá pixel; detector Haar thật từ chối ảnh trống; crop một mặt128x128; nhiều mặt/mờ/quá nhỏ; LBPH khớp/unknown/ambiguous; HSV trắng/xanh/khác màu/thân bị cắt/màu không trội.
- Enrollment:3mẫu khác nhau, metadata không bytes, thay toàn bộ nguyên tử, lỗi giữ bộ cũ, duplicate bị chặn, xóa crop và vô hiệu proposal.
- API: staff scope, STUDENT bị chặn, CSRF, schema strict không nhận danh tính giả; PENDING chưa PRESENT; thời hạn/version/identity; uniform sai rollback; UNKNOWN không thành vi phạm; sample xóa/đăng ký lại/chuyển lớp/manual/close chặn confirm; rate limit; roster>50; đúng ngày và khung giờ; idempotency đúng body/khác ảnh và replay sau close có scope.
- Reports: source VISION, arrived_at=scanned_at; đối soát cả2format xuất với JSON trong script HTTP.

## Review và sửa phát hiện

Reviewer độc lập đọc spec trước quality, kiểm tra scope/private bytes/idempotency/transaction/revision/version/manual/close/report. Phát hiện: session còn OPEN ngoài giờ vẫn cho scan/confirm. Đã thêm kiểm tra inclusive start_at≤now≤close_at và regression RED→GREEN trước/sau giờ; capture gần cuối buổi không confirm sau giờ đóng.

Root tự review tìm thấy analyze kiểm tra session trước replay khiến retry đã thành công sau close bị từ chối trái contract. Đã có regression RED→GREEN và chuyển kiểm tra trạng thái vào callback; kiểm tra quyền vẫn trước replay.

Reviewer chạy lại độc lập **23test đạt** và xác nhận không còn finding bắt buộc sửa trong backend đã review. Full149test và kiểm chứng cuối chạy sau các sửa. Lần regression sơ bộ có lỗi BOM trong file test sau thêm decorator; đã loại BOM và full suite cuối đạt. Review kỹ thuật không thay PM review.

Review bàn giao cuối cũng đọc script kiểm chứng, log149test, thiết kế/acceptance/demo và nội dung slide; không có finding chặn. Kiểm tra riêng CSV đã được bổ sung theo góp ý để evidence phản ánh đúng mức đối soát từng format.

## Giới hạn còn chờ

Luồng HTTP dương và các crop test dùng ảnh texture tổng hợp, chỉ mock detector trả vùng mặt; LBPH/HSV thật vẫn chạy. Haar thật mới được kiểm tra ca ảnh trống. Không có kiểm chứng camera/người thật, không có số đo accuracy hoặc chống ảnh giả; cần bộ ảnh được phép dùng và tách enrollment/evaluation. HSV chỉ heuristic dải màu, mặc định áo trắng/xanh, không chứng minh nhận biết mọi đồng phục.

SQLite và cache quota phút cố định từng process phục vụ demo nhỏ; không chứng minh tải toàn trường hay quota toàn hệ thống. PPTX đã kiểm tra nội dung/notes, chưa render trong PowerPoint. Không có frontend/camera trình duyệt/deploy/chia sẻ ngoài. PM/member review, thiết bị thật và API gate chưa hoàn tất; tracker Finish? và NOT_APPROVED được giữ.
