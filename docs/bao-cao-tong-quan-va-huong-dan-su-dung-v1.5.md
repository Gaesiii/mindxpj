# Báo cáo tổng quan và hướng dẫn sử dụng hệ thống điểm danh

**Phiên bản:** 1.5. **Ngày cập nhật:** 19/10/2026. **Mốc mã nguồn được mô tả:** c16042e.

Tài liệu dành cho người chạy demo, giáo viên chủ nhiệm, giám thị và người tiếp nhận project. Nội dung phản ánh chức năng đã triển khai cùng bằng chứng hiện có, không coi phần thiếu dữ liệu là đã hoàn thiện. Bản Word cùng nội dung: [tải báo cáo](bao-cao-tong-quan-va-huong-dan-su-dung-v1.5.docx).

## 1. Tóm tắt project

Đây là ứng dụng quản lý điểm danh học sinh theo lớp và buổi học, dùng Python/Django và OpenCV. Nhân sự đăng nhập, chọn lớp/buổi, đăng ký mẫu mặt và bật camera. Khi hai ảnh liên tiếp nhận diện nhất quán một học sinh trong danh sách buổi, server tự ghi có mặt và giờ đến, không cần xác nhận từng em. Người không nhận diện được vẫn có thể được ghi nhận thủ công.

Project có giao diện quản lý lớp/học sinh, lịch học, điểm danh, đồng phục và báo cáo. Giám thị quản lý toàn phạm vi; GVCN chỉ thao tác trong các lớp được giao. Mục Đồng phục và pipeline nhận diện mẫu áo trường đã được chuẩn bị, nhưng **chưa có bộ ảnh trường để huấn luyện và nghiệm thu model**. Vì vậy, hiện không được coi hệ thống đã nhận diện chính xác đồng phục trường; thiếu model sẽ giữ kết quả **Chưa kiểm tra**.

| Nội dung | Hiện trạng |
| --- | --- |
| Nhận diện mặt và tự điểm danh | Đã triển khai, đã thử ảnh ngoài bộ đăng ký qua browser/API và YuNet/SFace thật |
| CRUD lớp/học sinh | Đã triển khai thêm, sửa, lưu trữ, khôi phục, chuyển lớp theo quyền |
| Lịch/buổi, nhập thủ công, báo cáo | Đã triển khai; có xuất Excel/CSV |
| Camera và quản lý mẫu đồng phục riêng | Đã triển khai giao diện/API; không gian riêng dùng chung camera |
| Nhận diện đúng mẫu/logo đồng phục trường | Chưa nghiệm thu; thiếu bộ ảnh, model đã học và đánh giá độc lập |
| Vercel | Đã chuẩn bị cấu hình và build local; người dùng tự deploy |
| Tiến độ plan mới | 21/26 task hoàn tất kỹ thuật; 5 task còn phụ thuộc dữ liệu/thiết bị |
| Phê duyệt PM | API_Gate vẫn NOT_APPROVED; độc lập với việc người dùng đã cho triển khai |

## 2. Công nghệ, kiến trúc và dữ liệu

Backend dùng Django ORM/Auth/Forms và JSON API; giao diện dùng Django template, JavaScript và CSS. Runtime dùng OpenCV headless, NumPy, Pillow, openpyxl và SQLite demo. Không cần dịch vụ AI ngoài hay API key để nhận diện. Phần huấn luyện đồng phục dùng môi trường công cụ offline riêng, không đưa PyTorch vào runtime Vercel.

Luồng chính: trình duyệt chụp cặp ảnh → API kiểm tra phiên đăng nhập/quyền/buổi → YuNet phát hiện và căn chỉnh mặt → SFace so đặc trưng với đúng roster → server kiểm tra lại trạng thái và ghi attendance → UI cập nhật, báo cáo đọc dữ liệu đã lưu. Nếu có model áo đã duyệt, cùng cặp ảnh được đánh giá vùng áo để tạo kết quả đồng phục.

| Nhóm dữ liệu | Vai trò |
| --- | --- |
| Tài khoản, khối, lớp, học sinh | Xác định quyền và hồ sơ hiện tại |
| Lịch tuần, buổi học | Quy định thời gian, mốc muộn, loại đồng phục yêu cầu |
| Roster của buổi | Chụp lại danh sách và tên/mã/lớp tại lúc mở buổi để giữ lịch sử |
| Attendance | Có mặt/vắng/chưa ghi nhận, giờ đến, đồng phục, nguồn và phiên bản |
| FaceSample | Crop mặt và embedding private, tách khỏi ảnh hồ sơ |
| Mẫu áo, profile/model đồng phục | Dataset riêng và phiên bản dùng cho các buổi mới |
| Audit và idempotency | Truy vết thay đổi, tránh ghi trùng khi retry trong cùng DB |

YuNet/SFace là model nguồn mở được dự án tích hợp, không phải model khuôn mặt do nhóm tự huấn luyện. Model được khóa phiên bản/hash và chuẩn bị trước khi chạy/build; request nhận diện không tải model qua mạng. License/ghi công được giữ trong [third_party](../backend/third_party/opencv_zoo).

Ảnh hồ sơ, mẫu mặt và mẫu áo không có URL public tùy ý. Ảnh quét/video không được lưu lại. Đăng ký mặt là lưu đặc trưng của học sinh để so khớp, không huấn luyện lại mạng SFace cho từng em. Hai ảnh nhất quán không phải bằng chứng liveness hay khả năng chống ảnh chụp giả.

## 3. Vai trò và quyền sử dụng

| Thao tác | Giám thị | GVCN | Học sinh |
| --- | --- | --- | --- |
| Dùng staff console | Có | Có | Không |
| Xem lớp/hồ sơ/điểm danh/báo cáo | Toàn phạm vi | Lớp hiện được giao | Chỉ dữ liệu bản thân qua API cho phép |
| Tạo/sửa/lưu trữ/khôi phục lớp | Có | Không | Không |
| Thêm học sinh, sửa tên/trạng thái | Có | Trong lớp được giao | Không |
| Sửa mã học sinh hoặc chuyển lớp | Có | Không | Không |
| Đăng ký mẫu mặt, điểm danh, kiểm tra áo | Có | Trong lớp được giao | Không |
| Quản lý/export dataset, chọn profile áo | Có | Đọc dữ liệu trong scope; không quản lý dataset | Không |
| Bổ sung học sinh vào buổi OPEN | Có | Không | Không |
| Điều chỉnh buổi đã chốt | Có, cần lý do | Không | Không |

Quyền được kiểm tra ở server, bao gồm ảnh và export. Đổi GVCN làm thay đổi quyền đọc/ghi lịch sử lớp theo GVCN hiện tại. Cờ quản trị kỹ thuật của Django không tự thay thế vai trò nghiệp vụ. Không có đăng ký tài khoản công khai hoặc cổng phụ huynh.

## 4. Khởi động và đăng nhập demo local

Nếu server đang chạy, mở **http://127.0.0.1:8000/**. Khi cần cài/chạy mới trên Windows, dùng Python 3.12 và PowerShell tại thư mục project:

```powershell
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
backend/.venv/Scripts/python.exe .document-tools/run_demo.py
```

Chỉ tạo virtualenv/cài dependencies khi máy chưa chuẩn bị. Launcher tự tạo secret, DB thử riêng, tài khoản giả, mẫu lịch và buổi hôm nay cho demo mới. Lần đầu có thể cần tải hai model mặt đã pin; không đóng terminal trong lúc server chạy. Nếu cổng 8000 đang được dùng, dừng server cũ hoặc thêm `--port 8001` và mở URL mới mà launcher in ra.

Tài khoản demo:

- `demo_supervisor`: giám thị.
- `demo_teacher_a`, `demo_teacher_b`: GVCN của hai lớp demo.
- Mật khẩu được lưu trong file `demo-login.txt` ở thư mục runtime ngoài repository; lấy đường dẫn từ terminal. Tài liệu không chứa giá trị mật khẩu/secret. Tài khoản học sinh giả không dùng để vào staff console.

Chạy launcher không có tùy chọn resume tạo **DB demo mới**. Để giữ dữ liệu cũ, ghi lại đường dẫn runtime đã được in và dùng:

```powershell
# Thay đường dẫn ví dụ bằng thư mục runtime thực tế của bạn.
$demoRuntime = 'C:\Users\TEN_BAN\AppData\Local\Temp\projectmindx-demo-ui-THU_MUC_CUA_BAN'
backend/.venv/Scripts/python.exe .document-tools/run_demo.py --resume-runtime $demoRuntime
```

Resume giữ DB/login và chạy migration, không seed lại. Cần đăng nhập lại sau khởi động. Nếu ngày mới chưa có buổi học, tạo/mở qua UI; resume không hứa tự tạo buổi mới mỗi ngày. Sao lưu DB trước nâng cấp; không chạy seed để thay thế dữ liệu đang dùng. Cách setup backend trực tiếp xem [backend README](../backend/README.md).

## 5. Quản lý lớp và học sinh

### 5.1. Lớp học

1. Đăng nhập giám thị, mở **Lớp học → Thêm lớp**.
2. Nhập mã, tên, chọn khối/GVCN đã có và sức chứa từ 1–50.
3. Chọn **Lưu lớp**. Dùng **Sửa** để chỉnh thông tin sau đó.
4. Sĩ số là số học sinh đang hoạt động, tự tính từ hồ sơ; không có ô gõ một sĩ số giả. Sức chứa là giới hạn có thể sửa, nhưng không được thấp hơn sĩ số hiện tại.
5. **Lưu trữ** không xóa lịch sử. Phải xử lý học sinh active và buổi OPEN trước khi lưu trữ lớp. **Khôi phục** đưa lớp về hoạt động.

UI chọn từ khối và tài khoản GVCN đã được tạo sẵn; chưa có màn hình quản trị toàn bộ tài khoản/khối. Việc cấp tài khoản thuộc thao tác quản trị backend, không phải đăng ký công khai.

### 5.2. Học sinh

1. Chọn lớp ở thanh ngữ cảnh, vào **Học sinh → Thêm học sinh**.
2. Nhập mã, họ tên và lớp; mã phải duy nhất, lớp phải hoạt động và còn chỗ.
3. Dùng **Sửa / chuyển lớp** với giám thị, hoặc **Sửa tên** với GVCN. GVCN không được sửa mã hay chuyển lớp.
4. Dùng **Lưu trữ/Khôi phục** để đổi trạng thái. Học sinh ngừng hoạt động không được nhận diện mới; khôi phục vẫn kiểm tra sức chứa.
5. Đổi tên/mã/lớp không viết lại tên/mã/lớp đã chụp trong roster cũ. Hồ sơ và lịch sử không bị xóa cứng.

Học sinh thêm sau khi buổi đã mở không tự xuất hiện trong roster buổi đó. Giám thị có thể chọn **Điểm danh → Thêm vào buổi đang mở**, chọn học sinh active đúng lớp rồi lưu. Thao tác chỉ thêm người mới với trạng thái chưa ghi nhận, không dựng lại danh sách hay sửa các hàng đã điểm danh.

## 6. Thiết lập lịch và mở buổi

1. Chọn lớp, vào **Điểm danh → Thiết lập lịch**.
2. Chọn thứ/buổi, giờ bắt đầu/kết thúc, số phút cho phép và loại áo yêu cầu: Sơ mi hoặc Thể dục. Lưu lịch.
3. Chọn **Tạo buổi học**, nhập ngày/buổi phù hợp với lịch rồi lưu.
4. Chọn **Mở buổi** để đóng băng thời gian, đồng phục yêu cầu, profile áo và roster học sinh.

Điểm danh tự động chỉ hoạt động khi buổi OPEN, thuộc hôm nay và còn trong khoảng giờ quy định. Lịch mới không âm thầm đổi các snapshot của buổi đã mở. Mốc xác định muộn là giờ bắt đầu cộng số phút cho phép, không phải cứ có mặt là đúng giờ.

## 7. Đăng ký mẫu mặt và tự điểm danh

### 7.1. Đăng ký mẫu

1. Vào **Học sinh → Quản lý mẫu** tại đúng hồ sơ.
2. Chọn **3–10 ảnh khác nhau của cùng một học sinh**; mỗi ảnh một mặt rõ, đủ sáng, có vài góc/điều kiện khác nhau.
3. Chọn **Lưu bộ mẫu** và kiểm tra số mẫu dùng được.

JPEG/PNG/WebP, mỗi ảnh tối đa 2 MiB/4 triệu pixel; tổng bộ local tối đa 15 MiB, Vercel tối đa 3 MiB. Bộ mới thay toàn bộ bộ cũ; ảnh không hợp lệ làm thao tác bị từ chối thay vì lưu bộ dở dang. Ảnh hồ sơ không tự trở thành mẫu nhận diện. Mẫu LBPH cũ phải đăng ký lại để dùng SFace. Xóa/thay mẫu sẽ vô hiệu proposal legacy đang chờ.

### 7.2. Quét bằng camera

1. Chọn lớp và buổi OPEN phù hợp, mở **Điểm danh → Bật camera**.
2. Cho phép quyền camera; để một người trong khung, thấy rõ mặt và vùng áo.
3. Camera tự lấy hai frame cách nhau một khoảng ngắn; tối đa một lượt gửi mỗi khoảng 4 giây và không gửi chồng.
4. Cả hai frame phải khớp cùng học sinh trong roster và đủ ngưỡng. Khi đạt, UI tự hiển thị **Có mặt**, server lưu giờ đến, không cần bấm confirm danh tính.
5. Chờ người tiếp theo vào khung. Quét lại người đã ghi nhận không đổi giờ đến đầu; vắng/chỉnh sửa thủ công không bị camera ghi đè.
6. Tắt camera khi kết thúc. Đổi trang/lớp/buổi, ẩn tab hoặc đăng xuất sẽ dừng camera/luồng gửi mới.

Camera cần localhost hoặc HTTPS và quyền trình duyệt. Không nhận diện được, nhiều mặt hoặc kết quả mơ hồ thì không tự ghi attendance; điều chỉnh tư thế/ánh sáng hoặc dùng thủ công. Có quota 20 lượt phân tích/phút/nhân sự trong cache process demo; khi bị giới hạn hãy chờ hướng dẫn thay vì bấm liên tục.

### 7.3. Thử bằng ảnh có sẵn

Chọn **Hoặc chọn đúng 2 ảnh khác nhau**, chọn hai ảnh của người cần kiểm tra rồi bấm **Quét cặp ảnh**. UI thu nhỏ/nén; API nhận tối đa 1 MiB mỗi ảnh và 2 MiB tổng. Không dùng lại cùng một file hai lần. Khi đánh giá nhận diện, nên dùng ảnh khác bộ đăng ký; upload lại ảnh đã đăng ký không chứng minh khả năng nhận diện ảnh mới.

Nếu mất mạng sau gửi, dùng **Thử lại cùng yêu cầu** khi UI cung cấp để tránh tạo lượt không cần thiết. Thông báo “Đã ghi nhận trước đó” không đồng nghĩa với “Có mặt”: hãy đọc trạng thái trong bảng, vì bản ghi có thể là vắng do nhân sự đặt.

### 7.4. Ghi nhận thủ công và chốt buổi

Ở hàng học sinh, chọn **Ghi nhận**, chọn Có mặt/Vắng, nhập giờ đến nếu có và lý do rồi lưu. Đây là fallback khi camera lỗi, không có mẫu hoặc cần điều chỉnh. Sau cùng chọn **Chốt buổi**: các học sinh chưa ghi nhận chuyển thành Vắng; không chuyển toàn bộ đồng phục thành vi phạm. Buổi đã chốt không nhận quét mới. Chỉnh sửa sau chốt cần giám thị và lý do; buổi đã chốt không mở lại trong MVP.

## 8. Sử dụng mục Đồng phục

### 8.1. Điều có thể dùng ngay

Mục **Đồng phục** có camera và danh sách cần giáo viên kiểm tra. Nó dùng chung camera controller với điểm danh, không chạy hai camera đồng thời. Chế độ này chỉ kiểm tra người đã được ghi có mặt; người chưa có mặt phải sang Điểm danh trước.

**Ở hiện trạng chưa có model trường, kết quả áo giữ Chưa kiểm tra.** Có thể đối chiếu thủ công bằng nút **Đồng phục** trong bảng điểm danh: chọn loại áo thực tế, kết quả Đạt/Không đạt và lưu. Không đạt bắt buộc lý do; chọn Loại khác còn cần ghi chú mô tả. Sửa cảnh báo sai thành Đạt được; quyết định thủ công có nguồn riêng và không bị auto đè.

### 8.2. Luồng sau khi có model trường đạt đánh giá

| Kết quả quan sát | Hiển thị/hành vi | Nhân sự xử lý |
| --- | --- | --- |
| Hai ảnh đủ rõ, nhất quán đúng loại/mẫu yêu cầu | Đạt tự động, nguồn AUTO | Không cần xác nhận |
| Model tự tin sai mẫu/loại | Cần kiểm tra, chưa phải vi phạm đã xác nhận | Giáo viên ghi lý do để Không đạt hoặc sửa cảnh báo sai |
| Thiếu model, vùng áo không đủ hoặc kết quả không chắc | Chưa kiểm tra | Quét lại hoặc kiểm tra thủ công |

Hệ thống không tự viết lý do vi phạm như thể giáo viên đã nhập. Màu trắng/xanh hoặc ảnh sắc nét không tự chứng minh đúng logo/mẫu trường. Đạt đồng phục và Có mặt là hai kết quả riêng.

### 8.3. Chuẩn bị bộ ảnh trường

1. Giám thị vào **Mẫu đồng phục**, chọn lớp, tải ảnh một người thấy rõ mặt và áo.
2. Kéo ROI chỉ phần áo dưới khuôn mặt, chọn nhãn Sơ mi/Thể dục/Loại khác.
3. Nhập nhóm ảnh chụp không định danh, chẳng hạn `nhom-01`; chọn Huấn luyện/Đối chiếu/Kiểm thử rồi **Lưu mẫu áo**.
4. Xem lại crop, xóa ảnh không phù hợp. Các ảnh cùng người/buổi chụp phải cùng split; không dùng tên hoặc mã học sinh làm nhóm ảnh.
5. **Tải bộ mẫu** để làm pipeline offline. Upload ảnh **không tự huấn luyện/bật model**.
6. Người phụ trách kỹ thuật train/fine-tune, đánh giá ảnh độc lập, kiểm tra logo/đối chứng/che áo, import model và evidence đã duyệt. Sau đó giám thị chọn phiên bản ở **Bộ nhận biết đã duyệt → Áp dụng cho lớp**. Buổi đã OPEN vẫn dùng snapshot cũ; chọn profile trước khi mở buổi mới.

Mục tiêu dữ liệu khởi đầu khoảng 100–200 ảnh độc lập mỗi loại, có nhiều người/ngày/ánh sáng và áo trường khác cùng màu, ảnh che/thiếu logo. Đây không bảo đảm đủ dữ liệu hoặc đạt độ chính xác. Mẫu áo lưu private, tối đa 1 MiB/crop, 1.000 mẫu và 32 MiB/lớp trong demo; export lớn bị giới hạn thêm trên Vercel. Hướng dẫn lệnh, review và model import ở [pipeline offline](../tools/uniform_training/README.md).

## 9. Xem báo cáo và xuất dữ liệu

Chọn lớp → **Báo cáo** → khoảng ngày → **Xem báo cáo**, sau đó chọn **Excel** hoặc **CSV**. Export tối đa 5.000 dòng; nếu vượt giới hạn hãy chia nhỏ khoảng ngày/lớp. Dữ liệu luôn nằm trong scope tài khoản và dùng snapshot của buổi, không viết lại theo tên/lớp hiện tại.

Đọc riêng các trạng thái Có mặt/Vắng/Chưa ghi nhận; Đúng giờ/Muộn; Đạt/Không đạt/Cần kiểm tra/Chưa kiểm tra. **Cần kiểm tra** không được tính như vi phạm đã ghi lý do; tỷ lệ vi phạm dùng các kết quả đã kiểm tra. Nguồn nhận diện/đồng phục giúp phân biệt tự động và thủ công. Chốt buổi không có nghĩa mọi trường hợp đồng phục đã được xử lý.

## 10. Hướng dẫn tự deploy Vercel

Import repository, chọn Root Directory **backend**, framework Django, Python 3.12 và build command theo `backend/pyproject.toml`. Thêm `DJANGO_SECRET_KEY` và `DEMO_PASSWORD` vào đúng môi trường Production/Preview, lưu rồi tạo deployment mới từ `main`. Hai giá trị phải do bạn giữ riêng; `.env.vercel` ở máy local không được push và Vercel không tự đọc file này.

Build chuẩn bị face model, migrate/seed DB mẫu và static. Demo Vercel không cần `DATABASE_URL` hay dịch vụ DB riêng. Đăng nhập `demo_supervisor` hoặc hai GVCN bằng DEMO_PASSWORD đã đặt. Hướng dẫn xử lý thiếu env/seed, domain và giới hạn ở [tài liệu Vercel](deploy-vercel-demo.md). Project đã có bằng chứng build **local**, tài liệu này không xác nhận deployment thực đang thành công trên Vercel.

SQLite, ảnh và mẫu mặt mới chỉ tạm theo từng instance: redeploy/cold instance có thể mất thay đổi và các request có thể thấy dữ liệu khác nhau. Chống trùng chỉ đảm bảo trong cùng DB, không phải toàn deployment. Chỉ dùng cho demo nhỏ; database dùng chung bền vững cần scope triển khai riêng. Thiếu model áo trên môi trường chạy vẫn Chưa kiểm tra, dù local đã upload ảnh mẫu.

## 11. Kết quả kiểm chứng hiện có

Đợt kiểm chứng v1.5 ngày19/10/2026 đã ghi nhận:

- **255 tests đạt**, Django check/migration drift/pip check đạt; không lấy số test này làm tỷ lệ nhận diện đúng.
- Browser/API thật với YuNet/SFace thật: 3 ảnh đăng ký, 2 ảnh ngoài bộ đăng ký ghi Có mặt tự động; ảnh người khác bị từ chối; retry giữ giờ đến; không phát sinh lỗi JavaScript trong ca thử.
- Browser dùng API fixture và webcam giả kiểm tra cadence, dừng camera, CRUD/quyền, ghi lý do, ROI và cập nhật sĩ số; không chứng minh camera vật lý hay model áo.
- Hai thread trên SQLite file kiểm tra chỉ một người được thêm vào lớp sức chứa1 và cùng key chỉ tạo một attendance/scan/audit; không chứng minh distributed/serverless.
- Nâng cấp trên bản sao DB cũ giữ 20 học sinh,20 attendance,7 mẫu mặt cùng byte dữ liệu; build Vercel local thành công.
- Benchmark có wall time, CPU, working set/peak và kích thước source/model trên máy Windows với roster nhỏ; không suy thành tốc độ Vercel hoặc tải toàn trường.

Chi tiết, số đo và giới hạn: [evidence v1.5](project-management/evidence/v1.5/README.md). Tài liệu thiết kế chuẩn: [v1.5](thiet-ke-he-thong-diem-danh.md); giao diện kỹ thuật: [API contract](api-contract.md).

## 12. Lỗi thường gặp

| Hiện tượng | Kiểm tra/xử lý |
| --- | --- |
| Không đăng nhập được | Dùng tài khoản staff, đúng mật khẩu trong runtime local hoặc DEMO_PASSWORD của Vercel; hai nguồn có thể khác nhau |
| Local mất dữ liệu sau chạy lại launcher | Có thể đang vào DB demo mới; dùng đúng runtime cũ với resume, không seed đè |
| Bật camera nhưng không ghi có mặt | Kiểm tra buổi OPEN/hôm nay/khung giờ, quyền camera, đúng một mặt, đủ 3 mẫu dùng được và học sinh trong roster |
| Ảnh rõ nhưng UNKNOWN | Ảnh rõ chưa đủ chứng minh giống bộ mẫu; thử góc/ánh sáng khác, đăng ký mẫu đúng người, dùng ảnh ngoài enrollment để đánh giá; không tự hạ ngưỡng để ép khớp |
| Không gửi được bộ mẫu | Kiểm tra 3–10 ảnh khác nhau, định dạng/2MiB/4MP và tổng local15MiB hoặc Vercel3MiB |
| Chọn cùng một ảnh hai lần khi quét | Cần hai ảnh khác nhau, không gửi lặp cùng file |
| Thêm học sinh nhưng buổi không có tên | Roster đã snapshot; giám thị bổ sung riêng vào buổi OPEN hoặc dùng buổi mở sau |
| Không lưu được lớp/restore học sinh | Kiểm tra mã trùng, quyền, lớp active, sức chứa, học sinh active hoặc buổi OPEN đang cản archive |
| Thông báo dữ liệu đã thay đổi | Có người/lượt khác đã sửa; làm mới và đọc trạng thái trước khi thử lại |
| Upload ảnh áo rồi vẫn Chưa kiểm tra | Upload chưa tạo model; phải train/evaluate/import/chọn version và mở buổi mới |
| Vercel dữ liệu lúc có lúc mất | SQLite/ảnh/mẫu là tạm theo instance; không phải kho dữ liệu đồng bộ |
| Build lỗi thiếu env hoặc seed | Xem marker build và thông báo mã lỗi; đặt đúng hai biến ở môi trường tương ứng, không gửi giá trị secret vào log/chat công khai |

## 13. Phần còn lại và hướng phát triển đã có trong plan

| Task | Phần chưa xong |
| --- | --- |
| D01 | Thu thập bộ ảnh đồng phục trường và đối chứng, kiểm tra nhãn/nhóm/split |
| D02 | Benchmark candidate/baseline trên dữ liệu trường để chốt model |
| D03 | Train/fine-tune thực, đánh giá và xuất artifact trường đã được review |
| U02 | Kiểm chứng runtime nhận diện áo với artifact trường được nghiệm thu |
| Q02 | Calibration đầy đủ với ảnh độc lập, áo trường và camera vật lý |

Không đánh dấu các mục này hoàn tất chỉ vì có UI/API/script. Cần đo precision/recall, coverage/UNKNOWN, tình huống cùng màu khác logo và che áo; không công bố accuracy toàn trường hay liveness từ vài ảnh demo. [Tracker mới](project-management/auto-attendance-uniform-crud-tasks.csv) phân biệt Finish kỹ thuật với API_Gate/PM acceptance.

Không thêm SMS, parent portal, cloud AI/storage, worker/queue hay module duyệt sửa ngoài MVP. Các bản v1.2–v1.4 giữ trong archive để truy vết; luồng hiện hành là v1.5 tự điểm danh. [Slide thuyết trình hiện tại](thuyet-trinh-opencv.pptx) có 7 slide và speaker notes.
