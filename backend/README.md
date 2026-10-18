# Backend Django MVP — API trước frontend

Theo MVP v1.3, luồng hiện tại là OpenCV gợi ý danh tính/đồng phục → nhân sự xác nhận → điểm danh; thủ công là dự phòng. Auth/session/CSRF, lớp, học sinh/ảnh private, lịch/roster và report/XLSX/CSV được giữ. QR tắt mặc định, dữ liệu lịch sử không bị xóa. Người dùng đã cho làm UI demo local trước gate; giao diện tại `/`. PM API gate vẫn chờ review, không có triển khai ngoài.

Đọc [thiết kế v1.3](../docs/thiet-ke-he-thong-diem-danh.md), [hợp đồng API](../docs/api-contract.md), [API acceptance](../docs/api-acceptance.md) và [hướng dẫn demo/test/thuyết trình](../docs/huong-dan-demo-opencv.md). Bằng chứng QR/backend v1.2 là lịch sử; ZIP cũ không chứa OpenCV. SQLite dùng demo nhỏ.

Kiểm chứng mới: [149test + migrate/CSRF/export và review](../docs/project-management/evidence/opencv-backend.md). Chạy lại từ root bằng `backend/.venv/Scripts/python.exe .document-tools/verify_opencv.py`; script dùng DB tạm và xuất mẫu, không đổi DB hiện tại.

### Chạy UI demo ngay

Tại root `E:\projectmindx`:

```powershell
backend/.venv/Scripts/python.exe .document-tools/run_demo.py
```

Mở `http://127.0.0.1:8000/`. Launcher in đường dẫn file `demo-login.txt` trong thư mục tạm riêng của máy; mở file để lấy tài khoản/mật khẩu demo. Không đưa file đó vào repository/bàn giao. Mỗi lần chạy tạo DB demo riêng,20học sinh giả,2lớp và2buổi hôm nay đã mở với khung giờ demo00:00–23:59. DB gốc không thay đổi. Đây là lịch chỉ trong dữ liệu giả, không nới kiểm tra giờ của API. Dừng bằng Ctrl+C; chạy lại để bắt đầu demo mới. Không chạy cùng lúc hai server trên cổng8000.

UI có đăng nhập, tổng quan, lịch/buổi, điểm danh thủ công, camera/tải ảnh, xác minh ứng viên, đăng ký/xóa mẫu mặt và báo cáo/XLSX/CSV. Màu áo chỉ gợi ý; mặc định **Chưa kiểm tra**, nhân sự phải tự chọn trước khi lưu kết quả đồng phục. Mẫu mặt thật cần đăng ký từ3–10ảnh được phép sử dụng; seed không có mẫu mặt người thật.

Kiểm chứng browser tách riêng khỏi demo của bạn: `backend/.venv/Scripts/python.exe .document-tools/verify_demo_ui.py` khởi tạo serverQA riêng cổng8001 và dọn sau khi chạy. Tool Playwright cài riêng tại .document-tools/browser-deps, không phải dependency backend. Camera/mạng lỗi và hợp đồng proposal có mô phỏng trong browserQA, được ghi rõ trong evidence; UI đang chạy không giả lập kết quả nhận diện.

## Khởi tạo trên Windows / PowerShell

Mở terminal tại thư mục backend của project đã giải nén/clone. Python 3.12 phải được cài; kiểm tra `py -0p`. Không dùng python 3.9 mặc định của máy hiện tại.

```powershell
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
$env:DJANGO_SECRET_KEY = (& ./.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(48))")
$env:DJANGO_DEBUG = 'true'
./.venv/Scripts/python.exe manage.py check
./.venv/Scripts/python.exe manage.py migrate
./.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
./.venv/Scripts/python.exe manage.py test
./.venv/Scripts/python.exe manage.py seed_demo
./.venv/Scripts/python.exe manage.py runserver
```

Không cần activate venv hay đổi ExecutionPolicy. Với Linux/macOS dùng python3.12 tạo venv và .venv/bin/python, export biến môi trường tương ứng.

`seed_demo` hỏi mật khẩu hai lần tại prompt ẩn; không có tham số mật khẩu và không in mật khẩu ra log. Tạo 2 lớp DEMO10A/DEMO10B, 20 học sinh giả, tài khoản demo_supervisor, demo_teacher_a/b, demo_student_01..20 và lịch thứ Hai–Sáu sáng SHIRT/chiều SPORTS. Không tạo buổi tự động; tạo/mở qua API. Chạy lại giữ ID/mật khẩu/quy tắc đã có và lịch sử buổi; collision không tương thích trả lỗi và rollback. Chỉ dùng dữ liệu demo.

Để thử API: dùng [api-requests.http](../api-requests.http), đổi schoolDate thành ngày địa phương phù hợp lịch, nhập mật khẩu riêng của bạn và copy UUID từ response. GET auth/me cấp cookie CSRF kể cả401; login đổi token, dùng cookie/token mới cho mọi request ghi. Root `/` phục vụ UI staff; STUDENT không vào console nhân sự. Ngoài seed, dùng `manage.py provision_user <username> --role <ROLE>`; STUDENT thêm `--student-id <UUID>` sau khi đã tạo hồ sơ.

Secret được sinh cục bộ, không gửi cùng ZIP/commit. Nếu cần giữ phiên giữa các lần mở terminal, lưu secret riêng ngoài repository và nạp vào môi trường; đổi secret làm các phiên cũ mất hiệu lực. `.env.example` chỉ là mẫu, Django không tự đọc file .env. Không đưa password/secret thật vào README hoặc log.

## Cấu hình

| Biến | Mặc định / ý nghĩa |
| --- | --- |
| DJANGO_SECRET_KEY | Bắt buộc, không có secret mặc định |
| DJANGO_DEBUG | true cho phát triển cục bộ; false bật handler lỗi JSON chuẩn và secure cookie |
| DJANGO_ALLOWED_HOSTS | localhost,127.0.0.1,[::1] |
| DJANGO_DB_PATH | backend/db.sqlite3; có thể trỏ tới DB rỗng khác khi kiểm chứng |
| DEMO_PASSWORD | Tùy chọn cho seed trong môi trường process; nếu thiếu dùng prompt ẩn; không ghi vào repo |
| QR_ENABLED | false; chỉ bật true để chạy tương thích QR cũ, không dùng cho demo mới |
| VISION_FACE_MAX_DISTANCE | 55; khoảng cách LBPH tối đa, thấp hơn chặt hơn; không phải phần trăm chính xác |
| VISION_FACE_MIN_MARGIN | 10; chênh lệch tối thiểu với ứng viên tiếp theo |
| VISION_MIN_SHARPNESS | 50; ngưỡng phương sai Laplacian của mặt 128x128 |
| VISION_UNIFORM_HSV | JSON hai dải SHIRT/SPORTS; mặc định áo trắng/áo xanh dương; phải hiệu chỉnh theo đồng phục thật |

TIME_ZONE là Asia/Ho_Chi_Minh và USE_TZ=True. Khi DEBUG=false cookie Secure cần HTTPS; bản này chỉ bàn giao môi trường phát triển, chưa cấu hình hosting. Ảnh tương lai nằm private_media, không có URL media công khai.

`runserver` phục vụ `/api/v1` theo contract. DEBUG=true có thể hiển thị trang lỗi debug cho lỗi ngoài dự kiến; test lỗi JSON dùng DEBUG=false. Cookie Secure khi DEBUG=false cần HTTPS; ví dụ localhost dùng DEBUG=true. Chưa có hosting/deploy hoặc kiểm chứng camera thiết bị thật.

## Điểm cần phối hợp

- AUTH_USER_MODEL=accounts.User đã có trước migrate. Không migrate User mặc định rồi đổi lại.
- User mặc định role STUDENT để không tự cấp quyền nhân sự. createsuperuser có is_staff/is_superuser nhưng role vẫn STUDENT; task A02 phải gán SUPERVISOR rõ ràng nếu cần tài khoản nghiệp vụ. Cờ vận hành không thay role.
- User–Student OneToOne đã thêm bằng accounts/0002 phụ thuộc students/0001; không sửa accounts/0001 đã bàn giao.
- mem1 làm accounts/academics/students/reports; mem2 làm schedules/attendance/vision và QR lịch sử. Core/config/contracts và migrations phối hợp theo kế hoạch 18/10/2026. Migration attendance/0003 chỉ thêm source VISION; vision/0001 thêm mẫu mặt và đề xuất quét; không xóa schema cũ.
- Test nền và nghiệp vụ có assertion thực; permission cases nằm ở test_academics/test_students/test_qr/test_reports/test_http_contract. Hai file permission skeleton rỗng đã bỏ để tránh hiểu nhầm; không tính file tồn tại là test pass.

## Giới hạn demo

OpenCV chạy cục bộ bằng Haar + LBPH; đăng ký 3–10 ảnh mặt khác nhau/học sinh, thay thế nguyên bộ, crop 128x128 lưu trong DB riêng tư. GET mẫu chỉ trả số lượng; DELETE xóa crop và vô hiệu hóa đề xuất chờ. Không dùng ảnh hồ sơ thay cho đăng ký mẫu. Khung camera không được lưu; đề xuất hết hạn sau120s. Quét chỉ trả CANDIDATE/UNKNOWN/ALREADY_MARKED; luôn cần nhân sự xác nhận danh tính. Đồng phục là gợi ý màu vùng thân áo, UNKNOWN giữ NOT_CHECKED, không tự kết luận vi phạm. Không có nhận diện sống/chống ảnh chụp giả. Kiểm thử ảnh tổng hợp không chứng minh độ chính xác trên người thật.

Ảnh vision ≤2MiB/4MP mỗi ảnh, tổng đăng ký ≤15MiB; một ảnh quét/lần; roster ≤50 học sinh;20 phân tích/phút/nhân sự. Login10 lần/IP/5phút. Rate limit dùng cache process, SQLite không chứng minh tải toàn trường hoặc nhiều process. Cài đúng opencv-contrib-python-headless trong requirements, không cài đồng thời các gói OpenCV khác dùng chung module cv2. Thay đổi ngưỡng/màu cần chạy đánh giá lại trên bộ ảnh được phép dùng, tách khỏi ảnh đăng ký.

Ảnh hồ sơ riêng biệt tối đa5MiB/24MP, chuẩn hóa PNG bỏ metadata và lưu private; tải luôn kiểm tra scope. Windows có thể giữ file ảnh hồ sơ cũ đang tải sau thay thế. Export đồng bộ ≤5.000 dòng, XLSX3sheet/CSV BOM/formula-safe. Không SMS/phụ huynh/cloud/queue/workflow duyệt sửa; không triển khai hoặc chia sẻ ngoài.
