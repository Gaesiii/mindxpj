# Demo đồng phục KV cho PM — 22/10/2026

Đã đưa dataset/model thử vào bản demo **local**, có giao diện dùng model thật, ảnh mẫu từ tập test, tải ảnh vùng áo và camera tự quét vùng khung. Model vẫn là thử nghiệm KV hai lớp, tách khỏi school profile và điểm danh. Chưa deploy hoặc gửi cho PM qua ứng dụng bên ngoài.

## Mở và quay trên máy hiện tại

1. Mở `http://127.0.0.1:8001/`, đăng nhập bằng thông tin ở file `demo-login.txt` mà launcher hiển thị. Không quay màn hình lúc mở file mật khẩu.
2. Chọn **Demo đồng phục KV** trên thanh bên; trang ở `/uniform-demo/` dùng chung phiên đăng nhập.
3. Chọn **Đồng phục KV · 04**, sau đó **Trang phục khác · 01**, rồi **Mẫu khó · 07**. Kết quả lần lượt đã kiểm tra: Đồng phục KV, Trang phục khác, Chưa đủ tin cậy.
4. Thử thêm **Tải ảnh vùng áo** (JPEG/PNG/WebP ≤2 MiB), hoặc **Bật camera** và đặt vùng áo trong khung xanh. Camera gửi một ảnh vùng khung khoảng mỗi 1,5 giây, tuần tự, không chạy chồng request. Đây là căn ROI thủ công, không ghép danh tính học sinh với áo. **Dừng camera** kết thúc stream; đổi tab cũng dừng.
5. Khi quay cho PM, giữ nhãn thử nghiệm và UNKNOWN trong khung hình. Có thể nói: “Bản này minh họa model ngoài trường chạy local; trước khi dùng nghiệp vụ cần dữ liệu đúng trường và đánh giá riêng.” Không diễn giải kết quả thành đã nhận đúng logo/mẫu trường mình.

Nếu server đã dừng, từ thư mục project chạy `start-uniform-demo.cmd`, hoặc:

```powershell
backend/.venv/Scripts/python.exe .document-tools/run_demo.py `
  --port 8001 --uniform-trial-dir uniform-dataset/kv-demo
```

Lệnh mặc định tạo DB demo riêng và mật khẩu mới, không ghi đè DB hiện có. Nếu muốn giữ DB demo lần trước, dùng `--resume-runtime` với đường dẫn runtime mà launcher đã in. Không chạy lại launcher trên cùng port khi server vẫn đang chạy. Bỏ `--uniform-trial-dir` sẽ tắt trang/thư viện ảnh demo KV.

## Data và ảnh mẫu đã đưa vào

`uniform-dataset/kv-demo/` trong workspace (đã được `.gitignore` loại trừ) chứa:

- `prepared/`: 547 crop và manifest chia train/validation/test có hash.
- `model.onnx`: classifier KV hai lớp đã kiểm tra SHA-256.
- `bundle.json`: gallery allowlist tám crop từ tập test; ba trang phục khác, ba KV, hai mẫu confidence thấp.
- `report.json`, `provenance.json`: số đo và nguồn dữ liệu/weights.

Dataset KV chỉ có NON_UNIFORM/KV_UNIFORM; chưa có SPORTS hoặc đánh giá logo trường mình. Nguồn hiện ghi license Unknown. Ảnh, weights, video có ảnh mẫu và model chỉ giữ local, không đưa GitHub. Gallery chỉ phục vụ staff đã đăng nhập qua loopback. Upload/camera không ghi file hoặc bản ghi điểm danh. Khi triển khai Vercel, cả trang và API demo KV đều bị vô hiệu hóa dù có cấu hình root.

Chuẩn bị lại bundle từ bộ thử đã có:

```powershell
backend/.venv/Scripts/python.exe .document-tools/prepare_uniform_demo.py `
  --source E:/projectmindx-data/uniform-kv-20261021
```

Script không tự tải hoặc phê duyệt model, không tạo review giả. Clone GitHub mới chỉ có code/docs, không có dữ liệu/model thử riêng tư. [Báo cáo dataset và cách tái lập](thu-nghiem-dataset-dong-phuc-kv-2026-10-21.md).

## Video mẫu và bằng chứng

Có video không lời quay tám ảnh mẫu trên trình duyệt, không có mật khẩu, không có camera giả trong video. Bản local đặt trong `deliverables/PM-demo-2026-10-22/pm-demo.webm`, có ảnh chụp toàn trang và kịch bản quay kèm theo. Người dùng tự xem/chọn file để gửi PM; không tự liên hệ PM.

[Browser evidence đã lọc ảnh](project-management/evidence/kv-demo-2026-10-22/browser-check.json) xác nhận model thật trả đúng ba KV/ba trang phục khác/hai UNKNOWN, đổi upload lúc request trước chưa xong vẫn xử lý ảnh mới nhất, không có lỗi JavaScript. Kiểm tra camera tự động dùng stream giả của Chromium để xác minh căn khung/dừng stream; **chưa kiểm chứng camera vật lý**. Video cung cấp chỉ chứa thử ảnh mẫu, không chứa stream giả. Camera vẫn phụ thuộc quyền và thiết bị trên máy người dùng.

Review kỹ thuật độc lập đã kiểm tra auth, role, loopback, CSRF, hash, giới hạn ảnh, không ghi điểm danh và lifecycle camera. Đã sửa lỗi hủy request khi đổi ảnh, bảo toàn tỷ lệ khung video và chặn cập nhật camera cũ sau dừng. Đây là nghiệm thu kỹ thuật cho demo local, không phê duyệt model trường hoặc thay PM acceptance.

Kiểm chứng cuối: từ thư mục `backend`, chạy `manage.py test tests --verbosity 1`, **260/260 tests đạt** trong 67,960 giây, system check không lỗi. Bộ này gồm kiểm tra cold import API không kéo OpenCV/NumPy khi chỉ nạp URL thông thường. Đã giữ inference import lazy để phần demo tắt không làm chậm khởi động các API còn lại. [Tóm tắt kiểm chứng](project-management/evidence/kv-demo-2026-10-22/verification.json).
