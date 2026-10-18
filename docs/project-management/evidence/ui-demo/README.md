# UI demo local — 18/10/2026

UI được triển khai theo yêu cầu trực tiếp “làm luôn UI để demo”, ngoại lệ trước gate. PM API_Gate vẫn NOT_APPROVED; không tự tick Finish?, deploy hoặc chia sẻ ngoài.

## Kiểm chứng

- [Backend log](backend-validation.txt): **153test đạt,62.494s**; Django check, fresh migrate, migration drift và pip check đều exit0. DB gốc workspace không thay đổi.
- [Browser log](browser-validation.txt): Microsoft Edge headless, desktop1440px/mobile390px, **0 lỗi JavaScript chưa xử lý**.
- Browser kiểm tra đăng nhập thật qua CSRF, sai mật khẩu, staff scope, camera bị từ chối/upload dự phòng, Haar thật từ chối ảnh trắng, metadata mẫu riêng tư, manual/uniform/chốt, tải XLSX/CSV và mở lại đối chiếu10roster/1có mặt/9vắng/1vi phạm. [Excel](browser-attendance.xlsx), [CSV](browser-attendance.csv).
- Lưu lịch chiều, tạo buổi PLANNED và mở buổi qua UI thật; roster snapshot10học sinh xuất hiện đúng. Đây là dữ liệu QA riêng, không sửa lịch của demo người dùng.
- Regression đã thấy FAIL→PASS: server commit manual rồi browser giả lập mất body; retry giữ nguyên key, không ghi trùng. Response enrollment lớp cũ bị trì hoãn không được ghi lỗi vào dialog lớp mới.
- Logout/401 xóa bảng, tên ẩn, FileList và trả login; STUDENT không vào staff console, GVCN chỉ thấy lớp được giao.
- Test camera preview/capture/dừng track dùng **MediaStream tổng hợp** trong browserQA. Test proposal/confirm dùng **response fixture chỉ trong browserQA**, chứng minh gợi ýSHIRT không tự chọn uniform, checkbox danh tính bắt buộc và payload không có student_id/uniform khi chưa chọn. Fixture không ghi attendance, không thay detector server, không xuất hiện trong UI demo người dùng.

Ảnh chụp dùng dữ liệu giả: [đăng nhập](login-desktop.png), [dashboard desktop](dashboard-desktop.png), [điểm danh](attendance-desktop.png), [mobile](dashboard-mobile.png). Không dùng screenshot fixture để giả làm kết quả nhận diện mặt thật.

## Review

Reviewer độc lập đã duyệt spec rồi quality/security. Đã sửa hai finding bắt buộc: mặc định đồng phục Chưa kiểm tra thay vì tự chọn gợi ýHSV; giữ timeout và uncertain-error handling xuyên suốt đọc JSON/blob để không mất retry key. Bổ sung epoch/auth/class/session/view guards, chặn lỗi dialog trễ, xóa dữ liệu private sau logout và dừng camera khi chuyển tab/logout. Review lại không còn finding chặn; reviewer xác nhận log153test và browser mới.

## Tái lập

Từ root:

```powershell
backend/.venv/Scripts/python.exe .document-tools/run_demo.py
```

Mở `http://127.0.0.1:8000/`; lấy tài khoản trong file `demo-login.txt` tại đường dẫn launcher in ra. Mỗi lần chạy tạo DB tạm mới với20học sinh giả/2lớp/2buổi hôm nay OPEN00:00–23:59; không đổiDBgốc hoặc nới kiểm tra giờ API. Password/secret không nằm trong source/HTML/log. Dừng bằng Ctrl+C.

BrowserQA riêng:

```powershell
backend/.venv/Scripts/python.exe .document-tools/verify_demo_ui.py
```

Test khởi tạo server/DB riêng cổng8001, dừng đúng cây process đã tạo, kiểm tra đường dẫn runtime trước dọn. Không sửa demo người dùng cổng8000. Playwright1.58.0 đặt trong .document-tools/browser-deps, không thêm dependency backend; dùng Edge có sẵn trên Windows.

Chưa kiểm chứng camera vật lý, nhận diện người thật/accuracy/liveness hoặc PowerPoint rendering. Muốn thử mặt thật, đăng ký3–10ảnh cùng học sinh được phép dùng và đánh giá bằng ảnh khác/camera. HSV chỉ đo dải màu, không nhận diện mọi mẫu đồng phục. SQLite/cache quota phục vụ demo nhỏ. Review kỹ thuật không thay PM nghiệm thu.
