# Demo OpenCV — setup, API test và thuyết trình

## Luồng hiện hành v1.5 — 19/10/2026

Phần v1.4 bên dưới giữ làm hướng dẫn legacy; với bản hiện tại dùng luồng này:

1. Chạy launcher như mục local, đăng nhập giám thị/GVCN và chọn buổi OPEN hôm nay. Đăng ký 3–10 ảnh rõ mặt ở Học sinh → Quản lý mẫu.
2. Mở Điểm danh → Bật camera. Học sinh đứng lần lượt, thấy mặt và phần áo; ứng dụng tự chụp cặp ảnh và tự ghi có mặt khi đủ điều kiện. **Không cần xác nhận từng học sinh.** Có thể tải đúng hai ảnh khác nhau ngoài bộ đăng ký rồi chọn Quét cặp ảnh để thử.
3. Quét lại giữ giờ đến đầu, không đổi vắng/thủ công. Không nhận diện được thì chụp lại hoặc ghi thủ công. Hai ảnh không bảo đảm chống ảnh giả.
4. Mục Đồng phục dùng chung camera; chỉ kiểm tra học sinh đã PRESENT. Đúng mẫu rõ→Đạt tự động, nghi sai→giáo viên ghi lý do, chưa rõ→Chưa kiểm tra. Sửa cảnh báo sai được, quyết định thủ công không bị quét lại đè.
5. Khi chưa có model đúng trường (trạng thái hiện tại), áo luôn Chưa kiểm tra. Giám thị vào Mẫu đồng phục để upload ảnh, kéo ROI chỉ phần áo, gán loại/nhóm chụp/split. [Pipeline offline và điều kiện duyệt model](../tools/uniform_training/README.md). Không tự train trong web.
6. Mục Lớp cho giám thị thêm/sửa sức chứa/lưu trữ/khôi phục; sĩ số tự tính. Học sinh cho staff quản lý đúng phạm vi; giám thị sửa mã/chuyển lớp. Lưu trữ giữ lịch sử. Học sinh mới vào buổi sau hoặc giám thị chủ động bổ sung vào buổi OPEN.
7. Báo cáo có nhóm Cần kiểm tra riêng, nguồn AUTO/MANUAL và CSV/XLSX. [Evidence v1.5](project-management/evidence/v1.5/README.md) phân biệt browser API fixture/camera giả, ảnh mặt thật và phần chưa có dữ liệu trường.

Vercel vẫn chỉ hai biến môi trường cũ; không thêm cloud/API key. Người dùng tự deploy. SQLite/mẫu lưu tạm theo instance, không phải lưu trữ bền vững.

Theo thiết kế v1.4, đây là hướng dẫn tái lập và checklist thiết bị thật. Không phải cam kết accuracy. API_Gate = NOT_APPROVED; ngoại lệ ngày18/10/2026: người dùng yêu cầu rõ “làm luôn UI để demo”, cho phép UI local trước gate. Đây không phải phê duyệt PM API; Finish? không tự thay đổi. UI tại `/` có evidence153test/browser lịch sử trước SFace bên dưới; nâng cấp YuNet/SFace cần validation mới; camera vật lý/accuracy chưa được kiểm chứng.

## 1. Chuẩn bị local

Dùng Python 3.12, PowerShell, DB thử riêng và dữ liệu giả/ảnh được phép dùng. Xem backend/README.md để biết biến môi trường/password seed; không ghi mật khẩu thật vào request/evidence. Tại workspace E:\projectmindx:

```powershell
cd backend
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
$env:DJANGO_SECRET_KEY = (& .venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(48))")
$env:DJANGO_DEBUG = 'true'
.venv/Scripts/python.exe manage.py prepare_vision_models
# DB thử riêng; không trỏ DB demo đang dùng.
$env:DJANGO_DB_PATH = "$PWD/demo-vision.sqlite3"
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py seed_demo
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
```

DJANGO_DB_PATH được đọc từ backend/config/settings.py; kiểm tra DB đích trước khi migrate, không coi ví dụ là log đã chạy. Seed chỉ tạo hồ sơ giả, không tạo bộ ảnh nhận diện người thật. QR_ENABLED mặc định false; không bật QR để demo vision. OpenCV chạy cục bộ, không cần cloud/API key. Nếu thiếu cv2.FaceRecognizerSF hoặc cv2.FaceDetectorYN, kiểm tra đã cài opencv-contrib-python-headless từ requirements, tránh cài nhiều biến thể cv2 chồng nhau.

## 1.1 Chạy UI local để demo

Cách nhanh từ root: `backend/.venv/Scripts/python.exe .document-tools/run_demo.py`. Launcher tạo dữ liệu giả/buổi hôm nay sẵn sàng và chỉ ra file `demo-login.txt` ngoài repository để lấy đăng nhập. Mỗi lần chạy tạo DB mới; không thay DBgốc. [Bằng chứng153test/browser lịch sử trước SFace và giới hạn mô phỏng](project-management/evidence/ui-demo/README.md).

Mở `http://127.0.0.1:8000/` sau migrate/seed/runserver. Đăng nhập demo_teacher_a hoặc demo_supervisor bằng mật khẩu local đã chọn; STUDENT không được dùng staff console. Không có mật khẩu cứng trong tài liệu/UI.

1. Chọn lớp thuộc quyền; xem tổng quan và danh sách học sinh.
2. Trong điểm danh, tạo/chọn lịch và buổi đúng ngày/khung giờ, mở buổi để chốt roster. Nếu chưa có buổi phù hợp, cấu hình lịch demo riêng; không chỉnh dữ liệu vận hành để phục vụ bài thi.
3. Trong học sinh, chọn đúng người, đăng ký3–10ảnh được phép sử dụng. Ảnh đánh giá phải khác ảnh enrollment; xóa mẫu sau thử nếu cần.
4. Trong điểm danh, chọn camera hoặc upload một ảnh. Chưa đủ quyền camera/không có camera thì dùng upload/manual. Chụp ảnh rồi phân tích; kiểm tra proposal PENDING và attendance chưa đổi.
5. Nhìn người thực tế, xác nhận danh tính bắt buộc và đồng phục nếu đủ bằng chứng. Reject/chụp lại/manual khi không chắc chắn. Không tự coi UNKNOWN là đạt hoặc vi phạm.
6. Thử manual/uniform, chốt buổi; qua báo cáo lọc cùng lớp/ngày, tải và mở XLSX/CSV đối chiếu. Logout khi kết thúc; không để camera/ảnh/mẫu riêng tư hiển thị cho người khác.

Console dùng session/CSRF/API scope hiện có; ẩn nút không phải kiểm tra quyền. UI local là ngoại lệ theo yêu cầu người dùng, không mở PM gate hoặc cho phép deploy. Evidence kiểm chứng browser, responsive và lỗi camera/mạng được ghi riêng; các bước trên là hướng dẫn, không phải kết quả đã chạy.

## 2. Đăng ký và chạy API

Dùng [api-requests.http](../api-requests.http), cookie jar HTTP client; hoặc curl.exe theo mẫu dưới. GET /auth/me ban đầu trả 401 kèm csrftoken; copy cookie vào X-CSRFToken cho login. Login đổi token, copy token mới cho mọi request ghi sau đó. Giữ cookie/session đúng vai trò. Chọn lớp, student UUID, session OPEN/roster thuộc quyền từ response, ngày/khung giờ hiện tại: `start_at <= now <= close_at` kể cả hai biên; ngoài giờ trả409 SESSION_TIME. Không gửi student_id trong scan/confirm.

```powershell
$base = 'http://127.0.0.1:8000/api/v1'
curl.exe -c demo-cookies.txt "$base/auth/me"
# Dùng auth/login trong collection; copy csrftoken mới sau login.
$csrf = 'paste-current-csrftoken-cookie'
$student = 'paste-student-uuid'
$session = 'paste-open-session-uuid'
# 3 file của cùng người; ảnh profile không tự là enrollment.
curl.exe -b demo-cookies.txt -c demo-cookies.txt -H "X-CSRFToken: $csrf" -F "images=@sample-1.jpg" -F "images=@sample-2.jpg" -F "images=@sample-3.jpg" "$base/students/$student/face-samples"
curl.exe -b demo-cookies.txt "$base/students/$student/face-samples"
# Ảnh đánh giá khác bộ đăng ký, một người, thấy cả mặt và vùng áo.
curl.exe -b demo-cookies.txt -H "X-CSRFToken: $csrf" -H 'Idempotency-Key: vision-demo-analysis-01' -F "image=@evaluation-1.jpg" "$base/sessions/$session/vision-scans"
curl.exe -b demo-cookies.txt "$base/sessions/$session/vision-scans"
```

Enrollment 3–10 ảnh, tối đa 2MiB/4MP mỗi ảnh, tổng15MiB; đúng một mặt đủ nét. Chụp đa góc nhẹ/ánh sáng phù hợp; không đổi người trong bộ mẫu. Lỗi một ảnh phải giữ bộ cũ; xác nhận bằng GET metadata. Chỉ crop grayscale128x128 private trong DB; không GET byte crop. DELETE khi kết thúc thử dữ liệu cần xóa; xóa/re-enroll làm proposal cũ không xác nhận được.

Sau scan kiểm tra attendance vẫn UNMARKED/chưa đổi. Lấy scan UUID/version và attendance version mới từ queue/roster. Trong vòng120s, nhân sự nhìn người thật rồi gửi qua collection:

```http
POST /api/v1/vision-scans/<scan-uuid>/confirm
Content-Type: application/json
X-CSRFToken: <current-token>
Idempotency-Key: vision-demo-confirm-01

{"expected_scan_version":0,"expected_attendance_version":0,"identity_confirmed":true,"uniform":{"observed_uniform":"SHIRT","uniform_status":"COMPLIANT"}}
```

Chỉ chọn uniform sau khi nhân sự kiểm tra; có thể bỏ uniform để kiểm tra sau qua API hiện có. UNKNOWN không tự thành COMPLIANT/NON_COMPLIANT. Retry cùng key/body không thêm log/attendance; body khác cùng key phải conflict. Đổi key cho thao tác mới. Reject dùng expected_scan_version và reason. Sai/không rõ người → reject/chụp lại/manual, không sửa student_id trong confirm để chọn người khác. Nếu sample/attendance đã đổi hoặc scan hết hạn, lấy scan mới/manual.

Quota phân tích20/phút/actor dùng cửa sổ phút cố định, cache từng process; không chứng minh giới hạn toàn hệ thống hoặc cửa sổ rolling.

Dùng endpoint roster/manual/uniform/close/report/export từ collection hiện có để hoàn tất luồng, giữ version và cùng bộ lọc report. Mở lại XLSX/CSV so sánh tổng/chi tiết với JSON; source VISION và arrived_at phải là scanned_at server. File samples lịch sử là QR, không trình bày như output vision mới.

## 3. Kiểm chứng kỹ thuật trước review

```powershell
# Trong backend cwd, dùng DB thử riêng.
.venv/Scripts/python.exe manage.py test tests.test_vision_engine tests.test_vision_api
.venv/Scripts/python.exe manage.py test
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
.venv/Scripts/python.exe -m pip check
```

Chạy migrate trên DB rỗng và bản sao DB schema v1.2; không thao tác DB nguồn. Ghi command/ngày/exit code/count vào evidence, tách synthetic/mocked detector khỏi camera thật. Root backend validation cung cấp log mới; không lấy126test lịch sử làm số test hiện tại. Chỉ cập nhật Finish? sau implementation+validation+review; PM quyết định gate riêng.

## 4. Thuyết trình 5–7 phút

Mở [PowerPoint 7 slide](thuyet-trinh-opencv.pptx); mỗi slide có speaker notes và thời lượng. Tạo lại bằng `backend/.venv/Scripts/python.exe .document-tools/build_opencv_presentation.py`; dependency python-pptx chỉ ở .document-tools/presentation-deps, không thuộc backend runtime. Chưa render/chạy trên PowerPoint thật.

| Phút | Nội dung và thao tác |
| --- | --- |
| 0–1 | Bài toán đi học/đồng phục, GVCN/giám thị, roster và quyền theo lớp |
| 1–2 | Django + OpenCV local; Haar phát hiện, LBPH gợi ý người, HSV gợi ý màu áo; giải thích xác nhận bắt buộc |
| 2–3.5 | Đăng nhập staff, mở buổi, dùng ảnh đánh giá đã được phép; scan PENDING và attendance chưa đổi; nhìn người, confirm, xem source VISION |
| 3.5–4.5 | Một ảnh mờ/người lạ/không rõ áo; từ chối/chụp lại hoặc manual; nêu không bảo đảm chống ảnh giả |
| 4.5–5.5 | Chốt buổi, report JSON/XLSX/CSV cùng bộ lọc, đối chiếu tổng/chi tiết |
| 5.5–7 | Evidence hiện tại, giới hạn synthetic/camera/HSV, checklist còn chờ; UI local ngoại lệ và API gate vẫn chờ PM |

Demo bằng UI local được người dùng cho phép trước gate; API client vẫn là phương án dự phòng. Chỉ nói đã kiểm chứng camera/browser khi có log riêng. Nếu chưa có tập mặt thật được phép và đánh giá độc lập, dùng fixture có nhãn là dữ liệu thử và nói rõ giới hạn.

## 5. Checklist thiết bị thật — chưa hoàn tất

- [ ] Có sự cho phép sử dụng ảnh thử; tách enrollment và evaluation, ghi thiết bị/ánh sáng/góc chụp, xóa dữ liệu sau thử theo thỏa thuận.
- [ ] Đúng người, người lạ, hai người, mặt mờ/thiếu sáng/nghiêng, khuôn mặt sát ngưỡng và ảnh chụp giả; log đúng/nhầm/từ chối, không suy liveness.
- [ ] Áo trắng/xanh/khác màu, vùng áo che/khuất/cắt, nền giống áo; UNKNOWN không tự kết luận vi phạm.
- [ ] UI local: cho phép/từ chối camera, camera không có/bị mất, mất mạng và retry, không tạo điểm danh trùng.
- [ ] Staff khác lớp/STUDENT/logout bị chặn enrollment/queue/scan/confirm/reject/metadata; giáo viên chuyển lớp không giữ quyền cũ.
- [ ] Expiry120s, manual/close/transfer/re-enroll/delete, attendance version cũ, invalid uniform rollback và retry chính xác.
- [ ] Manual fallback, close, JSON/XLSX/CSV khớp dữ liệu; không lộ crop/frame/password trong response/evidence.
- [ ] Có log kết quả, người review, PM Comment; PM duyệt API gate riêng. Không tick checklist khi chỉ có code/fixture.


## Nâng cấp YuNet + SFace FP32 — v1.4

Chuẩn bị model trước manage.py nhận diện: `manage.py prepare_vision_models`; launcher tự gọi lệnh này. Revision/SHA-256 được pin, request không tải network. Giữ các giấy phép trong backend/third_party/opencv_zoo. DB đang dùng phải backup và migrate, giữ tài khoản/secret và không seed lại; đăng nhập bằng tài khoản cũ để enrollment3–10ảnh màu mới. Launcher dữ liệu giả là luồng riêng, không dùng thay quy trình migrate DB người dùng.

GET face-samples trả sample_count, usable_sample_count, requires_reenrollment, model_key=sface-2021dec-fp32. Mẫu LBPH legacy không tự chuyển đổi; khi chưa có3mẫu mới, UI yêu cầu đăng ký lại. Chưa có mẫu nào thì requires_reenrollment=false nhưng vẫn cần enrollment. Crop màu BGR căn chỉnh112x112 và embedding chuẩn hóa128float32 little-endian/512byte private, không trả bytes. Mẫu mới thay nguyên bộ nguyên tử và vô hiệu proposal cũ.

Đọc model_key/metric/cosine_score khi phân tích: SFace metric=cosine, điểm cao hơn giống hơn; distance=1-cosine, không phải phần trăm. Lịch sử LBPH giữ metric=lbph_distance, không so trực tiếp khoảng cách cũ/mới. Ngưỡng mặc định cosine≥0.45 và margin≥0.10, sharpness50; thiếu model503 VISION_UNAVAILABLE. Roster chỉ còn mẫu legacy trả UNKNOWN/REENROLLMENT_REQUIRED, không fallback LBPH. HSV/xác nhận bắt buộc/manual giữ nguyên.

Dùng ảnh đánh giá ngoài enrollment và người lạ độc lập; không chỉ upload lại ảnh mẫu để tuyên bố đạt. Bản nâng cấp đã đạt203test và kiểm thử trình duyệt thật trên ảnh ngoài mẫu của người dùng; xem [evidence SFace](project-management/evidence/sface-upgrade/README.md). Bộ ảnh nhỏ không phải accuracy tổng quát hoặc bảo đảm liveness.

Để tiếp tục DB demo local đã có, dùng `backend/.venv/Scripts/python.exe .document-tools/run_demo.py --resume-runtime <thư-mục-runtime-demo>`. Lệnh kiểm tra thư mục tạm và DB/login tồn tại, chạy migration rồi giữ dữ liệu/mật khẩu, không seed lại. Launcher tạo secret phiên mới nên cần đăng nhập lại. Không dùng launcher tạo demo mới nếu muốn giữ mẫu và điểm danh hiện tại.
