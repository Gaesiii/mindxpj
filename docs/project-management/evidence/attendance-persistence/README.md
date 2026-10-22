# Điểm danh đã lưu và camera chờ người tiếp theo — 22/10/2026

Mã ứng dụng: `8af8fbe`. Production: https://attendance-eta-silk.vercel.app. Deployment được xác nhận `READY`: `dpl_GiYXJM1PcoQ8CN7ZiMSaxwAeeTBs`. Native build dùng Python 3.12/Django 5.2.18, hoàn tất sau 40 giây; bundle trước tối ưu 317.89 MB. Build dùng SQLite staging riêng; runtime đã xác minh dùng PostgreSQL chung.

- Suite SQLite: 268 bài trong 66.708 giây, thành công; 1 bài khóa PostgreSQL được bỏ qua trên SQLite.
- PostgreSQL thật: 4 bài trong 165.172 giây, thành công. DB test riêng với migration; kiểm tra blur sau PRESENT, retry không ghi lặp, bảo toàn ABSENT và khóa giữa điểm danh/xóa mẫu qua hai connection.
- Browser Chromium camera giả: giữ biên nhận qua blur, nghỉ 5 giây, không chồng request, dừng khi chuyển view, CRUD lớp/học sinh, camera đồng phục riêng, sửa đồng phục, phân quyền UI và ROI. Không có lỗi JavaScript.
- Production: root 200; API staff khi chưa đăng nhập 401; login 200; hai lớp demo, 10 học sinh trong lớp kiểm tra. Đổi tạm nhãn một học sinh giả qua API, đọc lại sáu lần bằng context độc lập và đối chiếu trực tiếp PostgreSQL; khôi phục nhãn gốc trong `finally`.
- Native OpenCV production nhận ba ảnh PNG trống trả 422 `NO_FACE`, không lưu mẫu; đây là kiểm tra runtime và validation, không phải đo độ chính xác mặt.
- Mobile viewport 390×844: HTTPS, API camera có sẵn, không tràn chiều ngang, không có page error. Phòng thử KV local trả 404 trên production.

Review độc lập đã yêu cầu và kiểm tra lại khóa Student → Classroom → Session, hiển thị ABSENT của người tiếp theo và chuẩn bị buổi demo ngày mới. Không còn blocker sau chỉnh sửa; PostgreSQL test thực tế đã qua.

Camera điện thoại/mặt thật chưa được xác minh bởi lượt kiểm tra tự động này. Dữ liệu SQLite tạm cũ có thể không khôi phục được đầy đủ; cần đăng ký lại mẫu khi chuyển sang DB chung. Mật khẩu, URL DB, ảnh người dùng và snapshot dữ liệu không nằm trong evidence/repository. Bản mã cũ được giữ bằng Git history và Git bundle riêng đã verify.
