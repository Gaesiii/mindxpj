# Khắc phục điểm danh sau khi khuôn mặt bị mờ

Yêu cầu: commit PRESENT sau xác minh hai ảnh, giữ kết quả khi người vẫn ở camera nhưng ảnh mờ, có khoảng nghỉ rồi nhận người mới. Phạm vi gồm sửa UI và lưu dữ liệu dùng chung cho bản Vercel đang dùng; giữ quyền truy cập, CSRF, idempotency, lịch sử và sửa tay của giáo viên.

## Chẩn đoán

- API tự động không có nhánh xóa PRESENT khi `BLURRY_FACE`/`NO_FACE`; kiểm tra hồi quy xác nhận status, arrived_at, version và số VisionScan giữ nguyên sau các ảnh lỗi.
- UI cũ thay thông báo thành công bằng kết quả của khung hình kế tiếp và đọc lại roster ngay cả khi ảnh mờ.
- Runtime Vercel cũ sao chép SQLite riêng mỗi instance. Kiểm tra API có lần đọc thấy 1 PRESENT/3 mẫu mặt, lần đọc sau thấy 0 PRESENT/0 mẫu; dữ liệu tạm không ổn định giữa các lần truy cập. Không có bằng chứng để quy việc này cho thao tác xóa của thuật toán.

## Thay đổi

1. Gate camera: giữ biên nhận thành công, nghỉ 5 giây từ lúc nhận kết quả, không coi ảnh mờ/UNKNOWN là rời camera. Chấp nhận người khác đã được backend xác minh; hai `NO_FACE` liên tiếp cách nhau ≥1 giây giải phóng trạng thái chờ. Dừng/chuyển lớp/buổi/view xóa gate. Không cache PRESENT để giả thay DB.
2. Giữ sửa tay: nhận diện lại không đổi giờ đến, không thay ABSENT. Thông báo của người mới không bị biên nhận người cũ che. Không tải lại roster khi scan chưa rõ.
3. PostgreSQL tùy chọn bằng DATABASE_URL; explicit DJANGO_DB_PATH giữ build/local cách ly. Neon Free kết nối Production; không dùng DB production làm DB test. Migration/seed khởi tạo do operator thực hiện, không chạy trên request/build.
4. Khóa toàn bộ Student thuộc roster theo thứ tự pk, rồi Classroom và Session trước kiểm tra lại/commit: ngăn thay bộ mẫu hoặc chuyển lớp chen vào giữa xác minh revision và lưu PRESENT trên PostgreSQL. Không giữ khóa trong lúc OpenCV suy luận.
5. Buổi demo mỗi ngày vẫn tạo qua service với khóa hàng supervisor; không copy template vào DB chung. Mẫu face BinaryField được lưu chung; file avatar/export vẫn tạm.

## Kiểm chứng

- Suite local: 268 bài, thành công, 1 bài PostgreSQL bỏ qua trên SQLite.
- Browser Chromium camera giả: multipart hai ảnh/idempotency, nghỉ sau thành công và giữ biên nhận qua blur, dừng khi điều hướng, CRUD, sửa đồng phục, camera đồng phục riêng, phân quyền UI, ROI và không có lỗi JavaScript. Không phải bằng chứng độ chính xác hay camera điện thoại thật.
- Kiểm tra PostgreSQL thật dùng DB test riêng: 4 bài qua trong 165.172 giây, gồm hồi quy blur, retry không ghi lặp, bảo toàn ABSENT và giao dịch đồng thời xóa mẫu. Schema PostgreSQL đã migrate đủ 34 migrations trước kiểm tra; dữ liệu demo không bị dùng làm dữ liệu test.
- Review độc lập yêu cầu khóa enrollment/roster, giữ ABSENT của người tiếp theo và refresh buổi ngày mới; các điểm đã sửa, review tiếp không còn blocker. Kiểm tra PostgreSQL thật đã qua.

## Giới hạn chuyển đổi

Đã push mã `8af8fbe` và deploy production thành công. [Bằng chứng kiểm tra](../../project-management/evidence/attendance-persistence/README.md) ghi kết quả native build, API/DB dùng chung và phạm vi kiểm chứng camera.

API metadata của bản SQLite tạm không xuất ảnh/embedding hoặc đầy đủ audit/scan. Không thể khẳng định khôi phục toàn bộ dữ liệu đã biến mất cùng instance. Các snapshot API đọc được được lưu ngoài repository, không công bố dữ liệu cá nhân. Người demo có thể phải đăng ký lại mẫu khi chuyển DB. Không tăng phạm vi sang object storage/queue/external AI.
