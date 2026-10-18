# students

M03 - Member 1: students, class membership and private profile photos.

A04–A07 đã triển khai Student UUID, mã unique, tên trùng hợp lệ, classroom PROTECT và active. GET/POST `/api/v1/students`, GET/PATCH `/api/v1/students/:id`; tìm theo `search`, lọc `class_id`/`active=true|false`. GVCN chỉ lớp đang được giao; SUPERVISOR toàn trường. PATCH full_name/active; class_id chỉ SUPERVISOR. Khi chuyển lớp, quyền hồ sơ/ảnh đổi ngay; roster lịch sử dùng snapshot riêng.

STUDENT chỉ GET hồ sơ tối thiểu của chính mình: id/student_code/full_name/class_id/grade_id; không list, sửa hoặc tải ảnh. Danh tính lấy User.student từ session; không nhận student_id, role hoặc photo_path tự khai.

POST `/api/v1/students/:id/photo` dùng multipart với đúng một field `photo`; GET cùng URL tải ảnh có quyền. Pillow xác minh nội dung JPEG/PNG/WebP, tối đa5 MiB đầu vào và24 triệu pixel; xoay theo EXIF rồi tạo PNG mới bỏ EXIF/comment/ICC. Không tin tên file để xác định loại ảnh. Lưu cục bộ dưới PRIVATE_MEDIA_ROOT bằng tên server; không route media công khai hoặc path trong JSON. Download image/png, nosniff, private/no-store.

Ảnh lỗi giữ ảnh cũ; DB write lỗi xóa ảnh mới. Thay thành công xóa ảnh cũ sau commit. Nếu Windows đang giữ handle tải ảnh cũ, callback không biến commit thành lỗi: ảnh cũ có thể tồn tại dưới vùng private, không còn được endpoint truy cập. MVP chưa có worker/dọn orphan tự động.

Kiểm chứng: `manage.py test tests.test_students tests.test_student_models` kiểm tra unique/tên trùng, scope/search/transfer/self identity, link1:1 active, fake/oversize/pixel cap, metadata stripping, WebP, thay ảnh/rollback và CSRF. Evidence tại docs/project-management/evidence. Không giao diện hoặc delete API.
