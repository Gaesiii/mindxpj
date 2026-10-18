> Lịch/workflow v1.2 lịch sử. Phần QR bên dưới đã được thay bằng vision v1.3; xem [thiết kế hiện hành](thiet-ke-he-thong-diem-danh.md), [kế hoạch OpenCV](superpowers/plans/2026-10-18-opencv-demo.md) và tracker JSON/XLSX hiện tại. Lịch/ước lượng cũ cần PM đánh giá lại sau thử ảnh thật. UI local được người dùng cho phép trước gate bằng “làm luôn UI để demo” ngày18/10/2026; gate vẫn NOT_APPROVED, lịch frontend dưới đây là baseline lịch sử.

# Hướng dẫn workflow và thực hiện từng module

> Dự án điểm danh học sinh bằng Python/Django. Hướng dẫn mục tiêu, luồng dữ liệu, yêu cầu và cách thực hiện từng module với agent coding. Phạm vi theo MVP đã thống nhất.

**Nguồn yêu cầu:** Thiết kế MVP v1.2 và bảng task hiện có.  
**Trạng thái dự án (14/10/2026):** backend MVP đã có API/service/migration/test, seed_demo và api-requests.http. Xem backend/README.md, docs/api-acceptance.md và evidence/backend-api.md. PM/member review và API gate chờ xác nhận; frontend chưa có. Bàn giao/ZIP A01/B01 và Word cũ là trạng thái lịch sử trước các API mới.
**Ưu tiên:** Làm phần xử lý và API trước. Chưa làm giao diện; chỉ bắt đầu khi PM duyệt API.

## 1. Đọc tài liệu này và bắt đầu thế nào?

Các bạn đang làm một cuốn sổ điểm danh điện tử. Hồ sơ cho biết học sinh là ai; lịch cho biết phải đi học lúc nào và mặc gì; điểm danh ghi nhận điều xảy ra thực tế; báo cáo tổng hợp lại các ghi nhận đó.

Không cần đọc hết rồi mới bắt đầu. Đọc mục 2–4 một lần, sau đó đọc phần module được giao. Mỗi lần làm một chức năng nhỏ, thử được và giải thích được rồi mới chuyển sang chức năng tiếp theo. Nếu thuật ngữ chưa rõ, yêu cầu agent giải thích bằng chính ví dụ lớp 10A1 trong dự án.

| Người | Phần phụ trách | Task trong bảng |
| --- | --- | --- |
| mem1 | Tài khoản/quyền; khối/lớp; học sinh/ảnh; báo cáo và xuất file | A01–A15 cho backend |
| mem2 | Lịch/buổi; điểm danh; QR/xác minh; đồng phục | B01–B15 cho backend |
| Cả hai | Nối các module, kiểm chứng, trao đổi phần dữ liệu dùng chung | Review chéo và API gate |
| PM | Người quản lý dự án: giải đáp nghiệp vụ, nhận xét và duyệt kết quả | PM Comment và API_Gate |

Ngày 1–15 trong kế hoạch dành cho backend. Các task ngày 16 trở đi là kế hoạch sau khi API được duyệt, không phải việc cần làm ngay. Tên task trong bảng là công việc dự kiến; trạng thái finish chỉ dùng khi đã làm, thử và review xong.

Trước buổi làm đầu tiên, hãy nhờ agent kiểm tra Python và thư mục dự án. Nền dùng Python 3.12/Django 5.2; không mặc định python trên máy là đúng. A01 đã tạo cấu hình chạy được, xem backend/README.md để dựng môi trường trên máy mình. Các phần nghiệp vụ vẫn làm theo task, chưa phải ứng dụng hoàn chỉnh.

## 2. Những từ cần hiểu trước khi làm

### 2.1 Dự án gồm những phần nào?

| Từ | Giải thích bằng lời đơn giản | Ví dụ trong dự án |
| --- | --- | --- |
| Module | Một nhóm chức năng cùng giải quyết một việc | Module học sinh quản lý họ tên, lớp và ảnh |
| Backend | Phần xử lý phía máy chủ: kiểm tra, tính toán, lưu dữ liệu | Kiểm tra giáo viên có được sửa học sinh không |
| Frontend | Phần người dùng nhìn thấy và bấm vào | Màn hình danh sách lớp; chưa làm ở giai đoạn này |
| Server / máy chủ | Chương trình nhận yêu cầu và xử lý; lúc học có thể chạy ngay trên máy mình | Django nhận yêu cầu điểm danh |
| Database / cơ sở dữ liệu | Nơi lưu thông tin theo bảng, giống sổ có nhiều trang được liên kết | Bảng học sinh, lớp, điểm danh |
| Model | Lớp Python mô tả thông tin cần lưu và quan hệ của nó | Student mô tả một học sinh |
| Field / trường dữ liệu | Một loại thông tin của model, thường tương ứng một cột | full_name là họ tên |
| Record / bản ghi | Một đối tượng đã được lưu, thường tương ứng một dòng | Hồ sơ Nguyễn Minh An, mã HS001 |
| ID | Mã định danh để chương trình chọn đúng đối tượng | ID của An phân biệt với một An khác |
| UUID | Một dạng ID dài được tạo để tránh trùng; cứ coi là mã của đối tượng | API trả ID, các bạn dùng lại đúng ID đó |

Mã học sinh như HS001 để nhà trường sử dụng; ID UUID dùng để chương trình nối và tìm bản ghi. Hai thứ không phải một. Hai học sinh được trùng tên nhưng không được trùng mã học sinh.

### 2.2 API là gì và thử ra sao khi chưa có giao diện?

API là cách gửi yêu cầu cho backend và nhận kết quả. Ví dụ: “thêm học sinh vào lớp 10A1”, “cho tôi danh sách điểm danh”. Có thể thử bằng công cụ gửi yêu cầu như Postman hoặc file api-requests.http, chưa cần tự làm màn hình.

Endpoint là địa chỉ của một chức năng API. Method là loại thao tác đi kèm địa chỉ:

| Method | Nghĩa | Ví dụ |
| --- | --- | --- |
| GET | Đọc dữ liệu | GET /api/v1/students |
| POST | Tạo hoặc thực hiện một hành động | POST /api/v1/qr-scans |
| PATCH | Sửa một phần dữ liệu | PATCH /api/v1/attendance/:id |

Request là yêu cầu gửi đi; response là kết quả trả về. Payload hoặc body là phần dữ liệu kèm theo request. JSON là cách viết dữ liệu thành các cặp tên–giá trị. Ví dụ dưới đây là JSON hợp lệ, chưa phải một API đã có sẵn:

Header là phần thông tin đi kèm request ngoài body, chẳng hạn kiểu dữ liệu đang gửi, token CSRF hoặc Idempotency-Key. Nhờ agent chỉ rõ chỗ điền header và body trong công cụ API để không đặt nhầm.

```json
{
  "student_code": "HS001",
  "full_name": "Nguyễn Minh An"
}
```

Tên trường nằm trong dấu ngoặc kép; nội dung chữ cũng nằm trong dấu ngoặc kép. true/false là có/không, số không đặt trong dấu ngoặc kép, null nghĩa là chưa có giá trị. Đừng tự đổi full_name thành name nếu hai bạn đã thống nhất full_name, vì module khác sẽ không biết đọc trường mới.

Trong đường dẫn, :id là chỗ thay bằng ID thật của bản ghi; không gửi nguyên chữ :id. Các ví dụ dùng <id_lớp>, <id_buổi> cũng cần thay bằng ID lấy từ response tạo/xem dữ liệu. Mọi đường dẫn trong các phần module đều có tiền tố /api/v1.

HTTP status là mã kết quả. Các mã lỗi bên dưới theo hợp đồng dự án, không phải mọi lỗi đều được xử lý giống nhau:

| Mã | Hiểu đơn giản | Các bạn cần kiểm tra |
| --- | --- | --- |
| 200 / 201 | Xử lý được / tạo được dữ liệu | Đọc response, thử GET lại hoặc kiểm tra database |
| 401 | Chưa đăng nhập hoặc phiên hết hạn | Đăng nhập đúng tài khoản |
| 403 / 404 | Không có quyền hoặc tài nguyên không được hiển thị | Vai trò, lớp được giao và ID |
| 409 | Bị trùng, phiên bản cũ hoặc trạng thái không cho thao tác | Không tự gửi lặp bằng dữ liệu mới để ghi đè |
| 422 | Dữ liệu trái quy tắc nghiệp vụ | Đọc code/message; ví dụ vi phạm đồng phục thiếu lý do |
| 429 | Gửi quá nhiều yêu cầu trong thời gian ngắn | Dừng lại, thử theo khoảng chờ được trả về |

### 2.3 Dữ liệu liên kết với nhau thế nào?

Foreign key, hay khóa ngoại, là một trường trỏ đến bản ghi ở bảng khác. Student.class_id trỏ đến Classroom; Classroom.grade_id trỏ đến Grade. Nhờ vậy, chọn lớp 10A1 sẽ suy ra khối 10, không cần nhập lại khối ở từng hồ sơ.

Unique nghĩa là không được trùng. student_code unique nghĩa là hai học sinh không dùng cùng mã. Validation là kiểm tra dữ liệu có hợp lệ: thiếu họ tên, ảnh quá lớn hoặc ID lớp không có thật phải bị từ chối trước khi lưu.

Migration là bản ghi thay đổi cấu trúc database, như thêm bảng hoặc thêm cột. Django tạo migration từ model rồi áp dụng vào database. Migration không phải hồ sơ học sinh. Hai bạn cần trao đổi khi model của mình trỏ đến model của bạn kia; không tự xóa migration để hết lỗi.

## 3. Các file trong module có nhiệm vụ gì?

Mỗi module nằm trong backend/school_app/. Các file khung đã được tạo để chia trách nhiệm. Có file không đồng nghĩa chức năng đã hoạt động.

| File | Nhiệm vụ | Ví dụ với module học sinh |
| --- | --- | --- |
| models.py | Mô tả dữ liệu lưu trong database | Mã, họ tên, lớp, đường dẫn ảnh |
| forms.py | Kiểm tra dữ liệu gửi lên; dù chưa có màn hình vẫn dùng được | Họ tên bắt buộc, class_id hợp lệ |
| views.py | Nhận request và tạo response | Nhận POST thêm học sinh, trả JSON |
| services.py | Thực hiện quy tắc nghiệp vụ và lưu dữ liệu | Kiểm tra quyền lớp rồi tạo học sinh |
| urls.py | Nối địa chỉ API tới view | /students chuyển tới view tương ứng |
| migrations/ | Lưu thay đổi cấu trúc bảng | Migration tạo bảng Student |
| tests/ | Chứa các bài kiểm chứng chạy bằng chương trình | Giáo viên lớp A không sửa học sinh lớp B |

Trong Django, từ view là hàm/lớp xử lý request, không có nghĩa màn hình giao diện. Form là công cụ kiểm tra dữ liệu, không buộc các bạn phải làm một form HTML ngay.

Luồng cơ bản của một API:

```text
Request -> urls.py -> views.py
                         |
            forms.py kiểm tra đầu vào
                         |
            services.py kiểm tra quyền/quy tắc
                         |
            models.py + Django ORM đọc/ghi database
                         |
                 response JSON
```

ORM là công cụ giúp đọc/ghi database bằng mã Python thay vì tự viết từng câu SQL. SQL là ngôn ngữ truy vấn database; ở MVP, các bạn chủ yếu dùng Django ORM, chưa cần học sâu SQL mới bắt đầu được.

Service phải kiểm tra quyền trước khi đọc/ghi. Không chỉ viết “nếu là giáo viên thì cho phép”: còn phải kiểm tra giáo viên đó có được giao đúng lớp đang thao tác hay không.

Các thư mục đặc biệt: core chứa phần dùng chung như lỗi, ảnh riêng tư, chống ghi trùng; config chứa cấu hình của Django; management_app/management/commands sẽ có seed_demo để tạo dữ liệu giả. Seed nghĩa là tạo bộ dữ liệu ban đầu để thử chương trình.

## 4. Cách làm việc với agent coding từng bước

Agent coding là trợ lý hỗ trợ viết/đọc/sửa code. Các bạn cần cung cấp đúng việc cần làm, đọc giải thích và tự thử kết quả; câu “đã xong” của agent chưa thay thế bằng chứng chạy chương trình.

### 4.1 Trước khi yêu cầu agent viết code

1. Chọn một ID task trong bảng, ví dụ A04. Đọc đầu ra và điều kiện nghiệm thu.
2. Kiểm tra dependencies, nghĩa là các việc phải hoàn thành trước. A04 cần lớp từ A03; chưa có lớp thì chưa thể thêm học sinh đúng cách.
3. Đọc phần module tương ứng trong tài liệu này. Tự nói được: ai thao tác, gửi gì, lưu gì, nhận gì.
4. Yêu cầu agent đọc AGENTS.md và thiết kế MVP v1.2 để tránh thêm chức năng ngoài phạm vi.
5. Chia task thành một lát nhỏ: tạo model và test trước, rồi chức năng thêm, rồi chức năng xem; không yêu cầu xây toàn bộ ứng dụng trong một lần.

### 4.2 Mẫu yêu cầu mở đầu

```text
Hãy đọc AGENTS.md và docs/thiet-ke-he-thong-diem-danh.md v1.2.
Tôi đang làm task A04, module học sinh; chưa làm frontend.
Trước khi sửa, giải thích bằng tiếng Việt dễ hiểu:
1. Chức năng này làm gì và cần module nào trước đó?
2. Dữ liệu đầu vào, bảng cần đọc/ghi và kết quả trả ra là gì?
3. Những file nào sẽ sửa và vì sao?
Sau đó hỗ trợ từng bước nhỏ và giải thích các từ mới.
Chỉ làm phần của task này; không thêm tính năng ngoài MVP.
```

Sau khi hiểu lời giải thích, yêu cầu agent thực hiện một phần cụ thể, ví dụ “làm API thêm học sinh và các ca kiểm chứng của API đó”. Cách này giúp các bạn theo dõi được từng thay đổi.

### 4.3 Khi agent báo hoàn tất

1. Hỏi agent đã sửa file nào, từng file có nhiệm vụ gì.
2. Đọc ít nhất view, service và model liên quan; hỏi lại bất kỳ đoạn nào chưa hiểu.
3. Yêu cầu một request mẫu, response đúng và một request sai để tự thử.
4. Yêu cầu agent chạy kiểm chứng và đưa kết quả thật; nếu chưa chạy được phải nêu lý do.
5. Tự giải thích lại luồng bằng một học sinh giả, không cần đọc từng dòng code.
6. Gắn bằng chứng vào Evidence/PR, nhờ người còn lại review, rồi mới tick finish.

Review nghĩa là người khác đọc và kiểm tra thay đổi. Commit là một mốc lưu thay đổi trong Git, công cụ theo dõi lịch sử code. PR, hay pull request, là nơi đề nghị ghép thay đổi và để người khác review nếu nhóm dùng nền tảng hỗ trợ. Evidence là bằng chứng: kết quả test, request/response hoặc link commit. Không bắt buộc có PR nếu nhóm chưa dùng nền tảng đó; vẫn cần review và bằng chứng.

### 4.4 Khi bị lỗi

Gửi cho agent: task đang làm, lệnh/request đã gửi, dữ liệu giả dùng để thử, thông báo lỗi đầy đủ, kết quả mong muốn và kết quả thực tế. Traceback là chuỗi thông báo Python chỉ ra lỗi xuất hiện ở file/dòng nào; giữ cả phần đầu lẫn cuối thay vì chỉ chụp chữ “Error”. Che mật khẩu hoặc token thật trước khi chia sẻ.

```text
Tôi đang làm task [ID]. Tôi đã chạy [lệnh hoặc API].
Mong muốn: [điều đáng lẽ xảy ra].
Thực tế: [điều xảy ra].
Thông báo lỗi: [dán đầy đủ, bỏ thông tin bí mật].
Hãy giải thích nguyên nhân bằng ví dụ đơn giản và sửa đúng phần gây lỗi.
Không tắt phân quyền/CSRF, không xóa database hoặc migration để né lỗi.
```

## 5. M01 — Tài khoản và quyền truy cập

**Người làm:** mem1. **Task:** A01, A02, A07, A13. **Thư mục:** backend/school_app/accounts/.

### 5.1 Mục tiêu của module

Hệ thống phải biết người gửi yêu cầu là ai và người đó được làm gì. GVCN quản lý lớp được giao, giám thị quản lý toàn trường, học sinh chỉ gửi quét cho chính mình. Không biết danh tính thì chương trình không thể kiểm tra quyền.

Authentication, hay xác thực, là kiểm tra “bạn là ai”, ví dụ kiểm tra đăng nhập. Authorization, hay phân quyền, là kiểm tra “bạn được làm gì”, ví dụ cô Lan có được sửa học sinh lớp 10B1 không. Đăng nhập đúng chưa đồng nghĩa được sửa mọi lớp.

### 5.2 Thông tin cần quản lý

| Trường/khái niệm | Nghĩa | Quy tắc |
| --- | --- | --- |
| username | Tên tài khoản | Không trùng tài khoản khác |
| password | Mật khẩu khi đăng nhập | Django xử lý; không lưu mật khẩu rõ trong bảng riêng |
| role | Vai trò | HOMEROOM_TEACHER, SUPERVISOR hoặc STUDENT |
| is_active | Tài khoản còn được dùng không | Đã khóa thì không tiếp tục thao tác nghiệp vụ |
| student link | Hồ sơ học sinh của tài khoản STUDENT | Chỉ liên kết đúng một học sinh |

Hash mật khẩu là giá trị được tạo theo cách chuyên dụng để kiểm tra mật khẩu mà không lưu nguyên mật khẩu. Dùng cơ chế của Django; không tự mã hóa sơ sài bằng cách đổi ký tự.

Session đăng nhập là thông tin giúp server nhận ra người đã đăng nhập ở các request tiếp theo. Cookie là thông tin nhỏ trình duyệt/công cụ API lưu và gửi lại cho server. Đừng nhầm session đăng nhập với Session buổi học của module lịch: cùng từ tiếng Anh nhưng là hai việc khác nhau.

### 5.3 Workflow đăng nhập và đọc dữ liệu

1. Người dùng gửi username/password đến POST /api/v1/auth/login.
2. Server kiểm tra tài khoản tồn tại, đang active và mật khẩu đúng bằng Django Auth.
3. Nếu sai, trả thông báo chung; không đưa mật khẩu hoặc chi tiết tài khoản khác vào response.
4. Nếu đúng, tạo phiên đăng nhập, công cụ API giữ cookie cần thiết.
5. Người dùng gọi GET /api/v1/auth/me để kiểm tra mình đang dùng tài khoản/role nào.
6. Khi người dùng gọi API học sinh, server đọc lớp của học sinh và đối chiếu Classroom.teacher_id với người đang đăng nhập; giám thị có phạm vi toàn trường.
7. POST /api/v1/auth/logout kết thúc phiên; request sau đó không còn quyền như người đã đăng nhập.

CSRF là cơ chế ngăn trang khác lợi dụng phiên đăng nhập để gửi thao tác thay người dùng. Request thay đổi dữ liệu cần gửi token CSRF theo cách Django yêu cầu. Token là một chuỗi kiểm chứng; token CSRF và token QR phục vụ hai việc khác nhau. Nhờ agent hướng dẫn lấy cookie/token và gửi header khi thử API; không tắt CSRF chỉ để request chạy qua.

### 5.4 Thứ tự thực hiện và cách tự kiểm tra

1. A01 tạo môi trường, project và custom User — model tài khoản tùy chỉnh để có role/liên kết học sinh ngay từ đầu. Làm trước migration đầu tiên.
2. A02 dùng Django Auth để làm login/logout/me; tài khoản mẫu tạo qua Admin/seed.
3. Sau A03 có lớp, bổ sung kiểm tra lớp được giao và thử quyền thật.
4. Đăng nhập bằng giáo viên A, thử đọc lớp B: phải bị chặn dù tài khoản đăng nhập đúng.
5. Đăng nhập học sinh, thử gọi danh sách lớp hoặc export: phải bị chặn.
6. Đăng xuất, gọi API đang được bảo vệ: phải nhận lỗi chưa đăng nhập.

Mẫu yêu cầu agent: “Làm login/logout/me cho task A02 bằng Django Auth, giải thích session/cookie/CSRF bằng ví dụ. Giữ đúng ba role của MVP, chưa làm màn hình. Cho tôi request mẫu và test đăng nhập sai, logout và đọc dữ liệu ngoài quyền.”

**Bàn giao cho mem2:** Cách lấy user/role/student từ session và hàm kiểm tra quyền lớp. mem2 không tự tạo cách đăng nhập khác trong module QR.

## 6. M02 — Khối, lớp và giáo viên chủ nhiệm

**Người làm:** mem1. **Task:** A03. **Thư mục:** backend/school_app/academics/.

### 6.1 Mục tiêu của module

Tạo danh sách khối, lớp và GVCN để học sinh/lịch/điểm danh có nơi thuộc về. Grade nghĩa là khối lớp trong dự án này, không phải điểm số. Classroom nghĩa là lớp học, ví dụ 10A1.

| Model | Trường cần hiểu | Ví dụ |
| --- | --- | --- |
| Grade | code, name | Code 10, tên Khối 10 |
| Classroom | code, name, grade_id, teacher_id | 10A1 thuộc Khối 10, cô Lan chủ nhiệm |

teacher_id là một giá trị, nên mỗi lớp chỉ giữ một GVCN hiện tại. Một giáo viên được giao nhiều lớp nếu có nhu cầu; không tự đặt quy tắc “một giáo viên chỉ một lớp”.

### 6.2 Workflow tạo khối và lớp

1. Giám thị đăng nhập, gửi POST /api/v1/grades với code/name.
2. Server kiểm tra quyền giám thị, mã khối chưa trùng rồi tạo Grade; response trả ID khối.
3. Giám thị chọn một tài khoản có role GVCN; lấy ID tài khoản đó.
4. Gửi POST /api/v1/classes với code/name/grade_id/teacher_id.
5. Server kiểm tra khối và giáo viên tồn tại, giáo viên đúng role và mã lớp không trùng.
6. Lưu Classroom, trả ID lớp. ID này được dùng khi thêm học sinh và lịch học.
7. GET /api/v1/classes trả các lớp thuộc phạm vi người gọi: giám thị toàn trường, GVCN lớp được giao.

### 6.3 Workflow đổi GVCN

Giám thị dùng PATCH /api/v1/classes/:id thay teacher_id → server kiểm tra giáo viên mới → cập nhật lớp. Từ đó giáo viên cũ không còn quản lý lớp, giáo viên mới được quản lý lớp và xem lịch sử của lớp. Không tạo hệ thống phân công theo khoảng thời gian phức tạp trong MVP.

### 6.4 Những việc phải kiểm chứng

- Tạo khối và lớp hợp lệ, đọc lại đúng quan hệ.
- Mã lớp trùng bị từ chối; không lấy tên lớp làm ID nội bộ.
- Gán tài khoản STUDENT làm GVCN bị từ chối.
- GVCN không được tự tạo khối hoặc đổi GVCN của lớp.
- Lớp đã có học sinh/buổi không bị xóa cứng, vì các bản ghi khác còn tham chiếu.
- Khi đổi GVCN, thử lại cả tài khoản cũ và mới để kiểm tra quyền thay đổi.

Mẫu yêu cầu agent: “Làm task A03, model/API Grade và Classroom. Giải thích foreign key grade_id/teacher_id. Chỉ giám thị được tạo và gán GVCN; teacher_id phải thuộc tài khoản GVCN. Viết ca hợp lệ, trùng mã, gán sai role và đọc lớp ngoài quyền. Chưa làm frontend.”

**Bàn giao cho mem2:** Tên model, trường grade_id/teacher_id, API lấy ID lớp và bộ dữ liệu hai lớp giả. Không tự đổi tên trường đã bàn giao mà chưa thông báo.

## 7. M03 — Hồ sơ học sinh và ảnh

**Người làm:** mem1. **Task:** A04–A07. **Thư mục:** backend/school_app/students/; phần lưu ảnh dùng core/storage.py.

### 7.1 Mục tiêu của module

Quản lý hồ sơ để nhân sự biết ai đang được điểm danh. Ảnh hồ sơ giúp đối chiếu danh tính, không chứng minh học sinh đang mặc đúng đồng phục hôm nay. Không có ảnh vẫn được điểm danh.

| Trường | Nghĩa | Quy tắc |
| --- | --- | --- |
| student_code | Mã học sinh, ví dụ HS001 | Duy nhất trong trường |
| full_name | Họ tên | Bắt buộc; giữ dấu tiếng Việt |
| class_id | Lớp hiện tại | Trỏ tới lớp có thật và đúng quyền |
| photo_path | Vị trí lưu ảnh nếu có | Server quản lý, không nhận đường dẫn tùy ý từ người dùng |
| active | Học sinh còn thuộc diện đi học không | false thì không vào danh sách buổi mới |

Không thêm trường “có mặt hôm nay” hoặc “đồng phục sai” vào Student. Một học sinh có thể sáng đến, chiều vắng; kết quả đó phải thuộc từng buổi, không thuộc hồ sơ chung.

### 7.2 Workflow thêm học sinh

1. GVCN chọn lớp mình được giao, lấy class_id.
2. Gửi POST /api/v1/students với mã, họ tên và class_id.
3. Server kiểm tra tài khoản, quyền lớp, họ tên không rỗng và mã chưa trùng.
4. Tạo Student; khối lấy từ lớp chứ không nhập một giá trị khối độc lập.
5. Response trả hồ sơ/ID; gọi GET để kiểm tra thực sự đã lưu.
6. Khi cần tài khoản quét, giám thị/Admin hoặc seed tạo User STUDENT liên kết hồ sơ; không đưa mật khẩu vào API danh sách học sinh.

Payload minh họa, cần thay <id_lớp> bằng ID thật:

```json
{
  "student_code": "HS001",
  "full_name": "Nguyễn Minh An",
  "class_id": "<id_lớp>"
}
```

### 7.3 Workflow ảnh

1. Gửi file đến POST /api/v1/students/:id/photo. Upload file dùng dạng multipart/form-data, tức là gói request có thể chứa tệp, không phải dán đường dẫn máy mình vào JSON.
2. Server kiểm tra người gọi được sửa học sinh này.
3. Kiểm tra nội dung ảnh thực, loại JPEG/PNG/WebP, tối đa 5 MB và giới hạn kích thước ảnh.
4. Pillow, thư viện xử lý ảnh bằng Python, đọc và chuẩn hóa ảnh; loại bỏ thông tin EXIF không cần thiết. EXIF là thông tin phụ có thể nằm trong ảnh, ví dụ thiết bị/thời điểm chụp.
5. Lưu ảnh mới vào vùng private, nghĩa là không ai tự mở đường dẫn công khai để xem được.
6. Chỉ khi ảnh mới lưu thành công mới đổi photo_path. Nếu upload lỗi, ảnh cũ vẫn còn.
7. GET /api/v1/students/:id/photo kiểm tra quyền rồi trả ảnh; không chỉ bảo vệ API hồ sơ mà bỏ quên API ảnh.

### 7.4 Sửa hồ sơ và giữ lịch sử

GVCN được sửa hồ sơ trong lớp được giao. Giám thị có thể đổi class_id. Buổi đã mở phải giữ thông tin lớp cũ trong snapshot; buổi mới lấy lớp hiện tại. Snapshot sẽ được giải thích ở M04. Hồ sơ đã có điểm danh không xóa hẳn, dùng active=false để ngừng đưa vào buổi mới.

### 7.5 Thứ tự làm và tự kiểm tra

1. A04: thêm/xem hồ sơ trước, chưa cần ảnh.
2. A05: sửa/tìm theo mã hoặc tên và liên kết tài khoản học sinh.
3. A06: upload/thay/tải ảnh có quyền.
4. A07: thử sai quyền trên cả hồ sơ và ảnh.
5. Thêm hai học sinh cùng tên với mã khác: được phép. Thêm mã HS001 lần hai: bị chặn.
6. Gửi ảnh hỏng/quá lớn và thử thiếu ảnh: lỗi ảnh không làm mất hồ sơ hoặc chặn điểm danh.

Mẫu yêu cầu agent: “Hỗ trợ A04 trước: model Student và API thêm/xem, liên kết Classroom hiện có, giữ tên có dấu và mã duy nhất. Giải thích mỗi field và luồng kiểm tra quyền. Chưa làm ảnh/frontend ở bước này. Sau khi thử xong mới sang A05 và A06.”

**Bàn giao cho mem2:** Student.id, student_code, full_name, class_id, active và quan hệ tài khoản học sinh. Đưa dữ liệu giả có ID để mem2 thử roster/QR.

## 8. M04 — Lịch đi học và buổi học cụ thể

**Người làm:** mem2. **Task:** B02–B06. **Thư mục:** backend/school_app/schedules/.

### 8.1 Mục tiêu của module

Phải tách “lịch lặp” và “buổi xảy ra vào một ngày”. Lịch nói: lớp 10A1 học sáng thứ Hai lúc 07:00, mặc sơ mi. Buổi nói: sáng thứ Hai ngày 12/10/2026 của lớp 10A1 đang mở để điểm danh.

ScheduleRule là một quy tắc lịch tuần. Session trong module này là một buổi học, không phải session đăng nhập. SessionRoster là danh sách học sinh thuộc buổi đó; roster đơn giản nghĩa là danh sách người cần theo dõi.

| Dữ liệu | Nghĩa | Ví dụ |
| --- | --- | --- |
| weekday | Thứ trong tuần | Thứ Hai; cách mã hóa số/chữ cần hai bạn chốt ở B01 |
| slot | Buổi sáng hoặc chiều | MORNING / AFTERNOON |
| start_time | Giờ bắt đầu theo giờ Việt Nam | 07:00 |
| close_time | Giờ đóng theo lịch | Phải sau giờ bắt đầu |
| grace_minutes | Số phút được cho phép trễ so với giờ bắt đầu | 5 phút |
| required_uniform | Loại đồng phục phải mặc | SHIRT sơ mi / SPORTS thể dục |
| school_date | Ngày cụ thể của buổi | 2026-10-12 |

Giờ bắt đầu/cửa sổ cho phép trong ví dụ là dữ liệu giả. Khi PM chốt giờ thật, dùng cấu hình lịch thay vì viết cố định “07:00” trong mọi hàm.

### 8.2 Workflow lưu lịch

1. GVCN chọn lớp mình hoặc giám thị chọn một lớp.
2. Gửi POST /api/v1/classes/:id/schedule-rules với thứ/buổi/giờ/ngưỡng muộn/đồng phục.
3. Server kiểm tra quyền lớp, các trường bắt buộc và giờ hợp lệ.
4. Kiểm tra không có hai rule trùng lớp–thứ–buổi.
5. Lưu ScheduleRule; GET lại để kiểm tra. PATCH sửa rule khi cần.

### 8.3 Workflow tạo và mở buổi

1. Nhân sự gửi POST /api/v1/sessions, chọn class_id, school_date và slot.
2. Server tìm rule đúng lớp/thứ/buổi, tạo Session PLANNED, nghĩa là dự kiến, chưa ghi nhận điểm danh.
3. Nhân sự gọi POST /api/v1/sessions/:id/open.
4. Server đọc học sinh active trong lớp ở thời điểm mở và đọc chính sách của buổi.
5. Lưu snapshot: bản sao tên/mã/lớp/khối, giờ/ngưỡng muộn và đồng phục dùng cho chính buổi đó. Snapshot giống photocopy trang danh sách lúc mở buổi.
6. Tạo một SessionRoster và một Attendance UNMARKED cho mỗi học sinh. Attendance là bản ghi kết quả điểm danh, sẽ được dùng ở M05.
7. Chuyển buổi OPEN, nghĩa là đang cho phép ghi nhận; trả danh sách và trạng thái.

Mở buổi lần hai phải trả trạng thái đã mở hoặc xử lý an toàn, không tạo thêm một danh sách/điểm danh thứ hai. Mỗi lớp–ngày–buổi chỉ có một Session.

Transaction là nhóm thao tác phải thành công cùng nhau hoặc không ghi gì. Mở buổi gồm tạo roster, tạo attendance và đổi trạng thái. Nếu tạo được 5 học sinh rồi lỗi, không được để buổi có một nửa danh sách. Django dùng transaction để bảo vệ việc này; nhờ agent giải thích bằng tình huống đó.

### 8.4 Workflow chốt buổi

1. Nhân sự xem số học sinh chưa ghi nhận, QR còn chờ và đồng phục chưa kiểm tra.
2. Xác nhận trước khi chốt, vì học sinh UNMARKED sẽ thành ABSENT.
3. POST /api/v1/sessions/:id/close chuyển các UNMARKED thành ABSENT, scan PENDING thành EXPIRED.
4. Giữ các PRESENT và kết quả đồng phục đã ghi. NOT_CHECKED không được tự biến thành COMPLIANT.
5. Session trở thành CLOSED; không nhận quét hoặc ghi mới từ GVCN. Sửa sau chốt thuộc giám thị, có lý do và lịch sử.

### 8.5 Tự kiểm tra và bàn giao

- Tạo buổi đúng lớp/ngày/slot; thử tạo hai lần phải không trùng.
- Mở khi thiếu lịch phải báo rõ để sửa cấu hình, không tự đoán loại đồng phục.
- Học sinh active=false không vào danh sách mới.
- Sửa tên học sinh/lịch sau khi mở không làm đổi snapshot buổi cũ.
- Mở lại request sau lỗi không tạo roster thừa.
- Khi chưa làm QR, kiểm chứng chốt bằng các attendance mẫu; khi M05 xong thử lại với scan thực.

Mẫu yêu cầu agent: “Làm B05/B06 theo dữ liệu lớp/học sinh đã thống nhất. Giải thích khác nhau giữa ScheduleRule, Session và SessionRoster. Khi mở buổi, snapshot và tạo attendance UNMARKED trong một transaction. Viết ca mở lặp, thiếu lịch, active=false và lỗi giữa chừng. Chưa làm worker hoặc frontend.”

**Bàn giao:** ID buổi, ID roster, ID attendance, trạng thái OPEN và chuẩn đồng phục/cutoff. mem1 dùng dữ liệu này viết báo cáo; các ID khác nhau không được dùng thay cho nhau.

## 9. M05 — Điểm danh, QR và xác minh học sinh

**Người làm:** mem2. **Task:** B07–B11, B13, B14. **Thư mục:** attendance/, qr/ và core/idempotency.py.

### 9.1 Mục tiêu của module

Ghi nhận học sinh đến trường lúc nào. Có hai cách vào cùng một kết quả: nhân sự nhập thủ công, hoặc học sinh quét QR rồi nhân sự xác minh. Quét QR chưa chứng minh có mặt; chỉ sau khi đối chiếu tại chỗ mới chuyển PRESENT.

Attendance là kết quả chính thức của một học sinh trong một buổi. QrScan là sự kiện gửi lần quét. Không lấy “số dòng QrScan” để đếm số học sinh có mặt.

| Trạng thái | Giải thích |
| --- | --- |
| UNMARKED | Chưa có kết luận điểm danh |
| PRESENT | Đã xác minh có mặt |
| ABSENT | Đã xác nhận vắng hoặc kết luận khi chốt |
| PENDING | Lần quét đang chờ nhân sự xác minh |
| CONFIRMED | Lần quét được nhân sự xác minh |
| REJECTED | Lần quét bị từ chối có lý do |
| EXPIRED | Hết hạn xác minh hoặc buổi đã chốt |
| SUPERSEDED | Lần quét được thay bằng ghi nhận thủ công, không dùng để tạo kết quả thứ hai |

### 9.2 Bước đầu: điểm danh thủ công

1. Nhân sự lấy roster từ GET /api/v1/sessions/:id/roster.
2. Chọn đúng Attendance của học sinh; không chọn dựa vào tên nếu hai người trùng tên.
3. Gửi PATCH /api/v1/attendance/:id: PRESENT với arrived_at hoặc ABSENT với lý do nếu có.
4. Server kiểm tra quyền lớp, buổi OPEN và phiên bản bản ghi.
5. PRESENT bắt buộc giờ đến; ghi source MANUAL, nghĩa là nhập bởi nhân sự. UNMARKED/ABSENT không có giờ đến và đồng phục NOT_APPLICABLE.
6. Tính ON_TIME/LATE, ghi người/thời gian thao tác và trả bản ghi đã lưu.

arrived_at là giờ đến thực tế; recorded_at là giờ hệ thống lưu; verified_at là giờ nhân sự xác minh. Đây là các thời điểm khác nhau. UTC là mốc giờ chuẩn dùng khi lưu; Việt Nam đi trước UTC 7 giờ. Ví dụ 07:04 tại Việt Nam tương ứng 00:04Z. Chữ Z ở cuối thời gian nghĩa là UTC, không phải học sinh đi học lúc nửa đêm.

### 9.3 Workflow phát và quét QR

1. Nhân sự chọn Session OPEN, gọi POST /api/v1/sessions/:id/qr-challenges.
2. Server tạo token QR: chuỗi ngẫu nhiên dùng để chứng minh mã thuộc buổi đang mở. Không nhét mật khẩu, tên hay mã học sinh vào QR.
3. Lưu token_hash và thời hạn. Hash ở đây giúp kiểm tra token mà không lưu nguyên token dùng để quét. Nó khác thông tin token trả cho màn hình phát mã.
4. Mã được đổi sau 30 giây, token hết hạn sau 60 giây. Ở giai đoạn API, thử gọi các API này, chưa làm camera hoặc màn hình tự đổi mã.
5. Học sinh đăng nhập rồi POST /api/v1/qr-scans với token.
6. Server lấy student_id từ session, kiểm tra đúng buổi/lớp/roster, token còn hạn và buổi còn OPEN.
7. Tạo QrScan PENDING với scanned_at là giờ server nhận; trả “chờ xác nhận”. Attendance vẫn UNMARKED.

Một QR buổi dùng được cho nhiều học sinh trong roster. Không đặt quy tắc “token chỉ dùng một lần” khiến bạn thứ hai không quét được. Một học sinh chỉ có một PENDING cho buổi đó.

### 9.4 Workflow nhân sự xác minh

1. Nhân sự gọi GET /api/v1/sessions/:id/qr-scans để lấy hàng đợi PENDING.
2. Đọc mã/tên/lớp/ảnh và đối chiếu học sinh đang đứng tại điểm danh.
3. Nếu đúng, POST /api/v1/qr-scans/:id/confirm, có thể kèm đồng phục của M06.
4. Server kiểm tra quyền, buổi OPEN, pending chưa hết 15 phút và version đúng.
5. Trong cùng transaction: Attendance thành PRESENT, source QR, arrived_at lấy từ scanned_at, lưu người/giờ xác minh; QrScan thành CONFIRMED.
6. Nếu không đúng danh tính, gọi reject có lý do; scan REJECTED, không chuyển Attendance thành PRESENT.

Ví dụ học sinh quét 07:04, giám thị xác minh 07:08, cutoff 07:05: học sinh vẫn ON_TIME vì giờ đi học là 07:04. Không lấy giờ giám thị bấm xác nhận làm giờ đến.

QR động không ngăn tuyệt đối việc gửi ảnh mã hoặc dùng chung tài khoản. Bước nhân sự đối chiếu tại chỗ là phần cần thiết của workflow. Chưa làm AI nhận diện để thay bước đó.

### 9.5 Những lần gửi lại hoặc sửa cùng lúc

Retry là thử gửi lại khi chưa nhận được kết quả, ví dụ mạng bị ngắt. Idempotency nghĩa là một yêu cầu gửi lại không gây tác dụng thêm lần nữa. Idempotency-Key là mã của một thao tác, thường đặt ở header request.

Ví dụ thao tác “xác nhận An” đã lưu nhưng response bị mất: gửi lại cùng key và cùng dữ liệu phải nhận kết quả cũ, không tạo điểm danh mới. Cùng key nhưng đổi dữ liệu phải trả 409. Một thao tác khác dùng key mới.

Version là số lần bản ghi đã thay đổi, ví dụ 0 rồi 1 rồi 2. expected_version là phiên bản người gửi đang nhìn thấy. Hai người cùng xem version 1: người thứ nhất sửa thành version 2; người thứ hai không được ghi đè bằng dữ liệu cũ mà phải đọc lại. Với SQLite demo, cần kiểm chứng version/unique và báo giới hạn ghi đồng thời; không tuyên bố đã chịu tải toàn trường.

Các tình huống phải xử lý:

- Quét lại khi PENDING: trả scan đang chờ, giữ giờ đầu tiên.
- PENDING quá 15 phút: API đánh giá hết hạn thành EXPIRED; có thể quét mới nếu còn buổi OPEN. Token QR hết hạn 60 giây và thời hạn xác minh 15 phút là hai thời hạn khác nhau.
- Đã CONFIRMED: không tạo thêm Attendance.
- Nhân sự điểm danh thủ công khi đang PENDING: scan SUPERSEDED, giữ kết quả MANUAL.
- Buổi CLOSED: không nhận scan hoặc confirm mới.
- Mất mạng trước khi server nhận scan: không được báo đã quét thành công; gặp nhân sự để dùng phương án thủ công. Chưa có offline tự đồng bộ.

### 9.6 Thứ tự làm và tự kiểm tra

1. B07/B08: manual, thời gian, unique/version/retry trước.
2. B09: tạo token và hình QR, thử hạn thời gian.
3. B10: gửi scan và đọc trạng thái của học sinh; chưa confirm.
4. B11: hàng đợi/confirm/reject, dùng cùng service Attendance với manual.
5. Hai tài khoản học sinh quét cùng QR: cả hai PENDING hợp lệ. Một người quét hai lần: một PENDING.
6. Thử token hết hạn, sai lớp và giả student_id khác: đều không tạo có mặt.
7. Quét đúng giờ/confirm sau cutoff, chốt buổi rồi quét, retry sau mất response: kiểm tra đúng trạng thái và không trùng.

Mẫu yêu cầu agent: “Tôi làm B10. Hãy chỉ triển khai API gửi QR scan và đọc trạng thái của chính học sinh, lấy danh tính từ session. Giải thích QrScan/Attendance và hai thời hạn 60 giây/15 phút. Không tự đặt PRESENT khi quét, không làm camera/frontend. Cho tôi test quét hợp lệ, quét lặp, sai lớp và tự khai student_id khác.”

**Bàn giao cho mem1:** Một bộ dữ liệu có manual/QR đã confirm và QR còn pending; arrived_at, source, trạng thái và cách nhận diện bản ghi chính thức. Báo cáo chỉ đếm Attendance PRESENT.

## 10. M06 — Kiểm tra đồng phục

**Người làm:** mem2. **Task:** B12, B13. **Thư mục:** backend/school_app/attendance/; file uniform_rules.py xử lý quy tắc đồng phục.

### 10.1 Mục tiêu của module

Ghi kết luận của GVCN/giám thị về đồng phục thực tế so với đồng phục yêu cầu của buổi. Chương trình hỗ trợ kiểm tra dữ liệu và lưu kết quả; nhân sự quan sát học sinh. Không dùng ảnh hồ sơ để tự kết luận đồng phục hôm nay.

| Trường | Nghĩa | Ví dụ |
| --- | --- | --- |
| required_uniform_snapshot | Chuẩn đã lưu cho buổi | SHIRT, phải mặc sơ mi |
| observed_uniform | Loại nhân sự quan sát thực tế | SPORTS, đang mặc đồ thể dục |
| uniform_status | Kết luận | NON_COMPLIANT, không đúng quy định |
| uniform_reason | Vì sao không đúng | Buổi này yêu cầu sơ mi |
| checked_by / checked_at | Ai kiểm tra và lúc nào | Giám thị, giờ server ghi nhận |

### 10.2 Workflow kiểm tra riêng

1. Đọc Attendance của học sinh và chuẩn đồng phục trong snapshot buổi.
2. Kiểm tra Attendance là PRESENT. UNMARKED/ABSENT chưa phải người có mặt để đánh giá đồng phục.
3. Nhân sự quan sát, chọn loại thực tế và kết luận.
4. Gửi PATCH /api/v1/attendance/:id/uniform với expected_version và thông tin đồng phục.
5. Server kiểm tra quyền, trạng thái buổi, phiên bản và quy tắc: không đạt phải có lý do; COMPLIANT phải phù hợp chuẩn; OTHER phải có mô tả.
6. Ghi vào Attendance, tăng version và lưu ChangeLog, nghĩa là lịch sử trước/sau của thay đổi. Không lưu mật khẩu/token vào lịch sử đó.
7. Response trả kết quả đã ghi; người dùng kiểm tra lại bằng GET roster/report.

NOT_CHECKED nghĩa là có mặt nhưng chưa kiểm tra; NOT_APPLICABLE nghĩa là không áp dụng, vì học sinh vắng hoặc chưa được xác minh có mặt. Hai trạng thái không được gộp thành “đạt”. observed_uniform UNKNOWN nghĩa là chưa biết loại thực tế, không đủ dữ liệu để tự kết luận COMPLIANT.

### 10.3 Workflow xác minh QR và kiểm tra cùng lần

Nhân sự đang confirm QR có thể gửi kèm uniform. Server xử lý confirm và đồng phục trong cùng transaction. Nếu lý do vi phạm thiếu, cả thao tác phải bị từ chối: không ghi nửa phần điểm danh rồi báo nửa phần đồng phục lỗi. Nếu nhân sự confirm mà chưa kiểm tra đồng phục, ghi PRESENT + NOT_CHECKED, có thể kiểm tra sau khi buổi còn OPEN.

```json
{
  "expected_attendance_version": 0,
  "expected_scan_version": 0,
  "identity_confirmed": true,
  "uniform": {
    "observed_uniform": "SPORTS",
    "uniform_status": "NON_COMPLIANT",
    "reason": "Buổi này yêu cầu sơ mi"
  }
}
```

reason trong đối tượng uniform là lý do đồng phục, service lưu vào uniform_reason. Không nhầm với absence_reason, lý do nghỉ học, hoặc lý do chỉnh sửa hồi tố. Các field ví dụ phải khớp hợp đồng API hai bạn đã chốt.

### 10.4 Tự kiểm tra

- Buổi yêu cầu SHIRT, quan sát SHIRT và đã xác nhận đúng: COMPLIANT.
- Buổi yêu cầu SHIRT, quan sát SPORTS: NON_COMPLIANT với lý do.
- NON_COMPLIANT không lý do: từ chối, không đổi bản ghi cũ.
- Vắng hoặc QR PENDING rồi gửi đồng phục: từ chối.
- PRESENT chưa kiểm tra: NOT_CHECKED, không tự biến thành đạt khi chốt.
- Confirm kèm uniform không hợp lệ: cả hai phần không ghi; gửi dữ liệu đúng mới thực hiện.
- GVCN lớp khác kiểm tra hoặc GVCN sửa CLOSED: bị chặn.

Mẫu yêu cầu agent: “Làm B12 trong app attendance, giải thích NOT_CHECKED và NOT_APPLICABLE bằng hai học sinh giả. Dùng required_uniform snapshot. NON_COMPLIANT phải có lý do; confirm QR + uniform cùng transaction. Thử lỗi đồng phục không được ghi nửa phần confirm. Chưa làm AI hoặc frontend.”

**Bàn giao cho mem1:** Tên field/trạng thái đồng phục, người/giờ kiểm tra và dữ liệu mẫu đạt/không đạt/chưa kiểm tra/vắng. Vắng không được xuất như một vi phạm.

## 11. M07 — Báo cáo và xuất dữ liệu

**Người làm:** mem1. **Task:** A08–A13. **Thư mục:** backend/school_app/reports/.

### 11.1 Mục tiêu của module

Trả lời các câu hỏi: lớp nào có bao nhiêu học sinh đi học, ai đi muộn, ai mặc sai đồng phục; sau đó xuất thành tệp để nhà trường dùng. Module này đọc kết quả của module khác, không tự tạo một bộ điểm danh riêng.

Query là truy vấn đọc dữ liệu theo điều kiện; filter là điều kiện lọc, ví dụ ngày hoặc lớp; summary là tổng hợp; detail là chi tiết từng bản ghi. Export nghĩa là xuất thành tệp, XLSX là tệp Excel, CSV là bảng chữ có các giá trị được phân tách.

Hai kiểu kết quả phải phân biệt:

- Chi tiết: một dòng cho một học sinh trong một buổi, có giờ đến và kết quả đồng phục.
- Tổng hợp: số có mặt/vắng/muộn/vi phạm trong những dòng chi tiết phù hợp bộ lọc.

### 11.2 Workflow đọc báo cáo

1. Người dùng chọn khoảng ngày, lớp/khối, buổi và trạng thái nếu cần.
2. Server lấy danh tính và phạm vi quyền trước khi truy vấn.
3. GVCN chỉ lớp được giao; giám thị toàn trường; học sinh không có quyền báo cáo/xuất.
4. Từ Session OPEN/CLOSED, lấy roster và Attendance phù hợp bộ lọc. PLANNED chưa có kết quả nên không đưa vào thống kê thực tế.
5. Họ tên/mã/lớp/khối trong chi tiết lấy snapshot buổi, không dùng hồ sơ hiện tại để viết lại lịch sử.
6. Tính tổng hợp trên cùng các dòng đó, trả JSON từ /api/v1/reports/attendance và /api/v1/reports/summary.

Trong giai đoạn chưa có Attendance thực, A08 có thể viết với fixture: dữ liệu mẫu phục vụ bài kiểm chứng. Khi mem2 bàn giao API/data, bắt buộc thử lại liên kết thật; test fixture đúng chưa chứng minh kết nối các module đúng.

### 11.3 Cách đếm dễ nhầm

Đơn vị đếm là học sinh-buổi. An học cả sáng và chiều tạo hai dòng trong báo cáo ngày; không tự gộp thành một. Số học sinh duy nhất là một câu hỏi khác, chưa cần thêm báo cáo riêng trong MVP.

Giả sử buổi có 40 roster: 34 PRESENT, 3 ABSENT, 3 UNMARKED. Trong 34 có mặt, 30 đúng giờ/4 muộn; đồng phục có 27 đạt/4 không đạt/3 chưa kiểm tra.

| Chỉ số | Cách tính | Kết quả ví dụ |
| --- | --- | --- |
| Có mặt | 34 chia 40 nhân 100% | 85% |
| Đi muộn trong số có mặt | 4 chia 34 nhân 100% | 11,76% |
| Số đã kiểm tra đồng phục | 27 đạt cộng 4 không đạt | 31 |
| Vi phạm trong số đã kiểm tra | 4 chia 31 nhân 100% | 12,90% |
| Độ bao phủ kiểm tra | 31 chia 34 nhân 100% | 91,18% |

Không chia số vi phạm cho tất cả 40 rồi gọi là “vi phạm trong số đã kiểm tra”. Không cộng QR PENDING vào 34 có mặt. Không xem 3 UNMARKED là vắng trước khi chốt. Sau chốt, 3 UNMARKED thành ABSENT, số có mặt vẫn 34.

Mẫu số là số ở phía dưới phép chia. Nếu mẫu số bằng 0, trả null và hiển thị “—” thay vì lỗi chia cho 0 hoặc báo 0% dễ hiểu nhầm.

### 11.4 Workflow xuất file

1. Gửi GET /api/v1/reports/export với format=xlsx hoặc csv và cùng bộ lọc báo cáo.
2. Server kiểm tra quyền/bộ lọc và số dòng. Trên 5.000 dòng thì báo chia khoảng ngày/lớp; không xây hệ thống xử lý ngầm.
3. Đọc một bộ dòng nhất quán, dùng chính bộ đó cho chi tiết và tổng hợp.
4. openpyxl tạo XLSX có Chi_tiet, Tong_hop, Thong_tin; csv chuẩn Python tạo CSV.
5. Ghi metadata, nghĩa là thông tin mô tả báo cáo: ngày xuất, múi giờ, bộ lọc, phạm vi. Không kèm mật khẩu/ảnh hồ sơ.
6. Trả tệp qua request có quyền; thử mở tệp và đối chiếu JSON/tổng số dòng.

UTF-8 là cách mã hóa chữ giúp giữ dấu tiếng Việt. BOM là dấu nhận diện mã hóa ở đầu tệp CSV để phần mềm đọc đúng hơn. Nhờ agent giải thích và thử bằng tên “Nguyễn Minh An”, không chỉ dùng tên không dấu.

Spreadsheet formula injection nghĩa là nội dung người dùng bị phần mềm bảng tính hiểu là công thức. Ví dụ ghi chú bắt đầu bằng dấu = phải được xuất như chữ, không chạy như công thức. Đây là kiểm tra tệp cần thiết, không phải chức năng bổ sung cho người dùng.

### 11.5 Tự kiểm tra và bàn giao

- Cùng bộ lọc/dữ liệu thì JSON, XLSX và CSV có số liệu tương ứng đúng.
- Test ví dụ 40 học sinh ở trên và báo cáo rỗng.
- QR chưa confirm không góp PRESENT; vắng không góp vi phạm; NOT_CHECKED được đếm riêng.
- GVCN gửi class_id ngoài quyền và học sinh gọi export: đều bị chặn.
- Mã/lớp snapshot giữ lịch sử sau khi hồ sơ hiện tại đổi.
- Tệp mở đúng dấu, giờ đúng múi giờ, không chạy công thức trong nội dung người dùng.

Mẫu yêu cầu agent: “Làm A08 query báo cáo trước bằng fixture theo model đã thống nhất. Giải thích đơn vị học sinh-buổi và mẫu số từng tỷ lệ. Cho tôi test 40 roster: 34 present, 3 absent, 3 unmarked; uniform 27/4/3. Khi query đúng mới nối API và export openpyxl/csv. Chưa làm dashboard/frontend hoặc worker.”

**Bàn giao cho mem2/PM:** Bộ lọc, ví dụ response, tệp mở được và bảng đối soát tổng số. mem2 kiểm tra các trạng thái QR/đồng phục mình tạo xuất đúng.

## 12. M08 — Nối các module và nghiệm thu API

**Người làm:** Cả hai. **Task:** A14–A15, B13–B15; chỉ làm các task giao diện/QA về sau khi gate đạt.

### 12.1 Mục tiêu của module

Integration, hay tích hợp, là nối các module thành một workflow chạy được. Một API riêng lẻ hoạt động chưa đủ nếu module báo cáo đọc sai field của điểm danh hoặc QR không dùng đúng tài khoản.

Test là bài kiểm chứng có đầu vào và kết quả mong đợi. Unit test kiểm chứng một phần nhỏ, ví dụ tính đi muộn. Integration test kiểm chứng nhiều phần cùng hoạt động, ví dụ confirm QR tạo Attendance rồi báo cáo đếm đúng. End-to-end nghĩa là thử từ đầu đến cuối workflow; giai đoạn này có thể thực hiện bằng chuỗi API, chưa cần giao diện.

### 12.2 Workflow chuẩn bị dữ liệu và thử luồng

1. mem1 tạo seed_demo với hai lớp và dữ liệu học sinh giả, tài khoản GVCN/giám thị/học sinh; không dùng thông tin thật để thử.
2. Hai bạn lưu request/response mẫu vào tài liệu API/file api-requests.http để PM có thể chạy lại.
3. Dùng đúng cookie của từng tài khoản; ghi rõ request nào là giám thị, GVCN hay học sinh.
4. Chạy chuỗi từ tạo lớp/học sinh/lịch đến mở buổi, quét, confirm, đồng phục, chốt và export.
5. Ghi kết quả mong đợi trước khi chạy; so với response và dữ liệu thực, không chỉ nhìn mã 200.
6. Thử ít nhất một trường hợp sai quyền và một trường hợp lỗi của từng module.
7. Nếu sai, người sở hữu module sửa; người còn lại chạy kiểm chứng liên kết sau sửa.

Regression test là chạy lại ca đã đúng sau khi sửa để chắc chắn thay đổi không làm hỏng việc khác. Ví dụ sửa confirm QR thì thử lại manual và báo cáo, không chỉ thử QR mới sửa.

### 12.3 API gate là gì?

Gate là mốc phải được duyệt trước khi chuyển giai đoạn. API gate nghĩa là PM xác nhận phần API đủ dùng trước khi nhóm xây frontend. Hai bạn cần:

- Tất cả task API đã thực hiện, có bài kiểm chứng/bằng chứng.
- Luồng quét → xác minh → đồng phục → báo cáo → export chạy được qua API.
- Quyền GVCN/giám thị/học sinh đúng, không có lỗi chặn luồng.
- Tài liệu request/response và dữ liệu seed để PM tự thử.
- PM review A15/B15 và đổi API_Gate sang APPROVED trong bảng.

Không tick finish chỉ vì file đã tồn tại hoặc test hiện chỉ có dòng mô tả. Trong bảng, dependencies chưa finish thì task blocked, nghĩa là chưa đủ điều kiện bắt đầu. ready nghĩa là phụ thuộc đã đạt; không nghĩa là task đã làm xong.

Mẫu yêu cầu agent: “Hỗ trợ task tích hợp API, không viết frontend. Hãy chạy chuỗi có ba vai trò với dữ liệu giả và so kết quả cuối trong report/export. Cho biết lệnh test, số ca đạt/lỗi và file lỗi; không tự gọi skeleton là module hoàn tất. Sau sửa, thử lại phần liên quan.”

## 13. Ví dụ đi qua toàn bộ workflow

Đây là ví dụ nhỏ để hai bạn tự trình bày; không thay các ca kiểm chứng trong từng module. Dùng ngày 12/10/2026, thứ Hai, buổi sáng; lớp 10A1 có cô Lan, học sinh HS001 Nguyễn Minh An và HS002 Trần Minh Bình. Bộ seed có thể có thêm học sinh; khi tính tổng báo cáo phải tính theo roster thực của cả lớp.

| Bước | Người gửi request | Điều làm | Dữ liệu/kết quả cần thấy |
| --- | --- | --- | --- |
| 1 | Giám thị | Tạo Khối 10, 10A1 và gán cô Lan | Grade/Classroom có ID đúng, teacher_id là cô Lan |
| 2 | Cô Lan | Thêm An/Bình vào lớp | Student có mã riêng, class_id 10A1 |
| 3 | Giám thị/Admin | Tạo tài khoản STUDENT liên kết An/Bình | Mỗi tài khoản trỏ đúng một hồ sơ |
| 4 | Cô Lan | Tạo lịch thứ Hai sáng 07:00, grace 5, SHIRT | ScheduleRule đúng, không trùng |
| 5 | Cô Lan | Tạo/mở buổi ngày 12/10 | Roster snapshot; An/Bình UNMARKED |
| 6 | Cô Lan/giám thị | Phát QR buổi OPEN | Token còn hạn, không chứa tên/mật khẩu |
| 7 | Tài khoản An | Gửi scan lúc 07:04 | QrScan PENDING; Attendance UNMARKED |
| 8 | Giám thị | Confirm An lúc 07:08, thấy mặc SPORTS | PRESENT, arrived 07:04, ON_TIME; NON_COMPLIANT có lý do |
| 9 | Nhân sự | Bình thiếu điện thoại, ghi đến 07:10 thủ công | PRESENT, MANUAL, LATE; giờ server ghi và giờ đến tách biệt |
| 10 | Nhân sự | Kiểm tra Bình mặc SHIRT | COMPLIANT với người/giờ kiểm tra |
| 11 | Cô Lan | Chốt buổi | UNMARKED còn lại thành ABSENT, pending hết hạn, dữ liệu đúng được giữ |
| 12 | Cô Lan/giám thị | Đọc báo cáo, xuất XLSX/CSV | An/Bình có hai kết quả đúng; tổng tính theo toàn roster |

Khi test giờ 07:04/07:08, nhờ agent dùng đồng hồ giả trong bài kiểm chứng, không phải đổi đồng hồ máy hoặc chờ đúng giờ thật. Đồng hồ giả là cách test kiểm soát “giờ hiện tại” để thử những mốc cần thiết. Trong ứng dụng thật, giờ do server quyết định.

Câu hỏi hai bạn cần tự trả lời: Vì sao An đúng giờ dù giám thị bấm lúc 07:08? Vì sao QR pending chưa là có mặt? Vì sao Bình không có QR vẫn điểm danh được? Vì sao tên/lớp báo cáo cũ không đổi khi sửa hồ sơ? Nếu chưa giải thích được, quay lại phần module liên quan trước khi đánh dấu hoàn tất.

## 14. Checklist thực hành và bàn giao mỗi task

### 14.1 Những lệnh sẽ dùng sau khi A01 hoàn tất

Chạy trong thư mục backend, bằng Python 3.12 trong môi trường của dự án. Virtual environment, hay môi trường ảo, là nơi cài riêng thư viện cho dự án để không trộn với dự án khác. requirements.txt liệt kê các thư viện cần cài. Agent phải kiểm tra máy trước, không chỉ yêu cầu các bạn chạy một lệnh chưa phù hợp môi trường.

| Lệnh | Dùng để làm gì | Kết quả cần hiểu |
| --- | --- | --- |
| python manage.py check | Kiểm tra cấu hình Django | Chưa báo lỗi cấu hình không có nghĩa nghiệp vụ đã đúng |
| python manage.py makemigrations | Tạo migration từ thay đổi model đã review | Có thay đổi bảng/cột nào; cần trao đổi với người còn lại |
| python manage.py migrate | Áp dụng migration vào database | Bảng/cột tồn tại để ứng dụng dùng |
| python manage.py makemigrations --check --dry-run | Kiểm tra có model thay đổi nhưng chưa có migration không | Không tạo migration mới trong lần kiểm tra này |
| python manage.py test | Chạy các bài kiểm chứng đã viết | Đọc số test, lỗi và các ca chưa được kiểm chứng |
| python manage.py runserver | Chạy server học tập để gửi request | Không phải server vận hành thật; chưa có giao diện riêng |
| python manage.py seed_demo | Tạo dữ liệu giả khi A14 đã làm command này | Không phải lệnh có sẵn chỉ vì tài liệu nhắc tới |

Check/migrate trên DB mới/makemigrations --check/test và seed_demo đã được kiểm chứng cho backend; evidence ở docs/project-management/evidence/backend-api.md. Test nền không thay test nghiệp vụ; cần đọc assertion và review như trong tài liệu này. Nếu Python trỏ sai môi trường, dùng đúng .venv theo backend/README.md, không tự cài chồng thư viện hoặc đổi cấu hình hệ thống để hết lỗi.

### 14.2 Sáu câu trước khi tick finish

- [ ] Tôi nói được module/chức năng đang giải quyết việc gì.
- [ ] Tôi biết request gửi gì và response mong đợi là gì.
- [ ] Tôi chỉ ra được model/bảng nào được đọc hoặc ghi.
- [ ] Tôi đã thử trường hợp đúng, sai dữ liệu và sai quyền cần thiết.
- [ ] Tôi có bằng chứng chạy và người còn lại/PM đã review theo task.
- [ ] Tôi đã ghi Evidence/Dev Note và đọc PM Comment trước khi chuyển task.

Khi PM comment “chưa đúng”, hỏi lại điều kiện chưa đạt, cập nhật code và kiểm chứng đúng tình huống đó. Không chỉ sửa trạng thái bảng. Nếu dependencies chưa xong hoặc việc vượt năng lực hiện tại, ghi Dev Note cụ thể để PM hỗ trợ chia nhỏ task.

Mỗi lần bàn giao giữa hai bạn, ghi bốn điều: field/ID đang dùng, trạng thái hợp lệ, một request/response mẫu và những lỗi đã thử. Đây là đủ để bạn kia nối module; không cần viết một tài liệu dài mới cho mỗi thay đổi nhỏ.

Mục tiêu của việc dùng agent là hoàn thành phần việc và hiểu được nó. Một module tốt ở giai đoạn này là module nhỏ, đúng yêu cầu, thử được và hai bạn giải thích lại được bằng dữ liệu lớp 10A1.
