# API acceptance — A15/B15

Nguồn chuẩn: MVP v1.2. Người dùng yêu cầu triển khai toàn bộ backend A02–A15/B02–B15 ngày 14/10/2026. Đây là hồ sơ chuẩn bị review; **API_Gate = NOT_APPROVED** cho đến khi PM xác nhận. Review kỹ thuật của agent không thay PM/member review, không tự tick Finish? trong tracker.

## Phạm vi review

| Nhóm task | Điều PM cần kiểm tra | Bằng chứng dự kiến |
| --- | --- | --- |
| A02–A03 | Auth/cookie/CSRF; role; khối/lớp/GVCN hiện tại; đổi GVCN đổi scope ngay | test_accounts, test_academics, test_api_helpers |
| A04–A07 | Student/mã unique/tên trùng/search/transfer; User.Student1:1; ảnh private/Pillow/giữ ảnh cũ | test_students và evidence |
| B02–B06 | Form/sáng chiều/đồng phục; unique session; roster snapshot khi OPEN; transaction rollback/mở lặp/chốt | test_schedules, test_schedule_api và evidence |
| B07–B08 | Manual/PRESENT/ABSENT/cutoff; version/idempotency/log; CLOSED teacher bị chặn, supervisor lý do | test_attendance |
| B09–B12 | Token hash/60s/refresh30; own identity; pending15m/confirm/reject/manual supersede; uniform rollback | test_qr, test_uniforms |
| A08–A12 | Canonical snapshot report/filter/scope;40 roster; XLSX/CSV/BOM/formula/5000limit; QR/manual reconciliation | test_reports, test_report_reconciliation |
| A13/B13 | HTTP toàn luồng ba vai trò, CSRF, ảnh/export, đổi ID/quyền, chốt và retry | test_full_flow và kiểm chứng tích hợp |
| A14/B14 | 2 lớp/20 học sinh giả, seed idempotent, request collection và lỗi có code rõ | seed_demo, api-requests.http, module README |
| A15/B15 | Đọc kết quả kiểm chứng và review độc lập, xác nhận remaining limits và PM Comment | evidence/backend-api.md và validation log |

## Kết quả kỹ thuật đã có

126test đạt, check/migrate DB mới/migration check/pip check và seed hai lần đều exit0. Review độc lập không còn finding chặn. Bằng chứng/mapping task/test và giới hạn tại [backend-api.md](project-management/evidence/backend-api.md), output tại [backend-api-validation.txt](project-management/evidence/backend-api-validation.txt). Request collection có11JSON body hợp lệ; toànluồng tương ứng đã chạy bằng HTTP test với CSRF thật.

File tải mẫu để PM mở trực tiếp: [XLSX](project-management/evidence/samples/attendance-demo.xlsx), [CSV](project-management/evidence/samples/attendance-demo.csv), [summary JSON](project-management/evidence/samples/summary-demo.json). [Bản đối soát](project-management/evidence/samples/README.md) ghi luồng QR/manual/đồng phục/chốt, CSRF và ca sai quyền. Mẫu gồm 10 roster: 2 có mặt, 8 vắng, 1 đúng giờ, 1 muộn; file đã mở lại và khớp toàn bộ dữ liệu API.

## Cách PM review

1. Dựng môi trường theo backend/README.md, migrate DB riêng và chạy seed_demo; không dùng dữ liệu học sinh thật.
2. Chạy lại test/check/migration check/pip check trong backend cwd. Không coi file chỉ chứa docstring là test đã đạt.
3. Dùng api-requests.http với cookie/CSRF từng tài khoản; lấy ID lớp/học sinh/buổi/roster/attendance từ response. Thử quét→PENDING→confirm→uniform→close→report/export cùng bộ lọc.
4. Dùng GVCN khác lớp/STUDENT/phiên đã logout để thử truy cập ảnh/file/roster/chỉnh sửa; đọc cả code và trạng thái database.
5. Đối chiếu report JSON, XLSX và CSV; ghi lỗi/bằng chứng vào PM Comment/Evidence đúng task.
6. Chỉ khi tất cả task API được xác nhận implementation+validation+review, PM quyết định API_Gate. Frontend vẫn cần yêu cầu riêng sau gate.

## Giới hạn phải ghi khi demo

SQLite phục vụ demo nhỏ; test unique/atomic/CAS/retry không chứng minh tải toàn trường hoặc nhiều process. Login/scan rate limit cache cục bộ không distributed. QR không ngăn tuyệt đối chia sẻ tài khoản/mã; nhân sự xác minh tại chỗ bắt buộc. Export đồng bộ tối đa5.000 dòng. Ảnh local private; không cloud/worker/queue/AI/camera recognition hoặc workflow duyệt sửa.

Chưa có deploy hoặc kiểm chứng camera thiết bị thật/frontend trong phạm vi backend này. Tài khoản cấp qua command/service; không cần public registration/Admin UI. Setup local DEBUG=true, vận hành thật/HTTPS là yêu cầu riêng.

## Quyết định PM

- PM/member review: chờ xác nhận.
- API_Gate: NOT_APPROVED.
- Frontend: chưa yêu cầu, chưa triển khai.
- Tracker Finish?: không tự thay đổi.
