# accounts

M01 - Member 1: login, session, roles, own-class permission and student identity.

User(AbstractUser) có UUID/role từ migration 0001_initial; A05 thêm OneToOne Student bằng migration mới. Login/logout/me dùng Django Auth/session/CSRF. Role mặc định STUDENT; tài khoản chưa link không được quét. is_staff/is_superuser không thay quyền nghiệp vụ.

## Cấp tài khoản cục bộ

Chạy trong backend sau migrate, với DJANGO_SECRET_KEY đã nạp:

```powershell
./.venv/Scripts/python.exe manage.py provision_user teacher_a --role HOMEROOM_TEACHER
./.venv/Scripts/python.exe manage.py provision_user supervisor --role SUPERVISOR
```

Mật khẩu nhập hai lần tại prompt ẩn, kiểm tra bằng Django validators và lưu hash. Không truyền mật khẩu trong command-line, không có HTTP public signup. A05 đã thêm Student link; nhân sự không được gắn Student. Cấp tài khoản học sinh đã có hồ sơ bằng `manage.py provision_user pupil --student-id <Student UUID>`; thiếu liên kết vẫn login/me được nhưng không quét. Hồ sơ liên kết phải active và chưa thuộc tài khoản khác.

## Cookie và CSRF

1. GET `/api/v1/auth/me` chưa đăng nhập trả401 và cấp cookie csrftoken. Giữ cookie jar.
2. POST `/api/v1/auth/login` JSON `{username,password}` kèm cookie và X-CSRFToken bằng giá trị csrftoken. Sai/khóa/không tồn tại cùng INVALID_CREDENTIALS401.
3. Login đổi session/CSRF token; dùng token mới cho request ghi tiếp theo. GET me trả id/username/role/student_id/class_ids hiện tại.
4. POST `/auth/logout` với `{}` và CSRF flush phiên; cookie session cũ không truy cập API bảo vệ.

Field giả role/student_id bị từ chối422; JSON/UTF-8 lỗi400; method sai405; CSRF sai403. Không trả password/hash. Account khóa mất quyền dù đã login.

Login giới hạn 10 lần/peer IP/cửa sổ5 phút,429 kèm Retry-After. Cache trong process chỉ dành demo cục bộ, không bảo đảm giới hạn nhiều process, không tin X-Forwarded-For tùy ý.

Helpers `require_authenticated(request)`, `require_roles(request,*roles)` trả User đã kiểm tra; `require_student(request)` trả Student active từ phiên hoặc403 STUDENT_NOT_LINKED/FORBIDDEN. Mọi service lịch/QR/ảnh/export còn phải kiểm tra scope tài nguyên hiện tại.

Test `manage.py test tests.test_accounts` trong backend cwd; evidence tại docs/project-management/evidence. PM/member review và API gate ghi riêng.
