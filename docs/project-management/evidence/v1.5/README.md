# Bàn giao kỹ thuật v1.5 — 19/10/2026

Người dùng yêu cầu triển khai plan ngày19/10/2026. Bản này có tự điểm danh qua cặp ảnh, không gian Đồng phục/ảnh mẫu riêng, CRUD lớp/học sinh và xử lý ngoại lệ bằng lý do. **Chưa hoàn thành toàn bộ 26 task:** phần bộ ảnh trường, benchmark/fine-tune, nghiệm thu model và camera vật lý còn thiếu đầu vào. Không giả kết quả mô hình trường. API_Gate=NOT_APPROVED; không deploy.

## Chức năng đã triển khai

- Lớp: tạo/sửa/lưu trữ/khôi phục, khối/GVCN/sức chứa, sĩ số active/tổng tự tính. Học sinh: CRUD, phân quyền mã/chuyển lớp, restore/capacity, private ảnh/enrollment; không xóa lịch sử. Version/atomic write/audit.
- Camera tự động: hai frame khác nhau, cùng roster pupil, server quyết định; inference ngoài transaction, recheck quyền và mutable state, source VISION/mode AUTO, không giả verified_by. Giữ giờ đến đầu, không đè MANUAL/ABSENT/CLOSED. Có chế độ UNIFORM_ONLY không tạo PRESENT.
- UI: camera dùng chung giữa điểm danh/đồng phục; cadence/backoff/cancel, cặp ảnh upload, review pending/default vi phạm + lý do, sửa cảnh báo sai, nguồn AUTO/MANUAL; CRUD đúng role và bổ sung roster OPEN rõ ràng.
- Dataset/model: crop áo private, scope ảnh/export, group split/digest, version/profile snapshot, ONNX hash/lock/cached runtime, missing/uncertain NOT_CHECKED. Tool offline train/fine-tune bằng weights local verified, test held-out/parity/latency, import phải có review/hash/precision. Không Torch runtime hoặc download trong API.
- Báo cáo: REVIEW_REQUIRED riêng, không tính pending thành vi phạm; nguồn nhận diện/uniform và lịch sử scan auto vào export. Vercel export dataset quá lớn bị chặn trước materialize BLOB/ZIP.

## Bằng chứng chạy

| Kiểm tra | Kết quả | Giới hạn |
| --- | --- | --- |
| Full suite `manage.py test tests --noinput` | **255 tests pass,68.151s**, system check clean | Nhiều test workflow dùng inference có kiểm soát; không đo accuracy |
| `manage.py check`, `makemigrations --check --dry-run`, `pip check` | Pass, không drift/requirements hỏng | Môi trường Windows Python3.12 hiện tại |
| [Browser + mặt thật](real-face-browser.json) | Headless Edge, CSRF/API thật, enrollment3ảnh, hai ảnh held-out→RECORDED; người khác→UNKNOWN; retry/giờ đến giữ nguyên; UI tạo học sinh + API sửa/archive thật; không page error | Không mock detector/embedding/HTTP; chỉ các ảnh fixture local, không camera vật lý/liveness/population accuracy |
| [Ảnh chụp UI](automatic-attendance.png) | Buổi giả với một học sinh tự có mặt, áo Chưa kiểm tra | Dữ liệu fictitious, không chứa ảnh mặt mẫu |
| Browser fixture camera | Script `backend/tests/demo_ui_browser.cjs` đạt: cặp multipart/idempotency, cadence≥3.9s, dừng khi chuyển trang, CRUD/role/GVCN create/archive/restore, reason/correction, ROI1920→960 | API fixture + Chromium fake webcam; không phải nhận diện/HTTP backend thật |
| [Concurrent SQLite](concurrency.json) | Hai thread capacity1 chỉ một create; same-key auto cùng response, một attendance/scan/audit/version1 sau busy retry | Synthetic face matching/extraction; SQLite file local, không distributed serverless |
| [Nâng DB cũ](upgrade.json) | Backup chỉ đọc v1.4→migrate v1.5 giữ20attendance/20học sinh/7mẫu, các giá trị và byte private không đổi | Bản sao tạm riêng, không migrate/reset DB người dùng trong kiểm tra |
| [Build Vercel local](build-vercel.json), [log](build-vercel.log) | `python build_vercel.py` exit0,22.243s; hai face model verified, migrations/23account passwordchecks/seed/static/template thành công; không secret trong log | Windows local, không native Vercel deploy/build; SQLite tạm từng instance |
| [Benchmark hiện tại](performance.json) | GET cold/warm, enrollment kèm khởi tạo model, auto full inference với key mới và replay riêng; wall/CPU/working-set/peak và bytes source/model đo thực, chi tiết trong JSON | Routed Django Client local, roster nhỏ; không HTTP network/browser hay native Vercel; model áo trường chưa có. Ước lượng Linux dependency267.45MiB tách khỏi model/bundle/RAM |
| Word/slide | Word v1.5/current byte-identical,45content fragments,6sections/2tables;7slides+notes parse/reopen pass;v1.2/v1.3/v1.4 giữ lịch sử | Không render Word/PowerPoint hoặc thử thuyết trình trực tiếp |

Test migration legacy từng chỉ rollback vision, nên historical state nay lấy đúng graph đã áp dụng của các app còn lại; test upgrade đã chạy lại thành công. Full suite có một UserWarning đã có từ test override DATABASES, không test failure.

Review độc lập theo hai phần spec rồi code: CRUD không blocker (33test reviewer chạy), auto/roster/report không blocker (32test, sau sửa account revocation/export limit76test), uniform/UI/final integration không còn blocker. Đã sửa thiếu nguồn AUTO/MANUAL, stale sĩ số sau archive/restore và giữ buổi lịch sử đang chọn. Reviewer ROI ban đầu rút lại vì backend resize960. Root bổ sung test revoke account giữa inference, fail201→pass401. Final reviewer tìm race upload áo khi lớp archive giữa detect: đã sửa fresh actor/class dưới lock, hai regression archive/revoke từ fail→pass, reviewer chạy lại xác nhận. Q03 benchmark path/ước lượng dependency đã sửa và được review. Các review không phải PM acceptance.

## Các task chưa được đánh dấu hoàn tất

| Task | Trạng thái và lý do |
| --- | --- |
| D01 | NEEDS_SCHOOL_DATA: quy chuẩn/crop/manifest có, chưa nhận bộ ảnh trường và ảnh đối chứng |
| D02 | TOOLING_READY_NEEDS_DATA: candidate/license notes/local weights interface có, chưa benchmark trên dữ liệu trường để chốt model |
| D03 | TOOLING_READY_NEEDS_DATA: pipeline train/eval/export/import có, chưa thực sự train/fine-tune và đánh giá model trường |
| U02 | IMPLEMENTED_NEEDS_TRAINED_MODEL: runtime ROI/ONNX/fail-closed có tests, chưa chạy artifact trường đã được nghiệm thu |
| Q02 | PARTIAL_NEEDS_DATA_AND_DEVICE: ảnh mặt thật pass; chưa calibration đầy đủ, bộ test áo trường hay camera vật lý |

Các task còn lại có implementation+validation+review kỹ thuật, ghi Finish=true trong **tracker mới**, không thay tracker baseline hay API_Gate. Status này không công bố model trường hoạt động. Mọi task phụ thuộc nghiệm thu dữ liệu vẫn chưa Finish; nối fallback/UI có thể được kiểm chứng độc lập.

## Tái lập và đầu vào tiếp theo

```powershell
# Từ backend, dùng env riêng tư local; không in giá trị.
.venv/Scripts/python.exe manage.py test tests --noinput
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
.venv/Scripts/python.exe -m pip check

# Từ repo root, browser deps chỉ trong môi trường công cụ.
backend/.venv/Scripts/python.exe .document-tools/verify_v15_concurrency.py --output docs/project-management/evidence/v1.5/concurrency.json
backend/.venv/Scripts/python.exe .document-tools/verify_v15_demo.py --images PRIVATE_DEMO_IMAGES --query PRIVATE_HELD_OUT_1 PRIVATE_HELD_OUT_2
```

[Hướng dẫn dataset/model](../../../../tools/uniform_training/README.md): cần các loại áo hợp lệ, ảnh mẫu đúng trường và đối chứng cùng màu/khác logo, nhiều người/ngày/ánh sáng/che áo. Mục tiêu khởi đầu100–200ảnh/loại và test độc lập, không bảo đảm đủ. Chỉ duyệt model sau evidence precision/recall/UNKNOWN coverage và kiểm tra logo/occlusion riêng. Dữ liệu/model/review private không nằm trên GitHub. Local/Vercel thiếu artifact vẫn điểm danh mặt được, áo giữ NOT_CHECKED. Database shared và hosting thực không nằm trong lần triển khai này.
