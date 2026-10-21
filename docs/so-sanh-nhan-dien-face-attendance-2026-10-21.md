# So sánh nhận diện với source Face Attendance — 21/10/2026

**Quyết định: giữ YuNet + SFace hiện tại, không thay engine.** Source desktop người dùng cung cấp chưa tốt hơn trên bộ ảnh thử này, đồng thời có hành vi chấp nhận ảnh nhiều người. Không thay dependencies, dữ liệu khuôn mặt, API điểm danh hoặc luồng đồng phục của project.

## Kết quả đo

Baseline project: commit `94cee7e`. Chạy CPU Windows, OpenCV một thread, ba lần mỗi ảnh. Có một danh tính đăng ký (Obama), ba ảnh đăng ký khác nhau; hai ảnh kiểm tra cùng người và hai ảnh của người chưa đăng ký. Hai ảnh kiểm tra cùng người không được dùng làm ảnh đăng ký. Không điều chỉnh ngưỡng theo kết quả kiểm tra.

| Biến thể | Nhận đúng ảnh cùng người /2 | Nhận nhầm người lạ /2 | Nhận đúng biến đổi cùng người /10 | Chấp nhận sai ảnh hai người | p50 / p95 (ms) |
|---|---:|---:|---:|---|---:|
| Project hiện tại, Python 3.12 / OpenCV 4.13 | 2 | 0 | 9 | Không | 37,081 / 46,272 |
| Project hiện tại, Python 3.14 / OpenCV 4.11 | 2 | 0 | 9 | Không | 38,544 / 49,194 |
| Source tham khảo, dlib, đăng ký nguyên bản | 1 | 0 | 7 | Có | 276,127 / 296,950 |
| Source tham khảo, dlib, thử ba ảnh đăng ký khác nhau | 1 | 0 | 7 | Có | 276,569 / 292,368 |
| Source tham khảo, Haar + vector ảnh xám dự phòng | 1 | 0 | 4 | Có | 19,445 / 30,624 |

Ở cùng Python/OpenCV, p50 của SFace nhanh khoảng **7,16 lần** so với nhánh dlib trong phép đo này. Nhánh ảnh xám nhanh hơn SFace nhưng bỏ sót nhiều ảnh hơn và không loại ảnh hai người. Cả năm biến thể đều từ chối ảnh trống và không nhận nhầm mười ảnh biến đổi từ hai ảnh người lạ.

Ngưỡng project tự động là cosine `0.60` cùng margin `0.15`; nhánh dlib dùng điều kiện khoảng cách trung bình `<=0.55` của source. Điểm cosine và khoảng cách Euclidean không thể so trực tiếp hoặc diễn giải thành phần trăm chính xác. Hai ảnh cùng người đạt cosine khoảng `0.698`, `0.660`; dlib nguyên bản đạt khoảng cách `0.489` (nhận) và `0.557` (từ chối).

## Cách thử và giới hạn

Tổng cộng 28 probe mỗi biến thể: bốn ảnh kiểm tra gốc; hai ảnh kiểm tra lỗi cũ; hai ảnh đối chứng tạo trong RAM (trống, ghép hai khuôn mặt với người đã đăng ký lớn hơn); hai mươi ảnh biến đổi sáng, xoay hoặc mờ từ bốn ảnh kiểm tra gốc. Các ảnh biến đổi có tương quan, **không phải hai mươi mẫu độc lập**. Hai file cũ `no-face.jpg` và `multiple-detections.jpg` thực tế đều là ảnh một người; tên file phản ánh lỗi Haar cũ, không phải nhãn đúng. Chúng được tách nhóm `legacy_diagnostic`, không tính vào bốn ảnh kiểm tra gốc.

Ảnh đầu vào được decode chung, sửa EXIF và giới hạn cạnh 960px. Sau đó mỗi engine dùng detection/crop/encoding/matching của chính nó. Harness gọi các phương thức gốc của source tham khảo, không mở Qt, camera thật hay database. Đăng ký nguyên bản lặp một crop ba lần như UI nguồn; thử nghiệm ba ảnh khác nhau được báo riêng. Nguồn dùng `face_recognition` nếu import được; nhánh dự phòng được chạy riêng với thư viện này bị chặn trước khi import.

Thời gian là suy luận từng ảnh sau khi làm nóng, gồm detection/crop/encoding/matching; không gồm decode, truyền ảnh HTTP hoặc thời gian chờ camera. Mỗi lần thử source tham khảo bắt đầu với hình học camera mới, không hưởng cache preview. Helper lịch sử của source được cấp ba sự kiện cùng điểm để kiểm tra điều kiện chấp nhận; đây **không phải phép đo ba frame camera độc lập**. `pair_observations` trong JSON chỉ mô tả kết quả từng ảnh, không chạy API điểm danh hai frame. Không suy FPS camera hoặc thời gian điểm danh hoàn chỉnh từ bảng này.

Chỉ có một danh tính đăng ký và hai người lạ: chưa đánh giá nhầm lẫn giữa nhiều học sinh, độ chính xác toàn trường, camera thực tế, liveness hay Vercel Linux. Không kết luận FAR bằng 0 cho thực tế. Chỉ số initialization của hai nguồn khác cách nạp model (lazy/eager), không dùng so startup ứng dụng. Memory trong JSON là working set của tiến trình benchmark gồm Django, ảnh, các helper; việc tạo lại camera nguồn cũng tạo lại landmark giả. Không dùng nó để kết luận RAM desktop, FPS camera hoặc RAM Vercel.

## Những điểm cần lưu ý trong source tham khảo

- `camera.py` chọn khuôn mặt lớn nhất và cho phép tiếp tục khi ảnh có nhiều người; project hiện tại từ chối ảnh nhiều mặt trước khi điểm danh.
- `utils/face_utils.py` có thể chuyển từ dlib 128 chiều sang vector ảnh xám 2336 chiều khi encoding thất bại, rồi so phần chung khi khác chiều. Trong mỗi lượt dlib có bốn probe đi vào tình huống khác không gian đặc trưng này. Project hiện tại kiểm tra chiều và model key.
- `ui/touch_utils.py` lưu một crop ba lần; ba bản sao không tạo thêm góc nhìn để học.
- `ui/attendance.py` dùng lịch sử ứng viên chưa chắc liên tiếp, không reset khi mất mặt; sau cooldown có thể cộng lại số lần. Không đưa cơ chế đó vào điểm danh theo buổi vốn cần chống ghi trùng và bảo toàn chỉnh sửa thủ công.
- Các điểm lưới 468 trong camera nguồn là tọa độ sinh trên hình chữ nhật, không chứng minh có MediaPipe hoặc kiểm tra người thật.

Embedding dlib và SFace không tương thích dù cùng có 128 chiều. Không nhập trực tiếp file `.npy` nguồn vào dữ liệu project. Không tái sử dụng GUI desktop PyQt hoặc các binary Windows vào Vercel; cần port và đo Linux riêng nếu muốn triển khai nhánh đó sau này.

## Tái lập và bằng chứng

- [Script benchmark](../.document-tools/compare_face_projects.py).
- [Kết quả chi tiết, phiên bản thư viện và hash source](project-management/evidence/face-comparison-2026-10-21/results.json).
- [Manifest hash script và ảnh đầu vào](project-management/evidence/face-comparison-2026-10-21/reproducibility.json). Manifest chỉ chứa tên tương đối và SHA-256, không có ảnh hoặc embedding.

Source đi kèm dlib binary `cp314`, khác Python 3.12 của backend. Để chạy đúng nhánh dlib, phép thử dùng [Python 3.14.0 embeddable chính thức](https://www.python.org/downloads/release/python-3140/) trong thư mục tạm và các dependencies đi kèm source; không cài lại môi trường backend. Model công khai của `face_recognition_models` được copy sang đường dẫn tạm ASCII vì dlib không mở được đường dẫn Unicode của folder gốc trên máy thử. Python portable và model không được commit.

Lệnh dưới đây cần các ảnh local và môi trường Python 3.14 đã chuẩn bị như trên; script không tự tải dữ liệu hoặc dependencies:

```powershell
backend/.venv/Scripts/python.exe .document-tools/compare_face_projects.py `
  --reference 'E:/projectmindx/face_attendance_app_3backup2 - Sao chép' `
  --images 'E:/projectmindx/demo-images' `
  --python314 "$env:TEMP/mindx-face-compare-python314/python.exe"
```

Review độc lập đã đối chiếu harness với source và xác nhận bằng chứng đủ để giữ engine hiện tại, với các giới hạn nêu trên. Đây là review kỹ thuật, không thay PM `API_Gate=NOT_APPROVED`.

Kiểm tra sau khi lập báo cáo: `manage.py test tests.test_vision_engine --verbosity 1` đạt **12/12 tests**; system check không có lỗi. Đã kiểm tra đủ năm lượt benchmark × 28 probe × ba mẫu thời gian, hash source tham khảo không đổi, hash script/ảnh, SHA-256 các file backup và tính toàn vẹn ZIP. Không chạy lại toàn bộ suite vì không sửa backend; kết quả 255 tests ở báo cáo v1.5 là bằng chứng của đợt trước.

## Sao lưu và phạm vi thay đổi

Đã tạo bản sao trước khi thử ở ngoài repository, tên `before-face-comparison-20261021-133548-94cee7e` trong `E:\projectmindx-backups`. Có source ZIP tại baseline, Git bundle được kiểm tra bằng `git bundle verify`, manifest SHA-256 và bản backup SQLite riêng của demo. Secret môi trường không được đóng gói. Bản SQLite có dữ liệu riêng tư nên chỉ giữ local, không đẩy GitHub.

Có thể giải nén `project-source.zip` vào một thư mục mới để xem code cũ, hoặc clone `project-history.bundle` ra thư mục khác rồi checkout `94cee7e`. Không ghi đè workspace hay database đang chạy để xem bản sao. Source người dùng vừa thêm, archive gốc, PIN, `.npy`, môi trường `venv` và dữ liệu riêng tư của nó đều không được đưa vào commit.

Thay đổi lần này chỉ thêm công cụ đo, bằng chứng đã lọc và tài liệu. Giữ nguyên engine, ngưỡng nhận diện, API và dữ liệu hiện tại; không deploy.
