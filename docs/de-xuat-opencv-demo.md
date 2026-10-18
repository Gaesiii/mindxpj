# Đề xuất thay QR bằng OpenCV và chuẩn bị demo

Ngày: 18/10/2026. Trạng thái: người dùng đã cho triển khai bằng “làm đi”; chọn hướng A, “1 U” hiểu là UI demo. Nguồn chuẩn đã chuyển sang thiết kế v1.3; API gate vẫn NOT_APPROVED. Tài liệu này giữ rationale, không phải bằng chứng vision đã chạy.

## Yêu cầu mới

- Hoàn thành kế hoạch dự án với luồng quét mặt và kiểm tra đồng phục thay cho QR.
- Bổ sung “1 U để test + thuyết trình”; được hiểu là UI demo; yêu cầu tiếp theo “làm luôn UI để demo” cho phép local UI trước gate theo ngoại lệ18/10/2026.
- Yêu cầu nhận diện mới thay đổi giới hạn không camera/AI của MVP cũ. Sau khi chốt thiết kế, cập nhật nguồn chuẩn và AGENTS.md cùng đợt để tránh chỉ dẫn mâu thuẫn.

## Các hướng thực hiện

| Hướng | Cách hoạt động | Đánh đổi |
| --- | --- | --- |
| A — đề xuất | Camera nhận ảnh, đối chiếu mặt trong roster buổi học, gợi ý đồng phục; nhân sự xác nhận trước khi ghi điểm danh | Có thể kiểm soát nhận sai, cần bước xác nhận |
| B | Nhận diện và ghi điểm danh/đồng phục tự động | Cần dữ liệu và đánh giá nhận sai chặt hơn, phạm vi lớn hơn |
| C | OpenCV chỉ phát hiện có mặt người; nhân sự chọn học sinh và đồng phục | Dễ demo hơn nhưng không đáp ứng nhận diện danh tính tự động |

## Thiết kế đề xuất A

Giữ Django, auth/session, phạm vi lớp, lịch/buổi/roster, báo cáo và xuất file hiện có. Thay đường đi QR trong demo bằng module vision; giữ migrations và dữ liệu QR lịch sử, không xóa bảng cũ khi chuyển đổi.

Luồng: nhân sự đăng nhập → chọn buổi thuộc quyền → bật camera → gửi ảnh chụp → backend kiểm tra quyền và roster → phân tích mặt/đồng phục → trả ứng viên hoặc trạng thái chưa xác định → nhân sự xác nhận → service attendance hiện có ghi kết quả và log → chốt buổi → báo cáo/XLSX/CSV.

- Ảnh hồ sơ hiện có không mặc nhiên là bộ ảnh nhận diện. Cần bước đăng ký mẫu và kiểm tra chất lượng trên dữ liệu được phép sử dụng.
- Chọn thuật toán đối chiếu mặt sau thử nghiệm nhỏ; phát hiện khuôn mặt không được coi là nhận diện danh tính. Chưa tuyên bố độ chính xác hay chống ảnh chụp giả.
- Đồng phục trả SHIRT/SPORTS/UNKNOWN, sau đó đối chiếu yêu cầu snapshot của buổi. Không đủ bằng chứng thì UNKNOWN, không tự kết luận vi phạm.
- Không có mặt, nhiều mặt, mặt lạ, ảnh mờ hoặc kết quả không chắc chắn: yêu cầu chụp lại hoặc chuyển nhập thủ công, không ghi PRESENT tự động.
- Camera không mở được: hiển thị hướng dẫn và cho nhân sự điểm danh thủ công.
- API xử lý ảnh, lấy mẫu và xác nhận đều kiểm tra vai trò/phạm vi lớp. Tài khoản học sinh vẫn lấy danh tính từ session; kết quả nhận diện không tự cấp quyền hoặc thay phiên đăng nhập.
- Không lưu video liên tục. Ảnh/mẫu nhận diện nếu cần lưu phải ở vùng private, có thao tác xóa và kiểm tra quyền; chốt chính sách lưu trước khi triển khai.
- Xác nhận phải kiểm tra lại buổi OPEN, roster và version; retry không tạo bản ghi trùng. Không thay schema/contracts dùng chung trước khi thống nhất tác động giữa hai nhóm module.

## Phân công và thứ tự bàn giao

| Chặng | Phụ trách | Đầu ra | Điều kiện hoàn tất |
| --- | --- | --- | --- |
| 1. Chốt phạm vi | PM + mem1 + mem2 | Thiết kế phiên bản mới, contracts, phân công, tracker đồng bộ | Chốt ý nghĩa “U”, mức tự động, mẫu đồng phục và dữ liệu thử |
| 2. Thử nghiệm OpenCV | mem2; mem1 phối hợp ảnh/học sinh | Thử nhận diện mặt và đồng phục trên bộ mẫu có nhãn | Báo cáo nhận đúng/nhận nhầm/từ chối theo ánh sáng, góc mặt và trang phục; chọn thuật toán/ngưỡng bằng kết quả thật |
| 3. API vision | mem2; mem1 review scope | Đăng ký mẫu, phân tích ảnh, xác nhận; tích hợp attendance/manual fallback | Test quyền, dữ liệu ảnh, lỗi phân tích, trùng/retry và buổi đóng đạt |
| 4. API gate mới | PM; hai thành viên cung cấp evidence | Kiểm chứng API mới và regression backend | PM duyệt rõ ràng; kết quả QR cũ không chứng minh vision đạt |
| 5. UI local theo yêu cầu mới | mem1 auth/danh sách/report; mem2 camera/kết quả/xác nhận | Giao diện demo Django tối thiểu | Ngoại lệ local trước gate theo “làm luôn UI để demo”; browser/camera cần evidence riêng, PM gate không đổi |
| 6. Test và thuyết trình | Theo nhân sự được chốt ở chặng 1 | Checklist, evidence, kịch bản và tài liệu bàn giao | Chạy luồng thật, review và ghi giới hạn trước khi đánh dấu hoàn tất |

Giữ quyền sở hữu accounts/academics/students/reports của mem1 và schedules/attendance/luồng thay QR của mem2. Chưa chốt lại ngày hoàn thành trước khi thử nghiệm khả thi OpenCV và xác định nguồn lực “U”. Không ép phạm vi mới vào lịch QR cũ khi chưa có ước lượng.

## Kiểm chứng bắt buộc

- Regression backend hiện có trên DB thử riêng; migrate từ DB mới và từ schema hiện có; không thay DB demo đang dùng.
- Quyền: GVCN khác lớp, học sinh, phiên hết hạn; đọc ảnh/mẫu, phân tích và xác nhận đều phải bị chặn đúng.
- Nhận diện: đúng người, người lạ, hai người, ảnh mờ, thiếu sáng, góc nghiêng; tách bộ đăng ký khỏi bộ đánh giá.
- Đồng phục: SHIRT, SPORTS, sai loại, bị che, nền gần màu áo; UNKNOWN không tự chuyển thành đạt hoặc không đạt.
- Nghiệp vụ: buổi đóng, học sinh ngoài snapshot, confirm lặp, ảnh gửi lại, version cũ, lỗi giữa chừng; report/export khớp kết quả đã xác nhận.
- Thiết bị thật: xin quyền camera, từ chối quyền, mất camera/mạng, thử lại và nhập thủ công.
- Chỉ ghi số test đạt và độ chính xác từ lần chạy có log; các số liệu backend cũ là bằng chứng lịch sử.

## Kịch bản thuyết trình dự kiến 5–7 phút

1. Nêu bài toán, vai trò và phạm vi demo.
2. Giới thiệu kiến trúc Django + OpenCV và lý do cần xác nhận.
3. Mở buổi; quét một người đã đăng ký; xem gợi ý mặt/đồng phục; xác nhận.
4. Cho thấy một trường hợp chưa nhận diện được và cách nhập thủ công.
5. Chốt buổi, đối chiếu báo cáo và tải XLSX/CSV.
6. Trình bày bằng chứng test, kết quả thử nghiệm thực tế và giới hạn.

## Quyết định triển khai

Chọn hướng A: staff-operated OpenCV + xác nhận bắt buộc + manual fallback. “U” hiểu là UI demo. Ngoại lệ ngày18/10/2026: người dùng yêu cầu rõ “làm luôn UI để demo”, cho phép UI local trước gate. Đây không phải phê duyệt PM API; API_Gate vẫn NOT_APPROVED và Finish? không tự thay đổi. Kế hoạch chi tiết: [2026-10-18-opencv-demo.md](superpowers/plans/2026-10-18-opencv-demo.md). Giới hạn kỹ thuật, dữ liệu và contracts theo [v1.3](thiet-ke-he-thong-diem-danh.md). Không suy đoán accuracy/liveness từ việc người dùng đồng ý triển khai.
