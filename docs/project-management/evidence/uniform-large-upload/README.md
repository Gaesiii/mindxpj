# Ảnh mẫu đồng phục từ camera — 22/10/2026

Yêu cầu: cho chọn ảnh mẫu đồng phục thực tế có dung lượng/độ phân giải lớn, tương tự đăng ký mặt; push và cập nhật Vercel.

Nguyên nhân: UI trước đây kiểm tra ảnh gốc ≤2 MiB/4MP rồi gửi nguyên file; ảnh điện thoại lớn bị chặn dù Vercel có thể nhận bản đã tối ưu. Thay đổi dùng encoder ảnh local sẵn có: JPEG/PNG/WebP gốc ≤32MiB/120MP, thu nhỏ/nén thành JPEG ≤1,9MiB, cạnh tối đa1920px, rồi cho chọn ROI trên ảnh đã chuẩn bị. Gửi file đã chuẩn bị cùng ROI theo hệ tọa độ decoder960px, không gửi file gốc. Generation/context/file guards loại kết quả cũ khi đổi lựa chọn hoặc lớp/view/đăng xuất. Không đổi API/schema/model/ngưỡng hay bỏ kiểm tra vùng áo không chứa mặt.

Kiểm chứng:

- Suite backend:269 bài trong63,191giây, thành công;1 bài PostgreSQL chỉ chạy trên PostgreSQL thật được bỏ qua ở suiteSQLite.

- Node: ảnh gốc25MiB được nhận; ảnh>32MiB/HEIC bị từ chối, payload sau tối ưu vượt ngân sách bị chặn, đổi lựa chọn hủy kết quả cũ.
- Chromium thực thi encoder thật: ảnh JPEG8000×6000 (48MP),22.247.629byte → multipart1.378.513byte. ROI `[240,288,480,360]` khớp vùng chọn ở decoder960px.
- Kiểm tra browser hiện có vẫn qua: camera điểm danh/đồng phục, giữ kết quả sau blur, CRUD, sửa đồng phục, scope UI, ROI ảnh1920px và không có page error.
- Kiểm tra backend đồng phục giữ nguyên quyền supervisor, phát hiện mặt phía trên ROI, không lưu pixel mặt, chống ghi khi archive/revoke trong lúc phân tích.
- Review độc lập: không có blocker về ngân sách request/pixel, ánh xạ ROI hoặc vòng đời lựa chọn ảnh.

Ảnh48MP là fixture tổng hợp để kiểm tra kích thước/luồng tải; không dùng để kết luận độ chính xác nhận diện đồng phục. Giữ các giới hạn backend để request phù hợp Vercel. HEIC/RAW phải đổi sang JPEG trước.

## Sửa chẩn đoán ảnh mẫu

Sau rollout, người dùng thấy câu “tối đa2MiB/4MP”. Kiểm tra mã cho thấy UI ghi đè mọi `INVALID_IMAGE` bằng câu này, kể cả các kiểm tra không thấy mặt/vùng áo chạm mặt/crop lưu trữ. Native probe ảnh trống từ lượt deploy trước cũng trả INVALID_IMAGE dù file nhỏ và đúng định dạng. Chưa có ảnh gốc người dùng để xác định điều kiện cụ thể bị vi phạm.

Backend nay giữ mã lỗi/status cũ và trả thêm `details.reason` phân biệt thiếu mặt, nhiều mặt, vị trí ROI, mặt nằm trong ROI, crop lưu trữ lớn. UI dùng thông báo tiếng Việt theo reason; thông báo ảnh chung không còn kết luận sai về kích thước. Kiểm tra hồi quy backend cho thiếu mặt/nhiều mặt/ROI đã thất bại trước sửa và qua sau sửa; browser kiểm tra lỗi thiếu mặt không chứa câu2MiB, sau đó thử tải lại mẫu48MP thành công qua API fixture.

## Chẩn đoán trường dữ liệu và sửa mép vùng chọn

Phát hiện thêm: preview1920×1080 đã chuẩn bị được hiển thị600×338, trong khi backend giải mã960×540. Hệ số scalar0,625 cũ biến mép dưới338thành541, gây lỗi bounds dù người dùng chọn trong ảnh; việc làm tròn x và width riêng cũng có thể cộng thành961. Đã chuyển ảnh đồng phục về tối đa960px như decoder, dùng tỷ lệ riêng hai trục theo kích thước preview thực tế, làm tròn/clamp hai đầu mút trước khi tính width/height. Encoder mặt giữ cấu hình cũ.

VALIDATION_ERROR nay có reason/field cho thiếu trường, nhãn áo, bộ dữ liệu, tên nhóm, ROI không đúng định dạng/quá nhỏ/vượt mép, nhóm khác split và quota. UI báo kích thước thực khi ROI nhỏ, tên split hiện tại khi nhóm xung đột, focus/đánh dấu trường cần sửa. API giữ status/code, không echo dữ liệu cá nhân. Lỗi POST cũ bị bỏ qua khi người dùng đã đổi ảnh/lớp/view.

Kiểm tra red trước sửa:6 lỗi trường/ROI và1 lỗi ánh xạ mép ảnh. Kiểm tra browser:thông báo31×40px cần96×96px, đánh dấu canvas; nhóm ở Huấn luyện hiển thị rõ và đánh dấu select; retry vẫn tải48MP đúngROI. Ảnh fixture22.247.629byte → multipart335.916byte với encoder960px. Review độc lập kiểm tra thêm10.000vùng chọn ngẫu nhiên:đều giữ trong ảnh, không có blocker.
