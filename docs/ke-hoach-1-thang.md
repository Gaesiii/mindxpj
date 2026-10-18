> Lịch/workflow v1.2 lịch sử. Phần QR bên dưới đã được thay bằng vision v1.3; xem [thiết kế hiện hành](thiet-ke-he-thong-diem-danh.md), [kế hoạch OpenCV](superpowers/plans/2026-10-18-opencv-demo.md) và tracker JSON/XLSX hiện tại. Lịch/ước lượng cũ cần PM đánh giá lại sau thử ảnh thật. UI local được người dùng cho phép trước gate bằng “làm luôn UI để demo” ngày18/10/2026; gate vẫn NOT_APPROVED, lịch frontend dưới đây là baseline lịch sử.

# Kế hoạch MVP một tháng — 2 thành viên

**Ngày mặc định:** 12/10/2026–06/11/2026, 20 ngày làm việc, nghỉ thứ Bảy/Chủ Nhật. Chưa loại ngày nghỉ riêng; PM có thể thay ngày bắt đầu và bổ sung ngày nghỉ tại Config.  
**Nhân sự:** mem1, mem2; tên đổi tại Config.  
**Năng lực giả định:** có Python cơ bản, khoảng 6 giờ/người/ngày, PM phản hồi trong ngày.  
**Phạm vi hiện tại (14/10/2026):** theo yêu cầu toàn bộ backend, đã triển khai/kiểm chứng/review kỹ thuật A02–A14/B02–B14 và chuẩn bị hồ sơ A15/B15. PM/member review và gate vẫn chờ; tracker không tự tick. Frontend/phát hành chưa thực hiện. Evidence: project-management/evidence/backend-api.md.

## 1. Chia theo module

| Thành viên | Module chính | Trách nhiệm |
| --- | --- | --- |
| mem1 | Accounts, Academics, Students, Reports | Tài khoản/quyền, lớp/GVCN, hồ sơ/ảnh, báo cáo/XLSX/CSV |
| mem2 | Schedules, Attendance, QR, Uniform | Lịch/buổi, snapshot roster, điểm danh, QR/xác minh, đồng phục |
| Cả hai | Core/contract/tích hợp | Thống nhất field/migration, review chéo, sửa lỗi và cung cấp evidence |
| PM | Scope/API gate/nghiệm thu | Comment theo task, kiểm tra kết quả, duyệt API trước frontend |

Core/config có owner theo A01/B01; không đồng thời sửa hợp đồng/schema chung mà chưa trao đổi. mem1 mở pull request/commit theo module mình; mem2 làm tương tự; người còn lại review tương thích.

## 2. Các mốc

| Mốc | Ngày làm việc | Ngày dự kiến | Sản phẩm |
| --- | --- | --- | --- |
| Nền tảng và dữ liệu | 1–6 | 12–19/10/2026 | Auth/quyền, khối/lớp, học sinh/ảnh, lịch/buổi/roster |
| API nghiệp vụ | 7–12 | 20–27/10/2026 | Manual/QR/xác minh/đồng phục/report/XLSX/CSV |
| API tích hợp và gate | 13–15 | 28–30/10/2026 | Test, seed, request collection, PM duyệt |
| Frontend dự kiến sau gate | 16–18 | 02–04/11/2026 | UI tối thiểu theo module của từng người; hiện chưa thực hiện |
| Nghiệm thu/bàn giao | 19–20 | 05–06/11/2026 | Luồng thiết bị thật, sửa lỗi, README và demo |

Không thực hiện frontend trước API gate. Nếu PM chưa duyệt hoặc còn lỗi API chặn luồng, các task giao diện vẫn blocked; PM điều chỉnh lịch thay vì ghi finish để giữ ngày dự kiến.

## 3. Task cụ thể

Các đường dẫn ở cột đầu ra là file sẽ được triển khai trong backend/ hoặc docs/, không phải bằng chứng hiện đã có chức năng. Dependencies được ghi theo ID; cùng ngày cần bàn giao nội bộ trước khi task phụ thuộc bắt đầu. Giờ dự kiến đã gồm tự kiểm chứng/review ngắn, chưa gồm thời gian học Python từ đầu.

| ID | Owner | Ngày | Module/phase | Công việc | Giờ | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| A01 | mem1 | 1 | Nền tảng / API | Thiết lập project Django, custom User và quy ước API | 5 | — |
| B01 | mem2 | 1 | Hợp đồng module / API | Chốt schema/field/enum và payload lịch–điểm danh–QR | 5 | — |
| A02 | mem1 | 2 | M01 Tài khoản / API | API login/logout/me và cấp tài khoản tối thiểu | 6 | A01, B01 |
| B02 | mem2 | 2 | M04 Lịch / API | Đặc tả lịch tuần, session và snapshot; viết ca kiểm chứng | 4 | B01 |
| A03 | mem1 | 3 | M02 Khối/lớp / API | Model và API khối, lớp, gán một GVCN | 6 | A02 |
| B03 | mem2 | 3 | M04 Lịch / API | Chốt đầu vào/đầu ra lịch với model lớp/học sinh | 4 | B02 |
| A04 | mem1 | 4 | M03 Học sinh / API | Model học sinh và API thêm/xem theo lớp | 5 | A03 |
| B04 | mem2 | 4 | M04 Lịch / API | Model và API lịch tuần theo lớp | 6 | A03, B03 |
| A05 | mem1 | 5 | M03 Học sinh / API | API cập nhật, tìm kiếm và tài khoản học sinh quét QR | 6 | A04 |
| B05 | mem2 | 5 | M04 Buổi học / API | Tạo buổi từ lịch theo ngày, lấy danh sách học sinh snapshot | 6 | A04, B04 |
| A06 | mem1 | 6 | M03 Ảnh / API | Upload/thay/tải ảnh riêng tư bằng Pillow | 6 | A05 |
| B06 | mem2 | 6 | M04 Buổi học / API | API mở/chốt buổi tối thiểu và tạo attendance UNMARKED | 5 | B05, A05 |
| A07 | mem1 | 7 | M01–M03 Quyền / API | Kiểm chứng quyền tài khoản, lớp, học sinh và ảnh | 5 | A06, A03 |
| B07 | mem2 | 7 | M05 Điểm danh / API | API roster, điểm danh thủ công/vắng và thời gian đến | 6 | B06 |
| A08 | mem1 | 8 | M07 Báo cáo / API | Viết query báo cáo bằng fixture, công thức tổng hợp | 5 | B06, A07 |
| B08 | mem2 | 8 | M05 Điểm danh / API | Version, unique, retry chống điểm danh trùng và lỗi mạng | 5 | B07 |
| A09 | mem1 | 9 | M07 Báo cáo / API | API báo cáo chi tiết/tổng hợp, lọc ngày/lớp/khối | 5 | A08, B08 |
| B09 | mem2 | 9 | M05 QR / API | Token QR động theo buổi, hash, hạn và ảnh qrcode | 6 | B08, A05 |
| A10 | mem1 | 10 | M07 Xuất XLSX / API | Xuất Excel chi tiết/tổng hợp bằng openpyxl | 6 | A09 |
| B10 | mem2 | 10 | M05 QR / API | API học sinh gửi scan và lấy trạng thái chính mình | 6 | B09 |
| A11 | mem1 | 11 | M07 Xuất CSV / API | CSV UTF-8 BOM, endpoint download và metadata | 5 | A10 |
| B11 | mem2 | 11 | M05 QR xác minh / API | API danh sách scan, confirm/reject tại chỗ | 6 | B10 |
| A12 | mem1 | 12 | M07 Báo cáo / API | Đối soát báo cáo với QR/manual và các trạng thái đồng phục | 6 | A11, B11 |
| B12 | mem2 | 12 | M06 Đồng phục / API | API kiểm tra đồng phục và confirm QR kèm đồng phục | 6 | B11 |
| A13 | mem1 | 13 | Tích hợp API / API | Kiểm chứng quyền xuyên suốt và tải file/ảnh | 6 | A12, B12 |
| B13 | mem2 | 13 | Tích hợp API / API | Kiểm chứng quét→xác minh→đồng phục→chốt | 6 | B12 |
| A14 | mem1 | 14 | API docs/seed / API | Dữ liệu giả và request collection cho PM nghiệm thu | 5 | A13 |
| B14 | mem2 | 14 | API hoàn thiện / API | Sửa lỗi API lõi và viết hướng dẫn QR/đồng phục | 5 | B13 |
| A15 | mem1 | 15 | API gate / API | Review API gate với PM: auth/lớp/học sinh/report/export | 4 | A14, B14 |
| B15 | mem2 | 15 | API gate / API | Review API gate với PM: lịch/attendance/QR/uniform | 4 | B14, A14 |
| A16 | mem1 | 16 | UI M01–M03 / FRONTEND_LATER | Sau API gate: giao diện đăng nhập, lớp và học sinh tối thiểu | 5 | A15, B15 |
| B16 | mem2 | 16 | UI M04–M05 / FRONTEND_LATER | Sau API gate: giao diện lịch và danh sách điểm danh | 5 | A15, B15 |
| A17 | mem1 | 17 | UI M03/M07 / FRONTEND_LATER | Sau API gate: upload ảnh, bộ lọc báo cáo và xuất file | 6 | A16 |
| B17 | mem2 | 17 | UI QR / FRONTEND_LATER | Sau API gate: màn hình phát QR, camera quét và hàng đợi | 6 | B16 |
| A18 | mem1 | 18 | UI M07 hoàn thiện / FRONTEND_LATER | Sau API gate: tổng hợp báo cáo, lỗi và trạng thái đang lưu | 5 | A17 |
| B18 | mem2 | 18 | UI M06 hoàn thiện / FRONTEND_LATER | Sau API gate: xác minh và đồng phục cùng form, chốt buổi | 5 | B17 |
| A19 | mem1 | 19 | Nghiệm thu MVP / QA | Kiểm chứng luồng thật và quyền/report trên dữ liệu giả | 6 | A18, B18 |
| B19 | mem2 | 19 | Nghiệm thu MVP / QA | Kiểm chứng thiết bị QR, đồng phục và fallback | 6 | A18, B18 |
| A20 | mem1 | 20 | Bàn giao / QA | Sửa lỗi còn lại, README setup và kịch bản thi | 4 | A19, B19 |
| B20 | mem2 | 20 | Bàn giao / QA | Regression API/QR/uniform và chạy demo cuối | 4 | A19, B19 |

## 4. Acceptance theo task

### A01 — Thiết lập project Django, custom User và quy ước API

- [ ] Đầu ra: manage.py; config; accounts/models.py; requirements.txt.
- [ ] Kiểm chứng: Django check/migrate chạy trên DB rỗng; không dùng User mặc định rồi đổi sau.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B01 — Chốt schema/field/enum và payload lịch–điểm danh–QR

- [ ] Đầu ra: docs/api-contract.md; core/enums.py.
- [ ] Kiểm chứng: Hai thành viên dùng cùng status, timezone, ID và error format; PM review phạm vi.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A02 — API login/logout/me và cấp tài khoản tối thiểu

- [ ] Đầu ra: accounts/views.py; services.py; urls.py.
- [ ] Kiểm chứng: Đăng nhập 3 vai trò; STUDENT chỉ bản thân; logout thu hồi phiên; CSRF đúng.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B02 — Đặc tả lịch tuần, session và snapshot; viết ca kiểm chứng

- [ ] Đầu ra: schedules/README.md; tests/test_schedules.py.
- [ ] Kiểm chứng: Có ca sáng/chiều, sơ mi/thể dục, mở buổi lặp; chưa phụ thuộc migration lớp.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A03 — Model và API khối, lớp, gán một GVCN

- [ ] Đầu ra: academics/models.py; services.py; views.py.
- [ ] Kiểm chứng: Một lớp một GVCN; giám thị quản lý tất cả; giáo viên chỉ lớp được giao.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B03 — Chốt đầu vào/đầu ra lịch với model lớp/học sinh

- [ ] Đầu ra: docs/api-contract.md; schedules/forms.py.
- [ ] Kiểm chứng: Có class_id, weekday, slot, start_time, grace_minutes, uniform_type; không thêm module ngoài MVP.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A04 — Model học sinh và API thêm/xem theo lớp

- [ ] Đầu ra: students/models.py; services.py; views.py.
- [ ] Kiểm chứng: Họ tên, mã, lớp/khối; trùng tên được, trùng mã bị chặn; lớp ngoài quyền trả 403/404.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B04 — Model và API lịch tuần theo lớp

- [ ] Đầu ra: schedules/models.py; services.py; views.py.
- [ ] Kiểm chứng: Lưu giờ vào học và SHIRT/SPORTS; không có hai rule trùng thứ/slot/lớp.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A05 — API cập nhật, tìm kiếm và tài khoản học sinh quét QR

- [ ] Đầu ra: students/forms.py; accounts/services.py.
- [ ] Kiểm chứng: Sửa đúng phạm vi; student user liên kết một hồ sơ; không trả mật khẩu trong danh sách.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B05 — Tạo buổi từ lịch theo ngày, lấy danh sách học sinh snapshot

- [ ] Đầu ra: schedules/services.py; models.py.
- [ ] Kiểm chứng: Unique lớp/ngày/buổi; roster lấy học sinh active; sửa lịch không đổi snapshot buổi đã mở.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A06 — Upload/thay/tải ảnh riêng tư bằng Pillow

- [ ] Đầu ra: students/services.py; views.py; core/storage.py.
- [ ] Kiểm chứng: JPEG/PNG/WebP ≤5 MB; ảnh lỗi giữ ảnh cũ; tải ảnh lớp khác bị chặn.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B06 — API mở/chốt buổi tối thiểu và tạo attendance UNMARKED

- [ ] Đầu ra: schedules/services.py; attendance/models.py.
- [ ] Kiểm chứng: Mở lặp không nhân đôi; chốt có cảnh báo chưa ghi nhận; chốt giữ NOT_CHECKED.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A07 — Kiểm chứng quyền tài khoản, lớp, học sinh và ảnh

- [ ] Đầu ra: tests/test_permissions.py; test_students.py.
- [ ] Kiểm chứng: Teacher A không đọc/sửa/tải ảnh lớp B; student không đọc roster; supervisor được toàn trường.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B07 — API roster, điểm danh thủ công/vắng và thời gian đến

- [ ] Đầu ra: attendance/services.py; views.py; forms.py.
- [ ] Kiểm chứng: PRESENT có arrived_at; đúng giờ/muộn theo server và snapshot; vắng không có giờ đến.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A08 — Viết query báo cáo bằng fixture, công thức tổng hợp

- [ ] Đầu ra: reports/queries.py; tests/test_reports.py.
- [ ] Kiểm chứng: Phân biệt có mặt/vắng/chưa ghi nhận; không đếm buổi chưa mở; quyền lớp được lọc ở query.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B08 — Version, unique, retry chống điểm danh trùng và lỗi mạng

- [ ] Đầu ra: attendance/services.py; core/idempotency.py; tests/test_attendance.py.
- [ ] Kiểm chứng: Retry cùng key không nhân đôi; 07:05:00 đúng giờ, 07:05:01 muộn; không báo lưu thành công nếu lỗi.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A09 — API báo cáo chi tiết/tổng hợp, lọc ngày/lớp/khối

- [ ] Đầu ra: reports/views.py; forms.py; urls.py.
- [ ] Kiểm chứng: Bộ lọc ngoài quyền bị chặn; tổng đúng với dữ liệu attendance thực; mẫu số 0 hiển thị rõ.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B09 — Token QR động theo buổi, hash, hạn và ảnh qrcode

- [ ] Đầu ra: qr/models.py; services.py; views.py.
- [ ] Kiểm chứng: Đổi 30 giây, hạn 60 giây; chỉ OPEN; token không chứa dữ liệu học sinh.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A10 — Xuất Excel chi tiết/tổng hợp bằng openpyxl

- [ ] Đầu ra: reports/exporters.py; services.py.
- [ ] Kiểm chứng: Tối đa 5.000 dòng, đúng bộ lọc/quyền; không chạy formula do nội dung người dùng.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B10 — API học sinh gửi scan và lấy trạng thái chính mình

- [ ] Đầu ra: qr/views.py; services.py; tests/test_qr.py.
- [ ] Kiểm chứng: Identity từ session; sai lớp/hết hạn bị chặn; scan lặp giữ giờ đầu; PENDING chưa phải có mặt.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A11 — CSV UTF-8 BOM, endpoint download và metadata

- [ ] Đầu ra: reports/exporters.py; views.py; core/storage.py.
- [ ] Kiểm chứng: Đúng dấu tiếng Việt/timezone; tải kiểm tra quyền; XLSX và CSV đối soát cùng dữ liệu.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B11 — API danh sách scan, confirm/reject tại chỗ

- [ ] Đầu ra: qr/services.py; views.py; attendance/services.py.
- [ ] Kiểm chứng: Confirm tạo PRESENT với giờ scan, không lấy giờ confirm; reject không có mặt; manual supersede scan.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A12 — Đối soát báo cáo với QR/manual và các trạng thái đồng phục

- [ ] Đầu ra: tests/test_report_reconciliation.py; reports/queries.py.
- [ ] Kiểm chứng: QR chưa xác minh không góp PRESENT; vắng không bị tính vi phạm; tổng và chi tiết khớp.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B12 — API kiểm tra đồng phục và confirm QR kèm đồng phục

- [ ] Đầu ra: attendance/uniform_rules.py; forms.py; services.py.
- [ ] Kiểm chứng: COMPLIANT/NON_COMPLIANT/NOT_CHECKED; vi phạm có lý do; có mặt không tự đạt; lưu cùng transaction.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A13 — Kiểm chứng quyền xuyên suốt và tải file/ảnh

- [ ] Đầu ra: tests/test_api_permissions.py; test_reports.py.
- [ ] Kiểm chứng: Học sinh không xuất data; giáo viên xuất lớp mình; đổi ID không vượt quyền; trường bắt buộc validate.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B13 — Kiểm chứng quét→xác minh→đồng phục→chốt

- [ ] Đầu ra: tests/test_full_flow.py; test_qr.py.
- [ ] Kiểm chứng: Chốt không nhận scan mới; pending quá 15 phút không confirm; một attendance/học sinh/buổi.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A14 — Dữ liệu giả và request collection cho PM nghiệm thu

- [ ] Đầu ra: management command seed_demo; docs/api-contract.md; api-requests.http.
- [ ] Kiểm chứng: 2 lớp/20 học sinh giả, tài khoản các vai trò; PM gọi API không cần giao diện.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B14 — Sửa lỗi API lõi và viết hướng dẫn QR/đồng phục

- [ ] Đầu ra: docs/api-contract.md; qr/README.md; attendance/README.md.
- [ ] Kiểm chứng: Lỗi hết hạn/sai lớp/thiếu lý do có code rõ; request example và expected response đúng.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A15 — Review API gate với PM: auth/lớp/học sinh/report/export

- [ ] Đầu ra: docs/api-acceptance.md; link evidence.
- [ ] Kiểm chứng: PM có test result, collection và file export; chưa mở frontend khi còn lỗi chặn luồng.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B15 — Review API gate với PM: lịch/attendance/QR/uniform

- [ ] Đầu ra: docs/api-acceptance.md; link evidence.
- [ ] Kiểm chứng: Demo API hoàn chỉnh; các endpoint lõi qua test; PM đổi API_Gate thành APPROVED.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A16 — Sau API gate: giao diện đăng nhập, lớp và học sinh tối thiểu

- [ ] Đầu ra: Tạo frontend Django Templates sau PM duyệt.
- [ ] Kiểm chứng: Dùng API/service đã ổn định; không tạo frontend ở giai đoạn hiện tại.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B16 — Sau API gate: giao diện lịch và danh sách điểm danh

- [ ] Đầu ra: Tạo frontend Django Templates sau PM duyệt.
- [ ] Kiểm chứng: Hiển thị trạng thái và giờ từ server; không tính quyền/thời gian ở client.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A17 — Sau API gate: upload ảnh, bộ lọc báo cáo và xuất file

- [ ] Đầu ra: Templates học sinh/báo cáo sau PM duyệt.
- [ ] Kiểm chứng: Upload lỗi giữ ảnh cũ; đúng quyền lớp; xuất được XLSX/CSV.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B17 — Sau API gate: màn hình phát QR, camera quét và hàng đợi

- [ ] Đầu ra: Templates/JavaScript QR sau PM duyệt.
- [ ] Kiểm chứng: Thử camera thật HTTPS; scan pending rõ; không có điện thoại dùng thủ công.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A18 — Sau API gate: tổng hợp báo cáo, lỗi và trạng thái đang lưu

- [ ] Đầu ra: Templates báo cáo/học sinh sau PM duyệt.
- [ ] Kiểm chứng: Tổng khớp API; lỗi không báo thành công; mã/tên/lớp rõ.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B18 — Sau API gate: xác minh và đồng phục cùng form, chốt buổi

- [ ] Đầu ra: Templates xác minh/đồng phục sau PM duyệt.
- [ ] Kiểm chứng: Không mặc định đạt; chốt cảnh báo pending/chưa ghi nhận; giữ NOT_CHECKED.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A19 — Kiểm chứng luồng thật và quyền/report trên dữ liệu giả

- [ ] Đầu ra: docs/mvp-acceptance.md; evidence.
- [ ] Kiểm chứng: Teacher/supervisor/student chạy đúng quyền; số liệu/file khớp; PM ghi comment từng lỗi.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B19 — Kiểm chứng thiết bị QR, đồng phục và fallback

- [ ] Đầu ra: docs/mvp-acceptance.md; evidence.
- [ ] Kiểm chứng: Hai học sinh cùng QR; quét lặp/hết hạn; confirm đúng giờ scan; nhập thủ công khi thiếu thiết bị.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### A20 — Sửa lỗi còn lại, README setup và kịch bản thi

- [ ] Đầu ra: README.md; docs/demo-script.md; evidence.
- [ ] Kiểm chứng: Setup từ máy sạch theo README; migrations/seed/test có hướng dẫn; PM duyệt bàn giao.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

### B20 — Regression API/QR/uniform và chạy demo cuối

- [ ] Đầu ra: docs/mvp-acceptance.md; evidence.
- [ ] Kiểm chứng: Không lỗi chặn luồng; báo các giới hạn còn lại; chỉ tick finish khi có bằng chứng.
- [ ] Gắn link PR/commit/test và ghi Dev Note khi có lỗi hoặc phụ thuộc chưa hoàn tất.
- [ ] Tick Finish? sau implementation, kiểm chứng và review; PM ghi nhận xét ở PM Comment.

## 5. Giờ và tiến độ

mem1: 107 giờ dự kiến; mem2: 106 giờ dự kiến. Mỗi người có 120 giờ năng lực theo giả định 20×6 giờ; khoảng đệm tương ứng 13 và 14 giờ. Task không vượt 6 giờ/ngày/người. Ước lượng cần PM rà lại theo năng lực hai học viên; lịch một tháng có frontend tối thiểu chỉ khả thi khi API gate đạt đúng ngày 15.

Tất cả 40 task khởi tạo unfinish. 30 task API; 6 task FRONTEND_LATER; 4 task QA. FRONTEND_LATER/QA chỉ ready khi toàn bộ API finish, API_Gate APPROVED và dependencies finish. PM xem cả phần trăm API và phần trăm toàn dự án để không nhầm backend hoàn tất với ứng dụng hoàn tất.

Checkbox finish không thay thế nghiệm thu: thiếu evidence, chưa test hoặc chỉ có file skeleton vẫn unfinish. Bảng chỉ dùng finish/unfinish theo yêu cầu; blocked/ready ở cột riêng để không thêm trạng thái vào Status.

## 6. Quy tắc sử dụng bảng

Config có ngày bắt đầu, mem1, mem2, PM, API_Gate và danh sách ngày nghỉ tùy chọn. Tasks có ID/module/phase/owner/reviewer, ngày/giờ, dependencies, đầu ra, acceptance, checkbox Finish?, Status, Ready/Blocked, PM Comment, Evidence, Actual Finish và Dev Note. Dashboard thống kê tổng task, API/front/QA, finish/unfinish, tiến độ theo người và giờ dự kiến; Modules xác định owner/phạm vi.

PM duyệt API_Gate khi A15/B15 và toàn bộ API hoàn tất có bằng chứng. PM Comment là cột ghi nhận xét, không tự cấp quyền Google theo email vì chưa có email thành viên. Chia sẻ bảng và quyền chỉnh sửa do PM thiết lập.

Bản XLSX có giá trị TRUE/FALSE ở Finish?; khi nhập Google Sheets, dùng Apps Script để tạo checkbox thực. Mã tạo Sheets không triển khai code ứng dụng và không mời/chia sẻ với ai.

## 7. Bàn giao hiện tại

- backend/ có API MVP và seed_demo/request collection; xem docs/api-acceptance.md và evidence/backend-api.md. Bàn giao/ZIP A01/B01 là baseline lịch sử. Chưa tick finish khi PM/member review chưa có.
- Thiết kế MVP v1.2 có Markdown và Word đồng nhất.
- tasks.json là nguồn task; XLSX, CSV và mã Apps Script được tạo từ cùng nguồn.
- Không có templates/static hoặc frontend được tạo.
- Bản v1.1 lưu docs/archive để tham khảo, không được đưa vào backlog tháng này.
