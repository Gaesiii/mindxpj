# Cấu hình — Member 1 / A01

A01 tạo settings.py/urls.py/wsgi.py/asgi.py và manage.py. AUTH_USER_MODEL=accounts.User trước migration đầu; accounts0002 bổ sung Student link sau students0001. SQLite demo, USE_TZ=True và Asia/Ho_Chi_Minh; API dưới /api/v1 đã nối accounts/academics/students/schedules/attendance/qr/reports. Nạp secret qua môi trường theo backend/README.md; .env.example chỉ là mẫu. Không frontend/admin hoặc public media. Core config/contracts và cross-app migrations đã phối hợp trong plan backend-api; mọi thay đổi mới vẫn cần review chung.
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt

$env:DJANGO_SECRET_KEY = (& ./.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(48))")
$env:DJANGO_DEBUG = 'true'

./.venv/Scripts/python.exe manage.py check
./.venv/Scripts/python.exe manage.py migrate
./.venv/Scripts/python.exe manage.py test
./.venv/Scripts/python.exe manage.py runserver
