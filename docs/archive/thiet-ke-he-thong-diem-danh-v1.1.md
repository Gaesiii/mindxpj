# Thiết kế hệ thống điểm danh học sinh và kiểm tra đồng phục

> Tài liệu dành cho nhà trường, người phụ trách sản phẩm và agent code. Đây là bản phân tích và kế hoạch đề xuất; chưa triển khai ứng dụng. Agent chỉ bắt đầu xây dựng khi người dùng yêu cầu triển khai và xác nhận các quyết định ảnh hưởng nghiệp vụ.

**Phiên bản:** 1.1 — 08/10/2026; cập nhật công nghệ và kế hoạch cho học viên K12 đi thi.  
**Mục tiêu:** Quản lý học sinh theo lớp, lịch đi học, thời gian đến trường và việc mặc đồng phục; phân quyền giáo viên chủ nhiệm (GVCN), giám thị; xuất dữ liệu có thể kiểm tra lại.  
**Kiến trúc đề xuất:** Một ứng dụng Django theo module; giao diện responsive render bằng Django Templates; SQLite cho học tập/demo, PostgreSQL cho thử tải và vận hành nhiều người; ảnh/tệp lưu riêng tư.  
**Công nghệ chủ đạo:** Python 3.12 và Django 5.2; Django ORM, Auth, Forms và Admin; HTML/CSS/Bootstrap, JavaScript tối thiểu cho camera QR và polling; Pillow xử lý ảnh, qrcode tạo QR, openpyxl xuất XLSX, csv của Python xuất CSV. Chốt bản vá và khóa dependency khi triển khai; không yêu cầu frontend framework hoặc hệ thống build JavaScript riêng.  
**Cách thực hiện kế hoạch:** Đi theo các module và checklist ở mục 14; đọc quy tắc dữ liệu trước khi viết code. Có thể dùng skill `superpowers:executing-plans` nếu môi trường có sẵn; không tự động triển khai, tạo hạ tầng hoặc phát hành sản phẩm chỉ vì nhận được tài liệu.

**Định hướng K12:** Học viên cần hiểu và giải thích được model, view, form, template, service Python và luồng QR. Bản đi thi ưu tiên chạy được luồng hoàn chỉnh trên dữ liệu giả; các mục tải lớn, cloud storage và khôi phục cấp trường là hướng nâng cao, không phải điều kiện demo cơ bản.

## 1. Yêu cầu gốc và phạm vi

### 1.1 Yêu cầu đã được người dùng nêu

| Mã | Yêu cầu | Phần thiết kế đáp ứng |
| --- | --- | --- |
| R01 | Học sinh có họ tên, lớp, khối | Hồ sơ học sinh, lớp theo năm học, lịch sử xếp lớp |
| R02 | Mỗi lớp có một GVCN quản lý | Phân công GVCN có thời gian hiệu lực, quyền theo lớp |
| R03 | GVCN được thêm học sinh và hình học sinh | Module học sinh, quy trình tải ảnh riêng tư |
| R04 | Quản lý lịch học và loại đồng phục sơ mi/thể dục | Lịch tuần, buổi học, chính sách đồng phục, ngoại lệ theo ngày |
| R05 | Giám thị quản lý tất cả | Quyền toàn trường đối với nghiệp vụ; quyền hệ thống riêng |
| R06 | Điểm danh có thời gian đi học | Thời gian đến thực tế, thời gian nhập, trạng thái đúng giờ/đi muộn |
| R07 | Nhận định đồng phục đúng quy định hay không | Kết quả kiểm tra, loại thực tế, lý do vi phạm, người kiểm tra |
| R08 | GVCN và giám thị có thể xuất dữ liệu | Báo cáo và XLSX/CSV theo phạm vi quyền |

### 1.2 Giả định thiết kế cần xác nhận

Các mục dưới đây là đề xuất để tài liệu có thể dùng ngay, không phải thông tin nhà trường đã xác nhận.

| Mã | Giả định mặc định | Tác động khi thay đổi |
| --- | --- | --- |
| A01 | Một trường, nhiều khối/lớp, có năm học | Nếu nhiều trường, cần quản lý tenant và cách phân quyền liên trường |
| A02 | Đã được người dùng chọn: học sinh quét QR, GVCN/giám thị xác nhận đồng phục; đề xuất học sinh dùng trình duyệt điện thoại đăng nhập tài khoản riêng | Cần chốt thiết bị, tài khoản học sinh và vị trí hiển thị QR; có thao tác thủ công dự phòng |
| A03 | Điểm danh theo buổi đi học sáng/chiều, không theo từng tiết | Điểm danh tiết học cần mô hình môn học và giáo viên bộ môn |
| A04 | GVCN thao tác nghiệp vụ trong lớp đang được phân công; giám thị toàn trường | Phân công thay thế/kiêm nhiệm cần mở rộng bảng quyền |
| A05 | GVCN chỉnh lịch lớp trước khi buổi bắt đầu; giám thị xử lý thay đổi sau khi bắt đầu | Nếu cần duyệt lịch, bổ sung trạng thái và người phê duyệt |
| A06 | Kiểm tra đồng phục do con người xác nhận | Ảnh hồ sơ dùng để đối chiếu học sinh, không đủ để kết luận đồng phục hôm nay |
| A07 | Đồng phục chuẩn có hai loại: SHIRT và SPORTS | Loại khác được quản lý qua danh mục thay vì sửa logic |
| A08 | Dữ liệu thời gian lưu UTC; hiển thị Asia/Ho_Chi_Minh; ngưỡng đi muộn cấu hình được | Cần chốt giờ vào học và khoảng cho phép cho từng buổi |
| A09 | Sau khi chốt buổi, GVCN gửi yêu cầu sửa; giám thị duyệt có lý do | Nhà trường có thể cho GVCN sửa trong một khoảng thời gian được cấu hình |
| A10 | Xuất XLSX và CSV; Word chỉ dùng cho tài liệu thiết kế này | PDF thống kê là phạm vi tùy chọn |

### 1.3 Trong MVP

- Đăng nhập, phân quyền; năm học, khối, lớp, phân công GVCN.
- Hồ sơ học sinh, mã học sinh, ảnh, xếp lớp và chuyển lớp có lịch sử.
- Lịch đi học tuần, buổi học theo ngày, giờ vào học, đồng phục và ngày nghỉ/ngoại lệ.
- Điểm danh trực tiếp, thời gian đến, vắng có phép/không phép và kiểm tra đồng phục.
- QR động theo buổi/lớp, trang quét cho học sinh, hàng đợi xác minh danh tính và đồng phục của nhân sự.
- Chốt buổi, yêu cầu sửa sau chốt, nhật ký thay đổi.
- Dashboard, báo cáo, xuất XLSX/CSV đúng phạm vi quyền.
- Sao lưu, khôi phục, giám sát lỗi và bảo vệ ảnh/dữ liệu.

### 1.4 Ngoài MVP

Nhận diện khuôn mặt, AI nhận định đồng phục, tích hợp camera/cổng tự động, RFID, ứng dụng native, cổng phụ huynh, gửi SMS/Zalo, học phí, điểm số, kỷ luật tự động và điểm danh offline. QR nằm trong MVP; lần quét là sự kiện chờ xác minh, không tự suy ra đồng phục đạt.

## 2. Các cách tiếp cận và lựa chọn

| Phương án | Cách vận hành | Ưu điểm | Hạn chế | Giai đoạn |
| --- | --- | --- | --- | --- |
| Web điểm danh trực tiếp | GVCN/giám thị tìm học sinh, ghi thời gian đến và kết quả đồng phục | Ít phụ thuộc thiết bị; nghiệp vụ dễ kiểm tra | Cần nhân sự thao tác; chậm khi số lượng lớn | Dự phòng trong MVP |
| QR kết hợp kiểm tra trực tiếp — người dùng đã chọn | Học sinh quét mã; nhân sự xác nhận danh tính và đồng phục | Tăng tốc tại cổng; lưu thời gian sự kiện tự động | Có thể quét hộ; cần mã, tài khoản học sinh, thiết bị và xử lý mạng yếu | Phương án chính MVP |
| Camera hỗ trợ | Thiết bị tạo gợi ý danh tính/đồng phục; nhân sự xác nhận | Có khả năng giảm thao tác khi số lượng lớn | Chi phí, sai số, điều kiện ảnh, xử lý dữ liệu nhạy cảm và vận hành phức tạp | Dự án riêng sau thử nghiệm |

Chọn web có QR và xác nhận trực tiếp theo phản hồi của người dùng. Trường `source` nhận `QR` hoặc `MANUAL`. Thiết kế QR động theo buổi của từng lớp, học sinh quét bằng điện thoại cá nhân đã đăng nhập; đây là đề xuất vận hành cần nhà trường xác nhận. Nếu muốn máy tại cổng quét mã cá nhân trên thẻ học sinh, cần thay luồng quét M10, nhưng giữ nguyên dữ liệu điểm danh/đồng phục.

## 3. Vai trò, quyền và giới hạn

### 3.1 Vai trò

GVCN quản lý học sinh và lịch của lớp mình; điểm danh, kiểm tra đồng phục, xem và xuất báo cáo của lớp. Giám thị quản lý nghiệp vụ toàn trường, phân công lớp, chốt/mở lại buổi và duyệt chỉnh sửa. Quản trị kỹ thuật là vai trò bổ sung để tạo tài khoản, cấu hình và vận hành; không tự nhận quyền đọc toàn bộ dữ liệu học sinh nếu chưa được cấp vai trò giám thị.

Vai trò STUDENT là quyền tối thiểu phục vụ QR: đăng nhập, xem tên/mã và buổi của chính mình, quét QR, xem trạng thái gửi/chờ xác nhận của mình, đổi mật khẩu. Không xem danh sách lớp, ảnh người khác, sửa thời gian, kiểm tra đồng phục hoặc xuất báo cáo. Mỗi tài khoản STUDENT liên kết đúng một Student trong trường. Cấp/reset tài khoản do quản trị kỹ thuật; GVCN không nhận danh sách mật khẩu từ báo cáo.

| Hành động | GVCN | Giám thị | Quản trị kỹ thuật |
| --- | --- | --- | --- |
| Xem học sinh/ảnh | Lớp được phân công | Toàn trường | Không mặc định |
| Thêm/sửa hồ sơ, thay ảnh | Lớp được phân công | Toàn trường | Không mặc định |
| Đổi mã học sinh, chuyển lớp/ngừng học | Gửi yêu cầu | Thực hiện | Không mặc định |
| Tạo/sửa lịch trước buổi | Lớp được phân công | Toàn trường | Không mặc định |
| Tạo khối/lớp/năm học, phân công GVCN | Xem liên quan | Thực hiện | Không mặc định |
| Điểm danh/kiểm tra khi buổi mở | Lớp được phân công | Toàn trường | Không mặc định |
| Chốt buổi đã mở | Lớp được phân công | Toàn trường | Không mặc định |
| Sửa dữ liệu đã chốt | Gửi yêu cầu | Duyệt và thực hiện | Không mặc định |
| Xem/xuất báo cáo | Lớp được phân công | Toàn trường | Không mặc định |
| Xem audit nghiệp vụ | Lớp được phân công | Toàn trường | Nhật ký kỹ thuật được cấp |
| Quản lý tài khoản/cấu hình hệ thống | Không | Không, trừ khi kiêm quyền | Thực hiện |

### 3.2 Quy tắc phạm vi

- Backend kiểm tra quyền trên mọi API và từng tài nguyên; ẩn nút ở giao diện không thay thế kiểm tra quyền.
- Mỗi dòng dữ liệu nghiệp vụ có `school_id`. ID lớp/học sinh do client gửi không được coi là bằng chứng quyền.
- Một lớp có đúng một GVCN hiệu lực tại một thời điểm. Các khoảng phân công không được chồng lấn. Lớp mới có thể ở trạng thái DRAFT chưa có GVCN; chỉ ACTIVE khi đã có phân công.
- Một GVCN có thể được phân công nhiều lớp nếu nhà trường cho phép; không suy diễn rằng mỗi giáo viên chỉ được một lớp.
- Khi đổi GVCN, giáo viên cũ mất quyền ngay; giáo viên mới được xem lịch sử của lớp hiện được phân công. Giám thị xem toàn bộ lịch sử trong trường.
- Học sinh chuyển lớp: GVCN lớp cũ chỉ xem bản ghi buổi cũ thuộc lớp mình; GVCN lớp mới xem hồ sơ hiện tại và buổi lớp mới. Báo cáo gộp toàn bộ quá trình chuyển lớp thuộc giám thị.
- Tài khoản có nhiều vai trò được hợp quyền trong cùng trường; vô hiệu hóa tài khoản làm mất quyền và phiên đăng nhập.
- Export và tải ảnh kiểm tra lại quyền hiện tại; đường dẫn tải không công khai và có thời hạn.

## 4. Quy tắc nghiệp vụ cốt lõi

### 4.1 Tách ba loại dữ liệu

Hồ sơ học sinh trả lời “đây là ai”; lịch học trả lời “học sinh cần đến khi nào và mặc gì”; kết quả điểm danh trả lời “buổi đó thực tế xảy ra điều gì”. Không lưu trạng thái “hôm nay có mặt” hoặc “đồng phục sai” trực tiếp trên hồ sơ học sinh.

### 4.2 Buổi học, danh sách và thời điểm

- `school_date` là ngày theo múi giờ trường; `start_at`, `late_cutoff_at`, `close_at` là thời điểm có múi giờ quy đổi UTC. MVP không hỗ trợ buổi qua nửa đêm.
- Một lớp có tối đa một buổi MORNING và một buổi AFTERNOON mỗi ngày. Ràng buộc duy nhất `(school_id, class_id, school_date, slot)`.
- `late_cutoff_at = start_at + grace_minutes`. Ví dụ: bắt đầu 07:00, cho phép 5 phút, đến 07:05:00 vẫn ON_TIME; từ 07:05:01 là LATE. Đây là ví dụ cấu hình, không phải giờ học đã xác nhận.
- `arrived_at` là thời gian đến thực tế; `recorded_at` là thời gian server ghi nhận. Nhập hồi tố cần lý do, có audit; không thay thế `recorded_at`.
- Thời gian đến thông thường nằm trong ngày học, từ cửa sổ điểm danh sớm đến lúc chốt; nhập vượt cửa sổ cần giám thị và lý do. Không cho thời gian đến tương lai quá 60 giây sai lệch đồng hồ.
- Danh sách buổi dựa trên học sinh có xếp lớp hiệu lực trong ngày đó; sao chép thành `SessionRoster` tại lúc mở buổi. Xếp lớp tính theo ngày: ngày chuyển là ngày đầu ở lớp mới, áp dụng cả hai buổi.
- Lịch và roster của buổi đã mở là snapshot. Sửa lịch tuần hoặc chuyển lớp sau đó không âm thầm sửa dữ liệu buổi cũ.
- Học sinh bị bỏ sót trong roster buổi đang mở chỉ được giám thị bổ sung/xóa khỏi diện cần điểm danh với lý do và audit; không xóa bản ghi đã có mặt.

### 4.3 Trạng thái điểm danh và đồng phục

| Nhóm | Giá trị | Ý nghĩa |
| --- | --- | --- |
| Buổi học | PLANNED, OPEN, CLOSED, CANCELLED | Chưa mở, đang ghi nhận, đã chốt, đã hủy |
| Điểm danh | UNMARKED | Chưa có kết luận; không được báo cáo là vắng |
| Điểm danh | PRESENT | Có mặt, có arrived_at; suy ra ON_TIME hoặc LATE |
| Điểm danh | ABSENT_EXCUSED | Vắng có phép; có lý do và người xác nhận |
| Điểm danh | ABSENT_UNEXCUSED | Vắng không phép; kết luận khi chốt hoặc xác nhận trực tiếp |
| Đi muộn | ON_TIME, LATE, NOT_APPLICABLE | Tính từ arrived_at và ngưỡng snapshot; vắng/chưa ghi nhận là NOT_APPLICABLE |
| Đồng phục | NOT_CHECKED | Có mặt nhưng chưa kiểm tra |
| Đồng phục | COMPLIANT | Nhân sự đã xác nhận đạt |
| Đồng phục | NON_COMPLIANT | Không đạt; có ít nhất một mã lý do |
| Đồng phục | EXEMPT | Được miễn; có lý do và người phê duyệt có quyền |
| Đồng phục | NOT_APPLICABLE | Không cần kiểm tra trong buổi hoặc học sinh vắng |

`arrival_status` được tính, không cho nhập tay. `uniform_status` độc lập với điểm danh: có mặt không mặc nhiên đạt đồng phục. `observed_uniform` có SHIRT, SPORTS, OTHER, UNKNOWN; OTHER phải mô tả ngắn. Không suy ra COMPLIANT chỉ vì loại thực tế bằng loại yêu cầu: còn có tiêu chí như bảng tên hoặc giày nếu nhà trường cấu hình.

Quy tắc hợp lệ:

- PRESENT bắt buộc có `arrived_at`; nếu chính sách yêu cầu kiểm tra, mặc định NOT_CHECKED.
- ABSENT_EXCUSED/ABSENT_UNEXCUSED/UNMARKED có `arrived_at = null`, `observed_uniform = null`, `uniform_status = NOT_APPLICABLE`.
- COMPLIANT/NON_COMPLIANT/EXEMPT chỉ áp dụng cho PRESENT khi `uniform_check_required = true`.
- Khi miễn kiểm tra cả buổi, mọi học sinh dùng NOT_APPLICABLE dù có mặt; không nhập kết quả kiểm tra.
- NON_COMPLIANT bắt buộc lý do; EXEMPT bắt buộc lý do miễn. Cho GVCN ghi miễn trong lớp mình theo A04, nếu nhà trường muốn chỉ giám thị được miễn thì thay ma trận trước khi triển khai.
- Đổi PRESENT thành vắng làm trống các trường đến trường/đồng phục hiện tại nhưng giữ bản trước trong audit. Đổi vắng thành PRESENT tạo đánh giá mới NOT_CHECKED hoặc NOT_APPLICABLE.
- Chốt buổi: UNMARKED chuyển ABSENT_UNEXCUSED sau màn hình xác nhận số lượng. NOT_CHECKED được giữ nguyên và hiển thị trong báo cáo, không tự chuyển đạt.

### 4.4 Học sinh, ảnh và lịch sử

- Mỗi học sinh có UUID nội bộ và `student_code` duy nhất trong trường; họ tên không duy nhất. Chuẩn hóa khoảng trắng, giữ dấu tiếng Việt.
- Lớp và khối lấy từ xếp lớp hiệu lực; không nhập tự do ba trường họ tên/lớp/khối thành một chuỗi.
- Một học sinh có tối đa một lớp chính tại một thời điểm trong cùng năm học. Các khoảng enrollment dùng `[effective_from, effective_to)`; ngày kết thúc không còn thuộc lớp cũ.
- Ngừng học/khóa hồ sơ không xóa lịch sử; đóng xếp lớp kể từ ngày hiệu lực. Hồ sơ có dữ liệu điểm danh không được xóa cứng trong giao diện thông thường.
- Ảnh hồ sơ không bắt buộc để điểm danh; thiếu ảnh vẫn dùng mã học sinh và lớp để đối chiếu.
- Chỉ chấp nhận JPEG/PNG/WebP đã kiểm tra nội dung, tối đa 5 MB và giới hạn số điểm ảnh; loại bỏ EXIF, tạo thumbnail. Không nhận SVG hoặc đường dẫn ảnh công khai tùy ý.
- Chưa tự động thu ảnh đồng phục hằng ngày trong MVP. Nếu mở rộng bằng chứng ảnh, thiết kế quyền, thời hạn lưu và quy trình tải riêng.

## 5. Workflow toàn hệ thống

### 5.1 Chuẩn bị đầu năm học

1. Quản trị kỹ thuật tạo tài khoản; giám thị hoặc người kiêm quyền cấp vai trò phù hợp.
2. Giám thị tạo năm học, khối, lớp và phân công GVCN.
3. GVCN nhập học sinh vào lớp, bổ sung ảnh; giám thị xử lý trùng mã và chuyển lớp.
4. GVCN lập lịch đi học tuần, giờ bắt đầu, ngưỡng muộn và đồng phục; giám thị quản lý ngày nghỉ toàn trường.
5. Hệ thống tạo buổi dự kiến trong 14 ngày tới; bản demo chạy management command trước khi trình diễn, bản nâng cao có job hằng đêm để giữ cửa sổ 14 ngày. Có thao tác tạo lại buổi thiếu, không ghi đè buổi đã mở/chốt.
6. Kiểm tra thiếu GVCN, thiếu lịch, enrollment chồng lấn và buổi không có đồng phục trước khi đưa vào sử dụng.

### 5.2 Một ngày đi học

```text
Lịch tuần + ngoại lệ + xếp lớp hiệu lực
                  |
                  v
           Buổi PLANNED
                  |
     Mở buổi, đóng băng lịch và roster
                  v
              Buổi OPEN
                  |
      Học sinh đăng nhập và quét QR động
                  |
                  v
      QR PENDING: lưu scanned_at của server
                  |
       Nhân sự đối chiếu học sinh tại chỗ
                  |
                  v
 PRESENT + arrived_at=scanned_at + ON_TIME/LATE
                  |
       Kiểm tra đồng phục trực tiếp
                  v
    COMPLIANT / NON_COMPLIANT / EXEMPT
                  |
     Xác nhận vắng + xem học sinh chưa xử lý
                  v
            Chốt buổi CLOSED
                  |
                  v
     Dashboard -> lọc báo cáo -> XLSX/CSV
```

### 5.3 Điều chỉnh sau chốt

GVCN mở bản ghi thuộc lớp, nhập giá trị đề xuất và lý do → backend tạo CorrectionRequest với phiên bản bản ghi hiện tại → giám thị xem trước/sau → duyệt trong transaction → ghi bản mới, tăng version, lưu audit và trạng thái yêu cầu. Nếu bản ghi đã thay đổi sau khi yêu cầu được tạo, báo xung đột, không tự áp dụng dữ liệu cũ. Giám thị sửa trực tiếp vẫn bắt buộc lý do và audit.

### 5.4 Báo cáo

Người dùng chọn ngày/lớp/khối/trạng thái → backend kiểm tra phạm vi và chuẩn hóa bộ lọc → tính dữ liệu từ roster/bản ghi/snapshot → hiển thị chi tiết và tổng hợp → tạo export job → worker tạo tệp từ snapshot dữ liệu cùng thời điểm → người dùng tải qua đường dẫn có quyền và thời hạn. Báo cáo ghi rõ có bao nhiêu buổi đang mở và số chưa ghi nhận.

## 6. Phân tích từng module và luồng dữ liệu

Mỗi module dưới đây nêu tác nhân, đầu vào, xử lý, dữ liệu đọc/ghi, đầu ra, lỗi và tiêu chí nghiệm thu. Các dữ liệu ghi cùng một nghiệp vụ phải hoàn tất cùng transaction, trừ xử lý tệp có cơ chế bù và retry.

### M01. Tài khoản, đăng nhập và phân quyền

**Tác nhân:** Tất cả người dùng; quản trị kỹ thuật tạo/vô hiệu hóa tài khoản.

**Đầu vào:** Tên đăng nhập/email, mật khẩu; gán vai trò; phạm vi trường; phân công GVCN từ M02.

**Workflow và dữ liệu:** Client gửi thông tin → server kiểm tra định dạng và giới hạn thử đăng nhập → đọc User và UserRole → kiểm tra hash mật khẩu, trạng thái → tạo phiên → giao diện nhận danh tính/quyền → mỗi API đọc lại trạng thái tài khoản và phạm vi lớp. Đăng xuất hoặc vô hiệu hóa tài khoản thu hồi phiên. Không cho đăng ký công khai.

**Đọc/ghi:** User, UserRole, AuthSession, TeacherAssignment; AuditLog ghi thay đổi tài khoản/quyền và sự kiện đăng nhập theo chính sách, không chứa mật khẩu/token.

**Đầu ra:** Danh tính, vai trò, lớp được quản lý, ngày hết phiên. Mật khẩu khởi tạo phải đổi ở lần đăng nhập đầu.

**Lỗi:** Sai thông tin trả lỗi chung; tài khoản khóa; phiên hết hạn; thiếu quyền trả 403 hoặc 404 với tài nguyên không được phép tiết lộ.

**Nghiệm thu:** GVCN không truy cập lớp khác bằng đổi URL/ID; admin kỹ thuật không xuất dữ liệu học sinh khi chưa có vai trò nghiệp vụ; vô hiệu hóa tài khoản chặn cả download đang chờ.

### M02. Năm học, khối, lớp và phân công GVCN

**Tác nhân:** Giám thị cấu hình; GVCN xem lớp mình.

**Đầu vào:** Tên/năm bắt đầu-kết thúc, khối, mã/tên lớp, giáo viên, khoảng hiệu lực.

**Workflow và dữ liệu:** Tạo SchoolYear → tạo Grade/Classroom → chọn giáo viên đang hoạt động → kiểm tra cùng trường và không chồng khoảng → ghi TeacherAssignment → kích hoạt lớp → quyền truy cập GVCN phản ánh phân công mới. Thay giáo viên đóng phân công cũ và mở mới trong một transaction.

**Đọc/ghi:** SchoolYear, Grade, Classroom, TeacherAssignment, User; AuditLog. Khối thuộc lớp; tên lớp duy nhất trong năm học của trường.

**Đầu ra:** Cây năm học → khối → lớp; GVCN hiện tại; lịch sử phân công.

**Lỗi:** Ngày không hợp lệ; phân công chồng lấn; giáo viên sai trường/đã khóa; lớp đang sử dụng không được xóa cứng.

**Nghiệm thu:** Không có hai GVCN hiệu lực cùng lúc; chuyển GVCN không mất lịch sử; lớp DRAFT không xuất hiện trong buổi đang điểm danh. Kết thúc năm học chuyển READ_ONLY, chỉ giám thị được sửa có audit.

### M03. Hồ sơ học sinh, ảnh và xếp lớp

**Tác nhân:** GVCN thêm/sửa trong lớp; giám thị chuyển lớp và ngừng học.

**Đầu vào:** Mã học sinh, họ tên, lớp, ngày nhập học, trạng thái; ảnh tùy chọn. Ngày sinh hoặc liên hệ phụ huynh không thuộc trường bắt buộc MVP.

**Workflow tạo:** Chọn lớp có quyền → validate mã/họ tên → transaction tạo Student và Enrollment → audit → trả hồ sơ cùng lớp/khối suy ra. Nếu mã tồn tại, trả 409 và hướng dẫn giám thị kiểm tra; không tạo học sinh mới để xử lý chuyển lớp.

**Workflow ảnh:** Tạo upload có quyền → upload vùng riêng tư → worker xác minh/chuẩn hóa ảnh → chỉ khi READY mới transaction gắn Asset vào Student → thay ảnh ghi audit → ảnh cũ xóa theo chính sách, không xóa nếu vẫn đang được tham chiếu. Upload lỗi không làm mất ảnh hiện tại. Job dọn tệp mồ côi chạy định kỳ.

**Workflow chuyển lớp:** Giám thị chọn ngày hiệu lực → kiểm tra enrollment và buổi đã mở → đóng enrollment cũ, tạo enrollment mới → chỉ buổi chưa mở lấy roster mới. Chuyển hồi tố ảnh hưởng buổi đã mở phải xử lý như chỉnh sửa roster từng buổi có lý do; không tự đổi lớp trong lịch sử.

**Đọc/ghi:** Student, Enrollment, Classroom, Grade, Asset, SessionRoster, AuditLog.

**Đầu ra:** Danh sách tìm theo mã/tên/lớp/khối, hồ sơ, ảnh có quyền, lịch sử xếp lớp.

**Lỗi:** Trùng mã; enrollment chồng lấn; ảnh sai loại/quá lớn; thiếu quyền lớp đích; ngừng học trước ngày nhập học.

**Nghiệm thu:** Hai học sinh trùng tên vẫn phân biệt bằng mã; ảnh lỗi không mất hồ sơ; ngừng học giữ báo cáo cũ; lớp/khối trong báo cáo lấy snapshot của buổi.

### M04. Lịch đi học và chính sách đồng phục

**Tác nhân:** GVCN quản lý lớp; giám thị quản lý toàn trường và lịch nghỉ.

**Đầu vào:** Thứ trong tuần, slot, giờ bắt đầu, grace_minutes, giờ đóng gợi ý, ngày hiệu lực, SHIRT/SPORTS, yêu cầu kiểm tra; ngoại lệ đổi giờ/đồng phục hoặc nghỉ.

**Workflow và dữ liệu:** Đọc lớp và quyền → lưu phiên bản ScheduleRule/UniformPolicy có khoảng hiệu lực → ghi ngoại lệ CalendarException khi có ngày đặc biệt → generator kết hợp ngày học/lịch/ngoại lệ → upsert buổi PLANNED chưa mở. Thứ tự ưu tiên: nghỉ toàn trường → nghỉ riêng lớp → ngoại lệ riêng lớp → ngoại lệ chung toàn trường → lịch tuần. Cùng một cấp/ngày/slot không được có ngoại lệ mâu thuẫn.

**Mở buổi:** Server đọc phiên bản lịch có hiệu lực và roster → ghi snapshot start_at, cutoff, uniform_policy, học sinh/lớp/khối → tạo AttendanceRecord UNMARKED cho mỗi roster → chuyển OPEN. Toàn bộ cùng transaction; mở lại yêu cầu lặp không tạo bản ghi thứ hai.

**Đọc/ghi:** ScheduleRule, UniformPolicy, CalendarException, SchoolSession, SessionRoster, AttendanceRecord, AuditLog.

**Đầu ra:** Lịch tuần và lịch ngày; trạng thái buổi; nhãn đồng phục phải mặc; danh sách cảnh báo thiếu cấu hình.

**Lỗi:** Lịch chồng lấn; cutoff sau thời điểm kết thúc; thiếu đồng phục khi yêu cầu kiểm tra; job chạy lặp; ngày nghỉ bị mở nhầm. Thiếu chính sách bắt buộc chặn mở buổi và hiển thị lỗi cấu hình.

**Nghiệm thu:** Thứ Hai mặc sơ mi, thứ Ba thể dục theo cấu hình; ngoại lệ ngày hội thay được lịch tuần; sửa chính sách hôm nay không đổi kết quả đã chốt. Hủy buổi đã mở có dữ liệu chỉ giám thị được làm với lý do, giữ dữ liệu và loại khỏi mẫu số báo cáo.

### M05. Điểm danh và thời gian đến

**Tác nhân:** GVCN trong lớp; giám thị toàn trường. Đây là luồng thủ công dự phòng hoặc ghi nhận vắng; luồng QR chính ở M10.

**Đầu vào:** session_id, roster_id, trạng thái, arrived_at, lý do vắng/hồi tố, expected_version, idempotency_key.

**Workflow và dữ liệu:** Chọn ngày/buổi → đọc SchoolSession và roster có quyền → chọn học sinh → server kiểm tra OPEN, enrollment snapshot và version → ghi AttendanceRecord → tính ON_TIME/LATE từ cutoff snapshot → ghi AttendanceEvent và AuditLog → trả bản ghi chuẩn từ server → giao diện cập nhật hàng và số lượng. Ghi thời gian hiện tại dùng giờ server.

**Thao tác hàng loạt:** Chọn nhiều học sinh, xem trước thời gian áp dụng và xác nhận. Không mặc định “tất cả có mặt” hoặc “tất cả đúng đồng phục”. Chỉ hỗ trợ tối đa 100 bản ghi cùng buổi mỗi request; một lỗi validation làm rollback toàn bộ lô và trả vị trí lỗi.

**Đọc/ghi:** SchoolSession, SessionRoster, AttendanceRecord, AttendanceEvent, AuditLog; không ghi lại lớp/khối hiện tại lên buổi cũ.

**Đầu ra:** Trạng thái có mặt/vắng/chưa ghi nhận, thời gian đến, số phút muộn, người ghi và version mới.

**Lỗi:** Buổi đã chốt/hủy; không thuộc roster; trùng request; cạnh tranh giữa hai người; thời gian không hợp lệ. Mạng lỗi giữ hàng ở trạng thái “chưa lưu”, không tô “đã điểm danh”. Khi retry dùng cùng idempotency_key.

**Nghiệm thu:** Một học sinh chỉ có một bản ghi trong một buổi; buổi sáng/chiều độc lập; nhập hồi tố có lý do; hai người không ghi đè âm thầm.

### M06. Kiểm tra đồng phục

**Tác nhân:** GVCN và giám thị.

**Đầu vào:** Bản ghi PRESENT, loại thực tế, kết luận, mã lý do, ghi chú, expected_version. Tiêu chí mẫu: WRONG_TYPE, MISSING_REQUIRED_ITEM, OTHER; nội dung cụ thể do trường cấu hình.

**Workflow và dữ liệu:** Đọc uniform snapshot của buổi → hiển thị chuẩn phải mặc → người kiểm tra đối chiếu thực tế → chọn COMPLIANT/NON_COMPLIANT/EXEMPT → server kiểm tra quy tắc, quyền và version → cập nhật AttendanceRecord, lưu AttendanceEvent/AuditLog → cập nhật tổng hợp.

**Đọc/ghi:** SchoolSession.uniform_policy_snapshot, UniformPolicy, AttendanceRecord, AttendanceEvent, AuditLog. Mã lý do và nhãn tại lúc kiểm tra được lưu snapshot để đổi danh mục không đổi nội dung báo cáo cũ.

**Đầu ra:** Yêu cầu/loại thực tế, kết luận, lý do, người kiểm tra, checked_at.

**Lỗi:** Chưa có mặt; buổi không yêu cầu kiểm tra; thiếu lý do vi phạm/miễn; kết luận không phù hợp trạng thái điểm danh. Nếu đồng thời điểm danh và kiểm tra trên một form, API lưu cả hai trong cùng transaction.

**Nghiệm thu:** Không dùng ảnh hồ sơ để tự kết luận; không biến NOT_CHECKED thành COMPLIANT; vắng không bị tính vi phạm đồng phục; OTHER có mô tả.

### M07. Chốt buổi, duyệt sửa và nhật ký

**Tác nhân:** GVCN chốt/gửi yêu cầu; giám thị duyệt/sửa/mở lại.

**Đầu vào:** session_id, session_version; yêu cầu thay đổi và lý do; target_version; quyết định duyệt/từ chối.

**Workflow chốt:** Xem số UNMARKED và NOT_CHECKED → xác nhận số chưa điểm danh sẽ chuyển vắng → server khóa buổi, kiểm tra session_version → đổi UNMARKED thành ABSENT_UNEXCUSED → ghi sự kiện cho bản ghi bị chuyển → chuyển CLOSED và audit → trả tổng hợp. Ghi điểm danh đồng thời phải dùng chung khóa buổi nên không lọt qua thời điểm chốt.

**Workflow sửa:** CorrectionRequest PENDING → giám thị đọc target_version → kiểm tra quyền và xung đột → APPROVED và sửa hoặc REJECTED với lý do. Không tự duyệt khi ghi mới; yêu cầu cũ không được ghi đè kết quả mới. Giám thị có thể mở lại CLOSED thành OPEN với lý do, rồi chốt lại; những lần chốt được lưu lịch sử.

**Đọc/ghi:** SchoolSession, AttendanceRecord, AttendanceEvent, CorrectionRequest, AuditLog.

**Đầu ra:** Bản ghi cuối cùng, trạng thái yêu cầu, trước/sau, người thao tác, lý do và thời gian.

**Lỗi:** Duyệt hai lần; buổi bị hủy; version không còn đúng; người gửi mất quyền; yêu cầu chứa trường không cho sửa. Khi người gửi mất quyền, giữ yêu cầu cho giám thị quyết định; người gửi không tải nội dung lớp cũ nữa.

**Nghiệm thu:** Có thể giải thích mọi thay đổi báo cáo; giáo viên không sửa trực tiếp CLOSED; chốt lặp không tăng số vắng hoặc tạo sự kiện thừa.

### M08. Dashboard, báo cáo và xuất dữ liệu

**Tác nhân:** GVCN xem/xuất lớp mình; giám thị theo toàn trường/khối/lớp.

**Đầu vào:** Khoảng ngày, năm học, khối/lớp, slot, mã học sinh, trạng thái, loại đồng phục; định dạng XLSX/CSV; có/không gồm buổi đang mở.

**Workflow xem:** Backend kiểm tra bộ lọc và quyền → lấy buổi không CANCELLED → join roster/attendance/snapshot → phân trang chi tiết, tổng hợp theo cùng bộ lọc → trả dữ liệu và generated_at. Mặc định dashboard ngày gồm OPEN/CLOSED; báo cáo đối soát mặc định chỉ CLOSED và cho bật OPEN có nhãn “tạm thời”.

**Workflow xuất:** POST tạo ExportJob theo quyền → lưu canonical_filters, allowed_class_ids và requested_by → worker kiểm tra quyền hiện tại rồi lấy snapshot trong một transaction đọc nhất quán → materialize ExportRow riêng tư → tính tổng hợp/tạo tệp từ các dòng này → READY → client tải qua endpoint xác thực. Nếu quyền thay đổi hoặc job không còn trong phạm vi, chuyển CANCELLED và không phát tệp.

**Đọc/ghi:** SchoolSession, SessionRoster, AttendanceRecord, ExportJob, ExportRow, Asset, AuditLog. MVP truy vấn database trực tiếp; chỉ thêm bảng tổng hợp/materialized view khi đo được nhu cầu.

**Đầu ra:** Dashboard, báo cáo chi tiết, tổng hợp theo lớp/khối/học sinh; tệp và metadata bộ lọc, generated_at, múi giờ, phiên bản báo cáo, trạng thái buổi.

**Lỗi:** Lọc lớp ngoài quyền; khoảng quá lớn; xử lý export lỗi; quyền bị thu hồi; tệp hết hạn. Tối đa 1 năm học; demo giới hạn 5.000 dòng đồng bộ, bản nâng cao giới hạn 100.000 dòng qua command xử lý job. Vượt giới hạn hướng dẫn chia theo tháng/lớp. Retry job nâng cao tối đa 3 lần, cùng snapshot nếu đã materialize xong.

**Nghiệm thu:** Tổng các nhóm bằng mẫu số; dashboard và export cùng thời điểm/bộ lọc có số giống nhau; tải tệp lớp khác bị chặn; không có URL công khai lâu dài.

### M09. Vận hành, cấu hình và chất lượng dữ liệu

**Tác nhân:** Quản trị kỹ thuật; giám thị xử lý lỗi nghiệp vụ.

**Đầu vào:** Múi giờ, ngưỡng mặc định, cửa sổ mở/chốt, danh mục lý do, chính sách lưu; lịch backup; kiểm tra sức khỏe hệ thống.

**Workflow và dữ liệu:** Cấu hình được version hóa → thay đổi có quyền và audit → lịch mới áp dụng phiên bản mới → job tìm buổi thiếu/roster sai/tệp mồ côi → cảnh báo đúng người → quản trị khôi phục từ backup trong môi trường riêng → kiểm tra số bản ghi và ảnh tham chiếu trước khi đưa vào sử dụng.

**Đọc/ghi:** SchoolSettings, JobRun, AuditLog; dữ liệu nghiệp vụ chỉ đọc cho kiểm tra. Sửa nghiệp vụ phải đi qua service module tương ứng.

**Đầu ra:** Trạng thái job, báo lỗi cấu hình, lịch sử backup/restore, số tệp chưa xử lý.

**Nghiệm thu:** Job sinh lịch chạy lại không nhân đôi; backup chứa database và kế hoạch phục hồi object storage; có diễn tập khôi phục; không ghi ảnh hoặc token vào log kỹ thuật.

### M10. QR học sinh và hàng đợi xác nhận

**Tác nhân:** Học sinh quét QR; GVCN/giám thị hiển thị QR, xác minh và kiểm tra đồng phục.

**Đầu vào:** Phiên học sinh đã đăng nhập; token QR do server cấp; idempotency_key; quyết định xác minh của nhân sự và expected_version của bản ghi.

**Thiết kế được đề xuất:** QR của từng buổi/lớp được hiển thị trên màn hình do nhân sự kiểm soát tại khu vực điểm danh. Token ngẫu nhiên tối thiểu 128 bit, đổi mỗi 30 giây, hết hạn sau 60 giây; lưu hash token và buổi liên quan. Không chứa họ tên, mật khẩu hoặc mã học sinh. Luồng trình duyệt có trang camera dùng HTTPS và phương án mở link QR từ ứng dụng camera; không đặt token trong log/analytics hoặc gửi sang dịch vụ QR bên ngoài.

**Workflow phát QR:** Nhân sự có quyền chọn buổi OPEN → server cấp QrChallenge có thời hạn → màn hình hiển thị mã → sau 30 giây lấy token mới. Một challenge dùng được cho nhiều học sinh thuộc roster; không đánh dấu “đã dùng” sau người quét đầu tiên. Mỗi học sinh chỉ tạo một yêu cầu đang chờ cho một buổi.

**Workflow quét:** Học sinh đăng nhập → cho phép camera hoặc mở link QR → POST token → server lấy student_id từ phiên, không từ request → kiểm tra token/hash/expiry, buổi OPEN, cửa sổ nhận quét, roster và tài khoản → ghi QrScan PENDING với scanned_at từ server → trả “Đã gửi, chờ giáo viên/giám thị xác nhận”. AttendanceRecord vẫn UNMARKED; QR_PENDING là trạng thái hàng đợi, không phải trạng thái có mặt.

**Workflow xác nhận:** Nhân sự xem hàng đợi tên/mã/ảnh/lớp/thời gian quét → đối chiếu học sinh tại chỗ → xác nhận danh tính, có thể nhập đồng phục cùng lần → transaction khóa buổi, AttendanceRecord và QrScan → kiểm tra phiên bản → đặt PRESENT, arrived_at = scanned_at, source = QR, verifier_id/verified_at → tính đi muộn → ghi kết quả đồng phục hoặc NOT_CHECKED → QrScan CONFIRMED → audit và event. Thời điểm xác nhận muộn không làm học sinh đi muộn nếu đã quét đúng giờ và được xác minh hợp lệ.

**Trạng thái QrScan:** PENDING, CONFIRMED, REJECTED, EXPIRED, SUPERSEDED. PENDING phải được xác nhận trong 15 phút sau quét và trước khi chốt buổi; quá 15 phút chuyển EXPIRED, có thể quét lại nếu buổi còn mở. API quét/xác nhận tự kiểm tra expires_at và chuyển bản hết hạn trong transaction, không phụ thuộc job đã chạy hay chưa. Nếu nhân sự xác nhận quá hạn, dùng luồng thủ công với lý do và thời gian đến đã kiểm tra. Quét lại khi PENDING trả bản đang chờ, giữ scanned_at đầu tiên; sau EXPIRED/REJECTED tạo lần thử mới, không khôi phục giờ cũ tự động. CONFIRMED trả trạng thái đã có mặt, không tạo điểm danh thứ hai.

**Xung đột:** Nếu nhân sự đã điểm danh thủ công PRESENT, quét trả “Đã ghi nhận” và không đổi arrived_at. Điểm danh thủ công khi có PENDING làm scan SUPERSEDED. Khi từ chối danh tính, QrScan REJECTED có lý do, AttendanceRecord giữ nguyên. Buổi CLOSED/CANCELLED không nhận hoặc xác nhận scan. Hủy/chốt buổi chuyển PENDING thành EXPIRED; màn hình chốt phải liệt kê các scan chưa xác minh trước khi chuyển UNMARKED thành vắng.

**Chống quét hộ:** Token ngắn hạn giảm việc tái sử dụng, nhưng không ngăn tuyệt đối chia sẻ QR/đăng nhập. Xác minh học sinh tại chỗ là bước bắt buộc để có mặt chính thức. IP/GPS không được xem là bằng chứng duy nhất. Rate limit theo tài khoản/IP, giữ token khỏi log và giới hạn thời gian quét. Không triển khai nhận diện khuôn mặt trong luồng này.

**Đọc/ghi:** AuthSession, Student, SchoolSession, SessionRoster, QrChallenge, QrScan; lúc xác nhận cập nhật AttendanceRecord, AttendanceEvent và AuditLog cùng transaction.

**Đầu ra:** Trang “buổi hôm nay” của học sinh; QR của nhân sự; hàng đợi kiểm tra; kết quả quét/xác nhận; lỗi hết hạn/sai lớp/ngoài giờ rõ ràng.

**Dự phòng:** Không có điện thoại, camera không được cấp quyền, QR hết hạn hoặc mạng hỏng → nhân sự thao tác M05 khi có kết nối. Khi mất mạng toàn hệ thống dùng danh sách giấy, nhập hồi tố với lý do; MVP không tuyên bố hỗ trợ offline tự đồng bộ.

**Nghiệm thu:** Scan QR đúng giờ và xác nhận sau ngưỡng vẫn ON_TIME; scan sai lớp bị chặn; scan hết hạn không được nhận; học sinh A không gửi student_id B để điểm danh hộ; nhiều học sinh dùng chung challenge vẫn hoạt động; QR chưa xác minh không làm tăng số có mặt và không tự đạt đồng phục.

## 7. Kiến trúc và trách nhiệm thành phần

### 7.1 Stack Python phù hợp K12

| Thành phần | Lựa chọn | Cách dùng trong dự án |
| --- | --- | --- |
| Ngôn ngữ và web backend | Python 3.12 + Django 5.2 | Model, form, view, service và toàn bộ quy tắc nghiệp vụ bằng Python |
| Giao diện | Django Templates + HTML/CSS + Bootstrap | Render trang ngay trong Django, dùng form chuẩn cho quản lý hồ sơ/lịch/báo cáo |
| JavaScript cần thiết | JavaScript thuần + html5-qrcode | Mở camera/đọc QR, gọi fetch, polling hàng đợi; không quyết định quyền hoặc kết quả điểm danh |
| Database học tập/demo | SQLite | Dễ setup, ít người thao tác, dữ liệu giả; không dùng làm bằng chứng đạt tải toàn trường |
| Database nâng cao | PostgreSQL qua Django ORM | Kiểm chứng khóa hàng, thao tác đồng thời và vận hành nhiều người |
| Tài khoản và phân quyền | Django Auth + Groups + session | Custom User từ migration đầu tiên, nhóm vai trò và kiểm tra quyền theo lớp tại service/view |
| Công cụ quản trị | Django Admin | Tạo tài khoản/danh mục nhanh; giới hạn queryset và quyền theo vai trò; không cho sửa attendance trực tiếp để bỏ qua audit |
| Ảnh | Pillow + Django storage | Kiểm tra/chuẩn hóa ảnh; thư mục private ngoài static; tải qua view kiểm tra quyền |
| Tạo QR | qrcode của Python | Tạo ảnh QR tại server từ token ngẫu nhiên; giữ cơ chế hash/hết hạn |
| Báo cáo | openpyxl + csv chuẩn Python | XLSX/CSV; không cần pandas để thực hiện các bảng báo cáo MVP |
| JSON API tối thiểu | Django views + JsonResponse | Hợp đồng mục 9 cho quét/xác nhận/polling; validate bằng form/service; DRF chỉ bổ sung khi cần API cho ứng dụng khác |
| Job nâng cao | Django management commands | Sinh buổi, hết hạn scan, export lớn, dọn tệp; chạy thủ công khi demo hoặc qua scheduler khi vận hành |
| Kiểm chứng | Django TestCase/TransactionTestCase | Test model, quyền và API với test client; concurrency chạy trên PostgreSQL |

Django 5.2 hỗ trợ Python 3.12 và dùng SQLite mặc định; PostgreSQL là lựa chọn được tài liệu Django khuyến nghị cho production. Nguồn: https://docs.djangoproject.com/en/5.2/faq/install/. Python 3.9 đang có trong workspace chỉ phục vụ script tạo tài liệu, không phải phiên bản được chọn cho ứng dụng tương lai.

Camera quét QR là chức năng trong trình duyệt nên cần một phần JavaScript; Python đảm nhiệm sinh mã, xác minh token, tài khoản, thời gian, điểm danh và báo cáo. Tham khảo thư viện quét tại https://scanapp.org/html5-qrcode-docs/; khóa bản thư viện và lưu bản dùng cho demo trong static thay vì phụ thuộc CDN tại địa điểm thi.

### 7.2 Hai mức triển khai

**Bản học tập/đi thi — mặc định:** Một project Django, SQLite, file ảnh/báo cáo riêng tư trên máy demo, dữ liệu giả 2–5 lớp và 50–200 học sinh. Xử lý ảnh ngay trong request; xuất tối đa 5.000 dòng đồng bộ qua cùng export service, vẫn tạo ExportJob/metadata và kiểm tra quyền tải. Sinh lịch bằng management command trước demo hoặc khi người dùng yêu cầu; API tự kiểm tra expiry QR nên không cần worker luôn chạy. Chỉ trình bày đã đạt các ca nghiệm thu thực sự kiểm chứng được.

**Bản nâng cao/thử nghiệm tại trường:** Cùng code Django nhưng dùng PostgreSQL, web server và HTTPS phù hợp, management command xử lý job trong tiến trình riêng có scheduler, có thể dùng object storage riêng tư. Bổ sung kiểm chứng concurrency, export 100.000 dòng và mục tiêu tải/backup mục 13. Không bắt buộc Celery, Redis, Docker hoặc microservices cho bài thi.

Các trạng thái và kiểm tra quyền giữ nguyên ở cả hai mức. Bản demo không nhận export lớn rồi để job QUEUED mãi: vượt 5.000 dòng trả lỗi có hướng dẫn chia khoảng ngày; bản nâng cao mới cho nhận tới 100.000 dòng.

### 7.3 Trách nhiệm thành phần

```text
Web nhân sự                 Web học sinh
   | hồ sơ/lịch/xác nhận       | đăng nhập/quét QR
   +--------------------------+
                  |
       Django URLs + Views + Auth
                  |
       Django Templates / JSON views
   auth | academics | students | schedules
   attendance | uniforms | qr | corrections
              reports | audit
       |                 |                |
       v                 v                v
 SQLite hoặc       Django storage    Python commands
 PostgreSQL        tệp riêng tư      khi cần chạy job
```

- Frontend không quyết định quyền, đồng hồ chính thức hoặc trạng thái đi muộn; hiển thị dữ liệu server trả về.
- Django views xử lý request/response; Forms và service Python validate nghiệp vụ; Django ORM thực hiện truy vấn. Các app giao tiếp qua service rõ trách nhiệm, không để view cập nhật nhiều bảng tùy ý.
- Attendance service là điểm ghi duy nhất cho kết quả; QR service chuyển dữ liệu qua attendance service lúc xác minh; Uniform service validate kết quả cùng transaction.
- Database là nguồn dữ liệu chuẩn; Django models/migrations khai báo unique constraint, foreign key và transaction. PostgreSQL dùng cho bản nâng cao và kiểm chứng đồng thời; SQLite chỉ dùng bản học tập/demo nhỏ.
- Django storage chỉ chứa tệp; quyền xác định ở database/service. Bản demo dùng thư mục private ngoài static, không cấu hình MEDIA_URL công khai cho ảnh học sinh; bản nâng cao có thể thay storage backend.
- Worker trong các luồng mô tả ở tài liệu là management command Python xử lý job database trong bản nâng cao. Bản demo gọi cùng service đồng bộ cho ảnh/export nhỏ; không cần thiết lập queue. Export lớn có lease, retry và materialize để không trộn thời điểm dữ liệu.
- Hàng đợi xác nhận cập nhật bằng polling 5 giây khi đang mở màn hình, dừng khi tab ẩn; có thể chuyển SSE sau đo tải. Sau thao tác của mình, UI cập nhật ngay bằng response server.
- Chỉ deploy vào môi trường thử nghiệm/vận hành khi có yêu cầu riêng; bản này không tạo tài khoản cloud hoặc hạ tầng.

## 8. Mô hình dữ liệu và quan hệ

### 8.1 Nguyên tắc chung

ID dùng Django UUIDField; mọi bảng nghiệp vụ có school_id, created_at, updated_at khi phù hợp. Thời điểm dùng DateTimeField với USE_TZ=True; ngày nghiệp vụ dùng DateField. Khóa ngoại quan trọng kiểm tra cùng school_id qua service và constraint phù hợp. Danh mục dùng TextChoices hoặc bảng mã; không dùng chuỗi tiếng Việt làm khóa chương trình. Bản PostgreSQL bổ sung ràng buộc không chồng khoảng ở database; bản SQLite kiểm tra khoảng hiệu lực trong service và chỉ dùng cho demo ít thao tác ghi.

### 8.2 Data dictionary

Đây là các thực thể nghiệp vụ, không yêu cầu viết lại những phần Django có sẵn: User mở rộng AbstractUser; UserRole ánh xạ Groups; AuthSession dùng Django session kèm cơ chế thu hồi/theo dõi cần thiết. Mỗi thực thể còn lại ánh xạ thành Django model trong app tương ứng. Không tạo một hệ thống hash mật khẩu hoặc auth session riêng cạnh Django Auth.

| Bảng | Trường chính | Ràng buộc / trách nhiệm |
| --- | --- | --- |
| School | id, name, timezone | Một trường trong MVP; timezone mặc định Asia/Ho_Chi_Minh |
| SchoolSettings | school_id, version, config_json, effective_at | Ngưỡng mặc định, cửa sổ nhận quét/điểm danh, thời hạn lưu; thay đổi có audit |
| User | id, school_id, username, password_hash, status, must_change_password, student_id? | username duy nhất trong trường; STUDENT liên kết một hồ sơ; không lưu mật khẩu rõ |
| UserRole | user_id, role | HOMEROOM_TEACHER, SUPERVISOR, TECH_ADMIN, STUDENT; cấp/thu hồi có audit |
| AuthSession | id, user_id, token_hash, expires_at, revoked_at | Phiên có thể thu hồi; không lưu token rõ |
| SchoolYear | id, school_id, name, start_date, end_date, status | DRAFT/ACTIVE/READ_ONLY; ngày hợp lệ |
| Grade | id, school_id, code, name | code duy nhất trong trường |
| Classroom | id, school_id, school_year_id, grade_id, code, name, status | code duy nhất trong năm học; khối lấy qua grade_id |
| TeacherAssignment | id, school_id, class_id, teacher_id, effective_from, effective_to | Khoảng timestamp [from,to), không chồng trong cùng lớp; giáo viên có vai trò hợp lệ |
| Student | id, school_id, student_code, full_name, status, photo_asset_id? | student_code duy nhất; không xóa cứng khi có lịch sử |
| Enrollment | id, school_id, student_id, class_id, school_year_id, effective_from, effective_to | Không chồng lớp chính; khoảng [from,to); to null khi chưa kết thúc |
| Asset | id, school_id, storage_key, kind, mime, byte_size, status, owner_id, expires_at? | PROFILE_PHOTO/EXPORT; PRIVATE; UPLOADING/PROCESSING/READY/FAILED |
| UniformPolicy | id, school_id, class_id, version, required_type, check_required, criteria_json, effective_from, effective_to | SHIRT/SPORTS; tiêu chí có mã và nhãn; được snapshot vào buổi |
| ScheduleRule | id, school_id, class_id, weekday, slot, local_start_time, grace_minutes, local_close_time, uniform_policy_id, effective_from, effective_to | Không chồng lịch có hiệu lực cùng lớp/thứ/slot |
| CalendarException | id, school_id, class_id?, school_date, slot, kind, overrides_json, reason | CANCEL/OVERRIDE; class_id null là toàn trường; chống ngoại lệ trùng cấp |
| SchoolSession | id, school_id, class_id, school_date, slot, status, start_at, late_cutoff_at, close_at, scan_open_at, scan_close_at, uniform_policy_snapshot, class_snapshot, version, opened_at, closed_at | Unique lớp/ngày/slot; snapshot đóng băng lúc OPEN |
| SessionRoster | id, school_id, session_id, student_id, enrollment_id, student_code_snapshot, full_name_snapshot, class_code_snapshot, grade_code_snapshot, included, adjustment_reason? | Unique session/student; included=false chỉ loại có lý do, giữ lịch sử |
| AttendanceRecord | id, school_id, roster_id, status, arrived_at?, source?, absence_reason?, observed_uniform?, uniform_status, reason_codes_snapshot, uniform_note?, checked_by?, checked_at?, verified_by?, verified_at?, version, updated_by | Unique roster_id; bất biến theo mục 4.3; arrival_status tính từ thời gian; absence_reason khác lý do sửa lưu trong event |
| AttendanceEvent | id, school_id, attendance_id, type, before_json, after_json, actor_id, recorded_at, reason?, request_id | Lịch sử nghiệp vụ append-only; không chứa token/ảnh/mật khẩu |
| QrChallenge | id, school_id, session_id, token_hash, issued_by, issued_at, expires_at, revoked_at? | Token dùng chung cho roster; chỉ nhận khi buổi OPEN |
| QrScan | id, school_id, session_id, roster_id, challenge_id, student_user_id, scanned_at, expires_at, status, resolved_by?, resolved_at?, reason?, version | Chỉ một PENDING trên roster; CONFIRMED liên kết bản ghi chính thức; các lần thử giữ lịch sử |
| IdempotencyRequest | id, school_id, actor_id, operation, key, payload_hash, status, response_json, expires_at | Unique actor/operation/key; giữ ít nhất 24 giờ; key cũ khác payload trả 409 |
| CorrectionRequest | id, school_id, attendance_id, target_version, proposed_changes_json, reason, status, requested_by, reviewed_by?, reviewed_at?, review_reason? | PENDING/APPROVED/REJECTED/CANCELLED; duyệt một lần |
| AuditLog | id, school_id, actor_id, action, entity_type, entity_id, before_json, after_json, reason?, request_id, recorded_at | Nhật ký quyền, lịch, roster, export; chỉ backend append |
| ExportJob | id, school_id, requested_by, canonical_filters, allowed_class_ids, format, status, snapshot_at?, row_count?, asset_id?, error_code?, attempt, expires_at | QUEUED/RUNNING/READY/FAILED/CANCELLED/EXPIRED; kiểm tra quyền lúc chạy và tải |
| ExportRow | id, school_id, export_job_id, ordinal, row_json | Snapshot chỉ đọc cho worker; xóa cùng job theo thời hạn |
| JobRun | id, school_id, type, unique_key, status, lease_until, attempt, last_error | Chống job lịch chạy lặp, hỗ trợ retry và quan sát |

### 8.3 Quan hệ quan trọng

```text
SchoolYear -> Classroom -> TeacherAssignment -> User (GVCN)
Grade      -> Classroom
Student    -> Enrollment -> Classroom
Classroom  -> ScheduleRule -> UniformPolicy
Classroom  -> SchoolSession -> SessionRoster -> Student
SessionRoster -> AttendanceRecord -> AttendanceEvent
AttendanceRecord -> CorrectionRequest
SchoolSession -> QrChallenge -> QrScan -> SessionRoster
Student -> User (STUDENT)
ExportJob -> ExportRow; ExportJob -> Asset
Student -> Asset (ảnh hồ sơ)
```

### 8.4 Snapshot và dữ liệu hiện tại

| Dữ liệu | Khi nào chụp snapshot | Vì sao |
| --- | --- | --- |
| Lớp, khối, mã/tên học sinh trong roster | Khi mở buổi | Chuyển lớp/đổi tên không làm biến đổi báo cáo lịch sử |
| Giờ bắt đầu, ngưỡng muộn, đồng phục/tiêu chí | Khi mở buổi | Sửa lịch/chính sách không đổi kết luận buổi trước |
| Lý do vi phạm và nhãn | Khi lưu kết quả kiểm tra | Đổi tên danh mục không mất ý nghĩa cũ |
| Dòng báo cáo và metadata | Khi worker materialize export | Tránh từng trang xuất từ một thời điểm khác nhau |

Đổi tên/mã trong hồ sơ chỉ ảnh hưởng buổi mới. Nếu buổi cũ sai thông tin cần sửa roster snapshot có audit bởi giám thị, không tự đồng bộ toàn bộ lịch sử. Ảnh hiển thị trong hàng đợi là ảnh hiện tại có quyền, không phải bằng chứng học sinh đã mặc gì tại buổi cũ.

## 9. Hợp đồng API đề xuất cho agent code

### 9.1 Quy ước

Giao diện quản lý thông thường dùng Django HTML views/Forms; không cần xây SPA để gọi toàn bộ endpoint bên dưới. Bảng endpoint là hợp đồng nghiệp vụ, triển khai JSON views ở các điểm cần camera/polling/fetch; HTML view và JSON view cùng gọi service Python. URL trang HTML tách khỏi `/api/v1`.

- Base path `/api/v1`; JSON UTF-8; timestamp ISO 8601 có timezone; `school_date` YYYY-MM-DD.
- Backend suy ra school_id và student_id của người quét từ phiên; không tin giá trị do client tự khai.
- Ghi attendance/QR/correction cần `Idempotency-Key`; cập nhật cần `expected_version`. Không trộn retry với thao tác mới.
- Phân trang danh sách bằng cursor hoặc page/page_size, tối đa 100 dòng/trang; danh sách hàng đợi QR sắp scanned_at rồi id.
- Cookie phiên HttpOnly/Secure và cơ chế chống CSRF cho request thay đổi; không lưu bearer token dài hạn trong localStorage.
- Lỗi có dạng `{code, message, details, request_id}`; details không tiết lộ thông tin ngoài quyền.
- 400 payload sai; 401 chưa đăng nhập; 403 thiếu quyền; 404 không tồn tại/không được tiết lộ; 409 trùng/version/sai trạng thái; 422 quy tắc nghiệp vụ; 429 giới hạn tần suất; 503 tạm thời.

### 9.2 Nhóm endpoint

| Module | Method / endpoint | Ý nghĩa / quyền |
| --- | --- | --- |
| M01 | POST /auth/login; POST /auth/logout; GET /auth/me; POST /auth/change-password | Đăng nhập, đăng xuất, danh tính, đổi mật khẩu |
| M01 | POST /users; PATCH /users/:id; POST /users/:id/reset-password | TECH_ADMIN; student_id chỉ được gán hợp lệ |
| M02 | GET/POST /school-years; GET/POST /grades; GET/POST /classes | Đọc theo quyền; ghi SUPERVISOR |
| M02 | POST /classes/:id/teacher-assignments | SUPERVISOR, chuyển phân công cùng transaction |
| M03 | GET/POST /students; GET/PATCH /students/:id | Nhân sự trong phạm vi |
| M03 | POST /students/:id/transfers; POST /students/:id/deactivate | SUPERVISOR và lý do |
| M03 | POST /students/:id/photo-uploads; POST /photo-uploads/:id/complete; GET /students/:id/photo | Upload xác minh và tải ảnh có quyền |
| M04 | GET/POST /classes/:id/schedule-rules; POST /calendar-exceptions | GVCN lớp mình hoặc SUPERVISOR |
| M04 | GET /sessions; GET /sessions/:id; POST /sessions/:id/open; POST /sessions/:id/cancel | Mở có quyền; hủy có dữ liệu chỉ SUPERVISOR |
| M05 | GET /sessions/:id/roster; PATCH /attendance/:id; POST /sessions/:id/attendance-batch | Thủ công/vắng; cùng transaction cho đồng phục khi có |
| M06 | PATCH /attendance/:id/uniform | Validate đồng phục; cùng version của AttendanceRecord |
| M07 | POST /sessions/:id/close; POST /sessions/:id/reopen | Chốt có quyền; mở lại chỉ SUPERVISOR |
| M07 | POST /attendance/:id/corrections; GET /corrections; POST /corrections/:id/review | Gửi yêu cầu, xem theo quyền, giám thị duyệt |
| M07 | GET /attendance/:id/history; GET /audit-logs | Nhân sự theo phạm vi |
| M08 | GET /reports/dashboard; GET /reports/attendance | Dữ liệu/tổng hợp với canonical_filters |
| M08 | POST /exports; GET /exports/:id; GET /exports/:id/download | Tạo, xem tiến trình, download có quyền |
| M09 | GET/PATCH /settings; GET /jobs/health | TECH_ADMIN; config nghiệp vụ có thể cần SUPERVISOR |
| M10 | GET /me/today-sessions; GET /me/scan-status | STUDENT, chỉ bản thân |
| M10 | POST /sessions/:id/qr-challenges | Nhân sự có quyền, buổi OPEN, token trả chỉ một lần |
| M10 | POST /qr-scans | STUDENT; token QR, không nhận student_id |
| M10 | GET /sessions/:id/qr-scans; POST /qr-scans/:id/confirm; POST /qr-scans/:id/reject | Nhân sự có quyền; xác nhận danh tính, kèm đồng phục tùy chọn |

### 9.3 Ví dụ xác nhận QR và đồng phục trong một giao dịch

Các UUID bên dưới chỉ là dữ liệu minh họa. `recorded_at` và `verified_at` do server tạo.

```json
{
  "expected_attendance_version": 0,
  "expected_scan_version": 0,
  "identity_confirmed": true,
  "uniform": {
    "observed_uniform": "SPORTS",
    "uniform_status": "NON_COMPLIANT",
    "reason_codes": ["WRONG_TYPE"],
    "note": "Buổi này yêu cầu sơ mi"
  }
}
```

Response:

```json
{
  "attendance_id": "40b8e054-f2e4-450f-8e30-bc1b2c953101",
  "status": "PRESENT",
  "source": "QR",
  "arrived_at": "2026-10-08T00:04:00Z",
  "arrival_status": "ON_TIME",
  "late_minutes": 0,
  "uniform_status": "NON_COMPLIANT",
  "verified_at": "2026-10-08T00:08:00Z",
  "scan_status": "CONFIRMED",
  "version": 1
}
```

Ví dụ áp dụng start 07:00, grace 5 phút giờ Việt Nam: quét 07:04, xác nhận 07:08 vẫn đúng giờ. Không cho client gửi `arrived_at` vào endpoint xác nhận QR; muốn sửa giờ phải đi qua nghiệp vụ chỉnh sửa có lý do.

### 9.4 Ví dụ sửa thủ công có kiểm tra phiên bản

```json
{
  "expected_version": 1,
  "status": "PRESENT",
  "source": "MANUAL",
  "arrived_at": "2026-10-08T00:10:00Z",
  "reason": "Không có điện thoại; giám thị ghi nhận tại cổng"
}
```

Nếu version thực tế là 2, trả 409 `VERSION_CONFLICT` cùng hướng dẫn tải lại; không ghi dữ liệu, không tạo audit của một thay đổi chưa xảy ra. Replay Idempotency-Key cùng payload trả response gốc; cùng key khác payload trả 409 `IDEMPOTENCY_PAYLOAD_MISMATCH`.

DTO điểm danh vắng nhận `absence_reason` cho lý do nghỉ; `reason` trong thao tác chỉnh sửa/hồi tố là lý do mutation và được lưu AttendanceEvent/AuditLog. `uniform.note` trên API được ánh xạ vào `uniform_note` của bản ghi; lý do miễn đồng phục nằm trong payload uniform và snapshot lý do, không ghi nhầm vào absence_reason. Nguồn MANUAL của endpoint thủ công được server gán/kiểm tra; client không được tự nhận source QR.

## 10. Tính nhất quán, xử lý lỗi và luồng transaction

### 10.1 Một lần xác nhận điểm danh

Luồng khóa hàng dưới đây dành cho PostgreSQL: dùng `transaction.atomic()` và `select_for_update()` trong service. SQLite không thực thi khóa hàng qua `select_for_update()`; bản demo giữ atomic, version check/conditional update và giới hạn ghi đồng thời, xử lý database busy bằng báo chưa lưu/retry. Không đánh dấu AC19/AC21 và mục tiêu tải đã đạt chỉ vì test SQLite chạy qua. Nguồn: https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update.

1. Xác thực tài khoản, quyền trường/lớp và trạng thái đang hoạt động.
2. Kiểm tra Idempotency-Key và hash payload; nếu request đã hoàn tất, trả kết quả cũ.
3. Mở transaction; khóa SchoolSession trước, AttendanceRecord sau, QrScan cuối nếu có. Tất cả thao tác chốt/ghi dùng thứ tự khóa này để tránh deadlock.
4. Kiểm tra buổi OPEN, roster included, version và scan còn PENDING/chưa hết hạn.
5. Validate điểm danh/đồng phục; cập nhật bản ghi và tăng version; tăng session.version cho mỗi mutation ảnh hưởng roster/attendance để chốt nhận biết dữ liệu đã thay đổi.
6. Ghi AttendanceEvent, AuditLog và response idempotency cùng transaction.
7. Commit; gửi response. Nếu transaction thất bại, không đánh dấu thành công ở client.

Thay đồng phục cũng khóa session và attendance để không chạy sau khi chốt. Chốt khóa session rồi các attendance theo ID cố định. Giám thị sửa CLOSED có thể cập nhật trực tiếp qua service có quyền và lý do, vẫn tăng version/sự kiện; không tự chuyển buổi OPEN.

### 10.2 Mạng và cạnh tranh

- Mất response sau khi server đã lưu: retry cùng key trả kết quả gốc, không thêm lượt điểm danh.
- Hai người sửa cùng hàng: thao tác đầu thành công; thao tác sau nhận 409, hiển thị người/thời điểm thay đổi trong phạm vi quyền và yêu cầu đọc lại.
- Camera hoặc QR thất bại: thông báo cụ thể, đổi token mới hoặc điểm danh thủ công; không bỏ qua bước xác minh.
- Hai scan cùng học sinh đến đồng thời: partial unique index cho PENDING, transaction xử lý conflict bằng trả scan đang chờ. Không dùng unique(session,student) cho toàn lịch sử scan vì cần cho quét lại sau EXPIRED.
- Export/ảnh lỗi: retry có giới hạn, lưu trạng thái FAILED và thông báo có request_id; không để tệp lỗi thành READY.
- Không tin đồng hồ client; các timeout và expiry dùng server.

### 10.3 Hủy, mở lại và chỉnh lịch

Hủy buổi giữ roster/attendance/audit, thu hồi challenge và pending scan; báo cáo loại toàn bộ buổi CANCELLED. Khôi phục buổi hủy chỉ giám thị và lý do; buổi từng có roster quay về OPEN giữ snapshot, buổi chưa mở quay về PLANNED. Các scan EXPIRED không tự sống lại. Sửa giờ/đồng phục của buổi đã mở là thao tác riêng của giám thị: xem trước bản ghi bị ảnh hưởng, cập nhật snapshot và tính lại arrival_status theo giờ mới, audit rõ tác động; không âm thầm chạy khi sửa lịch tuần.

## 11. Báo cáo, mẫu xuất và công thức

### 11.1 Mẫu số

Đơn vị thống kê là “học sinh-buổi”, không phải số học sinh duy nhất. Chỉ lấy SessionRoster `included=true` thuộc buổi phù hợp bộ lọc và không CANCELLED. Buổi PLANNED chỉ phục vụ kế hoạch, không nằm trong kết quả thực tế.

```text
N_expected = số roster thuộc OPEN/CLOSED theo bộ lọc
N_present = số PRESENT
N_excused = số ABSENT_EXCUSED
N_unexcused = số ABSENT_UNEXCUSED
N_unmarked = số UNMARKED

N_expected = N_present + N_excused + N_unexcused + N_unmarked
N_present = N_on_time + N_late
Tỷ lệ có mặt = N_present / N_expected * 100%
Tỷ lệ đi muộn = N_late / N_present * 100%

N_present = N_compliant + N_non_compliant + N_exempt
            + N_not_checked + N_uniform_not_applicable
N_checked = N_compliant + N_non_compliant
Tỷ lệ vi phạm trong số đã kiểm tra = N_non_compliant / N_checked * 100%
Độ bao phủ kiểm tra = N_checked / (N_checked + N_not_checked) * 100%
```

Nếu mẫu số bằng 0 hiển thị “—”, không ghi 0% để tránh hiểu nhầm. Độ bao phủ loại EXEMPT và NOT_APPLICABLE. QR PENDING/EXPIRED/REJECTED không phải PRESENT; có chỉ số hàng đợi riêng, không cộng vào tổng trạng thái điểm danh. ABSENT không nằm trong tổng kiểm tra đồng phục.

### 11.2 Ví dụ kiểm tra số liệu

Buổi lớp có 40 học sinh: 34 PRESENT (30 đúng giờ, 4 muộn), 2 vắng có phép, 1 vắng không phép, 3 chưa ghi nhận. Trong 34 có mặt: 25 đạt, 4 vi phạm, 2 miễn, 3 chưa kiểm tra. Khi đó có mặt 85%; muộn 4/34 = 11,76%; vi phạm trong số đã kiểm tra 4/29 = 13,79%; độ bao phủ 29/32 = 90,63%. Nếu 2 trong 3 chưa ghi nhận đã quét QR nhưng chưa xác minh, số có mặt vẫn là 34. Khi chốt, 3 chưa ghi nhận chuyển vắng không phép, có mặt vẫn 34.

### 11.3 Cột báo cáo chi tiết

| Nhóm | Cột |
| --- | --- |
| Buổi | Ngày học, năm học, buổi, trạng thái buổi, giờ chuẩn, ngưỡng muộn |
| Học sinh | Mã, họ tên snapshot, lớp snapshot, khối snapshot |
| Điểm danh | Trạng thái, nguồn QR/thủ công, giờ quét nếu có, giờ đến chính thức, giờ xác minh, số phút muộn, lý do vắng |
| Đồng phục | Loại yêu cầu, loại thực tế, kết quả, mã/nhãn lý do, ghi chú, người kiểm tra, giờ kiểm tra |
| Truy vết | Người cập nhật, thời điểm cập nhật, phiên bản bản ghi |

`late_minutes = ceil(max(0, arrived_at - late_cutoff_at) / 60 giây)`; trạng thái LATE vẫn quyết định bằng so sánh thời điểm chính xác. Ví dụ muộn 1 giây hiển thị 1 phút; cần chú thích cách làm tròn trong báo cáo.

### 11.4 Tệp xuất

- XLSX gồm sheet `Chi_tiet`, `Tong_hop`, `Thong_tin_bao_cao`; freeze header, bộ lọc, định dạng ngày/giờ và trạng thái dễ đọc; không kèm ảnh hồ sơ mặc định.
- CSV UTF-8 có BOM, header thống nhất, quote/escape đúng; một hàng trên mỗi học sinh-buổi. Metadata đi kèm trong thông tin job và tên tệp, không chen dòng metadata vào bảng CSV.
- Nội dung người dùng bắt đầu bằng `=`, `+`, `-`, `@` được ghi dưới dạng text an toàn; bảo vệ spreadsheet formula injection.
- Tên tệp ví dụ `diem_danh_10A1_2026-10-01_2026-10-31.xlsx`; không đưa thông tin học sinh vào URL tải.
- Tệp mặc định hết hạn sau 24 giờ, link tải ngắn tối đa 5 phút; giá trị này là đề xuất cấu hình. Endpoint tải kiểm tra quyền; file mở lại sau khi tải về nằm ngoài khả năng thu hồi của ứng dụng.
- Mỗi export ghi snapshot_at, timezone, bộ lọc, người yêu cầu, phạm vi, row_count và có bao gồm OPEN hay không.

## 12. Màn hình và trải nghiệm thao tác

| Màn hình | Người dùng | Nội dung / thao tác chính |
| --- | --- | --- |
| Đăng nhập / đổi mật khẩu | Tất cả | Tài khoản, mật khẩu, lỗi chung; đổi mật khẩu ban đầu |
| Buổi hôm nay / quét QR | Học sinh | Tên/mã bản thân, lớp/buổi, quét, trạng thái gửi/chờ/xác nhận, hướng dẫn gặp giám thị khi lỗi |
| Dashboard | Nhân sự | Ngày/buổi, có mặt/vắng/muộn, đồng phục, hàng đợi QR, lớp chưa chốt |
| Khối/lớp/GVCN | Giám thị | Cây tổ chức, phân công, cảnh báo thiếu GVCN |
| Danh sách và hồ sơ học sinh | Nhân sự | Mã, tên, ảnh, lớp/khối; thêm/sửa, lịch sử, chuyển lớp theo quyền |
| Lịch và đồng phục | Nhân sự | Lịch tuần, lịch ngày, giờ/ngưỡng, loại đồng phục, ngoại lệ |
| QR tại điểm danh | Nhân sự | Chọn lớp/buổi, mã động, thời hạn, không hiển thị danh sách học sinh ra màn hình công cộng |
| Hàng đợi xác nhận | Nhân sự | Tên/mã/ảnh, giờ quét, xác minh, đồng phục trong cùng form, từ chối có lý do |
| Điểm danh lớp | Nhân sự | Danh sách roster, trạng thái, giờ đến, đồng phục; tìm nhanh; fallback thủ công |
| Chốt buổi | Nhân sự | Tổng hợp, chưa ghi nhận, QR chờ, chưa kiểm tra; xác nhận chuyển vắng |
| Yêu cầu sửa | Nhân sự | Trước/sau, lý do, người gửi, version; giám thị duyệt/từ chối |
| Báo cáo và export | Nhân sự | Bộ lọc theo quyền, số tổng, chi tiết, job xuất, tải tệp |
| Tài khoản / vận hành | Quản trị | Cấp/reset/khóa tài khoản, health, cấu hình, audit kỹ thuật |

Nguyên tắc giao diện: hiển thị trạng thái bằng chữ kèm màu; tên trùng luôn kèm mã và lớp; giữ bộ lọc khi quay lại; thời gian hiện tại rõ ràng; báo “đang lưu/đã lưu/lưu lỗi”; xác nhận trước thao tác hàng loạt, chốt, hủy và chuyển lớp. Trên điện thoại dùng thẻ học sinh và nút thao tác đủ lớn; không bắt kéo bảng ngang để xác nhận.

## 13. Bảo mật, hiệu năng và vận hành đề xuất

### 13.1 Bảo vệ dữ liệu

HTTPS khi truy cập từ điện thoại; dùng password hasher của Django; phiên có expiry và thu hồi; rate limit đăng nhập/quét QR; Django CSRF; validate upload bằng Forms/Pillow; ảnh/tệp trong kho riêng tư. Bản demo tải qua Django view kiểm tra quyền, bản object storage dùng signed URL có thời hạn sau kiểm tra quyền. Dữ liệu tối thiểu: chưa thu địa chỉ, giấy tờ, GPS hoặc ảnh hằng ngày. Audit không lưu token, mật khẩu hoặc raw image.

Nhà trường cần quyết định mục đích sử dụng ảnh, đối tượng được xem, thời hạn giữ dữ liệu/ảnh, thủ tục cung cấp/xóa dữ liệu và người chịu trách nhiệm. Tài liệu không đưa ra kết luận tuân thủ pháp luật hoặc thời hạn pháp lý. Chính sách xóa phải xử lý cả database, object storage, export, backup và yêu cầu giữ hồ sơ; không chỉ ẩn dòng ở giao diện.

### 13.2 Mục tiêu kỹ thuật để đo thử

Đối với bản K12 đi thi: kiểm chứng luồng với 2–5 lớp, 50–200 học sinh giả, vài thiết bị và export dưới 5.000 dòng. Các mục tiêu quy mô toàn trường dưới đây chỉ thuộc bản nâng cao PostgreSQL; không bắt buộc đạt trước khi trình diễn bài thi.

Các số sau là giả định sizing, cần đo và điều chỉnh theo số học sinh thực: 2.000 học sinh, 50 lớp, tối đa 2 buổi/ngày, 300 tài khoản hoạt động đồng thời gồm học sinh và nhân sự, đỉnh 30 request quét/giây. Khoảng 800.000 dòng attendance/năm với 200 ngày; event/audit/scan tăng thêm tùy số lần sửa.

- API xem danh sách/ghi nhận p95 dưới 1 giây ở tải mục tiêu, không tính thời gian mạng thiết bị.
- Export 100.000 dòng hoàn thành dưới 3 phút trên cấu hình thử nghiệm đã ghi nhận; không chặn request điểm danh.
- Hàng đợi hiển thị scan mới trong tối đa 10 giây khi kết nối ổn định.
- Index cần có school/session/status, roster/student, school/student_code, enrollment/student/date, classes/year/grade, QrScan/session/status/scanned_at, ExportJob/requested_by/status.
- Dashboard không quét toàn bộ AttendanceEvent; truy vấn bảng hiện trạng, lịch sử chỉ khi mở chi tiết.

### 13.3 Khôi phục và giám sát

Bản đi thi chuẩn bị bản sao database SQLite khi ứng dụng dừng ghi, thư mục private và dữ liệu giả để phục hồi demo; chưa cam kết RPO/RTO cấp trường. Các mục tiêu tiếp theo áp dụng khi chuyển sang vận hành nâng cao.

Đề xuất mục tiêu RPO tối đa 1 giờ, RTO 4 giờ nếu hạ tầng hỗ trợ PITR/backup phù hợp; cần nhà trường xác nhận chi phí và mức yêu cầu. Backup hằng ngày đơn thuần không đạt RPO 1 giờ. Object storage bật versioning/backup phù hợp; kiểm tra restore database lẫn ảnh/tệp tham chiếu. Nếu hạ tầng chỉ backup ngày, ghi rõ RPO thực tế tối đa 24 giờ thay vì tuyên bố đạt mục tiêu.

Giám sát lỗi API, QR expired, số scan chưa xác minh, export queue, generator thiếu buổi, upload lỗi, dung lượng và lần backup gần nhất. Alert có request_id, không đưa tên/ảnh học sinh vào kênh log công khai. Có checklist vận hành giờ cao điểm: kiểm tra Internet/QR, mở buổi, nhân sự xác nhận, fallback giấy, đối soát và chốt cuối buổi.

## 14. Kế hoạch triển khai chi tiết cho agent code

Đây là kế hoạch ở mức thiết kế chức năng và thứ tự xây dựng, chưa phải mã ứng dụng. Các đường dẫn dưới đây là cấu trúc đề xuất sẽ được tạo khi triển khai; hiện tại chưa có các file đó. Không xem checkbox là nhiệm vụ đã hoàn tất. Agent cần xác nhận P01–P04 ở mục 17 trước khi tạo nền tảng; các điểm còn lại áp dụng mặc định đề xuất nếu người dùng chấp nhận.

### 14.1 Cấu trúc repository đề xuất

```text
manage.py
requirements.txt
config/
  settings.py             môi trường, database, private storage
  urls.py                 URL trang và JSON API
  wsgi.py                 chạy server khi triển khai
school_app/
  accounts/               User, Groups, auth, phạm vi quyền
  academics/              năm học, khối, lớp, phân công
  students/               hồ sơ, enrollment, ảnh
  schedules/              lịch, ngoại lệ, buổi và roster
  attendance/             điểm danh, đồng phục, chốt buổi
  qr/                     challenge, scan, xác minh
  corrections/            yêu cầu sửa/duyệt
  reports/                tổng hợp, XLSX/CSV, export job
  audit/                  lịch sử nghiệp vụ
  core/                   enum, lỗi, idempotency, private storage
  templates/              base.html và thư mục theo module
  static/
    css/app.css
    js/qr_scan.js
    js/verification_queue.js
    vendor/               thư viện UI/QR dùng tại buổi thi
  management_app/
    management/commands/
      seed_demo.py
      generate_sessions.py
      process_exports.py
      expire_qr_scans.py
      cleanup_private_files.py
tests/
  test_permissions.py
  test_qr_flow.py
  test_concurrency.py
  test_report_reconciliation.py
  performance/locustfile.py
docs/                     thiết kế, API, vận hành, kịch bản thi
```

Mỗi Django app có `models.py`, `views.py`, `forms.py`, `services.py`, `urls.py`, `admin.py`, `migrations/` và test khi cần. Django ORM/migrations là công cụ mặc định; chỉ viết migration SQL riêng cho constraint PostgreSQL khi cần. Không tạo repository layer chỉ để bọc lại mọi truy vấn ORM. JSON payload được kiểm tra bởi Forms và service; giữ field/enum thống nhất bằng TextChoices/core. Đặt `management_app` trong INSTALLED_APPS để Django nhận command; đặt `tests/__init__.py` để test discovery. Logic điểm danh không nhân bản giữa thủ công và QR.

### 14.2 Thứ tự và phụ thuộc

```text
T01 nền tảng
   -> T02 quyền
   -> T03 lớp/GVCN
   -> T04 học sinh/ảnh
   -> T05 lịch/roster
   -> T06 điểm danh + T07 đồng phục
   -> T08 QR và xác nhận
   -> T09 chốt/sửa/audit
   -> T10 dashboard/export
   -> T11 tải, restore và pilot
```

Audit nền tảng bắt đầu ở T01, không đợi T09 mới lưu lịch sử. Có thể làm giao diện từng module sau khi hợp đồng của module đó ổn định. Chỉ làm song song phần không thay chung schema/contract; tài liệu này không tự cho phép agent con hoặc dịch vụ bên ngoài.

### T01. Chốt thiết kế và nền tảng dữ liệu — 3–4 ngày công

**Files dự kiến:** `docs/decisions.md`, `requirements.txt`, `manage.py`, `config/settings.py`, `school_app/core/enums.py`, `school_app/accounts/models.py`, `school_app/academics/migrations/0001_initial.py`, `school_app/audit/services.py`, `tests/test_database_constraints.py`.

- [ ] Ghi P01–P04 đã xác nhận: hình thức QR/thiết bị, tài khoản học sinh, đơn vị điểm danh, phạm vi/quy mô trường; cập nhật bản thiết kế nếu có thay đổi.
- [ ] Tạo môi trường Python 3.12 bằng venv; chọn Django 5.2 bản vá được hỗ trợ, khóa requirements; dùng pip, Django migrations và test runner sẵn có; ghi lệnh setup vào README.
- [ ] Tạo schema nền tảng, foreign key cùng trường và unique/index theo mục 8; seed chỉ dùng dữ liệu giả.
- [ ] Tạo TextChoices/enum, validation bằng Forms/service dùng chung; error format, request_id, USE_TZ và TIME_ZONE; custom User từ migration đầu tiên.
- [ ] Tạo transaction helper và AuditService append-only; che dữ liệu nhạy cảm khỏi log.
- [ ] Kiểm chứng: mã học sinh trùng bị database từ chối; tham chiếu lớp trường khác bị chặn; migration chạy từ database rỗng thành công.

**Điều kiện bàn giao:** Database tái tạo được từ migrations; phạm vi quyền và trạng thái dùng thống nhất trong mọi module.

### T02. Tài khoản và phân quyền — 3–4 ngày công

**Files dự kiến:** `school_app/accounts/models.py`, `views.py`, `forms.py`, `services.py`, `permissions.py`, `admin.py`; `school_app/templates/accounts/login.html`; `tests/test_permissions.py`.

- [ ] Viết kiểm chứng quyền cho teacher A/teacher B/supervisor/admin/student trước khi nối UI.
- [ ] Dùng Django Auth/session cho đăng nhập/đăng xuất/đổi mật khẩu và CSRF; thêm giới hạn thử đăng nhập và kiểm tra tài khoản bị khóa ở mọi view nghiệp vụ.
- [ ] Tạo cấp/reset/vô hiệu hóa tài khoản; student account liên kết đúng Student; lần đầu phải đổi mật khẩu.
- [ ] Guard kiểm tra UserRole và TeacherAssignment hiệu lực; student endpoint chỉ dùng danh tính từ phiên.
- [ ] Tạo màn hình đăng nhập/đổi mật khẩu và xử lý hết phiên; không lưu mật khẩu/token vào log.
- [ ] Kiểm chứng: teacher A gọi API lớp B bị chặn; student A không đọc student B; tài khoản khóa không dùng phiên cũ được.

**Điều kiện bàn giao:** Ma trận mục 3 hoạt động ở API; không dựa vào giao diện để bảo vệ quyền.

### T03. Tổ chức năm học, lớp và GVCN — 2–3 ngày công

**Files dự kiến:** `school_app/academics/models.py`, `services.py`, `forms.py`, `views.py`, `migrations/0002_assignment_constraints.py`; `school_app/templates/academics/classes.html`; `tests/test_teacher_assignment.py`.

- [ ] Tạo năm học/khối/lớp và trạng thái DRAFT/ACTIVE/READ_ONLY.
- [ ] Thêm ràng buộc không chồng thời gian phân công; dùng transaction khi đổi GVCN.
- [ ] Tạo cây lớp và form phân công, cảnh báo lớp thiếu GVCN.
- [ ] Cập nhật quyền tức thời khi phân công thay đổi, kể cả endpoint ảnh/export.
- [ ] Kiểm chứng: hai phân công cùng khoảng bị chặn; giáo viên cũ mất quyền; giáo viên mới xem lịch sử lớp; năm READ_ONLY không nhận ghi từ GVCN.

**Điều kiện bàn giao:** Một GVCN hiệu lực trên mỗi lớp ACTIVE, lịch sử không mất.

### T04. Học sinh, xếp lớp và ảnh — 4–5 ngày công

**Files dự kiến:** `school_app/students/models.py`, `services.py`, `forms.py`, `views.py`; `school_app/core/private_storage.py`; `school_app/templates/students/list.html`, `form.html`; `tests/test_student_history.py`, `tests/test_photo_access.py`.

- [ ] Tạo hồ sơ/enrollment cùng transaction, mã duy nhất, khoảng xếp lớp không chồng lấn.
- [ ] Tạo tìm kiếm tên/mã và danh sách theo lớp/khối, phân trang.
- [ ] Tạo upload qua Django Form/Pillow; kiểm tra nội dung/kích thước, chuẩn hóa/thumbnail đồng bộ cho demo, private storage và cập nhật chỉ sau READY.
- [ ] Tạo chuyển lớp/ngừng học có ngày hiệu lực; chặn xóa cứng hồ sơ có lịch sử.
- [ ] Tạo tài khoản STUDENT bằng quy trình quản trị, không trả mật khẩu trong API danh sách học sinh.
- [ ] Kiểm chứng: trùng tên vẫn thêm được; trùng mã trả 409; ảnh giả định dạng bị chặn; chuyển lớp không đổi snapshot buổi cũ; tải ảnh ngoài phạm vi bị chặn.

**Điều kiện bàn giao:** Có dữ liệu giả 2 lớp, đủ học sinh để chạy buổi mẫu và thử QR; ảnh thiếu không chặn điểm danh.

### T05. Lịch, đồng phục và mở buổi — 4–5 ngày công

**Files dự kiến:** `school_app/schedules/models.py`, `services.py`, `forms.py`, `views.py`; `school_app/management_app/management/commands/generate_sessions.py`; `school_app/templates/schedules/calendar.html`; `tests/test_session_snapshot.py`.

- [ ] Tạo rule tuần, uniform policy version và CalendarException với ưu tiên mục M04.
- [ ] Generator tạo cửa sổ 14 ngày bằng management command, retry không nhân đôi, chỉ cập nhật PLANNED; demo chạy trước buổi thi, bản nâng cao thêm scheduler hằng ngày.
- [ ] Mở buổi cùng transaction tạo roster snapshot và AttendanceRecord UNMARKED.
- [ ] Cấu hình scan_open_at/scan_close_at và cửa sổ thao tác; đề xuất mở trước start 30 phút, nhận quét đến close_at, cần chốt P05.
- [ ] Tạo UI lịch tuần/ngày, nghỉ/đổi đồng phục, cảnh báo thiếu cấu hình.
- [ ] Kiểm chứng: ngày nghỉ toàn trường ưu tiên cao nhất; mở hai lần không nhân đôi; sửa policy không sửa OPEN/CLOSED; học sinh chưa hiệu lực không vào roster.

**Điều kiện bàn giao:** Có buổi OPEN với roster và chuẩn đồng phục/giờ muộn nhất quán.

### T06. Điểm danh thủ công và tính đi muộn — 3–4 ngày công

**Files dự kiến:** `school_app/attendance/models.py`, `services.py`, `forms.py`, `views.py`; `school_app/core/idempotency.py`; `school_app/templates/attendance/roster.html`; `tests/test_arrival_status.py`, `tests/test_concurrency.py`.

- [ ] Viết các trường hợp ngưỡng 07:05:00 ON_TIME / 07:05:01 LATE, hồi tố, vắng, buổi đã chốt.
- [ ] Dùng transaction.atomic, version, IdempotencyRequest, AttendanceEvent và audit; select_for_update/lock order mục 10 chỉ kiểm chứng trên PostgreSQL.
- [ ] Tạo endpoint thủ công và batch giới hạn 100, rollback toàn lô khi có lỗi.
- [ ] Tạo UI roster/tìm kiếm, trạng thái đang lưu/lỗi/thành công và form lý do.
- [ ] Kiểm chứng retry sau mất response chỉ một lần ghi; cùng key khác payload bị chặn; hai người sửa cùng version chỉ một người thắng.

**Điều kiện bàn giao:** Kết quả đúng và có audit ngay cả khi chưa tích hợp QR; làm nền dùng lại cho T08.

### T07. Kiểm tra đồng phục — 2–3 ngày công

**Files dự kiến:** `school_app/attendance/uniform_rules.py`, `forms.py`, `services.py`; `school_app/templates/attendance/uniform_form.html`; `tests/test_uniform_rules.py`. Đồng phục là phần riêng trong app attendance để học viên không phải tạo thêm app nhỏ.

- [ ] Tạo validation chuyển trạng thái mục 4.3, snapshot lý do và trường checked_by/checked_at.
- [ ] Tạo form chuẩn phải mặc, loại thực tế, kết luận và lý do; có lựa chọn “chưa kiểm tra”.
- [ ] Cho phép ghi điểm danh + đồng phục atomically; mọi ghi nhận đi qua cùng attendance service.
- [ ] Kiểm chứng: vắng không vi phạm; thiếu lý do NON_COMPLIANT bị chặn; miễn có lý do; cùng loại không tự đạt; thay policy cũ không làm đổi báo cáo.

**Điều kiện bàn giao:** Kiểm tra độc lập nhưng không tạo trạng thái trái với attendance.

### T08. QR và xác nhận tại chỗ — 4–6 ngày công

**Files dự kiến:** `school_app/qr/models.py`, `services.py`, `views.py`, `forms.py`; `school_app/templates/qr/scan.html`, `display.html`, `queue.html`; `school_app/static/js/qr_scan.js`, `verification_queue.js`; `school_app/management_app/management/commands/expire_qr_scans.py`; `tests/test_qr_flow.py`.

- [ ] Dùng secrets/hashlib của Python tạo challenge ngẫu nhiên/hash, qrcode tạo ảnh; rotation 30s/expiry 60s, thu hồi khi buổi đóng/hủy.
- [ ] Tạo endpoint STUDENT quét lấy identity từ phiên, kiểm tra lớp/roster/cửa sổ/token; idempotency và partial unique PENDING.
- [ ] Tạo Django Template cho camera/link QR, html5-qrcode trong static và fetch kèm CSRF; màn hình phát mã theo lớp dùng ảnh qrcode do Python tạo.
- [ ] Tạo hàng đợi polling 5s, xác minh danh tính và đồng phục trong một transaction; thời gian đến lấy scanned_at.
- [ ] Tạo EXPIRED sau 15 phút, reject có lý do, manual supersede và xử lý quét lại.
- [ ] Kiểm chứng token hết hạn/sai lớp, hai học sinh một challenge, duplicate scan, giả student_id, confirm sau cutoff, mất response, scan chưa xác minh không tăng PRESENT.
- [ ] Thử trên điện thoại thật với HTTPS và camera permission; trường hợp không có thiết bị đi qua fallback.

**Điều kiện bàn giao:** Luồng người dùng đã chọn hoạt động từ quét tới xác nhận và báo cáo; có giới hạn chống quét hộ được trình bày rõ.

### T09. Chốt, chỉnh sửa và truy vết — 3–4 ngày công

**Files dự kiến:** `school_app/attendance/session_close.py`; `school_app/corrections/models.py`, `services.py`, `forms.py`, `views.py`; `school_app/templates/corrections/list.html`; `tests/test_close_correction.py`.

- [ ] Tạo preview chốt có UNMARKED/NOT_CHECKED/QR PENDING; chốt bằng session_version.
- [ ] Chuyển UNMARKED sang ABSENT_UNEXCUSED, pending scan sang EXPIRED; giữ NOT_CHECKED.
- [ ] Tạo yêu cầu sửa/review, so target_version, approve/reject một lần và audit trước/sau.
- [ ] Tạo mở lại/hủy/khôi phục có lý do; chỉnh snapshot buổi đang mở chỉ giám thị.
- [ ] Kiểm chứng chốt đồng thời xác nhận QR không có bản ghi lọt; yêu cầu cũ không ghi đè bản mới; sửa CLOSED bởi teacher bị chặn.

**Điều kiện bàn giao:** Trạng thái khóa có hiệu lực và thay đổi báo cáo truy nguyên được.

### T10. Dashboard, báo cáo và export — 4–5 ngày công

**Files dự kiến:** `school_app/reports/models.py`, `queries.py`, `services.py`, `exporters.py`, `views.py`; `school_app/management_app/management/commands/process_exports.py`; `school_app/templates/reports/attendance.html`, `exports.html`; `tests/test_report_reconciliation.py`, `tests/test_export_permission.py`.

- [ ] Tạo canonical filters và scope dùng chung cho dashboard/chi tiết/export.
- [ ] Implement công thức mục 11, phân biệt OPEN/CLOSED, pending scan, mẫu số 0 và snapshot lớp.
- [ ] Tạo ExportJob/ExportRow nhất quán một thời điểm; metadata; demo tối đa 5.000 dòng xử lý đồng bộ, nâng cao tối đa 100.000 dòng qua management command.
- [ ] Tạo XLSX bằng openpyxl với 3 sheet, CSV bằng csv chuẩn Python với UTF-8 BOM; escape formula, định dạng date/time đúng timezone.
- [ ] Tạo UI job progress/lỗi/retry/tải; kiểm tra lại quyền khi chạy/tải; cleanup sau expiry.
- [ ] Kiểm chứng bộ dữ liệu 40 học sinh mục 11.2, đổi lớp/quyền giữa tạo và tải, sửa bản ghi khi đang xuất, retry worker không trộn snapshot.

**Điều kiện bàn giao:** Số liệu và file đối soát được; người dùng không xuất/tải vượt phạm vi.

### T11. Vận hành, thử tải và pilot — 4–6 ngày công

**Files dự kiến:** `tests/test_full_school_day.py`, `tests/performance/locustfile.py`, `docs/operations.md`, `docs/demo-script.md`, `docs/pilot-acceptance.md`; cấu hình CI/deploy chỉ tạo khi môi trường triển khai đã được yêu cầu.

- [ ] Chạy end-to-end từ phân công → thêm học sinh → lịch → mở buổi → quét → xác nhận → chốt → sửa → export.
- [ ] Demo trên vài thiết bị, 2–5 lớp và dữ liệu giả; bản nâng cao dùng Locust/Python thử 30 request/giây và 300 phiên trên PostgreSQL, ghi p95/error rate/số dòng đúng.
- [ ] Kiểm tra quyền, token logging, upload giả, spreadsheet injection và phiên bị thu hồi.
- [ ] Demo: thử restore database/thư mục private từ bản sao, kiểm tra ảnh/audit và dữ liệu giả. Bản nâng cao: ghi RPO/RTO đạt thực tế.
- [ ] Chuẩn bị kịch bản thi 5–7 phút: giới thiệu vấn đề → học sinh quét → nhân sự xác nhận và kiểm tra đồng phục → chốt → xuất báo cáo → giải thích model/quyền/timezone. Nếu dùng tại trường, pilot 2 lớp trong 5 ngày và đối soát với sổ trực.
- [ ] Sửa lỗi mức chặn sử dụng, cập nhật hướng dẫn, trình nhà trường nghiệm thu trước khi mở toàn trường.

**Điều kiện bàn giao:** Bản đi thi chạy demo hoàn chỉnh, học viên giải thích được luồng, có kết quả kiểm chứng và fallback. Bản vận hành nâng cao cần nhà trường xác nhận dữ liệu pilot và các tiêu chí tải/restore.

### 14.3 Ước lượng và mốc review

Các ước lượng T01–T11 là mức triển khai đầy đủ, gồm kiểm chứng nâng cao: tổng 36–49 ngày công của người có kinh nghiệm. Không áp thời gian này làm cam kết cho học viên K12. Lịch học đề xuất 10–12 tuần, 2 buổi/tuần, 2 giờ/buổi và tự thực hành 3–5 giờ/tuần; cần Python cơ bản trước khi bắt đầu. Đây là khung hướng dẫn, điều chỉnh theo năng lực và hạn cuộc thi. Bản đi thi ưu tiên Django/SQLite và demo hoàn chỉnh; PostgreSQL, thử tải lớn và vận hành tại trường triển khai sau hoặc làm phần nâng cao khi đủ thời gian.

Phân bổ học tập: tuần 1–2 Django/model/auth; tuần 3–4 lớp/học sinh/ảnh; tuần 5–6 lịch/roster/điểm danh/đồng phục; tuần 7–8 QR/xác minh; tuần 9–10 chốt/sửa/báo cáo; tuần 11–12 hoàn thiện, kiểm chứng, hồ sơ và luyện demo. Học viên phải tự giải thích và sửa được các phần được dùng trong bài thi; agent hỗ trợ từng module, không thay toàn bộ quá trình học.

| Mốc | Sản phẩm review | Điều kiện chuyển tiếp |
| --- | --- | --- |
| G0 trước T01 | Quyết định P01–P04, phạm vi MVP, trường dữ liệu | Có yêu cầu triển khai và lựa chọn QR cụ thể |
| G1 sau T05 | Lớp/học sinh/ảnh/lịch/roster mẫu | Dữ liệu và snapshot được chấp nhận |
| G2 sau T08 | Điểm danh thủ công + QR + đồng phục | Demo có mặt đúng giờ/muộn/quét trùng/fallback |
| G3 sau T10 | Chốt, sửa, dashboard, XLSX/CSV | Quyền và số liệu được đối soát |
| G4 sau T11 | Kịch bản thi, kiểm chứng và hướng dẫn phục hồi demo; pilot/báo tải là nâng cao | Học viên trình bày và chạy lại demo được; nếu vận hành thật cần nhà trường xác nhận |

## 15. Ma trận nghiệm thu chức năng và dữ liệu

Các ca dưới đây là đặc tả kiểm chứng, chưa phải kết quả chạy test của một ứng dụng đã tồn tại.

| Mã | Tình huống / dữ liệu vào | Kết quả bắt buộc |
| --- | --- | --- |
| AC01 | Teacher A đổi class_id thành lớp Teacher B | 403/404; không trả danh sách, ảnh hoặc export |
| AC02 | Hai học sinh tên Nguyễn Văn An, mã khác nhau | Tạo được; hiển thị mã/lớp để phân biệt |
| AC03 | Tạo trùng student_code trong một trường | 409; không tạo Student hoặc Enrollment dư |
| AC04 | Chuyển lớp từ ngày 10/10 sau buổi 09/10 đã mở | Buổi 09/10 vẫn lớp cũ; buổi mới 10/10 theo lớp mới |
| AC05 | Đổi GVCN giữa năm | Giáo viên cũ mất quyền; mới xem lịch sử lớp; export cũ tải lại bị kiểm tra quyền |
| AC06 | Start 07:00, grace 5; arrived 07:05:00 và 07:05:01 | Lần lượt ON_TIME và LATE; đúng công thức số phút |
| AC07 | Học sinh quét QR 07:04, xác minh 07:08 | PRESENT arrived 07:04, verified 07:08, ON_TIME |
| AC08 | Hai học sinh quét cùng QR còn hạn | Mỗi người một PENDING hợp lệ; token không hết hạn sau người đầu |
| AC09 | Cùng học sinh quét hai lần khi còn PENDING | Trả scan cũ, không đổi scanned_at, không thêm attendance |
| AC10 | QR hết hạn/sai lớp/ngoài cửa sổ | Từ chối; không tạo PENDING hoặc PRESENT |
| AC11 | Student A gửi student_id B trong payload | Schema từ chối field hoặc bỏ qua; không ghi cho B; danh tính từ phiên |
| AC12 | Scan PENDING 16 phút chưa xác minh | EXPIRED; không có mặt; quét lại tạo timestamp mới nếu còn cửa sổ |
| AC13 | Điểm danh thủ công khi đang có PENDING | Bản ghi MANUAL; scan SUPERSEDED; không có hai kết quả |
| AC14 | PRESENT nhưng chưa kiểm tra đồng phục | NOT_CHECKED; không đếm đạt hoặc vi phạm |
| AC15 | NON_COMPLIANT không lý do | 422; rollback, giữ bản ghi cũ |
| AC16 | ABSENT có uniform_status NON_COMPLIANT | 422; vắng chỉ có NOT_APPLICABLE |
| AC17 | Đổi lịch đồng phục sau khi buổi CLOSED | Buổi cũ và báo cáo cũ giữ snapshot |
| AC18 | Replay Idempotency-Key giống/khác payload | Giống trả response cũ; khác trả 409; không ghi lần hai |
| AC19 | Hai người sửa expected_version=1 | Một thành công version=2, một 409 |
| AC20 | Chốt lúc có 3 UNMARKED, 2 PENDING, 3 NOT_CHECKED | 3 vắng không phép; 2 scan EXPIRED; 3 NOT_CHECKED được giữ |
| AC21 | Chốt đồng thời confirm QR | Một thứ tự hợp lệ theo khóa; không confirm thành công sau CLOSED |
| AC22 | GVCN sửa CLOSED; giám thị sửa không lý do | Bị chặn; sửa đúng quy trình có audit trước/sau |
| AC23 | Yêu cầu sửa target_version cũ | 409; không duyệt/ghi đè tự động |
| AC24 | Dữ liệu 40 học sinh tại mục 11.2 | Đúng tổng và 85%; 11,76%; 13,79%; 90,63% |
| AC25 | Buổi CANCELLED có bản ghi cũ | Không góp mẫu số; dữ liệu/audit vẫn tồn tại |
| AC26 | Không có roster/không có kiểm tra | Tỷ lệ có mẫu số 0 hiển thị “—” |
| AC27 | Hồ sơ ghi chú bắt đầu '=HYPERLINK(...)' | XLSX/CSV ghi text, không chạy formula khi mở |
| AC28 | Thu hồi quyền sau khi export READY | Download bị chặn, dù biết job_id hoặc URL endpoint |
| AC29 | Attendance thay đổi giữa các trang worker đọc | Export lấy cùng snapshot; tổng và chi tiết khớp |
| AC30 | PNG giả/ảnh quá 5 MB/upload lỗi | Từ chối hoặc FAILED; ảnh trước còn nguyên |
| AC31 | Mất mạng sau server commit, client retry | Một bản ghi/một sự kiện cho thao tác; client lấy trạng thái chuẩn |
| AC32 | Học sinh không có điện thoại | Nhân sự điểm danh MANUAL, kiểm tra đồng phục bình thường |
| AC33 | Chạy generator và open buổi hai lần | Không nhân đôi session/roster/attendance |
| AC34 | Restore database và object storage | Đối chiếu số dòng, quyền và ảnh tham chiếu; ghi thời gian phục hồi |

Agent cần biến các ca rủi ro dữ liệu/quyền thành Django TestCase; ca transaction/cạnh tranh dùng TransactionTestCase trên PostgreSQL; camera cần thử điện thoại thật. Bản demo kiểm chứng quyền, trạng thái, QR, đồng phục và báo cáo; AC19/AC21 và tải nhiều người cần PostgreSQL. Không gọi test tuần tự SQLite là test concurrency đạt.

Các lệnh dự kiến sau khi tạo ứng dụng: `python manage.py check`; `python manage.py makemigrations --check --dry-run`; `python manage.py test`; `python manage.py test tests.test_qr_flow tests.test_report_reconciliation`; `python manage.py test tests.test_concurrency` với cấu hình PostgreSQL; `ruff check .` nếu đã thêm ruff; `locust -f tests/performance/locustfile.py` cho bản nâng cao đã cài Locust. Ghi settings/database thực tế khi chạy. Các lệnh ứng dụng chưa được chạy trong workspace hiện tại vì hiện chỉ có tài liệu.

## 16. Ví dụ xuyên suốt một học sinh

1. Giám thị tạo năm học 2026–2027, khối 10, lớp 10A1; phân công cô Lan.
2. Cô Lan thêm mã HS001, họ tên Nguyễn Minh An; Enrollment hiệu lực 01/09; ảnh tùy chọn.
3. Lịch 08/10 buổi sáng: 07:00, grace 5 phút, đồng phục SHIRT. Mở buổi tạo roster và AttendanceRecord UNMARKED.
4. HS001 đăng nhập và quét QR lớp 10A1 lúc 07:04. QrScan PENDING; điểm danh vẫn UNMARKED.
5. Giám thị đối chiếu HS001 tại chỗ lúc 07:08, xác nhận và thấy mặc SPORTS. Ghi PRESENT arrived 07:04, ON_TIME; uniform NON_COMPLIANT, lý do WRONG_TYPE.
6. Cô Lan xem dashboard thấy có mặt đúng giờ và một vi phạm; không thể suy ra học sinh đi muộn từ giờ xác minh 07:08.
7. Chốt buổi; sau đó cô Lan đề nghị sửa vì có quyết định đổi đồng phục riêng chưa được nhập. Giám thị kiểm tra, duyệt bằng quy trình có lý do; lịch sử vẫn giữ kết luận và dữ liệu trước/sau.
8. Export tháng 10 ghi lớp 10A1 theo snapshot, thời gian đến/nguồn QR/kết quả cuối; nếu HS001 chuyển 10A2 ngày 15/10, buổi 08/10 vẫn là 10A1.

Ví dụ bước 7 không có nghĩa người dùng được miễn tùy tiện: giám thị phải kiểm tra căn cứ đổi chính sách hoặc miễn của học sinh. Nếu sai chính sách toàn buổi, chỉnh snapshot và xử lý những bản ghi bị ảnh hưởng theo mục 10.3, không chỉ sửa một học sinh rồi để buổi mâu thuẫn.

## 17. Những quyết định cần chốt trước triển khai

| Mã | Câu hỏi nghiệp vụ | Mặc định đề xuất / trạng thái | Chốt trước |
| --- | --- | --- | --- |
| P01 | QR hiển thị theo buổi để học sinh dùng điện thoại quét, hay máy tại cổng quét thẻ từng học sinh? | Người dùng đã chọn học sinh quét QR; đề xuất mã động theo lớp/buổi trên màn hình nhân sự | T01 |
| P02 | Mọi học sinh có điện thoại/tài khoản không; tài khoản được cấp bằng cách nào? | Tài khoản riêng liên kết Student; TECH_ADMIN cấp; thiếu điện thoại dùng MANUAL | T01 |
| P03 | Điểm danh theo ngày, sáng/chiều hay từng tiết? | Sáng/chiều độc lập | T01 |
| P04 | Quy mô bài thi và quy mô vận hành sau này? | Demo một trường với 2–5 lớp, 50–200 học sinh giả; nâng cao mới sizing 2.000 học sinh/50 lớp | T01 |
| P05 | Giờ bắt đầu, grace, giờ kết thúc nhận scan và hạn xác minh? | Giờ theo lịch; grace ví dụ 5 phút; scan trước start 30 phút; pending 15 phút | T05 |
| P06 | Nhân sự xác minh có mặt cùng lúc kiểm tra đồng phục hay được tách? | Xác minh danh tính bắt buộc; đồng phục có thể làm cùng lần hoặc để NOT_CHECKED | T07–T08 |
| P07 | Có ngày miễn đồng phục, tiêu chí giày/bảng tên và ai được miễn? | Hai loại SHIRT/SPORTS; hỗ trợ miễn có lý do; GVCN lớp mình/giám thị | T05–T07 |
| P08 | GVCN có quyền sửa sau chốt, thay lịch cần duyệt không? | Sau chốt gửi yêu cầu; trước buổi sửa lịch lớp trực tiếp | T09 |
| P09 | Học sinh chuyển lớp giữa ngày có cần hỗ trợ không? | Chuyển theo ngày; cả sáng/chiều cùng lớp mới | T04 |
| P10 | Có dữ liệu cũ cần nhập Excel hoặc hệ thống khác không? | Thêm trực tiếp trong MVP; nhập hàng loạt là task bổ sung khi có mẫu và quy mô | T04 |
| P11 | Muốn báo cáo mẫu nào, XLSX/CSV hay PDF; tần suất xuất? | XLSX/CSV, chi tiết và tổng hợp theo lớp/khối/ngày | T10 |
| P12 | Ai quản lý ảnh, lưu trong bao lâu; môi trường hosting/backup? | Demo dùng private storage và dữ liệu giả; vận hành thật chốt retention/storage; export 24 giờ, link ký 5 phút nếu dùng object storage | Trước pilot |
| P13 | Khi chuyển GVCN, giáo viên mới được xem toàn lịch sử lớp không? | Có; giáo viên cũ mất quyền | T02–T03 |
| P14 | Chấp nhận mục tiêu RPO/RTO và hạ tầng tương ứng không? | Mục tiêu 1 giờ/4 giờ cần hạ tầng và chi phí phù hợp | T11 |

Đã đủ để review thiết kế và ước lượng, nhưng P01/P02/P04 ảnh hưởng mạnh thiết bị, auth và vận hành. Việc có QR chưa đồng nghĩa đã xác nhận kiểu QR, thiết bị hoặc số lượng học sinh.

## 18. Hướng dẫn bàn giao cho agent code

1. Đọc toàn bộ mục 1–4 trước khi chọn schema; nhận diện yêu cầu gốc và giả định đề xuất.
2. Xác nhận các quyết định có mốc trước triển khai, đặc biệt P01–P04; ghi vào `docs/decisions.md` khi bắt đầu dự án.
3. Giữ UUID/mã học sinh, enrollment có hiệu lực, snapshot buổi và event/audit; không làm schema một bảng vừa chứa hồ sơ vừa chứa điểm danh hôm nay.
4. Triển khai T01 → T11 bằng Django theo phụ thuộc; mặc định cấu hình demo K12, cập nhật checklist và hợp đồng khi có quyết định mới. Chỉ tăng lên hạ tầng nâng cao khi có yêu cầu hoặc đã chọn làm phần nâng cao.
5. Dùng cùng service ghi dữ liệu cho manual/QR; không tạo đường tắt QR bỏ qua quyền, version hoặc audit.
6. Chạy kiểm chứng tương ứng AC01–AC34; báo kết quả thực tế và các ca chưa kiểm chứng. Không dùng tài liệu thiết kế làm bằng chứng hệ thống đã chạy.
7. Chưa thêm AI, phụ huynh, SMS, học phí hoặc dữ liệu cá nhân bổ sung nếu không được yêu cầu.
8. Bàn giao ứng dụng kèm Django migrations, requirements, command seed_demo, dữ liệu giả, tài liệu setup, kịch bản thi, giới hạn QR và kết quả kiểm chứng. Bổ sung kết quả pilot khi vận hành thử tại trường; phát hành thật là bước có yêu cầu riêng.

## 19. Tự rà soát tài liệu

| Hạng mục | Kết quả rà soát thiết kế |
| --- | --- |
| Bao phủ yêu cầu R01–R08 | Có module, workflow, dữ liệu và nghiệm thu tương ứng |
| Phản hồi người dùng về QR | QR là luồng chính; manual dự phòng; chưa chốt kiểu thiết bị cụ thể |
| Quyền học sinh | Chỉ bản thân và quét; không quyền danh sách/ảnh/export |
| Thời gian | Tách scan/đến/ghi/xác minh; đi muộn theo arrived_at và snapshot |
| Đồng phục | Không tự đạt khi có mặt/quét; vắng NOT_APPLICABLE; thiếu kiểm tra có chỉ số riêng |
| Lịch sử | Chuyển lớp/đổi GVCN/đổi lịch không ghi đè buổi cũ; chỉnh sửa có audit |
| Cạnh tranh và retry | Khóa buổi/version/idempotency; dữ liệu chính và audit cùng transaction |
| Báo cáo | Mẫu số học sinh-buổi; loại hủy; snapshot export; download kiểm tra quyền |
| Phạm vi hiện tại | Chỉ tài liệu thiết kế và kế hoạch; chưa có ứng dụng hoặc test ứng dụng được chạy |
| Công nghệ K12 | Python/Django là chủ đạo; Templates thay SPA; SQLite demo/PostgreSQL nâng cao; cấu trúc, file và lệnh kiểm chứng đều theo Python |
