# Bàn giao A01/B01 cho mem1 và mem2

Hai bạn dùng **cùng một project nền**. A01 chứa project/User/migration; B01 chứa enum/hợp đồng mà cả hai app phải dùng. Không gửi riêng accounts cho mem1 và schedules cho mem2 rồi tự ghép project Django khác nhau.

## 1. Gửi gì ngay bây giờ?

Bộ ZIP ở `deliverables/projectmindx-a01-b01.zip` chứa thư mục backend, docs, README, AGENTS.md và .gitignore. Có cấu hình, migration, requirements và test; không chứa .venv, DB, mật khẩu/secret, cache hoặc ảnh riêng tư. Bạn tự gửi **cùng file ZIP đó** cho cả hai thành viên bằng kênh mình chọn; chưa có thao tác chia sẻ/upload/invite nào được thực hiện.

Giải nén vào hai máy riêng. Mỗi người đọc AGENTS.md, docs/thiet-ke-he-thong-diem-danh.md v1.2, docs/api-contract.md và backend/README.md rồi chạy các lệnh khởi tạo trong README. Mỗi máy tạo venv/secret/SQLite riêng; không copy venv hoặc database của máy PM. Chỉ paste một file models.py không đủ vì thiếu config, dependency và migration.

Nền hiện chạy được nhưng chưa có API nghiệp vụ/màn hình. Request `/` trả 404 không phải lỗi cài đặt. `seed_demo` và login chưa có; chỉ chạy khi task tương ứng được làm.

## 2. Làm việc lâu dài

Một repository Git chung giúp quản lý các thay đổi và review. Workspace hiện chưa có Git/repository; chưa tạo remote, commit, push hay mời thành viên. Khi nhóm có repository, đưa nguyên bộ nguồn nền vào đó, cả hai clone cùng baseline rồi làm trên branch riêng, ví dụ mem1/a02-auth và mem2/b02-schedules. Merge thông qua review của người còn lại; không sửa migration đã được chia sẻ.

Nếu chưa dùng Git, có thể bắt đầu từ ZIP. Mỗi lần trao đổi thay đổi gửi đủ file code + migration + test + ghi chú đường dẫn; một người tích hợp vào bản chung rồi chạy check/migrate/test trước khi gửi baseline mới cho cả hai. Cách này dễ ghi đè hơn nên chỉ phù hợp giai đoạn đầu. Không để hai người dùng hai bộ enum/config khác nhau.

## 3. Phần nào mỗi người dùng và làm tiếp?

| Người | Dùng từ baseline | Task tiếp theo |
| --- | --- | --- |
| mem1 | config, accounts.User, accounts/0001_initial, core/enums và errors; toàn bộ hợp đồng | A02 login/logout/me/CSRF và cấp tài khoản; A03 lớp; A04 Student; A05 liên kết User–Student |
| mem2 | Cùng project/config/User; core/enums và docs/api-contract.md | B02 đặc tả/test lịch; B03 phối hợp field lớp/học sinh trước B04 migration; chưa tạo Student/Classroom thay mem1 |
| Cả hai | requirements, tests/test_foundation.py và evidence | Review field class_id↔classroom, weekday, UTC, version, snapshot, identity và thứ tự migration |
| PM | evidence và bảng task | Review scope B01, ghi comment/evidence và quyết định Finish?; API_Gate giữ NOT_APPROVED |

mem2 import `from school_app.core.enums import SessionStatus, AttendanceStatus, QrScanStatus` thay vì viết lại các chuỗi. Tham chiếu tài khoản bằng settings.AUTH_USER_MODEL, không import django.contrib.auth.models.User. Liên kết Student chưa có ở A01; không gọi request.user.student_id cho đến khi A05 được merge.

Mọi endpoint sau này phải scope lại user/lớp; đặc biệt photo/export/confirm. Student quét cho chính mình từ session, không nhận danh tính trong body. Không dùng is_superuser để vượt quyền nghiệp vụ. Không tạo frontend trước PM API gate.

## 4. Cập nhật Google Sheet

Workspace có nguồn tasks.json/XLSX/Apps Script nhưng chưa có kết nối/link bảng Google đang dùng. Chưa cập nhật Google Sheet, checkbox Finish? hoặc tự đặt PM review.

Sau khi bạn review và hai thành viên đối chiếu baseline, cập nhật **đúng hai dòng**:

| ID | Evidence/PR | Dev Note |
| --- | --- | --- |
| A01 | Link nội bộ tới bộ baseline/PR và evidence/a01-b01.md | Django check + migrate DB rỗng; User UUID từ migration đầu; 9 test nền đạt; FK Student bổ sung A05 |
| B01 | Link nội bộ tới docs/api-contract.md, core/enums.py và evidence | Field/enum/timezone/payload/migration thống nhất kỹ thuật; PM review phạm vi trước finish |

Nếu review chưa xong thì giữ unfinish và ghi “implemented/validated, pending review” vào Dev Note. Không tick các task sau hoặc đổi API_Gate chỉ vì 9 test nền đạt. Không dán secret hay dữ liệu học sinh thật vào Sheet.
