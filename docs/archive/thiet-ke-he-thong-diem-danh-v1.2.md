# Thiết kế MVP điểm danh học sinh — Python/Django

> Nguồn chuẩn cho dự án và agent code. Bản 1.2 thay thế kế hoạch mở rộng v1.1; chỉ triển khai yêu cầu MVP. Cập nhật14/10/2026: backend A02–A14/B02–B14 đã triển khai và kiểm chứng/review kỹ thuật; A15/B15 chuẩn bị hồ sơ API acceptance, còn chờ PM/member review. Chưa frontend/API gate. Cập nhật tiến độ không thay đổi phạm vi thiết kế; Word trước đó còn mô tả giai đoạn skeleton.

**Phiên bản:** 1.2 — 08/10/2026.  
**Goal:** Học sinh quét QR; GVCN/giám thị ghi nhận thời gian đi học, xác nhận đồng phục và xuất dữ liệu đúng phạm vi quyền.  
**Architecture:** Một project Django chia app theo nghiệp vụ. API và service Python hoàn thành trước; giao diện Django Templates thực hiện sau API gate của PM.  
**Tech Stack:** Python 3.12, Django 5.2, Django ORM/Auth/Forms, SQLite cho demo nhỏ, Pillow, qrcode, openpyxl và csv chuẩn Python. Khóa bản vá dependency trong task A01.  
**Kế hoạch:** 2 thành viên mem1/mem2; 20 ngày làm việc trong một tháng, mặc định 12/10/2026–06/11/2026. Chi tiết trong docs/ke-hoach-1-thang.md và task tracker.  
**For agentic workers:** Thực hiện từng module và task theo checklist; có thể dùng superpowers:executing-plans khi có sẵn. Chưa thực hiện task frontend ở giai đoạn hiện tại.

## 1. Phạm vi theo yêu cầu

| Mã | Yêu cầu | Module |
| --- | --- | --- |
| R01 | Họ tên, lớp, khối của học sinh | M02/M03 |
| R02 | Mỗi lớp có một GVCN quản lý | M01/M02 |
| R03 | GVCN thêm học sinh và ảnh học sinh | M03 |
| R04 | Lịch đi học, đồng phục sơ mi/thể dục | M04 |
| R05 | Giám thị quản lý tất cả | Quyền tại tất cả module |
| R06 | Thời gian đi học qua QR; thao tác thủ công dự phòng | M05 |
| R07 | GVCN/giám thị nhận định đồng phục đúng hay sai | M06 |
| R08 | GVCN/giám thị xuất điểm danh và đồng phục | M07 |
| R09 | Python chủ đạo, phù hợp học viên K12 đi thi | Cấu trúc Django và lộ trình |
| R10 | API/module trước frontend; hai người làm theo module trong một tháng | M08 và bảng task |

### 1.1 Trong MVP

- Tài khoản GVCN, giám thị và tài khoản học sinh chỉ phục vụ quét QR.
- Khối/lớp và một GVCN của mỗi lớp; học sinh gồm mã, họ tên, lớp và ảnh tùy chọn.
- Lịch tuần theo lớp, buổi sáng/chiều, giờ bắt đầu, ngưỡng muộn và loại đồng phục SHIRT/SPORTS.
- Buổi học cụ thể, danh sách snapshot khi mở buổi và chốt tối thiểu để xác định vắng.
- QR theo lớp/buổi; học sinh gửi lần quét, nhân sự xác minh tại chỗ.
- Có mặt, vắng, chưa ghi nhận; thời gian đi học, đúng giờ/đi muộn.
- Kết quả đồng phục đạt/không đạt/chưa kiểm tra, lý do không đạt.
- Báo cáo chi tiết/tổng hợp và xuất XLSX/CSV, tối đa 5.000 dòng mỗi lần.
- Kiểm tra quyền, unique/version, retry và lịch sử chỉnh sửa tối thiểu trong các service.

### 1.2 Không đưa vào task hiện tại

Không thực hiện AI/camera nhận diện, RFID, phụ huynh, SMS/Zalo, học phí, điểm số, offline tự đồng bộ, nhiều trường, dashboard phân tích nâng cao, workflow xin phép/duyệt sửa, chuyển lớp có lịch sử hiệu lực phức tạp, đồng phục miễn có phê duyệt, xuất PDF, cloud storage, worker/queue, microservices và tải cấp toàn trường. Bản v1.1 được lưu tại docs/archive chỉ để đối chiếu; các mục đó không thuộc lịch một tháng hiện tại.

### 1.3 Giả định để triển khai

Một trường; buổi sáng/chiều; học sinh dùng điện thoại đăng nhập và quét QR buổi của lớp mình. Nhân sự hiển thị QR ở vị trí giám sát và xác minh học sinh. Thiếu điện thoại dùng điểm danh thủ công. Ngày/thời gian hiển thị Asia/Ho_Chi_Minh, lưu thời điểm UTC. Lịch tháng bắt đầu giả định 12/10/2026; được thay tại Config của bảng task. Chưa có ngày bắt đầu chính thức được người dùng cung cấp.

Một tháng gồm 15 ngày API và 5 ngày giao diện tối thiểu/nghiệm thu sau API gate. Đây là lịch mục tiêu với khoảng 6 giờ làm việc hữu ích/người/ngày, có Python cơ bản và PM phản hồi trong ngày; không phải bảo đảm hoàn thành với hai học viên chỉ học vài giờ/tuần. Nếu API chưa được duyệt ngày 15, hoãn frontend và PM điều chỉnh hạn; không bỏ qua API gate.

## 2. Vai trò và quyền

| Hành động | GVCN | Giám thị | Học sinh |
| --- | --- | --- | --- |
| Xem/thêm/sửa hồ sơ, ảnh | Lớp được giao | Toàn trường | Chỉ hồ sơ tối thiểu của mình |
| Tạo khối/lớp/gán GVCN | Xem lớp mình | Thực hiện | Không |
| Sửa lịch, mở/chốt buổi | Lớp được giao | Toàn trường | Không |
| Phát QR, xem hàng đợi, xác minh | Lớp được giao | Toàn trường | Không |
| Gửi QR scan | Không dùng danh tính học sinh | Không dùng danh tính học sinh | Chỉ bản thân |
| Điểm danh thủ công/đồng phục | Lớp được giao | Toàn trường | Không |
| Xem/xuất báo cáo | Lớp được giao | Toàn trường | Không |
| Sửa bản ghi sau chốt | Không | Có lý do và log | Không |

Giám thị tạo tài khoản qua quy trình quản trị Django; không xây một module quản trị kỹ thuật riêng. Django superuser chỉ dùng thiết lập/vận hành, không thay quyền nghiệp vụ GVCN trong demo. Django Admin không cho sửa attendance/QR trực tiếp để bỏ qua service và log.

Mỗi lớp có một teacher_id hiện tại. Khi đổi GVCN, giáo viên cũ mất quyền; giáo viên mới quản lý lớp và lịch sử lớp đó. Mỗi tài khoản học sinh liên kết đúng một Student. Backend lấy student_id từ session, không nhận danh tính điểm danh tùy ý trong payload. Mọi API, upload/download ảnh và xuất file đều kiểm tra quyền; không chỉ dựa vào việc ẩn nút.

## 3. Quy tắc dữ liệu

### 3.1 Thực thể độc lập

Student lưu hồ sơ; Schedule/Session lưu thời gian và đồng phục yêu cầu; Attendance lưu kết quả thực tế. Không lưu “hôm nay có mặt” hoặc “đồng phục sai” trên Student.

Lớp và khối trong hồ sơ được suy từ class_id và grade_id. Mã học sinh duy nhất; trùng họ tên được phép. Khi tạo buổi OPEN, lưu snapshot tên/mã/lớp/khối và quy tắc giờ/đồng phục; sửa hồ sơ hoặc lịch về sau không âm thầm sửa buổi cũ.

### 3.2 Trạng thái

| Nhóm | Trạng thái | Điều kiện |
| --- | --- | --- |
| Session | PLANNED / OPEN / CLOSED | Dự kiến / đang điểm danh / đã chốt |
| Attendance | UNMARKED | Chưa xác minh, không tự tính là vắng |
| Attendance | PRESENT | Đã xác minh có mặt; bắt buộc arrived_at |
| Attendance | ABSENT | Đã ghi vắng hoặc UNMARKED chuyển vắng khi chốt |
| Arrival | ON_TIME / LATE / NOT_APPLICABLE | Tính từ thời gian đến và cutoff; vắng/chưa ghi nhận không áp dụng |
| Uniform | NOT_CHECKED | PRESENT nhưng nhân sự chưa kiểm tra |
| Uniform | COMPLIANT / NON_COMPLIANT | Nhân sự kết luận; không đạt bắt buộc lý do |
| Uniform | NOT_APPLICABLE | Vắng hoặc chưa có mặt |
| QrScan | PENDING / CONFIRMED / REJECTED / EXPIRED / SUPERSEDED | Trạng thái sự kiện quét, độc lập với Attendance |

PRESENT không tự suy ra đồng phục đạt. Vắng không được ghi vi phạm đồng phục. Required uniform có SHIRT/SPORTS; observed uniform có SHIRT/SPORTS/OTHER/UNKNOWN; OTHER cần mô tả. COMPLIANT yêu cầu loại thực tế phù hợp chuẩn; nếu không phù hợp phải NON_COMPLIANT với lý do. Miễn/ngoại lệ đồng phục là tính năng sau MVP.

### 3.3 Thời gian và chốt

cutoff = giờ bắt đầu + grace_minutes. Ví dụ 07:00 và grace 5: đến 07:05:00 vẫn đúng giờ, 07:05:01 là muộn. Đây là ví dụ, giờ thực dùng lịch lớp.

arrived_at là thời gian đến chính thức; scanned_at là giờ server nhận quét; recorded_at/verified_at là giờ ghi nhận/xác minh. Xác minh QR dùng arrived_at = scanned_at, không dùng giờ xác minh. Nhập thủ công hồi tố cần lý do; không tin đồng hồ client, không cho giờ tương lai.

Chốt buổi hiển thị số UNMARKED, QR PENDING và NOT_CHECKED; chuyển UNMARKED thành ABSENT, scan PENDING thành EXPIRED, giữ NOT_CHECKED. CLOSED không nhận quét hoặc ghi mới từ GVCN; giám thị được sửa có lý do và log. Không xây luồng yêu cầu/duyệt sửa riêng.

## 4. Workflow và luồng dữ liệu

### 4.1 Thiết lập

Giám thị tạo tài khoản/khối/lớp → gán GVCN → GVCN thêm học sinh/ảnh → liên kết tài khoản quét cho học sinh → GVCN tạo lịch và đồng phục → tạo/mở buổi → server snapshot danh sách và chính sách.

### 4.2 Điểm danh

```text
Session OPEN + roster + chuẩn đồng phục
                 |
Học sinh đăng nhập -> quét QR còn hạn
                 |
Server kiểm tra session/identity/roster
                 |
QrScan PENDING (Attendance vẫn UNMARKED)
                 |
GVCN/giám thị đối chiếu học sinh tại chỗ
                 |
PRESENT, arrived_at=scanned_at, ON_TIME/LATE
                 |
Kiểm tra đồng phục -> COMPLIANT/NON_COMPLIANT
                 |
Chốt buổi -> báo cáo -> XLSX/CSV đúng quyền
```

### 4.3 Xuất dữ liệu

Người dùng chọn ngày/lớp/khối/buổi/trạng thái → service kiểm tra phạm vi → lấy cùng danh sách dòng kết quả → tính tổng từ danh sách đó → openpyxl/csv tạo file đồng bộ → response tải có quyền. Dữ liệu xuất tối đa 5.000 dòng, vượt giới hạn trả hướng dẫn chia khoảng ngày. Không dùng ExportJob/worker/cloud storage trong MVP.

## 5. Đặc tả từng module

### M01. Tài khoản và quyền — mem1

**Files:** backend/school_app/accounts/models.py, forms.py, services.py, permissions.py, views.py, urls.py.

**Đầu vào:** Tài khoản/mật khẩu; role HOMEROOM_TEACHER/SUPERVISOR/STUDENT; liên kết Student khi tạo học sinh.

**Luồng:** Django Auth xác minh → tạo session → trả danh tính và role → mỗi request service kiểm tra tài khoản active và classroom.teacher_id. Logout thu hồi phiên. Custom User được chọn ngay từ migration đầu tiên.

**Đọc/ghi:** User, Django session, Classroom và Student; không tự viết hash mật khẩu hoặc auth session riêng.

**Đầu ra:** me, role và phạm vi lớp. **Lỗi:** 401 chưa đăng nhập; 403/404 ngoài quyền; CSRF sai; tài khoản khóa.

**Nghiệm thu:** Giáo viên A không dùng ID lớp B; học sinh chỉ bản thân; mật khẩu không có trong response/log. **Tasks:** A01/A02/A07/A13.

### M02. Khối, lớp, GVCN — mem1

**Files:** backend/school_app/academics/models.py, forms.py, services.py, views.py, urls.py.

**Đầu vào:** Mã/tên khối, mã/tên lớp, grade_id, teacher_id.

**Luồng:** Giám thị tạo Grade → Classroom → gán User có role GVCN → service kiểm tra một GVCN trên lớp → ghi → phạm vi teacher cập nhật. Một GVCN có thể được giao nhiều lớp.

**Đọc/ghi:** Grade, Classroom, User. **Đầu ra:** Danh sách khối/lớp/GVCN.

**Lỗi:** Trùng mã lớp, gán student làm GVCN, thiếu quyền, xóa lớp có dữ liệu. **Nghiệm thu:** Trường teacher_id đơn trị; không xóa cứng lớp đang có học sinh/buổi. **Tasks:** A03.

### M03. Học sinh và ảnh — mem1

**Files:** backend/school_app/students/models.py, forms.py, services.py, views.py, urls.py; core/storage.py.

**Đầu vào:** Mã, họ tên, class_id, trạng thái active, ảnh tùy chọn.

**Luồng:** Kiểm tra quyền lớp → validate → tạo Student → liên kết User STUDENT nếu cần → trả lớp/khối suy ra. Ảnh upload qua form → Pillow kiểm tra nội dung thật → bỏ EXIF/chuẩn hóa → lưu vùng private → gắn vào Student sau khi thành công. Upload lỗi giữ ảnh cũ.

**Đọc/ghi:** Student, Classroom, Grade, User và private photo. **Đầu ra:** Hồ sơ/danh sách/tìm theo mã hoặc tên, ảnh tải có quyền.

**Lỗi:** Trùng mã; ảnh ngoài JPEG/PNG/WebP, quá 5 MB/quá giới hạn điểm ảnh; đổi class_id vượt quyền. **Nghiệm thu:** Trùng tên hợp lệ; ảnh không công khai; thiếu ảnh vẫn điểm danh được. **Tasks:** A04–A07.

Không xây enrollment lịch sử nhiều khoảng trong MVP. Giám thị có thể đổi class_id; chỉ roster buổi mới dùng lớp mới, buổi đã mở giữ snapshot. Hồ sơ đã có lịch sử dùng active=false thay vì xóa cứng.

### M04. Lịch và buổi học — mem2

**Files:** backend/school_app/schedules/models.py, forms.py, services.py, views.py, urls.py.

**Đầu vào:** Lớp, weekday, slot MORNING/AFTERNOON, giờ bắt đầu/đóng, grace_minutes, required_uniform SHIRT/SPORTS, ngày tạo buổi.

**Luồng:** GVCN/giám thị lưu ScheduleRule → tạo Session PLANNED cho ngày yêu cầu → mở Session → snapshot start/cutoff/uniform và roster học sinh active → tạo Attendance UNMARKED → OPEN, cùng transaction. Tạo/mở lặp không nhân đôi.

**Đọc/ghi:** ScheduleRule, Session, SessionRoster, Attendance; đọc Student/Classroom/Grade.

**Đầu ra:** Lịch lớp, buổi theo ngày, danh sách snapshot. **Lỗi:** Rule trùng, giờ không hợp lệ, thiếu lịch, ngoài quyền. **Nghiệm thu:** Unique lớp/ngày/slot; sửa rule không đổi OPEN/CLOSED. **Tasks:** B02–B06.

Ngày nghỉ chỉ cần không tạo/mở buổi; chưa xây calendar exception engine, generator hằng đêm hoặc scheduler.

### M05. Điểm danh, QR và xác minh — mem2

**Files:** backend/school_app/attendance/models.py, forms.py, services.py, views.py; backend/school_app/qr/models.py, forms.py, services.py, views.py; core/idempotency.py.

**Đầu vào:** Phiên học sinh và token QR; hoặc thao tác nhân sự chọn Attendance, trạng thái/arrived_at; expected_version và Idempotency-Key.

**Phát QR:** Nhân sự có quyền chọn OPEN → secrets tạo token tối thiểu 128 bit → lưu hash/hạn → qrcode tạo hình. Token đổi 30 giây, hết hạn 60 giây; không chứa tên/mã/mật khẩu; một challenge dùng được nhiều học sinh đúng roster.

**Quét:** student_id lấy từ session → kiểm tra token/hạn/OPEN/roster → QrScan PENDING, scanned_at của server → trả trạng thái chờ. Không chuyển PRESENT ngay.

**Xác minh:** Nhân sự xem tên/mã/ảnh/lớp/giờ quét → đối chiếu tại chỗ → confirm → transaction cập nhật Attendance PRESENT với arrived_at=scanned_at, source=QR, verifier/time → tính arrival status → scan CONFIRMED và ChangeLog. Có thể nhập đồng phục trong cùng transaction.

**Trùng/hết hạn:** Một PENDING trên roster. Quét lại khi PENDING giữ timestamp đầu; hết 15 phút chuyển EXPIRED tại API, không cần job. REJECTED/EXPIRED cho quét mới nếu còn OPEN. CONFIRMED trả trạng thái đã có mặt. MANUAL khi có PENDING làm SUPERSEDED; không đổi giờ thủ công bởi scan mới.

**Đọc/ghi:** QrChallenge, QrScan, Attendance, Session, SessionRoster, ChangeLog, IdempotencyRequest. **Đầu ra:** Trạng thái chờ/xác nhận, thời gian đến, ON_TIME/LATE, source, version.

**Lỗi:** 409 version/buổi đóng, 422 QR hết hạn/sai lớp/thiếu roster, 429 rate limit. **Nghiệm thu:** Quét 07:04, confirm 07:08 với cutoff 07:05 vẫn đúng giờ; pending không góp số có mặt; cùng QR nhiều học sinh hợp lệ. **Tasks:** B07–B11/B13/B14.

QR động không ngăn tuyệt đối chia sẻ mã hoặc tài khoản; xác minh nhân sự là bước bắt buộc. Thiếu điện thoại/camera/mạng dùng nhân sự nhập khi có kết nối, hồi tố có lý do; không có offline tự đồng bộ.

### M06. Đồng phục — mem2

**Files:** backend/school_app/attendance/uniform_rules.py, forms.py, services.py, views.py.

**Đầu vào:** Attendance PRESENT, loại thực tế, COMPLIANT/NON_COMPLIANT, lý do và expected_version.

**Luồng:** Đọc required_uniform snapshot → nhân sự đối chiếu thực tế → validate → ghi uniform_status/observed_uniform/reason/checked_by/checked_at → tăng version/ChangeLog → trả hàng đã lưu.

**Đọc/ghi:** Attendance, Session snapshot, ChangeLog. **Đầu ra:** Chuẩn, thực tế, kết quả, người/thời gian kiểm tra.

**Lỗi:** Vắng/chưa có mặt; thiếu lý do sai; buổi đóng; version cũ. **Nghiệm thu:** Không tự đạt vì có mặt; vắng NOT_APPLICABLE; chưa kiểm tra NOT_CHECKED; cùng form confirm QR + uniform rollback cùng nhau khi lỗi. **Tasks:** B12/B13.

### M07. Báo cáo và xuất — mem1

**Files:** backend/school_app/reports/queries.py, forms.py, services.py, exporters.py, views.py, urls.py.

**Đầu vào:** Khoảng ngày, lớp/khối, slot, status và định dạng xlsx/csv.

**Luồng:** Scope user → validate filter → query Session/roster/Attendance → đánh giá cùng bộ dòng kết quả → trả JSON chi tiết/tổng hợp hoặc file. Dùng snapshot lớp/khối/tên để giữ lịch sử; ảnh hồ sơ không kèm export.

**Đọc:** Session, SessionRoster, Attendance, Classroom để xác định quyền. **Đầu ra:** Chi tiết, tổng hợp, XLSX/CSV và metadata ngày xuất/timezone/bộ lọc.

**Lỗi:** Bộ lọc ngoài quyền; trên 5.000 dòng; ngày không hợp lệ. **Nghiệm thu:** Export giống báo cáo cùng dữ liệu/bộ lọc, UTF-8 đúng dấu, không spreadsheet formula injection, student không được xuất. **Tasks:** A08–A13.

### M08. Tích hợp và bàn giao — cả hai

**Files:** backend/tests; docs/api-contract.md; docs/api-acceptance.md; api-requests.http; command seed_demo; README.

**Luồng:** Seed dữ liệu giả → gọi từng API theo workflow → kiểm tra quyền/quét/đồng phục/số liệu → sửa lỗi → lưu bằng chứng → PM API gate → mới bắt đầu frontend theo lịch. Không coi việc có thư mục hoặc file test rỗng là module đã hoàn thành.

**Nghiệm thu API gate:** Tất cả task API finish, có test result/request examples, không lỗi chặn workflow, PM phê duyệt. **Tasks:** A14–A15/B13–B15; nghiệm thu cuối A19–A20/B19–B20 sau frontend đã được mở.

## 6. Data dictionary MVP

| Model | Trường chính | Ràng buộc |
| --- | --- | --- |
| User | id UUID, username, password hash Django, role, is_active, student link optional | Custom User từ đầu; identity theo session; student link một-một |
| Grade | id, code, name | Code duy nhất |
| Classroom | id, code, name, grade_id, teacher_id | Code duy nhất; một GVCN đúng role |
| Student | id, student_code, full_name, class_id, photo_path?, active | Mã duy nhất; lớp/khối suy ra; ảnh private |
| ScheduleRule | id, class_id, weekday, slot, start_time, close_time, grace_minutes, required_uniform | Unique lớp/thứ/buổi; giờ hợp lệ |
| Session | id, class_id, school_date, slot, status, start_at, late_cutoff_at, close_at, required_uniform_snapshot, version | Unique lớp/ngày/buổi; snapshot khi mở |
| SessionRoster | id, session_id, student_id, code/name/class/grade snapshots | Unique session/student |
| Attendance | id, roster_id, status, arrived_at?, source?, absence_reason?, observed_uniform?, uniform_status, uniform_reason?, uniform_note?, verified_by?, verified_at?, checked_by?, checked_at?, version, updated_at | Unique roster; status/time/uniform hợp lệ; source QR/MANUAL |
| QrChallenge | id, session_id, token_hash, issued_by, issued_at, expires_at | Token không lưu rõ; không nhận khi buổi đóng |
| QrScan | id, roster_id, challenge_id, student_user_id, scanned_at, expires_at, status, resolved_by?, resolved_at?, version, reason? | Tối đa một PENDING trên roster |
| IdempotencyRequest | actor_id, operation, key, payload_hash, response_json, expires_at | Unique actor/operation/key; key khác payload trả 409; lưu 24 giờ |
| ChangeLog | id, entity_type, entity_id, action, actor_id, before/after JSON, reason?, recorded_at | Append từ service; không token/mật khẩu/ảnh |

Dùng UUIDField, TextChoices, DateField và DateTimeField với USE_TZ=True. Django migrations/constraints bảo vệ unique và foreign key; service bảo vệ phạm vi quyền/trạng thái. Không tạo School/tenant/SchoolYear/Enrollment/CorrectionRequest/ExportJob/ExportRow/Asset riêng trong MVP này. Ảnh quản lý bởi private storage và trường photo_path; export nhỏ tạo đồng bộ.

Quan hệ: Grade → Classroom → Student; Classroom → ScheduleRule/Session; Session → SessionRoster → Attendance; QrChallenge → QrScan → SessionRoster; User student link → Student. ChangeLog tham chiếu entity_id của thao tác.

## 7. Hợp đồng API

### 7.1 Quy ước

Base /api/v1; JSON UTF-8; datetime ISO 8601 có timezone; ngày YYYY-MM-DD. Cookie session HttpOnly, Django CSRF cho request ghi. expected_version khi cập nhật; Idempotency-Key cho ghi điểm danh/scan/confirm. Error {code,message,details,request_id}. 401 chưa đăng nhập; 403/404 ngoài quyền; 409 trùng/version/trạng thái; 422 nghiệp vụ; 429 rate limit.

View/form chỉ parse/validate request; service giữ nghiệp vụ; cùng service cho manual và QR. JSON view dùng JsonResponse; chưa cần DRF/SPA. URL cho HTML sẽ bổ sung sau API gate, dùng cùng service.

| Module | Endpoint | Tác dụng / quyền |
| --- | --- | --- |
| M01 | POST /auth/login; POST /auth/logout; GET /auth/me | Phiên và danh tính |
| M02 | GET/POST /grades; GET/POST /classes; PATCH /classes/:id | Ghi chỉ giám thị; đọc theo scope |
| M03 | GET/POST /students; GET/PATCH /students/:id | GVCN lớp mình/giám thị |
| M03 | POST /students/:id/photo; GET /students/:id/photo | Upload/thay/tải ảnh có quyền |
| M04 | GET/POST /classes/:id/schedule-rules; PATCH /schedule-rules/:id | Lịch lớp đúng scope |
| M04 | POST /sessions; GET /sessions; GET /sessions/:id | Tạo/xem buổi |
| M04/M05 | POST /sessions/:id/open; POST /sessions/:id/close | Snapshot/mở/chốt; có quyền |
| M05 | GET /sessions/:id/roster; PATCH /attendance/:id | Xem roster, ghi thủ công/vắng |
| M05 QR | POST /sessions/:id/qr-challenges | Nhân sự phát QR của OPEN |
| M05 QR | GET /me/today-sessions; POST /qr-scans; GET /me/scan-status | STUDENT chỉ bản thân |
| M05 QR | GET /sessions/:id/qr-scans; POST /qr-scans/:id/confirm; POST /qr-scans/:id/reject | Nhân sự xác minh/từ chối |
| M06 | PATCH /attendance/:id/uniform | Kết quả đồng phục |
| M07 | GET /reports/attendance; GET /reports/summary | Chi tiết/tổng hợp theo quyền |
| M07 | GET /reports/export?format=xlsx hoặc csv | Xuất đồng bộ tối đa 5.000 dòng |

Tạo tài khoản ban đầu qua Django Admin/seed và service, không mở đăng ký công khai. UI quản trị về sau không được sửa attendance trực tiếp qua Admin.

### 7.2 Payload minh họa confirm QR + đồng phục

```json
{
  "expected_attendance_version": 0,
  "expected_scan_version": 0,
  "identity_confirmed": true,
  "uniform": {
    "observed_uniform": "SPORTS",
    "uniform_status": "NON_COMPLIANT",
    "reason": "Buổi này yêu cầu sơ mi"
  }
}
```

Server lấy arrived_at từ scanned_at. Không nhận student_id, source QR hoặc arrived_at tự khai trong confirm. Response trả PRESENT, source QR, arrived_at, verified_at, arrival_status, uniform_status, version mới.

## 8. Transaction, lỗi và giới hạn demo

Một lần ghi: xác thực/quyền → idempotency → transaction → kiểm tra OPEN và expected_version → validate attendance/uniform/scan → cập nhật + tăng version → ChangeLog + kết quả idempotency → commit → response. Key lặp cùng payload trả kết quả cũ; cùng key khác payload trả 409. Nếu mất response, retry cùng key; nếu lỗi không tick thành công.

SQLite dùng demo nhỏ, không phải bằng chứng đạt nhiều người ghi đồng thời. Dùng atomic, unique, conditional update theo version; khi database busy báo chưa lưu và retry đúng key. Nếu nhà trường yêu cầu chạy nhiều người thật, đổi PostgreSQL và kiểm chứng select_for_update/khóa session-attendance-scan trước; việc đó không nằm trong task hạ tầng tháng này. Giới hạn này phải được ghi khi demo, không hứa throughput toàn trường.

Không thu GPS, giấy tờ, phụ huynh hoặc ảnh đồng phục hằng ngày. Tệp ảnh private ngoài static; download kiểm tra quyền. Rate limit đăng nhập/scan; tránh log raw token; secret cấu hình qua môi trường. Không triển khai cloud/backup SLA. Dùng dữ liệu giả tại cuộc thi.

## 9. Báo cáo và công thức

Đơn vị thống kê là học sinh-buổi. Chỉ Session OPEN/CLOSED; PLANNED không vào kết quả.

```text
expected = present + absent + unmarked
present = on_time + late
present = compliant + non_compliant + not_checked

tỷ lệ có mặt = present / expected
tỷ lệ đi muộn = late / present
đã kiểm tra = compliant + non_compliant
tỷ lệ vi phạm = non_compliant / đã kiểm tra
độ bao phủ kiểm tra = đã kiểm tra / present
```

Mẫu số 0 trả null và hiển thị “—”. UNMARKED không phải ABSENT; QR PENDING không phải PRESENT. Vắng không vào mẫu số kiểm tra đồng phục. Khi chốt UNMARKED đổi ABSENT, số present không đổi.

Ví dụ 40 roster: 34 present (30 đúng giờ, 4 muộn), 3 absent, 3 unmarked; trong present có 27 compliant, 4 non_compliant, 3 not_checked. Có mặt 85%, muộn 11,76%, vi phạm trong số kiểm tra 12,90%, bao phủ 91,18%. Hai trong ba unmarked đang PENDING vẫn không tăng present.

Cột xuất: ngày/buổi, mã/tên snapshot, lớp/khối snapshot, trạng thái, source, scanned_at nếu có, arrived_at, verified_at, đúng giờ/muộn, chuẩn đồng phục, loại thực tế, kết quả, lý do, người/giờ kiểm tra. XLSX có Chi_tiet/Tong_hop/Thong_tin; CSV UTF-8 BOM, quote/escape và bảo vệ formula injection. Không kèm ảnh hoặc mật khẩu.

## 10. Cấu trúc backend và ownership

```text
backend/
  config/                   cấu hình tương lai ở A01
  school_app/
    core/                   quy ước chung, storage, idempotency
    accounts/               mem1 — M01
    academics/              mem1 — M02
    students/               mem1 — M03
    schedules/              mem2 — M04
    attendance/             mem2 — M05/M06
    qr/                     mem2 — M05 QR
    reports/                mem1 — M07
    management_app/
      management/commands/  seed_demo tại A14
  tests/                    kiểm chứng module và quyền
docs/
  thiet-ke-he-thong-diem-danh.md
  ke-hoach-1-thang.md
  project-management/
    tasks.json
    task-tracker.xlsx
    create_task_sheet.gs
    README.md
```

Cấu trúc này đã có implementation backend: A01/config/User từ migration đầu, B01/enum/contract, các API auth/lớp/Student/ảnh/lịch/attendance/QR/uniform/report/export và seed_demo. Xem evidence/backend-api.md và docs/api-acceptance.md cho kiểm chứng/review. Không tạo templates/static/frontend; đường dẫn giao diện task ngày16–18 vẫn là kế hoạch sau PM duyệt.

Mỗi app dùng models/forms/views/services/urls và migrations khi có model. Không tách repository hoặc service nhỏ không cần thiết. Đồng phục nằm trong attendance để dùng cùng transaction. Hai thành viên thống nhất field và import trước khi tạo cross-app migrations; người sở hữu module review thay đổi vào module mình.

## 11. Kế hoạch module trong một tháng

Lịch task chi tiết, dependencies, giờ dự kiến và acceptance nằm trong tasks.json/bảng Sheets. ID A thuộc mem1, B thuộc mem2. Thay tên/ngày tại Config, không cần đổi từng dòng.

### T01. Nền tảng và quyền — A01–A02/B01

- [ ] mem1 tạo Django/config/custom User và Auth/session.
- [ ] mem2 chốt payload/model/enum, không thêm tính năng ngoài MVP.
- [ ] Cả hai review hợp đồng, migration và phạm vi quyền.
- [ ] Chạy check/migrate từ database rỗng và test quyền.

### T02. Lớp, học sinh, ảnh — A03–A07

- [ ] Khối/lớp và một GVCN.
- [ ] Hồ sơ/mã/lớp/khối/tài khoản học sinh.
- [ ] Upload/tải ảnh private và test scope.
- [ ] Cung cấp dữ liệu/schema cho mem2 tạo roster.

### T03. Lịch và buổi — B02–B06

- [ ] Lịch tuần/đồng phục/giờ và buổi theo ngày.
- [ ] Snapshot roster/chuẩn khi OPEN.
- [ ] Chốt tối thiểu, trạng thái không nhân đôi.
- [ ] Kiểm chứng schedule/session bằng fixture.

### T04. Điểm danh và QR — B07–B11

- [ ] Manual/vắng/thời gian đến, unique/version/idempotency.
- [ ] QR challenge, scan PENDING và xác minh.
- [ ] Hết hạn/sai lớp/quét lặp/manual supersede.
- [ ] Giờ đến theo scan, không theo confirm.

### T05. Đồng phục — B12–B14

- [ ] Validate chỉ PRESENT được kiểm tra.
- [ ] Đạt/không đạt/chưa kiểm tra, lý do không đạt.
- [ ] Confirm + uniform atomically, test chốt/xung đột.

### T06. Báo cáo/XLSX/CSV — A08–A13

- [ ] Query/filters theo quyền và công thức.
- [ ] Báo cáo chi tiết/tổng hợp, export nhỏ đồng bộ.
- [ ] Đối soát QR/manual/uniform và file.
- [ ] Kiểm chứng student/teacher không xuất ngoài scope.

### T07. API gate — A14–A15/B13–B15

- [ ] Seed giả, request collection và tài liệu API.
- [ ] Luồng toàn hệ thống kiểm chứng không cần frontend.
- [ ] Có bằng chứng task API hoàn tất, PM duyệt.
- [ ] Chỉ khi được duyệt mới mở các task FRONTEND_LATER.

### T08. Giao diện và nghiệm thu sau gate — A16–A20/B16–B20

- [ ] Đây là task dự kiến cuối tháng, hiện chưa thực hiện.
- [ ] mem1 làm giao diện module của mình; mem2 làm giao diện module của mình.
- [ ] Kiểm chứng thiết bị/quyền/báo cáo, sửa lỗi, luyện demo.
- [ ] Nếu API gate trễ, PM điều chỉnh lịch; không tạo frontend sớm.

## 12. Nghiệm thu và cách dùng task tracker

| Mã | Ca kiểm chứng | Kết quả cần đạt |
| --- | --- | --- |
| AC01 | Giáo viên A dùng ID lớp B | Không đọc/sửa/điểm danh/ảnh/export được |
| AC02 | Giám thị theo dõi tất cả lớp | Đúng phạm vi toàn trường |
| AC03 | Hai học sinh cùng tên, mã khác | Cả hai hợp lệ; mã trùng bị từ chối |
| AC04 | Ảnh giả loại/quá 5 MB | Từ chối, giữ ảnh cũ |
| AC05 | Tạo/mở buổi hai lần | Một session/roster/attendance duy nhất |
| AC06 | Sửa lịch sau mở | Snapshot buổi cũ giữ nguyên |
| AC07 | Đến đúng cutoff và sau 1 giây | ON_TIME/LATE đúng |
| AC08 | Quét 07:04, confirm 07:08, cutoff 07:05 | Có mặt đúng giờ, arrived 07:04 |
| AC09 | PENDING chưa xác minh | Không tính present/đạt đồng phục |
| AC10 | Hai học sinh cùng challenge | Mỗi người scan hợp lệ |
| AC11 | Scan trùng một học sinh | Một pending, giữ timestamp đầu |
| AC12 | Token hết hạn/sai lớp | Từ chối, không có mặt |
| AC13 | Student A tự gửi ID B | Không ghi cho B |
| AC14 | Pending quá 15 phút | EXPIRED; API tự kiểm tra |
| AC15 | Manual khi pending | Attendance MANUAL, scan SUPERSEDED |
| AC16 | Vắng hoặc chưa có mặt kiểm tra đồng phục | Từ chối; NOT_APPLICABLE |
| AC17 | Có mặt chưa kiểm tra | NOT_CHECKED, không tự đạt |
| AC18 | NON_COMPLIANT thiếu lý do | Từ chối, rollback |
| AC19 | Confirm và uniform lỗi | Không ghi nửa transaction |
| AC20 | Retry cùng key / khác payload | Response cũ / 409, không nhân đôi |
| AC21 | Chốt còn unmarked/pending/not_checked | Chuyển vắng/expired, giữ not_checked |
| AC22 | Giáo viên sửa CLOSED | Bị chặn; giám thị sửa có lý do/log |
| AC23 | Ví dụ 40 roster tại mục 9 | Tổng và tỷ lệ đúng |
| AC24 | Lọc lớp ngoài quyền hoặc student export | Bị chặn |
| AC25 | CSV/XLSX dữ liệu dấu tiếng Việt và formula | Đúng Unicode, không chạy formula |
| AC26 | Hơn 5.000 dòng | Trả hướng dẫn chia khoảng ngày |
| AC27 | File test chỉ có docstring | Không được xem là test API đạt |
| AC28 | Frontend chưa API gate | Task blocked, chưa tạo frontend |

Task tracker có Config, Tasks, Dashboard và Modules. Tick Finish? để Status tự đổi finish/unfinish. PM ghi cột PM Comment; người làm gắn link PR/test/evidence. Dependencies chưa finish làm task blocked. Task frontend và QA cần toàn bộ API finish + API_Gate APPROVED. Gate là quyết định của PM, không tự suy ra chỉ từ checkbox.

Các lệnh nền A01 đã chạy: python manage.py check; migrate trên database rỗng; makemigrations --check --dry-run; test (9 ca nền); pip check. Evidence ở docs/project-management/evidence/a01-b01.md. Chạy trong backend với đúng môi trường Python/dependencies; test nền không chứng minh API nghiệp vụ hay concurrency/tải lớn đã đạt trên SQLite.

Tài liệu và bảng tracker là kế hoạch thực hiện, không phải bằng chứng API đã được xây dựng. Mọi task nghiệp vụ khởi tạo unfinish; các task frontend vẫn giữ trạng thái blocked đến khi PM duyệt API.
