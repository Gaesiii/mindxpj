# Khảo sát GitHub: nhận diện đồng phục qua camera

Ngày kiểm tra: 21/10/2026. **Có source làm camera nhận diện trang phục/đồng phục; đã clone bốn repo ngoài workspace để đối chiếu. Chưa có bằng chứng để thay model hiện tại bằng một model nhận đúng đồng phục trường.** Đây là so sánh source và artifact, chưa phải benchmark độ chính xác hoặc tốc độ suy luận.

## Kết quả tìm và clone

Tìm bằng GitHub CLI theo `uniform detection`, `school uniform`, `uniform recognition`, `dress code detection`, sắp xếp star; kết hợp tìm web và kiểm tra trực tiếp repository. Kết quả tìm kiếm không đảm bảo bao phủ toàn GitHub. Số star là snapshot lúc kiểm tra, không phải chất lượng model. Repo đúng chủ đề nhiều star nhất trong nhóm đã đối chiếu là 16 star; không gọi đây là repo lớn hoặc tiêu chuẩn ngành.

| Repository | Star | Source/artifact đã kiểm tra | Đánh giá cho project |
|---|---:|---|---|
| [hynjxn/uniform-detection-using-YOLOv5](https://github.com/hynjxn/uniform-detection-using-YOLOv5) | 16 | Flask/React, camera OpenCV, YOLOv5; checkpoint `best.pt` 42.204.077 bytes. Nhãn kiểu áo/váy/quần, không phải danh tính logo trường mình. | Tốt để tham khảo detector và luồng camera; chưa thể thay classifier trường. GPL-3.0. |
| [Muhammad-Muzammil-Shah/School-Uniform-detection](https://github.com/Muhammad-Muzammil-Shah/School-Uniform-detection) | 6 | Notebook YOLOv5/YOLO11/YOLOv12 và hướng dẫn dataset; không thấy checkpoint `.pt/.pth/.onnx` trong clone. | Tài liệu huấn luyện, chưa phải dịch vụ camera chạy ngay. Chưa thấy license repo rõ ràng. |
| [LaThanhTrong/Monitoring-Attendance-and-Checking-School-Uniforms](https://github.com/LaThanhTrong/Monitoring-Attendance-and-Checking-School-Uniforms) | 2 | PyQt5, camera Windows, YOLOv8 + ArcFace; có weights. Source phân áo có tay/không tay, quần dài/ngắn, thẻ. | Gần bài toán điểm danh nhất; có thể học cách crop theo người. Chưa thấy license repo rõ ràng. |
| [yixin16/Staff_Uniform_SOP_Compliance_Analysis](https://github.com/yixin16/Staff_Uniform_SOP_Compliance_Analysis) | 0 | Detector người + áo; `main.py` dùng Swin-T và capture cửa sổ Windows. Có hai detector nhưng thiếu classifier `best_model_finegrained_swin.pth` được main yêu cầu. | Ý tưởng tách vùng áo đáng tham khảo; clone hiện chưa đủ model để chạy pipeline đầy đủ. Chưa thấy license repo rõ ràng. |

Repo `gisketch/complete-uniform-detection-YOLOv8` còn xuất hiện trong kết quả web cache với tám star, nhưng kiểm tra GitHub API và mở trang trực tiếp đều không truy cập được (404). Không tính nó là source đã clone hoặc dùng số star cache để xếp hạng hiện tại.

## So với phần đồng phục hiện tại

| Tiêu chí | Project hiện tại | Các ứng viên đã clone |
|---|---|---|
| Camera | Browser gửi ảnh tới API; xử lý hai frame gắn với người được nhận diện | Hynjxn đọc camera máy server; LaThanhTrong desktop Windows; yixin16 đọc cửa sổ CCTV Windows |
| Vùng trang phục | Crop thân trên theo vị trí mặt, có kiểm tra đủ vùng/độ rõ | YOLO tìm vật thể/người/áo; linh hoạt hơn về vị trí, cần kiểm tra ghép đúng mặt với áo |
| Đúng mẫu trường | Contract ba lớp `SHIRT/SPORTS/OTHER`, cần dữ liệu trường và đánh giá riêng | Nhãn trường khác hoặc kiểu trang phục; chưa có đánh giá logo/mẫu của trường mình |
| Model sẵn dùng | Chưa có model trường được phê duyệt; training/import tooling đã có | Hynjxn và LaThanhTrong có checkpoint; yixin16 thiếu classifier; Muhammad có notebook |
| Không đủ bằng chứng | Thiếu model, thiếu thân trên, hai frame bất nhất hoặc confidence thấp: `NOT_CHECKED` | Không thể coi threshold detection của họ là bằng chứng tương đương về mẫu trường |
| Tích hợp điểm danh | Scope lớp, snapshot model, chống ghi trùng, bảo toàn chỉnh sửa thủ công, lý do vi phạm | Cần port riêng và kiểm tra lại các quy tắc này; không thay cả ứng dụng |
| Runtime hướng Vercel | OpenCV DNN/ONNX, không đưa PyTorch vào backend; artifact giới hạn 32 MiB | Source dùng PyTorch; GUI/camera server cần đổi; chưa đo Linux/serverless |

Project hiện tại không chỉ dùng màu HSV để kết luận đúng trường: logic chính nằm ở `backend/school_app/vision/uniform_model.py`. Tuy nhiên **chưa có dataset/model trường được nghiệm thu**, vì vậy chưa thể nói project nhận đồng phục chính xác hơn các ứng viên. 23 tests hiện tại kiểm tra hành vi phần mềm, không chứng minh độ chính xác model.

Đối chiếu cụ thể: Hynjxn chọn áo và quần/váy có điểm cao nhất trên toàn ảnh trong `server/model/detect.py`, nên cần kiểm tra ghép theo từng người trước khi dùng cho nhiều người. Nhánh runtime của LaThanhTrong nạp năm YOLO weights tổng 123.071.552 bytes, chưa tính ArcFace hoặc thư viện; hai weights quần/áo khoảng 52 MB mỗi file. Đây là dung lượng file, **không phải RAM, latency hoặc bundle cuối**. Các checkpoint `.pt` không thể đưa thẳng vào OpenCV ONNX runtime hiện tại; cần export và kiểm tra parity trước.

README yixin16 nói EfficientNet nhưng `main.py` tại commit đã clone dùng Swin-T; khi đánh giá khả năng chạy, báo cáo ưu tiên source đang tồn tại. Những khác biệt đó cùng model bị thiếu khiến kết luận từ README đơn thuần không đủ tin cậy.

## Hướng phù hợp để tiếp tục

Giữ luồng Django và dữ liệu hiện tại. Ứng viên nên thử tiếp là **detector vùng áo/người kiểu YOLO**, rồi classifier riêng cho trường. Đây là hướng đề xuất từ source, chưa phải cải thiện đã đo. LaThanhTrong gần bài toán và có artifact nhất; Hynjxn có nhiều star hơn trong nhóm nhưng nhãn tập trung kiểu trang phục mùa hè nữ sinh. Không tự động thay engine hay nhận checkpoint của trường khác là model trường mình.

Để benchmark có ý nghĩa cần bộ ảnh chung được phép sử dụng: đồng phục sơ mi/thể dục trường; áo cùng màu sai logo/kiểu; áo thường; bị che logo; crop thiếu thân; ánh sáng/góc khác nhau. Tách người và buổi chụp giữa train/validation/test. Đo precision/recall từng lớp, confusion matrix, độ phủ sau ngưỡng, hành vi UNKNOWN, crop sai người, p50/p95 CPU và RAM. Dùng cùng ảnh, máy và cấu hình; tách thời gian detect/crop/classify/API. Chưa có bộ này nên không đưa ra con số accuracy/FPS suy đoán.

Trước khi tích hợp: xác minh quyền dùng code/weights/dataset, fine-tune hoặc train model trên dữ liệu trường, export ONNX, kiểm tra output/OpenCV parity, đánh giá độc lập rồi import như một phiên bản model mới. Chưa có license rõ ràng thì chỉ tham khảo, không copy code/weights vào repo công khai. Giữ attribution và điều kiện license khi có tái sử dụng.

## Bằng chứng local và kiểm tra

Clone nằm ở `E:\projectmindx-references\uniform-20261021`, mỗi repo một thư mục tác giả; được giữ ngoài Git của project. [Inventory commit, metadata, dung lượng và SHA-256](project-management/evidence/uniform-github-2026-10-21/inventory.json) ghi lại artifact thực tế. Chỉ đọc source và hash file; không chạy ứng dụng, mở camera hay load checkpoint bên ngoài. Không tải dependency vào môi trường backend.

Chạy `manage.py test tests.test_school_uniform tests.test_uniforms --verbosity 1`: **23/23 tests đạt**, system check không lỗi. Không thay backend, model, ngưỡng, database hay deployment. Báo cáo này bổ sung phần khảo sát D02; không đánh dấu D01/dataset hoặc D03/model evaluation đã hoàn thành, không thay PM acceptance.
