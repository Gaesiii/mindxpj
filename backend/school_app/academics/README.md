# academics

M02 - Member 1: grades, classrooms and one homeroom teacher per class.

A03 đã triển khai Grade/Classroom UUID, mã unique, FK PROTECT và một GVCN hiện tại. GET/POST `/api/v1/grades`, `/api/v1/classes`; PATCH `/api/v1/classes/:id`. Chỉ SUPERVISOR ghi; GVCN chỉ đọc khối/lớp được giao; STUDENT không được liệt kê. GVCN phải có role HOMEROOM_TEACHER và active khi gán. is_superuser không vượt quyền nghiệp vụ.

Service `scoped_classes(user)` lọc query theo teacher hiện tại; `require_class(user,id)` trả404 cho object ngoài quyền; `assert_class_filter(user,id)` trả403 cho filter ngoài quyền. Khi đổi teacher, quyền cũ mất ngay, teacher mới có scope lịch sử lớp. Class JSON dùng grade_id/teacher_id; student JSON dùng class_id theo contract.

Kiểm chứng: `manage.py test tests.test_academics` có ca scope, gán role sai/inactive, duplicate, reassignment, CSRF và trường giả/kiểu sai. Evidence tại docs/project-management/evidence. Không giao diện hoặc delete API.
