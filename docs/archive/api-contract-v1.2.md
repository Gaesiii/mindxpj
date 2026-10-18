# Hợp đồng module/API — B01

Nguồn chuẩn: [MVP v1.2](thiet-ke-he-thong-diem-danh.md). Đây là hợp đồng kỹ thuật để mem1/mem2 nối module; không thay thế phê duyệt API gate. Backend auth, lớp/Student/ảnh, lịch/buổi, attendance/QR/uniform và report/export đã triển khai theo yêu cầu toàn bộ backend ngày14/10/2026. Kiểm chứng/review từng đợt nằm trong evidence/backend-api.md; PM/member review và gate chờ xác nhận. Không có frontend.

## 1. Quy ước dùng chung

- Backend một project Django, Django ORM/Auth/Forms và JsonResponse; không DRF.
- Base `/api/v1`, đường dẫn không có dấu `/` cuối; không redirect để sửa URL request ghi. `:id` trong tài liệu phải thay bằng UUID thật.
- Mọi ID thực thể là UUID, JSON dạng chuỗi có dấu gạch. ID User, Student, SessionRoster, Attendance, QrScan là các ID khác nhau.
- JSON UTF-8. Object response trả trực tiếp; danh sách trả `{"items": [...]}`. Tạo mới trả 201; đọc/sửa/thao tác hoặc retry đã tồn tại trả 200. Logout trả 200 với `{"ok": true}`. Không dùng status 200 để báo lỗi.
- `school_date`: YYYY-MM-DD. `start_time`/`close_time`: HH:MM:SS, giờ địa phương Việt Nam, không gắn Z; không hỗ trợ buổi qua ngày trong MVP.
- `weekday` dùng số 0–6 theo Python `date.weekday()`: 0 Thứ Hai, 6 Chủ Nhật. Không dùng ISO weekday 1–7.
- `TIME_ZONE=Asia/Ho_Chi_Minh`, `USE_TZ=True`. Thời điểm lưu UTC; response datetime ISO 8601 UTC có `Z` (hoặc chuẩn hóa `+00:00`). Đầu vào datetime phải có offset; `07:04:00+07:00` tương ứng `00:04:00Z`. Từ chối datetime không timezone; không tin đồng hồ client.
- Version là số nguyên không âm, bắt đầu 0; ghi thành công tăng 1. Không nhận role, actor, verifier, timestamp server, source hoặc snapshot tùy ý từ payload.
- Chuỗi bắt buộc không được rỗng sau trim. Trường tùy chọn chưa có giá trị trả null; không dùng chuỗi `"null"`. PATCH chỉ đổi field có mặt; field ngoài danh sách cho phép trả 422, không bỏ qua danh tính giả gửi lên.
- Khóa dependency ở `backend/requirements.txt`. Enum import từ `school_app.core.enums`, không khai báo bản sao ở từng app.

## 2. Enum chuẩn

| Class Python | Giá trị lưu/JSON |
| --- | --- |
| Role | HOMEROOM_TEACHER, SUPERVISOR, STUDENT |
| Weekday | MONDAY=0, TUESDAY=1, WEDNESDAY=2, THURSDAY=3, FRIDAY=4, SATURDAY=5, SUNDAY=6 |
| Slot | MORNING, AFTERNOON |
| SessionStatus | PLANNED, OPEN, CLOSED |
| AttendanceStatus | UNMARKED, PRESENT, ABSENT |
| ArrivalStatus | ON_TIME, LATE, NOT_APPLICABLE |
| RequiredUniform | SHIRT, SPORTS |
| ObservedUniform | SHIRT, SPORTS, OTHER, UNKNOWN |
| UniformStatus | NOT_CHECKED, COMPLIANT, NON_COMPLIANT, NOT_APPLICABLE |
| AttendanceSource | QR, MANUAL |
| QrScanStatus | PENDING, CONFIRMED, REJECTED, EXPIRED, SUPERSEDED |

ArrivalStatus được tính khi serialize/báo cáo từ Attendance và cutoff snapshot, không tạo một nguồn trạng thái lưu trùng. Source chưa ghi nhận là null. PRESENT ban đầu có uniform_status=NOT_CHECKED; ABSENT/UNMARKED dùng NOT_APPLICABLE. PRESENT không tự đồng nghĩa COMPLIANT.

## 3. Dictionary và quan hệ giữa module

Trừ khi ghi khác, `id` là UUID primary key. Mọi FK JSON dùng hậu tố `_id`. Giá trị `class_id` trong API tương ứng field Python `classroom` (Django tạo `classroom_id`, tránh từ khóa Python `class`). Hai bạn phải serialize/map theo bảng này, không tự đổi API thành classroom_id.

| Model / owner | Trường và kiểu | Ràng buộc / ghi chú |
| --- | --- | --- |
| accounts.User / mem1 | id UUID; username string; password hash Django; role Role; is_active bool; student nullable OneToOne(Student) ở A05 | Username unique; custom User từ migration đầu. A01 chưa có Student nên chưa có field student. is_staff/is_superuser là cờ vận hành, không bypass quyền nghiệp vụ. Role mặc định STUDENT; tài khoản chưa link không được quét. |
| academics.Grade / mem1 | id; code, name string | code unique |
| academics.Classroom / mem1 | id; code, name string; grade FK; teacher FK(User) | code unique; một teacher hiện tại, role HOMEROOM_TEACHER; một teacher có thể nhiều lớp |
| students.Student / mem1 | id; student_code, full_name string; classroom FK; photo_path nullable string; active bool | student_code unique; trùng tên được phép; grade suy từ classroom; photo_path do server quản lý |
| schedules.ScheduleRule / mem2 | id; classroom FK; weekday Weekday; slot Slot; start_time, close_time TimeField; grace_minutes integer >=0; required_uniform RequiredUniform | unique(classroom, weekday, slot); start_time < close_time; cutoff không sau close_time |
| schedules.Session / mem2 | id; classroom FK; school_date DateField; slot Slot; status SessionStatus; start_at, late_cutoff_at, close_at nullable aware datetime; required_uniform_snapshot nullable RequiredUniform; version integer | unique(classroom, school_date, slot); giờ/chuẩn chính thức chốt snapshot khi mở, null nếu PLANNED chưa mở; OPEN/CLOSED bắt buộc snapshot đầy đủ |
| schedules.SessionRoster / mem2 | id; session FK; student FK; student_code_snapshot, full_name_snapshot, class_code_snapshot, class_name_snapshot, grade_code_snapshot, grade_name_snapshot string | unique(session, student); snapshot bất biến từ OPEN; student hiện tại đổi lớp không đổi dòng cũ |
| attendance.Attendance / mem2 | id; roster OneToOne; status AttendanceStatus; arrived_at nullable aware datetime; source nullable AttendanceSource; absence_reason nullable string; observed_uniform nullable ObservedUniform; uniform_status UniformStatus; uniform_reason, uniform_note nullable string; verified_by, checked_by nullable FK(User); verified_at, checked_at nullable aware datetime; version integer; updated_at aware datetime | một bản ghi/roster; version=0 khi mở; PRESENT cần arrived_at; ABSENT/UNMARKED không có arrived_at/source/observed_uniform, uniform NOT_APPLICABLE |
| qr.QrChallenge / mem2 | id; session FK; token_hash string; issued_by FK(User); issued_at, expires_at aware datetime | Không lưu token rõ; tối thiểu 128 bit ngẫu nhiên; token dùng cho nhiều học sinh; hết hạn sau 60s |
| qr.QrScan / mem2 | id; roster FK; challenge FK; student_user FK(User); scanned_at, expires_at aware datetime; status QrScanStatus; resolved_by nullable FK(User); resolved_at nullable aware datetime; version integer; reason nullable string | một PENDING/roster qua conditional unique; hết hạn xác minh sau 15 phút; scanned_at server và bất biến |
| core.IdempotencyRequest / chung B08 | actor FK(User); operation string; key string; payload_hash string; response_json JSON; expires_at aware datetime | unique(actor, operation, key); 24h; response lưu cả HTTP status và body để retry chính xác |
| core.ChangeLog / chung B08 | id; entity_type string; entity_id UUID; action string; actor FK(User); before, after JSON; reason nullable string; recorded_at aware datetime | Append qua service; không token rõ, mật khẩu hoặc ảnh |

`recorded_at` của thao tác điểm danh nằm trong ChangeLog; thời gian hiện tại của bản ghi là updated_at. Không tự thêm Attendance.recorded_at làm bản sao mơ hồ. `arrival_status` là trường response tính toán. IdempotencyRequest có thể dùng surrogate id mặc định của Django, không expose ra API.

Field string thực tế/giới hạn độ dài được owner chọn khi triển khai model và review trước migration; không tự đổi tên, kiểu quan hệ, enum hoặc unique ở bảng này. Không tạo School, SchoolYear, Enrollment, CorrectionRequest, ExportJob hay Asset.

### Thứ tự migration đã phối hợp trong baseline

1. A01: accounts/0001_initial tạo User UUID + role; chưa FK tới Student.
2. A03: academics tạo Grade/Classroom, dùng `settings.AUTH_USER_MODEL` và `migrations.swappable_dependency`.
3. A04: students tạo Student phụ thuộc academics.
4. A05: accounts migration bổ sung `student=OneToOneField("students.Student", null=True, blank=True, on_delete=PROTECT)` phụ thuộc students; student link unique. Service bắt buộc active STUDENT có đúng hồ sơ trước quét; các role nhân sự không được gắn Student.
5. B04/B05: schedules tham chiếu Student/Classroom và User. Nếu mở buổi gọi service attendance, import trong service sau setup, không circular import model.
6. B06: tạo model/migration Attendance phụ thuộc SessionRoster ở B05, để mở buổi tạo được UNMARKED. B07 bổ sung API roster/manual/vắng trên model đó. QR phụ thuộc roster/attendance/User ở B09–B11. Core model idempotency/log chỉ phụ thuộc User, không FK ngược attendance/qr; entity_id trong ChangeLog là UUID tham chiếu logic.

FK dữ liệu lịch sử dùng PROTECT; hồ sơ có lịch sử ngừng hoạt động thay vì xóa. Không thêm model Student rỗng để làm migration accounts chạy. Không xóa/đánh lại migration đã chia sẻ; khi đổi schema ghi migration mới và review dependency graph cùng nhau.

## 4. Auth, phạm vi quyền và lỗi

Đăng nhập dùng Django Auth/cookie session HttpOnly. Request ghi cần Django CSRF (`csrftoken` và header `X-CSRFToken`); không dùng csrf_exempt. GET /auth/me cấp cookie CSRF cả khi chưa đăng nhập và trả 401; client giữ cookie và gửi X-CSRFToken khi login. Login thành công đổi CSRF token, cần dùng token mới cho logout/request ghi tiếp theo. Không có đăng ký công khai.

### Auth A02 và bàn giao B03

- POST /auth/login nhận đúng `{username,password}` chuỗi JSON; role/student_id/class_id không được nhận từ body. Sai mật khẩu, tài khoản không có hoặc bị khóa trả cùng 401 INVALID_CREDENTIALS. JSON hỏng trả 400; sai schema/field thừa trả 422. Không log/response mật khẩu hoặc hash.
- GET /auth/me và login thành công trả `{id,username,role,student_id,class_ids}`. STUDENT chỉ student_id liên kết và class_ids của hồ sơ active; nhân sự student_id=null, class_ids theo lớp hiện tại trong scope. Không có lớp được giao thì class_ids=[]. Không trả role/danh tính do client chọn.
- POST /auth/logout dùng body `{}`, CSRF hợp lệ và phiên đang đăng nhập; flush phiên và trả `{ok:true}`. Cookie phiên cũ không còn quyền.
- Provision tài khoản là thao tác cục bộ qua service/management command, không endpoint public. Xem `backend/school_app/accounts/README.md`; chưa tạo Student link ở A02.
- B03 có ScheduleRuleForm, SessionCreateForm và SessionVersionForm; B04–B06 có model/API lịch và test mở lặp/snapshot/chốt/rollback. ScheduleRuleForm PATCH nhận current payload đã scope từ service, validate sau merge. Sử dụng required_uniform, không uniform_type; class_id của rule chỉ từ URL. Bool/string không thay số nguyên JSON weekday/grace/expected_version.

Service kiểm tra request.user đã authenticate/active rồi mới đọc/ghi. Không xem is_superuser như SUPERVISOR; muốn demo giám thị phải gán role SUPERVISOR rõ ràng. GVCN dùng Classroom.teacher_id hiện tại ở mọi API/ảnh/export; đổi GVCN làm quyền cũ mất ngay, giáo viên mới xem được lịch sử lớp. Không chỉ lọc response sau khi đã đọc dữ liệu ngoài quyền.

STUDENT chỉ /auth/me, /me/today-sessions, /qr-scans và /me/scan-status cho chính mình, cùng hồ sơ tối thiểu bản thân nếu triển khai. Danh tính quét lấy `request.user.student_id` sau liên kết A05; không nhận student_id/student_user_id trong body. Trước liên kết trả 403 STUDENT_NOT_LINKED. Nhân sự không quét thay bằng cách gửi student_id. Photo/export kiểm tra quyền như API đọc/ghi.

Lỗi luôn có dạng dưới đây trong chế độ DEBUG=false; DEBUG=true chỉ dành phát triển, Django có thể hiển thị trang debug cho lỗi chưa xử lý. Không đưa stack trace vào response nghiệp vụ.

```json
{
  "code": "VERSION_CONFLICT",
  "message": "Bản ghi đã thay đổi, hãy đọc lại",
  "details": {"expected_version": 0, "current_version": 1},
  "request_id": "00000000-0000-4000-8000-000000000001"
}
```

request_id do server sinh mới mỗi request và trả header X-Request-ID; không tin header client. Retry idempotency giữ status/body nghiệp vụ cũ nhưng thay request_id/header cho request mới. Không trả raw exception, token QR, password hoặc đường dẫn ảnh riêng tư trong lỗi/log.

| HTTP | code chuẩn / trường hợp |
| --- | --- |
| 400 | BAD_REQUEST: JSON sai cú pháp/encoding |
| 401 | UNAUTHENTICATED, INVALID_CREDENTIALS: chưa đăng nhập hoặc sai thông tin, không tiết lộ tài khoản tồn tại |
| 403 | FORBIDDEN, CSRF_FAILED, STUDENT_NOT_LINKED |
| 404 | NOT_FOUND: không tồn tại hoặc object ngoài phạm vi, tránh dò ID |
| 409 | DUPLICATE, VERSION_CONFLICT, SESSION_CLOSED, INVALID_STATE, IDEMPOTENCY_CONFLICT, DATABASE_BUSY |
| 422 | VALIDATION_ERROR, QR_INVALID, QR_EXPIRED, ROSTER_REQUIRED, EXPORT_LIMIT_EXCEEDED |
| 429 | RATE_LIMITED, kèm Retry-After |
| 500 | INTERNAL_ERROR: lỗi không dự kiến, thông báo chung |

A01 helper `error_response(request, code, message, status, details=None)` và handler 400/403/404/500/CSRF đã có. Các code/service 401/409/422/429 triển khai ở task nghiệp vụ. Service từ chối phạm vi filter chủ động với 403; tìm object cụ thể ngoài scope với 404.

## 5. Endpoint và payload chuẩn cho mem2

Tất cả đường dẫn dưới đây cộng tiền tố /api/v1, đã implement trong đợt backend sau B01. JSON minh họa dùng UUID giả; thay bằng ID từ API/seed. Request ghi phải kèm cookie/CSRF hợp lệ theo quyền; xem api-requests.http.

### Lịch, tạo/mở/chốt buổi

| Method / đường dẫn | Request | Kết quả / quyền |
| --- | --- | --- |
| GET/POST /classes/:id/schedule-rules | POST payload lịch dưới đây | items / ScheduleRule; GVCN lớp được giao hoặc giám thị |
| PATCH /schedule-rules/:id | Các field lịch cần sửa | Rule đã lưu; rule không đổi snapshot OPEN/CLOSED |
| POST /sessions | class_id, school_date, slot | Session PLANNED; tạo lặp trả Session cũ 200, không nhân đôi |
| GET /sessions | Query class_id, date_from, date_to, slot tùy chọn | items theo scope |
| GET /sessions/:id | Không body | Session và snapshot |
| POST /sessions/:id/open | expected_version | Atomically snapshot, roster, attendance; OPEN; lặp OPEN trả trạng thái hiện tại, CLOSED không mở lại |
| POST /sessions/:id/close | expected_version | CLOSED và số chuyển đổi; lặp CLOSED trả kết quả hiện tại; PLANNED phải mở trước |
| GET /sessions/:id/roster | Không body | items gồm roster ID, Student ID và snapshot, Attendance ID/status/version |

```json
{
  "weekday": 0,
  "slot": "MORNING",
  "start_time": "07:00:00",
  "close_time": "08:00:00",
  "grace_minutes": 5,
  "required_uniform": "SHIRT"
}
```

class_id lấy từ URL rule; không nhận class_id mâu thuẫn trong body. PATCH rule không có version vì dictionary ScheduleRule chưa có version. Tạo Session:

```json
{
  "class_id": "00000000-0000-4000-8000-000000000010",
  "school_date": "2026-10-12",
  "slot": "MORNING"
}
```

Mở/chốt dùng `{"expected_version": 0}` theo version đã GET. Mở snapshot chỉ Student active; Attendance khởi tạo UNMARKED, uniform NOT_APPLICABLE, version 0. Chốt chuyển UNMARKED→ABSENT, PENDING→EXPIRED, giữ PRESENT và NOT_CHECKED; response có `converted_unmarked`, `expired_pending`, `remaining_not_checked`. Trước chốt, GET roster/hàng đợi cho biết số chưa xử lý. Khóa phiên/version tránh tạo nửa roster; SQLite busy không báo thành công.

Session OPEN response ví dụ:

```json
{
  "id": "00000000-0000-4000-8000-000000000020",
  "class_id": "00000000-0000-4000-8000-000000000010",
  "school_date": "2026-10-12",
  "slot": "MORNING",
  "status": "OPEN",
  "start_at": "2026-10-12T00:00:00Z",
  "late_cutoff_at": "2026-10-12T00:05:00Z",
  "close_at": "2026-10-12T01:00:00Z",
  "required_uniform_snapshot": "SHIRT",
  "version": 1
}
```

### Điểm danh thủ công và đồng phục

PATCH /attendance/:id và PATCH /attendance/:id/uniform cần Idempotency-Key + expected_version. Nhân sự đúng scope; CLOSED chỉ SUPERVISOR có reason và ChangeLog. Không có workflow duyệt sửa.

```json
{
  "expected_version": 0,
  "status": "PRESENT",
  "arrived_at": "2026-10-12T07:10:00+07:00",
  "reason": "Nhập hồi tố vì học sinh không có điện thoại"
}
```

Manual server gán source=MANUAL; không nhận source/verified_by/verified_at. PRESENT bắt buộc arrived_at aware cùng school_date tại Việt Nam, không tương lai; hồi tố cần reason. Vắng gửi status=ABSENT, absence_reason tùy chọn; arrived_at/source/observed_uniform phải null và uniform NOT_APPLICABLE. Không cho client reset UNMARKED. Ghi manual khi có scan PENDING làm SUPERSEDED trong cùng transaction.

```json
{
  "expected_version": 1,
  "observed_uniform": "SPORTS",
  "uniform_status": "NON_COMPLIANT",
  "reason": "Buổi này yêu cầu sơ mi",
  "note": ""
}
```

Trong payload uniform, reason→uniform_reason và note→uniform_note. OTHER bắt buộc note mô tả. Chỉ PRESENT được kiểm tra; COMPLIANT phải đúng required_uniform_snapshot; NON_COMPLIANT cần reason. checked_by/checked_at do server. observed_uniform UNKNOWN có thể đi với NON_COMPLIANT có lý do, không cho COMPLIANT. Không nhận NOT_APPLICABLE/NOT_CHECKED như kết luận kiểm tra.

Attendance response dùng field model, thêm arrival_status tính toán:

```json
{
  "id": "00000000-0000-4000-8000-000000000030",
  "roster_id": "00000000-0000-4000-8000-000000000031",
  "status": "PRESENT",
  "source": "QR",
  "arrived_at": "2026-10-12T00:04:00Z",
  "arrival_status": "ON_TIME",
  "absence_reason": null,
  "observed_uniform": "SPORTS",
  "uniform_status": "NON_COMPLIANT",
  "uniform_reason": "Buổi này yêu cầu sơ mi",
  "uniform_note": null,
  "verified_by_id": "00000000-0000-4000-8000-000000000040",
  "verified_at": "2026-10-12T00:08:00Z",
  "checked_by_id": "00000000-0000-4000-8000-000000000040",
  "checked_at": "2026-10-12T00:08:00Z",
  "version": 1,
  "updated_at": "2026-10-12T00:08:00Z"
}
```

Đến đúng cutoff vẫn ON_TIME, sau một giây LATE. ABSENT/UNMARKED có arrival_status NOT_APPLICABLE. required_uniform_snapshot lấy từ Session, có thể kèm trong roster/report nhưng không ghi trùng lên Attendance.

### QR và danh tính học sinh

| Method / đường dẫn | Request | Response / quy tắc |
| --- | --- | --- |
| POST /sessions/:id/qr-challenges | `{}` | id, session_id, token, issued_at, expires_at, refresh_after_seconds=30, qr_image_base64 (PNG); chỉ nhân sự, Session OPEN |
| GET /me/today-sessions | Không body | items gồm Session và Attendance của chính học sinh theo roster hôm nay tại Việt Nam |
| POST /qr-scans | `{"token":"opaque-token"}` + Idempotency-Key | QrScan PENDING; 201 khi mới, 200 khi lặp; tuyệt đối không student_id |
| GET /me/scan-status | Query session_id | scan nullable và attendance của bản thân; không có quyền hỏi Student khác |
| GET /sessions/:id/qr-scans | Query status tùy chọn, mặc định PENDING | items hàng đợi theo scope; expired đánh giá tại API, ảnh qua endpoint có quyền |
| POST /qr-scans/:id/confirm | Payload dưới đây + Idempotency-Key | `{"scan": {...}, "attendance": {...}}` sau transaction |
| POST /qr-scans/:id/reject | expected_scan_version, reason + Idempotency-Key | scan REJECTED, Attendance không đổi |

Challenge token ngẫu nhiên tối thiểu 128 bit, chỉ hash lưu DB. Challenge sống 60s, phát lại mỗi 30s khi client yêu cầu; token cũ còn hạn được dùng đến expires_at. Không job tự đổi token; API B09 tạo PNG, chưa màn hình/camera. Trả token rõ cho nhân sự khi phát; không log token, không nhúng tên/mã học sinh. Token xác định Session nên scan không nhận session_id tùy ý.

QrScan response:

```json
{
  "id": "00000000-0000-4000-8000-000000000050",
  "roster_id": "00000000-0000-4000-8000-000000000031",
  "status": "PENDING",
  "scanned_at": "2026-10-12T00:04:00Z",
  "expires_at": "2026-10-12T00:19:00Z",
  "version": 0
}
```

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

identity_confirmed phải true; uniform có thể bỏ qua (PRESENT/NOT_CHECKED). Không nhận student_id, source hoặc arrived_at trong confirm. Server arrived_at=scanned_at, verified_at=giờ confirm. Uniform lỗi rollback cả Attendance/Scan/ChangeLog/idempotency.

Một PENDING/roster, scan lặp giữ scanned_at đầu. Hết 15 phút chuyển EXPIRED tại API; token đúng ở thời điểm scan không cần còn hạn lúc confirm, nhưng scan phải còn hạn xác minh. REJECTED/EXPIRED có thể scan mới khi OPEN. Đã CONFIRMED trả trạng thái có mặt; Attendance MANUAL không bị scan mới ghi đè hoặc đổi giờ. Một challenge dùng được cho nhiều học sinh hợp lệ.

## 6. Version, idempotency và transaction

Thứ tự: auth/active/scope → kiểm tra Idempotency-Key → atomic → kiểm tra trạng thái/version → validate → ghi + tăng version + ChangeLog + response idempotency → commit → response. Retry đã thành công phải trả kết quả đã lưu trước khi chặn bởi version cũ/buổi vừa chốt, nhưng vẫn kiểm tra lại auth/scope hiện tại.

Key là chuỗi header 1–128 ký tự, khuyến nghị UUID cho một thao tác. Operation phải định danh action và object, ví dụ `attendance.update:<uuid>` hoặc `qr.confirm:<uuid>`; scan dùng `qr.scan`. Cùng actor/operation/key và payload chuẩn hóa trả status/body cũ; payload khác 409 IDEMPOTENCY_CONFLICT. Key mới cho thao tác mới, lưu 24h. Không hash thứ tự key JSON; canonical JSON trước hash. Raw token không lưu/log, chỉ fingerprint/hash đủ để phát hiện payload khác.

Conditional update với expected_version; affected rows=0 trả 409 VERSION_CONFLICT. Unique/conditional unique bảo vệ roster/session/pending. SQLite chỉ demo nhỏ; busy trả 409 DATABASE_BUSY và hướng dẫn retry cùng key, không nói đã lưu. Không dùng select_for_update trên SQLite để tuyên bố khóa ghi đã hiệu quả. Không triển khai worker/queue/Redis/PostgreSQL ở B01.

## 7. Hợp đồng phần mem1 và báo cáo

Các endpoint còn lại theo mục 7 v1.2: POST /auth/login, POST /auth/logout, GET /auth/me; GET/POST /grades, /classes; PATCH /classes/:id; GET/POST /students; GET/PATCH /students/:id; POST/GET /students/:id/photo; GET /reports/attendance, /reports/summary, /reports/export.

Ví dụ input mem1: Grade `{code,name}`; Classroom `{code,name,grade_id,teacher_id}`; Student `{student_code,full_name,class_id}`; sửa Student cho phép full_name, active và class_id chỉ giám thị. GVCN chỉ sửa hồ sơ lớp mình. Student JSON trả id/student_code/full_name/class_id/grade_id/active/has_photo; không expose photo_path. Me không bao giờ trả password/hash/token QR.

Báo cáo lọc date_from/date_to (bắt buộc), class_id/grade_id/slot/status tùy chọn; export thêm format=xlsx|csv. Dùng Session OPEN/CLOSED và snapshot, scope từ Classroom hiện tại; không tính PLANNED, không tính PENDING là PRESENT. Cùng bộ dòng tạo chi tiết/tổng hợp/export; tối đa 5.000 dòng, vượt trả 422 EXPORT_LIMIT_EXCEEDED. Tệp XLSX Chi_tiet/Tong_hop/Thong_tin; CSV UTF-8 BOM và chống formula injection; không ảnh/mật khẩu.

`expected=present+absent+unmarked`; `present=on_time+late=compliant+non_compliant+not_checked`. Tỷ lệ JSON dạng số 0–1, mẫu số 0 trả null; UI về sau nhân 100%. Tỷ lệ vi phạm dùng (compliant+non_compliant) làm mẫu số. Giữ trường/code thống nhất trước khi mem1 viết query A08.

## 8. Review và bàn giao

A01 tạo User 0001, config, dependency. B01 cung cấp enum/contract. Mem1/mem2 review class_id↔classroom, weekday, snapshot, User–Student và graph migration trước A02/B02. PM review scope, ghi vào PM Comment/Evidence rồi mới tick Finish?; không tự đổi API_Gate. Evidence kỹ thuật ở `docs/project-management/evidence/a01-b01.md`.

Backend có API auth/lớp/Student/ảnh/lịch/attendance/QR/uniform/report/export và seed_demo. Không có giao diện/Admin UI hoặc deploy. PM/member review, tracker Finish? và API_Gate vẫn phải do đúng người xác nhận; reviewer kỹ thuật của agent không thay PM.

### Response report/queue và giới hạn đã triển khai

GET reports/attendance trả `{items,metadata}`; summary trả expected/present/absent/unmarked/on_time/late/compliant/non_compliant/not_checked/checked cùng presence_rate/late_rate/violation_rate/check_coverage (0–1, mẫu số0 null). Metadata chứa generated_at UTC, timezone Asia/Ho_Chi_Minh, filters và scope.role/class_ids. XLSX gồm Chi_tiet/Tong_hop/Thong_tin; CSV là một bảng chi tiết BOM, metadata tại headers X-Report-Timezone/Generated-At/Filters/Scope. Nội dung người dùng được phòng formula và ký tự không hợp lệ XML1.0 trong XLSX.

Queue scan trả snapshot mã/tên/lớp/khối và photo_url khi hồ sơ Student hiện tại còn trong scope nhân sự; chuyển Student sang lớp khác không tiết lộ metadata ảnh lớp mới. Download ảnh luôn scope lại độc lập.

QR challenge tạo201, token sống60s/hint refresh30s khi client gọi phát mới; không tự job. Scan new201, pending mới key lặp200 giữ timestamp; retry **cùng key/body** trả nguyên HTTP status/body đã lưu (có thể201), scope vẫn kiểm tra lại trước replay. Attendance MANUAL không bị scan đổi giờ. Login10 lần/peer IP/5phút, scan30 lần/student/phút (kể cả token sai), cache process demo; replay scan đã thành công không bị quota ngăn trả kết quả cũ.
