# Demo trên Vercel

API đã được tối ưu để request thông thường không nạp OpenCV/NumPy/Excel trước khi cần; quét mặt chỉ đọc embedding, không kéo crop ảnh từ DB. Runtime đã khởi tạo bỏ qua copy-lock/tạo thư mục lặp lại, vẫn tự phục hồi khi mất DB tạm. [Kiểm chứng API/Vercel](project-management/evidence/vercel-api-performance/README.md). Đây là cấu hình bàn giao để bạn tự deploy; không có deployment được tạo tự động.

Import repository `Gaesiii/mindxpj` vào Vercel, chọn **Root Directory: `backend`**, framework **Django**, giữ build command theo `pyproject.toml`. Python được khóa ở 3.12. Chưa thực hiện deploy trong lần bàn giao này.

Chỉ cần thêm hai Environment Variables trước khi build:

File `.env.vercel` tạo trên máy chỉ dùng để nhập giá trị; không được push và Vercel không tự đọc file local đó. Trong đúng project Vercel, mở Environment Variables, nhập từng Name/Value, chọn Production và Preview, Save rồi tạo deployment mới. Nếu build vẫn báo thiếu env, tìm dòng `[demo-build:v2]`: dòng này chỉ in tên biến=set/missing, môi trường và commit, không in giá trị. Log không có marker này là bản code cũ; cần chọn deployment mới từ nhánh main.

Nếu hai biến đều `set` nhưng seed thất bại, bản mới kiểm tra mật khẩu cho cả23tài khoản trước khi tạo dữ liệu. `DEMO_PASSWORD rejected [...]` chỉ rõ mã như `password_too_short`, `password_too_common`, `password_entirely_numeric`, `password_too_similar`; thay bằng giá trị mật khẩu ngẫu nhiên trong file private và tạo deployment mới. Chỉ copy phần giá trị sau `DEMO_PASSWORD=`, không copy tên biến/dấu `=` vào ô Value. Nếu báo `data validation`, `data creation rejected` hoặc `database constraint`, giữ dòng mã lỗi đó để chẩn đoán dữ liệu, không tự bỏ kiểm tra mật khẩu.

| Biến | Giá trị |
| --- | --- |
| `DJANGO_SECRET_KEY` | Chuỗi ngẫu nhiên dài, giữ nguyên giữa các lần build cần dùng chung phiên |
| `DEMO_PASSWORD` | Mật khẩu demo đủ mạnh, tối thiểu 8 ký tự và không quá phổ biến |

Có thể tạo secret bằng `python -c "import secrets; print(secrets.token_urlsafe(64))"`. Lưu trong cấu hình Vercel; không đưa giá trị thật vào repository. Không cần `DATABASE_URL`, dịch vụ DB hay chạy migrate thủ công.

Sau khi deploy, mở `/`, đăng nhập `demo_supervisor` với mật khẩu đã đặt. Có thêm `demo_teacher_a` và `demo_teacher_b` để trình bày phân quyền theo lớp. Dữ liệu gồm hai lớp, 20 học sinh giả; buổi sáng và chiều của ngày hiện tại tự mở để demo. Đóng buổi sẽ giữ trạng thái đóng trên instance đó. Xem [kịch bản demo](huong-dan-demo-opencv.md) và [slide](thuyet-trinh-opencv.pptx). Đăng ký 3–10 ảnh mẫu khác nhau trước khi thử nhận diện; kết quả phải được nhân sự xác nhận. Camera cần HTTPS và quyền trình duyệt.

Build chạy prepare_vision_models để tải/kiểm SHA-256 model YuNet+SFace FP32 đã pin trước khi bundle, rồi migration, tạo DB mẫu có hash mật khẩu và thu gom static. Lần truy cập đầu của mỗi instance chỉ copy DB mẫu vào vùng tạm có khóa khởi tạo; không migrate hay hash mật khẩu tại cold start. Static được phục vụ qua cơ chế Django/CDN của Vercel. `config.wsgi` được chọn rõ ràng, timeout 60 giây; OpenCV dùng bản headless, không cần GUI hệ thống. Cấu hình theo [Django trên Vercel](https://vercel.com/docs/frameworks/full-stack/django) và [Python runtime](https://vercel.com/docs/functions/runtimes/python).

DB SQLite, ảnh riêng tư và mẫu khuôn mặt mới tạo **chỉ tồn tại tạm trên từng instance**. Instance mới/redeploy có thể mất thay đổi; các instance không đồng bộ dữ liệu. Chỉ dùng dữ liệu giả hoặc người tự nguyện cho buổi demo. Đây là lựa chọn để giảm setup, không phải lưu trữ lâu dài; xem [giới hạn SQLite của Vercel](https://vercel.com/kb/guide/is-sqlite-supported-in-vercel). Phiên đăng nhập dùng cookie ký có hạn một giờ; không có cơ chế thu hồi phiên toàn cục bền vững giữa các instance. Dữ liệu nhạy cảm không nằm trong cookie.

Vercel giới hạn request/response 4.5 MB, nên demo giới hạn tổng ảnh enrollment **3 MiB**, mỗi ảnh tối đa 2 MiB/4 triệu pixel. UI báo trước khi gửi; localhost vẫn cho tổng 15 MiB. Chọn ảnh JPEG nhỏ khi trình bày. Xem [giới hạn Functions](https://vercel.com/docs/functions/limitations).

Hostname deployment và production do Vercel cung cấp được thêm tự động vào `ALLOWED_HOSTS`. Nếu dùng domain riêng chưa nằm trong các biến platform, thêm `DJANGO_ALLOWED_HOSTS` là danh sách hostname phân cách dấu phẩy, không có `https://`. Không bật `DJANGO_DEBUG` trên bản public. Giữ hai biến platform host được Vercel cung cấp khi cấu hình project.

Kiểm chứng local và giới hạn bằng chứng nằm trong [evidence Vercel](project-management/evidence/vercel-demo/README.md). Đã tải đủ Linux wheels; tổng nội dung wheel khoảng267.4MiB; model đã xác minh38,928,942byte (khoảng38.9MB/37.1MiB), tổng ước tính304.5MiB trước source/runtime/overhead. Đây là estimate không phải kích thước function deployed. Chưa xác nhận build thực tế trên hạ tầng Vercel hay camera/người thật.


YuNet + SFace FP32 được chuẩn bị tại build, include trong bundle, không download ở HTTP request/cold start. Thiếu/hỏng model trả503 VISION_UNAVAILABLE, không fallback LBPH. Hai biến người dùng cần cấu hình vẫn chỉ DJANGO_SECRET_KEY và DEMO_PASSWORD. Giữ license/attribution YuNet MIT và SFace Apache2.0 trong backend/third_party/opencv_zoo khi đóng gói. Mẫu LBPH từ DB cũ cần enrollment lại3–10ảnh; SFace lưu crop màu112x112 và embedding private, scan metric=cosine không phải xác suất. SQLite/ảnh/mẫu chỉ tạm từng instance như mô tả trên. Chưa deploy và chưa kiểm chứng bundle thực tế trên Vercel hoặc độ chính xác camera; không công bố kết quả đang chạy là đã đạt.
