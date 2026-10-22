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
