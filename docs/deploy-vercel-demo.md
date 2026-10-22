# Demo Django/OpenCV trên Vercel

Cập nhật 22/10/2026. Production: https://attendance-eta-silk.vercel.app. Root Directory: `backend`, Python 3.12, entrypoint `config.wsgi:application`, build script `python build_vercel.py`. Camera cần HTTPS và quyền trình duyệt. PM API_Gate vẫn chờ review nghiệp vụ.

## Lưu dữ liệu dùng chung

Production dùng PostgreSQL qua Neon Free, kết nối bằng biến bí mật `DATABASE_URL` do integration Vercel cấp. Điểm danh, mẫu mặt (crop + embedding trong DB), tài khoản và dữ liệu lớp/học sinh được dùng chung giữa các instance và các lần redeploy. Không thay `DATABASE_URL` hoặc xóa DB để làm mới giao diện.

| Biến | Mục đích |
| --- | --- |
| `DJANGO_SECRET_KEY` | Secret Django; giữ ổn định để cookie đăng nhập tiếp tục hợp lệ |
| `DEMO_PASSWORD` | Mật khẩu đủ mạnh khi tạo tài khoản demo lần đầu |
| `DATABASE_URL` | URL PostgreSQL có TLS, lấy từ Vercel → Storage/integration Neon; không đưa vào Git/log/chat |

Integration hiện kết nối **Production**. Preview chưa có `DATABASE_URL` vẫn dùng SQLite tạm. Khi tạo preview riêng, dùng database/branch riêng để tránh sửa dữ liệu production trong lúc thử nghiệm.

Nếu không có `DATABASE_URL`, ứng dụng vẫn hỗ trợ SQLite cho local/demo tạm: trên Vercel mỗi instance có bản sao riêng và có thể mất điểm danh/mẫu khi cold start hoặc redeploy. Không dùng chế độ này để chứng minh dữ liệu được lưu lâu dài. `DJANGO_DB_PATH` luôn ưu tiên SQLite để build/test/local được cách ly; **không đặt biến này trong cấu hình runtime production PostgreSQL**. URL PostgreSQL sai hoặc không có TLS sẽ báo cấu hình lỗi, không tự rơi về SQLite.

## Khởi tạo DB mới và cập nhật schema

Operator nạp các biến môi trường qua kênh riêng; Django không tự đọc `.env`. Với DB mới, chạy từ `backend`:

```powershell
python manage.py migrate --noinput
python manage.py seed_demo
python manage.py shell -c "from config.vercel_demo import prepare_demo_rules, refresh_demo_sessions; prepare_demo_rules(); refresh_demo_sessions()"
```

Hai lệnh chuẩn bị chỉ dành cho dữ liệu demo giả đã được seed. Không chạy lại `prepare_demo_rules` để ghi đè lịch đã tùy chỉnh. `seed_demo` giữ mật khẩu cũ và dừng khi gặp dữ liệu trùng không tương thích. Với DB đã có dữ liệu, thay đổi schema qua `migrate` sau khi backup; build/redeploy không tự seed/reset DB dùng chung. Mỗi ngày middleware mở buổi demo giả bằng service hiện có, có khóa DB để phối hợp các instance; không chạy migration hay tạo lại tài khoản trong request.

Build luôn tạo SQLite template **riêng** bằng đường dẫn staging, kể cả khi môi trường có `DATABASE_URL`. Build tải/kiểm SHA-256 YuNet + SFace FP32, chuẩn bị static và template; không ghi production PostgreSQL. Hai model được bundle, không tải trong request. Thiếu/hỏng model trả `VISION_UNAVAILABLE`, không fallback sang nhận diện khác.

## Luồng camera và kiểm tra nhanh

Đăng nhập `demo_supervisor` bằng mật khẩu đã cấu hình; có thêm `demo_teacher_a/b` và tài khoản học sinh giả. Chọn buổi hôm nay đang mở. Đăng ký 3–10 ảnh rõ mặt cho học sinh, rồi mở camera trong **Điểm danh**.

1. Server xác minh hai khung hình độc lập cùng một học sinh trong roster, đủ ngưỡng → commit PRESENT ngay, không cần xác nhận tay.
2. UI giữ biên nhận “Đã lưu”, nghỉ ít nhất **5 giây** sau kết quả thành công rồi quan sát người tiếp theo. Ảnh mờ/không rõ danh tính không xóa điểm danh và không được coi là người đã rời camera.
3. Người khác được xác định đủ điều kiện có thể vào tiếp sau khoảng nghỉ. Hai lần quan sát `NO_FACE` liên tiếp, cách nhau ít nhất một giây, đưa camera về trạng thái chờ trống; với nhịp quét 4 giây việc này có thể lâu hơn một giây.
4. Cùng học sinh đã PRESENT không ghi thêm lượt và không đổi giờ đến. Kết quả ABSENT đã ghi được giữ nguyên và hiển thị rõ; sửa thủ công qua giáo viên khi cần.
5. Thử làm mờ sau khi thành công, làm mới trang, rồi mở một trình duyệt/điện thoại khác: roster trong cùng buổi phải tiếp tục giữ PRESENT và giờ đến cũ.

Camera gửi tối đa một cặp/4 giây khi không nghỉ/backoff, mỗi ảnh ≤1 MiB, tổng ≤2 MiB, không chồng request. Giới hạn phân tích 20/phút/nhân sự dùng cache process, chưa phải hạn mức phân tán. Hai ảnh nhất quán không phải bảo đảm chống giả mạo/liveness.

## Ảnh mẫu và đồng phục

UI nhận JPEG/PNG/WebP gốc ≤32 MiB/120 MP mỗi ảnh, thu nhỏ/nén tuần tự trước khi gửi. Enrollment Vercel tổng ≤3 MiB sau tối ưu, mỗi ảnh ≤2 MiB/4 MP; local API ≤16 MiB/64 MP mỗi ảnh và tổng ≤64 MiB. HEIC/RAW cần đổi sang JPEG. Mẫu đã đăng ký bằng SQLite tạm có thể cần đăng ký lại khi chuyển DB: API metadata không xuất ảnh/embedding để khôi phục đầy đủ.

**Mẫu đồng phục** cũng nhận ảnh gốc ≤32 MiB/120 MP qua UI. Ảnh tự thu nhỏ/nén xuống ≤1,9 MiB và cạnh tối đa1920px trước khi chọn vùng áo; chỉ ảnh đã tối ưu được gửi lên server. Tọa độ vùng áo được ánh xạ về ảnh decoder960px như API hiện có. API đồng phục giữ giới hạn2MiB/4MP; không gửi ảnh gốc lớn trực tiếp vào API. Backend vẫn kiểm tra một khuôn mặt nằm phía trên vùng áo và chỉ lưu phần áo; ảnh có mặt không được giữ trong dataset. Đổi ảnh/lớp/view khi đang tối ưu hủy kết quả cũ.

Đồng phục trường cần model local đã được đánh giá riêng; thiếu bằng chứng giữ `NOT_CHECKED`. Không dùng màu áo để khẳng định logo/mẫu trường. Phòng thử dataset KV chỉ chạy local, không được xuất bản trong deployment này.

Ảnh đại diện học sinh và file export dùng filesystem vẫn là file tạm trên Vercel; PostgreSQL ở đây bảo đảm dữ liệu bản ghi và mẫu nhận diện trong BinaryField, không bổ sung cloud object storage. Không đưa DB/runtime, ảnh người dùng, mật khẩu hay `.env` vào Git. Phân quyền và CSRF vẫn do backend kiểm tra trên mỗi API.

Tham khảo vận hành: [Django trên Vercel](https://vercel.com/docs/frameworks/full-stack/django), [Neon integration](https://vercel.com/marketplace/neon), [Psycopg binary](https://www.psycopg.org/psycopg3/docs/basic/install.html), [giới hạn Functions](https://vercel.com/docs/functions/limitations).
