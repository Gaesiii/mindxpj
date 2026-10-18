# Backend MVP — bằng chứng thực thi14/10/2026

Phạm vi được người dùng xác nhận: **toàn bộ backend A02–A15/B02–B15**, theo MVP v1.2. Code/service/API/migration/test A02–A14/B02–B14 đã triển khai. A15/B15 có hồ sơ [API acceptance](../../api-acceptance.md) để PM/member review; **không tự duyệt API_Gate hoặc tick Finish?**. Không frontend, Admin UI, deploy hoặc chia sẻ ngoài.

## Kiểm chứng cuối

Log chạy thật: [backend-api-validation.txt](backend-api-validation.txt). Python3.12.2, requirements đã khóa; chạy trong backend bằng .venv/Scripts/python.exe. Sinh secret/password chỉ trong process, không in/log; DJANGO_DB_PATH trỏ SQLite mới trong thư mục tạm riêng. DB hiện có không bị thay thế; DB tạm được dọn sau kiểm chứng.

| Lệnh / kiểm chứng | Kết quả |
| --- | --- |
| manage.py check | Exit0, không có issue |
| manage.py migrate --noinput trên DB rỗng | Exit0, toàn bộ graph auth/User/academics/Student/link/schedules/attendance/core/qr/session đạt |
| manage.py makemigrations --check --dry-run | Exit0, No changes detected |
| manage.py seed_demo hai lần trên DB mới | Hai lần exit0, 2lớp/20học sinh giả, giữ dữ liệu/mật khẩu khi chạy lại |
| manage.py test | **126test đạt, 0lỗi;60,233s**, exit0 |
| python -m pip check | Exit0, No broken requirements found |
| api-requests.http | 11JSON body hợp lệ sau thay biến, mọi biến đã định nghĩa; workflow tương ứng được kiểm chứng HTTP trong test |

Reviewer độc lập cũng chạy toàn bộ **126test đạt/60,884s**, review spec trước quality, không còn finding chặn trong phạm vi đã review. Kết quả đó không thay review PM hoặc chứng minh tải/thiết bị thật.

## Mapping task và test thực thi

| Task | Implementation / acceptance được kiểm chứng | Test |
| --- | --- | --- |
| A02 | Ba role login, CSRF bootstrap/rotation, flush phiên/logout, account inactive, strict payload, lỗi chung/không hash/password; provision CLI/service, role explicit | test_accounts |
| A03 | Grade/Classroom UUID/unique/PROTECT, một GVCN, active đúng role, teacher scope và đổi GVCN | test_academics |
| A04–A05 | Student CRUD/search/tên trùng/mã unique, transfer chỉ supervisor, own minimal Student; link protected1:1 và nhân sự không gắn Student | test_students, test_student_models |
| A06–A07 | Private photo JPEG/PNG/WebP<=5MiB/24MP, metadata strip, fake/oversize/path/scope/reassignment, lỗi giữ ảnh cũ/DBrollback, downloadCSRF | test_students |
| B02–B03 | Weekday0–6/sáng chiều/SHIRT SPORTS/strict số nguyên/giờ/cutoff/PATCH toàn rule/date UUID; matrix mở/chốt | test_schedules |
| B04–B06 | Model graph/unique, scope, create/open retry, snapshots policy/active roster, rollback giữa chừng, version/missingrule/chốt | test_schedule_api, test_full_flow |
| B07–B08 | Manual/PRESENT/ABSENT, aware không tương lai/cùng ngày/reason, cutoff inclusive, CAS/retry payloadconflict/replayscope, CLOSED supervisorreason+log, atomic | test_attendance, test_http_contract |
| B09–B11 | Token hash/60s/PNG/refreshhint30, own sessionidentity, sameQR2student, pending timestamp/15mexpiry/reject/confirmscan-time, manualsupersede, scope+retryclose, invalidquota | test_qr, test_full_flow |
| B12 | PRESENT only; NOT_CHECKED không tự compliant; COMPLIANTmatch/NON_COMPLIANTreason/OTHERnote; confirmuniform rollback | test_uniforms, test_qr, test_http_contract |
| A08–A11 | 40roster34/3/3 và27/4/3uniform; filter/scope/snapshot/zero denominator; canonical detail+summary+export; BOMUnicode/formula/XML/5000limit | test_reports |
| A12 | HTTP QR/manual/uniform/chốt thật;4roster→3present1absent, uniform1/1/1; XLSX/CSV khớp summary | test_report_reconciliation |
| A13/B13 | CSRF thật và toànluồng, reads/writes/export/photo ba role, retry sauclose và reassignment, pending không PRESENT, unmarked→absent | test_http_contract, test_full_flow cùng các permission cases ở module |
| A14/B14 | Seed20fake/2class/23account/20rules; repeat giữ password/history/customrules, collisionrollback, privateprompt; requestcollection/modulesREADME/errorcode | test_seed_demo, api-requests.http |
| A15/B15 | Hồ sơ review gồm evidence/checklist/setup/request/examples/limits; PM decision còn chờ | docs/api-acceptance.md |

Tổng126 gồm62test mem1+nền+seed,29test lịch/attendance/QR/fullflow,15form lịch,7helper chung,10report/reconciliation và3HTTP contract. Hai file permission skeleton rỗng đã bỏ; test quyền thật nằm trong test_academics/test_students/test_qr/test_reports/test_http_contract. Không tính file tồn tại là bằng chứng.

## Review và lỗi đã sửa

- JSON date sai kiểu có thể ném AttributeError: field parse kiểm tra kiểu trước Django, RED→GREEN regression.
- UUID body dạng không dấu gạch/braced/URN trái contract: form validate canonical wire shape, regression ở lịch/lớp/Student.
- Provision whitespace password không login được, escaped lone surrogate có thể lỗiUTF8, exponent1e999 tạoInfinity: validation đồng nhất và HTTP boundary reject trước DB/response, regression.
- XLSX có Unicode không hợp lệ XML1.0: sanitize cell và kiểm chứng file mở lại, formula protection vẫn giữ.
- Invalid QR token không tính quota: lỗi/schema/roster token sai có rate limit; retry đã thành công vẫn replay.
- Queue snapshot sau Student transfer có thể tiết lộ metadata ảnh lớp mới: photo metadata query scope riêng theo lớp hiện tại; snapshot lịch sử giữ nguyên; regression teacher/supervisor.
- Windows giữ file ảnh cũ đang tải: commit thay ảnh vẫn thành công; lỗi dọn file cũ không giả báo thao tác chưa lưu. Hạn chế orphan private ghi trong README.

Các log RED/GREEN của từng nhóm nằm cùng thư mục evidence. Review kỹ thuật không đóng vai trò PM/member nghiệp vụ.

## Bổ sung hồ sơ A15/B15

Theo yêu cầu tiếp tục plan, đã tạo [bộ mẫu XLSX/CSV/JSON](samples/README.md) bằng API thật và CSRF trên DB tạm riêng. Chốt 10 roster thành 2 PRESENT/8 ABSENT; QR 07:04 xác minh 07:08 vẫn ON_TIME, manual 07:10 LATE, đồng phục 1 đạt/1 không đạt. Scan PENDING chưa xác minh hết hạn khi chốt. Mở lại file và đối chiếu từng dòng chi tiết/tổng với JSON đạt; ca sai quyền student/teacher B và logout bị chặn. Database hiện tại không thay đổi, mật khẩu/token không đưa vào artifact. PM gate vẫn chờ quyết định riêng.

## Giới hạn / bước PM

SQLite chỉ demo nhỏ, chưa kiểm chứng concurrent process/throughput toàn trường. Cache limiter process cục bộ; QR client gọi phát mới30s, pending expiry tại API, không worker. QR vẫn cần đối chiếu tại chỗ. Export<=5.000dòng, private local photo có thể còn orphan khi file cũ bị Windows khóa. Chưa UI/camera thiết bị/HTTPSdeployment; accountprovision command thay Admin UI cho backend.

PM dùng backend/README.md và api-requests.http với DB/mật khẩu riêng, xem api-acceptance.md, ghi PM Comment/Evidence và xác nhận Finish?/gate theo task. Source tasks.json/XLSX/CSV/AppsScript không tự thay checkbox hoặc API_Gate. ZIP/deliverables A01/B01 cũ vẫn là baseline lịch sử, không được coi chứa API mới.
