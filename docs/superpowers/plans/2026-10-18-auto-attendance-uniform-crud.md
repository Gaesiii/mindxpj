# Kế hoạch đề xuất: tự điểm danh, đồng phục trường và CRUD

Ngày: 18/10/2026. Trạng thái: **DRAFT / PLAN_ONLY**. Đây là kế hoạch theo yêu cầu người dùng, chưa phải phê duyệt thiết kế hay bằng chứng tính năng đã chạy. API_Gate giữ nguyên NOT_APPROVED; không triển khai/deploy trong task lập kế hoạch này.

Đọc [thiết kế đề xuất](../specs/2026-10-18-auto-attendance-uniform-crud-design.md) trước khi thực hiện. Bản chuẩn v1.4 và tracker cũ được giữ nguyên. Sau khi thiết kế được duyệt, cập nhật hợp đồng v1.5 cùng quy tắc tự động thay cho xác nhận thủ công trước khi viết code.

## Kết quả và thứ tự ưu tiên

1. Hoàn thiện màn hình quản lý lớp/học sinh dựa trên API có sẵn: thêm/sửa/lưu trữ/khôi phục, chuyển lớp, sức chứa và sĩ số thực tế.
2. Camera tự nhận diện mặt và ghi có mặt; không bắt giáo viên xác nhận từng người. Giữ thao tác thủ công cho trường hợp không nhận diện được.
3. Thêm mục **Đồng phục** với camera và quản lý ảnh mẫu đúng trường. Dùng chung camera controller, không mở hai camera cùng lúc.
4. Đúng đồng phục được ghi tự động; nghi vi phạm vào danh sách để giáo viên ghi lý do. Không chắc thì giữ Chưa kiểm tra. Báo cáo tách ba nhóm rõ ràng.

Auto-face và CRUD không chờ model đồng phục. Khi chưa có model đạt kiểm chứng, mặt vẫn có thể điểm danh tự động nhưng đồng phục giữ NOT_CHECKED. Không dùng màu áo làm bằng chứng đúng logo/mẫu trường.

## Bộ ảnh cần chuẩn bị

- Danh sách loại áo hợp lệ theo buổi: ví dụ sơ mi, thể dục; gồm các biến thể thực sự được trường chấp nhận.
- Mục tiêu ban đầu 100–200 ảnh độc lập mỗi loại, nhiều người/ngày/ánh sáng; ảnh chỉ vùng áo, đủ rõ logo/chi tiết cần phân biệt. Đây là mốc khởi đầu để đánh giá, không bảo đảm đủ.
- Ảnh áo thường và đồng phục trường khác có màu tương tự; tình huống áo khoác, thiếu thân áo, logo che/mờ. Không yêu cầu đưa ảnh trẻ em lên GitHub.
- Chia tập theo người và buổi chụp, giữ test độc lập: đề xuất ít nhất 30 ảnh/loại và 60 đối chứng khó. Không dùng ảnh enrollment hay ảnh augment trùng nguồn để chứng minh tổng quát hóa.
- Thu thập ảnh là dependency của nghiệm thu model; thời gian chờ ảnh không nằm trong giờ lập trình bên dưới. Nếu dữ liệu chưa đạt, ghi kết quả và bổ sung dữ liệu trước khi bật tự kết luận đồng phục.

## Backlog có thể nhập vào tracker

Member 1: accounts/academics/students/reports và UI tương ứng. Member 2: schedules/attendance/vision và camera. Shared: cùng chốt interface/migration; chỉ một người tạo migration mỗi app sau khi thống nhất. Giờ là tổng công sức dự kiến, không phải cam kết thời hạn.

Tổng **26 task / 192 giờ công**: Member 1 trực tiếp 50 giờ, Member 2 trực tiếp 84 giờ, phần chung 58 giờ. Nếu chia đều phần chung thì khoảng 79/113 giờ; Member 2 là điểm nghẽn. Hai người làm 6 giờ tập trung/ngày cần tối thiểu khoảng 19 ngày theo tải Member 2, dự trù 20–24 ngày làm việc khi tính phụ thuộc và tích hợp, chưa gồm chờ ảnh hoặc huấn luyện lại khi dữ liệu chưa đạt. Đây là ước tính ban đầu, sẽ điều chỉnh sau D02/D03.

| ID | Owner | Hours | Depends on | Task | Tiêu chí nghiệm thu |
| --- | --- | --- | --- | --- | --- |
| P01 | Shared | 8 | - | Chốt contracts v1.5 và quyền | State tự động, uniform review, CRUD, snapshot và lỗi được mô tả; PM gate độc lập |
| P02 | Shared | 8 | P01 | Schema và migration liên app | Capacity/active/version, auto attribution, review/model/profile version; migrate dữ liệu cũ không đổi nghĩa CONFIRMED |
| C01 | Member 1 | 6 | P02 | Mở rộng API lớp | Chi tiết, sửa, sức chứa, sĩ số tự tính; unique, version và role scope đúng |
| C02 | Member 1 | 6 | C01 | Mở rộng API học sinh | Thêm/sửa mã/tên, trạng thái; kiểm tra lớp active/capacity; GVCN không tự chuyển lớp |
| C03 | Member 1 | 6 | C02 | Archive/restore và chuyển lớp | Không hard-delete lịch sử; chặn archive lớp còn active/OPEN; chuyển nguồn/đích atomic, đúng quyền |
| C04 | Member 1 | 6 | C03 | UI quản lý lớp | Tìm kiếm, tạo/sửa/lưu trữ/khôi phục, hiển thị sĩ số/sức chứa; xử lý conflict rõ |
| C05 | Member 1 | 6 | C04 | UI quản lý học sinh | CRUD, chuyển lớp, trạng thái và enrollment hiện có dùng được; không nhập sĩ số giả |
| C06 | Member 2 | 6 | C03,P02 | Bổ sung roster buổi OPEN có kiểm soát | Supervisor thêm đúng lớp/active; version/audit; không rebuild hay sửa attendance cũ |
| D01 | Shared | 12 | P01 | Quy chuẩn và chuẩn bị dataset trường | Nhãn, quyền sử dụng, crop áo, manifest/split theo người/buổi; báo số ảnh còn thiếu |
| D02 | Member 2 | 8 | D01 | Chọn baseline/model và license | So baseline với MobileNetV3-Small hoặc ứng viên nhẹ; kiểm tra quyền code/weights/dataset và khả năng ONNX OpenCV |
| D03 | Member 2 | 16 | D02 | Train offline, đánh giá, export ONNX | Script tái lập, seed/config, test độc lập, confusion matrix, precision/recall/coverage, latency/bytes và hash model |
| D04 | Member 1 | 8 | D01,P02 | API/UI ảnh mẫu đồng phục riêng | Supervisor quản lý/export riêng tư, scope ảnh; crop loại mặt; không public dataset hoặc train trong request |
| U01 | Member 2 | 6 | P02 | Profile/quy tắc đồng phục và model version | Theo loại buổi/lớp; snapshot lúc OPEN; kích hoạt version mới không viết lại lịch sử |
| U02 | Member 2 | 10 | D03,U01 | Runtime ROI áo và ONNX | Áo gắn đúng người; thiếu logo/thân áo hoặc bất định thành UNKNOWN; cache model/hash, không tải mạng trong request |
| A01 | Member 2 | 8 | P02,C03 | Service/API tự điểm danh | Hai frame khớp cùng roster pupil; server quyết định; idempotency và recheck trước atomic write; không cần model áo |
| A02 | Member 2 | 6 | A01 | Camera tự chụp cặp ảnh | Một request/4 giây, không chồng; giới hạn ảnh, CSRF, backoff; dừng khi đổi trang/tab/logout |
| A03 | Member 2 | 6 | A02 | Feedback quét và chống lặp UI | Hiện tên/kết quả/hướng dẫn; một camera; không spam toast, không ghi lại giờ đến đầu |
| A04 | Member 2 | 6 | A01 | Attribution và lịch sử auto/manual | AUTO_RECORDED tách CONFIRMED; không giả verified_by; không đè chỉnh sửa MANUAL/ABSENT/CLOSED |
| U03 | Member 2 | 6 | U02,A01 | Ghép đồng phục vào API scan | AUTO_ATTENDANCE và UNIFORM_ONLY; UNIFORM_ONLY không tự tạo PRESENT; thiếu model giữ NOT_CHECKED |
| U04 | Member 2 | 6 | U03,A02,D04 | Không gian Đồng phục có camera | Camera/framing, mẫu trường, profile và kết quả; chia sẻ controller với điểm danh |
| R01 | Member 1 | 6 | U03,A04 | UI/API xử lý ngoại lệ đồng phục | REVIEW_REQUIRED, giáo viên ghi lý do để NON_COMPLIANT hoặc sửa cảnh báo sai; không confirm danh tính lần nữa |
| R02 | Member 1 | 6 | R01,C03 | Báo cáo và export tương thích | Tách đúng/nghi sai/chưa kiểm tra/vi phạm đã ghi lý do; giữ snapshot lịch sử và scope |
| Q01 | Shared | 8 | C05,C06,U04,R02,A03 | Regression bảo mật/nghiệp vụ | Role/CSRF/private ảnh, conflict, retry/concurrency, rollback, inactive/transfer giữa inference và write |
| Q02 | Shared | 10 | D03,U02,A03,R01 | Kiểm chứng ảnh và camera thực | Test ngoài enrollment, người lạ/nhiều mặt, logo tương tự/che; calibration threshold, precision và coverage công khai |
| Q03 | Shared | 8 | Q01,Q02 | Kiểm tra Vercel demo/API | Build và cold/warm CPU/RAM/bundle đo được; không thêm Torch runtime; không hứa SQLite chia sẻ; không deploy |
| Q04 | Shared | 4 | Q03 | Review, tài liệu và kịch bản thuyết trình | Review độc lập, đóng lỗi quan trọng, ghi evidence và giới hạn; chỉ cập nhật Finish khi đủ kiểm chứng/phê duyệt |

File nhập tracker: [JSON](../../project-management/auto-attendance-uniform-crud-tasks.json), [CSV UTF-8](../../project-management/auto-attendance-uniform-crud-tasks.csv). Mọi task khởi tạo PLANNED, Finish=false; không sửa tracker 40 task cũ.

## Bản đồ file dự kiến

Các đường dẫn dưới đây tương đối với repo; file mới là dự kiến, chưa được tạo bởi task lập plan.

| Nhóm | File hiện có cần mở rộng | File mới dự kiến |
| --- | --- | --- |
| Contracts/schema | docs/thiet-ke-he-thong-diem-danh.md; backend/school_app/core/; academics/models.py; students/models.py; attendance/models.py; vision/models.py | Migration mới từng app, tài liệu v1.5 có lịch sử v1.4 |
| CRUD | backend/school_app/academics/{views,services,urls}.py; backend/school_app/students/{views,services,urls}.py | backend/tests/test_class_student_crud.py |
| Roster | backend/school_app/schedules/; backend/school_app/attendance/ | backend/tests/test_roster_append.py |
| Auto-face | backend/school_app/vision/{views,services,urls,engine}.py; backend/school_app/attendance/ | backend/school_app/vision/auto_attendance.py; backend/tests/test_auto_attendance.py |
| Uniform | backend/school_app/vision/; backend/school_app/core/ | backend/school_app/vision/uniform_model.py; backend/tests/test_school_uniform.py; tools/uniform_training/README.md và script offline |
| UI | backend/school_app/demo_ui/templates/demo_ui/index.html; static/demo_ui/{app.js,app.css} | Tách camera controller và các màn CRUD/uniform thành module khi cần; không refactor ngoài phạm vi |
| Reports/Vercel | backend/school_app/reports/; backend/build_vercel.py; backend/pyproject.toml | Evidence benchmark và dataset/model card không kèm dữ liệu riêng tư |

## Cách thực hiện và kiểm chứng mỗi task

1. Đọc contracts và test liên quan; tạo test hành vi thất bại cho thay đổi nghiệp vụ trước khi sửa service/model.
2. Làm thay đổi nhỏ trong app sở hữu; mọi interface/migration liên app phải thống nhất trước. Không thay role scope bằng kiểm tra riêng ở UI.
3. Chạy test tập trung; kiểm tra lỗi/rollback và dữ liệu cũ. Có migration thì chạy `python manage.py makemigrations --check --dry-run` và thử migrate DB fixture cũ trên bản sao.
4. Kiểm tra UI/camera thực cho task giao diện; ghi evidence không chứa ảnh cá nhân/secret. Test nhận diện thực không dùng mock thay kết quả engine.
5. Review diff và bằng chứng trước khi tick Finish; PM acceptance là bước riêng. Push code theo quyền đã có, không deploy.

Các lệnh chạy từ backend với virtualenv hiện có:

```powershell
.\.venv\Scripts\python.exe manage.py test tests.test_academics tests.test_students
.\.venv\Scripts\python.exe manage.py test tests.test_vision_api tests.test_uniforms tests.test_attendance tests.test_reports
.\.venv\Scripts\python.exe manage.py test tests
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Khi test file mới được tạo, thêm module tương ứng vào lệnh tập trung. Full suite chạy ở mốc tích hợp sau khi test tập trung đạt; không lặp vô ích. Build Vercel dùng env riêng tư đã chuẩn bị, không ghi giá trị secret vào evidence.

## Các điểm chặn nghiệm thu

- Không có bộ ảnh trường độc lập hoặc model chưa đạt đánh giá: chưa nghiệm thu đồng phục; có thể bàn giao CRUD/auto-face riêng.
- Mục tiêu đề xuất cho auto-correct uniform là precision ít nhất 95% trên tập test đã khai báo, kèm coverage/UNKNOWN và confusion matrix. Đây không phải độ chính xác đã đạt hay bảo đảm vận hành thực.
- Ngưỡng face tự động phải đo false match/false reject với ảnh ngoài enrollment; không lấy ngưỡng luồng confirm cũ làm bằng chứng. Hai frame là kiểm tra nhất quán, không phải liveness.
- Retry/hai tab chỉ chống trùng trong cùng database; SQLite tạm trên Vercel không cung cấp tính nhất quán toàn deployment. Muốn vận hành thật cần scope database dùng chung riêng.
- Thay đổi tự động chỉ được bật sau khi cập nhật thiết kế/contracts phù hợp yêu cầu mới và review; không tuyên bố hoàn thiện dựa vào việc có file plan.
