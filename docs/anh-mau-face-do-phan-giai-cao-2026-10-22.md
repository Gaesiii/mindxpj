# Ảnh mẫu khuôn mặt từ camera độ phân giải cao

Theo yêu cầu22/10/2026, UI cho chọn **3–10 ảnh JPEG/PNG/WebP, mỗi ảnh gốc tới32MiB/120MP**. UI tự xử lý từng ảnh tuần tự, giữ nguyên toàn khung và tỷ lệ, đổi thành JPEG trước khi upload. Có trạng thái “Đang tối ưu ảnh…” và tổng dung lượng trước/sau; không cần tự giảm file trước khi chọn. HEIC/RAW cần chuyển JPEG trước.

Giới hạn backend local tăng từ tổng15MiB lên **64MiB/bộ**, từng ảnh đăng ký tối đa **16MiB/64MP**. UI vẫn tối ưu ảnh trước upload kể cả local. Chỉ lưu crop mặt112×112 và embedding như trước, không lưu ảnh camera gốc. Giới hạn của ảnh quét/auto-attendance không thay đổi.

Vercel vẫn giới hạn [payload mỗi request4,5MB](https://vercel.com/docs/functions/limitations). Vì vậy backend Vercel giữ tổng3MiB sau tối ưu, từng ảnh2MiB/4MP. Thay đổi nằm ở việc cho phép chọn ảnh gốc lớn và tối ưu tự động, không tăng một con số khiến deployment trả413. UI chia ngân sách theo số ảnh, giới hạn ảnh gửi≤1,9MiB, chừa10% cho multipart; giảm cạnh dài từ1920px theo từng bước và thử chất lượng JPEG từ0,92 xuống0,64. Không crop tự động hoặc gửi ảnh gốc lên Vercel.

Thử trên Chromium với ba fixture48MP (8000×6000) dựng từ bộ portrait đăng ký đã được phép dùng, thêm nhiễu nhẹ để thử dung lượng:

- File gốc10.330.541,9.703.096,10.039.546bytes, tổng30.073.183bytes (~28,7MiB).
- Đặt ngân sách UI3MiB như Vercel; multipart thực được serialize887.203bytes (~0,85MiB).
- API model thật trả201 và lưu **ba mẫu dùng được** trên học sinh demo giả lập; không chỉ kiểm tra thu nhỏ file.
- Đóng rồi mở lại cùng học sinh khi đang chuẩn bị ảnh không gửi nhầm bộ cũ. Token chuẩn bị cũng vô hiệu khi đổi ảnh/xóa mẫu; token kết quả ngăn response cũ đóng dialog mới.
- Không có lỗi JavaScript. Fixture48MP chỉ chứng minh xử lý dung lượng/độ phân giải, không phải ảnh mới chụp từ camera hoặc đánh giá độ chính xác nhận diện ngoài thực tế.

[Evidence browser đã lọc ảnh](project-management/evidence/large-face-enrollment-2026-10-22/browser-result.json). Tests kiểm tra decoder chỉ mở rộng ngân sách trong enrollment; scan vẫn từ chối ảnh vượt4MP, xử lý file tuần tự, giữ budget, hủy chuẩn bị cũ và role/scope/atomic replacement từ các suite hiện có. Cập nhật này không đổi ngưỡng chất lượng/nhận diện, số ảnh hoặc cơ chế điểm danh.
