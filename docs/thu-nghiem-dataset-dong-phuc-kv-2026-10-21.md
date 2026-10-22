# Nhập và thử dataset đồng phục KV — 21/10/2026

Cập nhật 22/10: đã bổ sung [UI demo KV local có ảnh mẫu và camera để quay cho PM](demo-dong-phuc-cho-pm-2026-10-22.md). Trang thử riêng này không kích hoạt model trong điểm danh hoặc school profile.

**Đã tải dữ liệu, nhập vào bộ thử local, huấn luyện classifier hai lớp và kiểm tra model ONNX bằng OpenCV. Chưa nhập model vào hồ sơ lớp hoặc bật trên UI điểm danh.** Dataset ngoài trường, thiếu nhãn thể dục và chưa rõ quyền tái phân phối nên không thể coi là model đồng phục trường đã nghiệm thu.

## Dataset và cách chuẩn bị

Nguồn: [Kendriya Vidyalaya School Uniform Vs. Non-Uniform — Sanju Kumar Giri](https://www.kaggle.com/datasets/sanjukumargiri/kendriya-vidyalaya-school-uniform-vs-nonuniform). Kaggle API ghi license `Unknown` lúc tải. Archive 199.442.311 bytes, SHA-256 `2d47b2c200694edc5a2a7df5c8b8e1eb8b80bf666f6e8df586cd164e774365e9`. Chỉ giữ ảnh và model local, không tái phân phối lên GitHub.

Có 2.016 ảnh train mang nhãn qua tên file: 1.008 `normal.*` và 1.008 `school.*`. Mapping này được đối chiếu [notebook của tác giả](https://github.com/Sanju-Kumar-Giri/School-Uniform-Identification-using-Deep-Learning-based-Approach/blob/main/CODE/School_vs_Normal_Classification_using_CNN.ipynb). 1.000 ảnh trong thư mục test không có nhãn kèm theo nên không chấm accuracy trên chúng. Bộ test có nhãn của lần thử này được tách từ 2.016 ảnh ban đầu, không phải bộ test gốc của tác giả.

Lần đầu áp dụng nguyên `torso_crop` của project chỉ còn 15 crop đồng phục sau lọc trùng, không đủ số lượng tối thiểu của phép thử. Nguyên nhân thể hiện ở ảnh nguồn nhỏ, thiếu vùng thân hoặc có nhiều người. Giữ nguyên quy tắc runtime; chỉ thêm nhánh chuẩn bị dữ liệu cho thử nghiệm: một mặt YuNet ở ngưỡng 0,9, mặt tối thiểu 12px, thân áo tối thiểu 24px, crop bên dưới mặt và cắt theo biên ảnh, loại ảnh trống/tối. Nhánh này **không được đưa vào API/camera** và không được tính là qua gate runtime.

Kết quả: loại 1.412 ảnh không có đúng một mặt phát hiện được, một ảnh không đủ crop; còn 603 crop. Nhóm trùng theo SHA-256 nguồn và perceptual hash DCT (Hamming <=6), bỏ nhóm xung đột nhãn, giữ một đại diện mỗi nhóm: 547 crop sau khi bỏ 56 dòng trùng/gần trùng. Đây chỉ là lọc trùng gần đúng, không chứng minh người/buổi chụp độc lập. Không sử dụng face embedding hoặc thông tin danh tính để chia dữ liệu.

| Nhãn ngoài trường | Train | Validation | Test |
|---|---:|---:|---:|
| NON_UNIFORM | 309 | 66 | 66 |
| KV_UNIFORM | 74 | 16 | 16 |
| Tổng | 383 | 82 | 82 |

Trong 547 crop đại diện, chỉ 420 crop NON_UNIFORM và 12 crop KV_UNIFORM qua nguyên điều kiện crop runtime. Trong 82 ảnh test, tương ứng 65 và bốn crop qua điều kiện đó. Kết quả classifier dưới đây bao gồm cả crop dùng nhánh chuẩn bị ảnh nhỏ; **không phải kết quả end-to-end của camera project**. Đã xem riêng một sheet mẫu 12 crop; không tuyên bố duyệt thủ công toàn dataset. Phát hiện mặt tự động có thể bỏ sót, vì vậy dữ liệu chuẩn bị không được công khai.

## Model và kết quả

Dùng MobileNetV3 Small, đóng băng convolution features từ [weights ImageNet của torchvision](https://docs.pytorch.org/vision/0.21/models/generated/torchvision.models.mobilenet_v3_small.html), huấn luyện linear head hai lớp trong môi trường riêng. Tải weights một lần từ máy chủ chính thức, ghi SHA-256 đầy đủ trước khi nạp bằng `weights_only=True`. Không cài PyTorch vào backend.

Seed 2026; head học tối đa 150 epoch, chọn checkpoint bằng validation loss (lần chạy này epoch 150). Ngưỡng 0,95 cố định trước khi test; không chọn ngưỡng bằng test. Resize crop về 224x224, RGB, chuẩn hóa ImageNet giống contract preprocessing của project. Không gán `KV_UNIFORM` thành `SHIRT` hoặc tạo nhãn giả `SPORTS`.

| Nhãn thực tế | Quyết định đúng ở ngưỡng 0,95 | Quyết định sai | UNKNOWN | Recall gồm abstention |
|---|---:|---:|---:|---:|
| NON_UNIFORM (66 ảnh) | 63 | 0 | 3 | 95,45% |
| KV_UNIFORM (16 ảnh) | 11 | 0 | 5 | 68,75% |
| Tổng (82 ảnh) | 74 | 0 | 8 | Độ phủ 90,24% |

Argmax không áp ngưỡng đúng 82/82 ảnh của bộ thử này. Mẫu nhỏ, dữ liệu lệch lớp, kiểu áo KV đặc trưng và ảnh thiên về sản phẩm; không được hiểu là độ chính xác 100% ngoài thực tế hoặc nhận được logo trường mình. Sau lọc trùng vẫn có thể còn cùng người, kiểu áo hoặc bối cảnh giữa các split. Không dùng kết quả này thay đánh giá độc lập theo người/buổi chụp.

ONNX 3.726.424 bytes (~3,55 MiB), hai logits. Đã so parity với PyTorch trên toàn bộ 82 ảnh test, sai số tuyệt đối lớn nhất khoảng `1,41e-5`. OpenCV CPU một thread: forward p50 **8,46 ms**, p95 **11,89 ms**, sau warm-up; không gồm đọc/decode ảnh, tìm mặt, crop, preprocessing, HTTP hay hai frame camera. Không suy FPS end-to-end từ số này.

Đối chứng ngoài phân phối: ba ảnh trống đen/trắng/xám trả UNKNOWN, nhưng ảnh nhiễu ngẫu nhiên bị trả NON_UNIFORM với confidence khoảng 0,981. Điều này cho thấy confidence classifier chưa đủ để kiểm tra có áo hoặc xử lý mọi ảnh lạ. Cần kiểm tra thân áo, che logo, sai trường và dữ liệu camera thực trước khi dùng vào nghiệp vụ.

## Dùng thử ngay trên máy

Toàn bộ dữ liệu/model ở `E:\projectmindx-data\uniform-kv-20261021`:

- `output/test-results.html`: mở bằng trình duyệt để xem crop test, nhãn đúng, dự đoán và confidence. Trang này chỉ ở local.
- `output/external-kv-binary.onnx`: model thử hai lớp.
- `output/report.json`, `output/integration-checks.json`: số đo và kiểm tra tương thích.
- `prepared/manifest.json`: dataset đã nhập và split, hash từng crop; `provenance.json`: nguồn dữ liệu/weights.

Thử ảnh **đã crop riêng vùng áo** bằng backend venv (chỉ cần OpenCV, không cần PyTorch):

```powershell
backend/.venv/Scripts/python.exe .document-tools/uniform_dataset_trial.py predict `
  --directory E:/projectmindx-data/uniform-kv-20261021 `
  --image 'E:/duong-dan/anh-vung-ao.jpg'
```

Kết quả `KV_UNIFORM`, `NON_UNIFORM` hoặc `UNKNOWN` chỉ thuộc chế độ thử. Lệnh này không tự ghép mặt/người với áo, không ghi điểm danh và không chỉnh dữ liệu lớp. Không đưa ảnh toàn cảnh vào lệnh rồi coi kết quả là kiểm tra trang phục đầy đủ.

Lệnh tái lập sau khi đã giải nén dữ liệu và có weights đúng hash:

```powershell
backend/.venv/Scripts/python.exe .document-tools/uniform_dataset_trial.py prepare `
  --directory E:/projectmindx-data/uniform-kv-20261021
$trialWeightsHash = Get-Content E:/projectmindx-data/uniform-kv-20261021/initial-weights.sha256
.venv-uniform-training/Scripts/python.exe .document-tools/uniform_dataset_trial.py train `
  --directory E:/projectmindx-data/uniform-kv-20261021 `
  --weights E:/projectmindx-data/uniform-kv-20261021/mobilenet_v3_small-047dcff4.pth `
  --weights-sha256 $trialWeightsHash --epochs 150 --threshold 0.95
```

Môi trường riêng dùng Python 3.12.2, torch 2.6.0+cpu, torchvision 0.21.0+cpu, ONNX 1.17.0, OpenCV headless 4.13.0.92, NumPy 2.2.6, Pillow 11.3.0. Script không tự tải weights hoặc dataset. Dataset không được commit nên clone GitHub mới sẽ cần tự tải nguồn và cài môi trường như trên.

## Kiểm tra tích hợp và giới hạn hoàn thành

Đã chạy thật lệnh predict với một crop mỗi lớp, so SHA-256 model khi nạp, kiểm tra hash/split không trùng chính xác. `validate_review` của importer production từ chối model thử này; không tạo review phê duyệt giả. Runtime thiếu profile được phê duyệt vẫn trả `UNKNOWN/NOT_CHECKED`, lý do `NO_APPROVED_MODEL`. Không có ghi database hay sửa profile lớp.

Chạy `manage.py test tests.test_school_uniform tests.test_uniforms --verbosity 1`: **23/23 tests đạt**, system check không lỗi. Các tests này chứng minh hành vi phần mềm, tách biệt kết quả classifier thực nêu trên. Review kỹ thuật đã đối chiếu số liệu report, artifact, nhãn và điều kiện importer; PM acceptance vẫn riêng.

Đã hoàn thành yêu cầu tải/nhập dataset vào bộ thử và test model local. Chưa hoàn thành nhận diện đúng mẫu trường trong ứng dụng: còn thiếu dữ liệu trường gồm sơ mi/thể dục, hard negatives sai logo/kiểu, camera và occlusion, đánh giá độc lập và license rõ ràng. Không thay backend, hạ gate runtime, bật model trên UI điểm danh hoặc deploy.

[Script](../.document-tools/uniform_dataset_trial.py) · [Report đã lọc dữ liệu](project-management/evidence/uniform-dataset-trial-2026-10-21/report.json) · [Kiểm tra tích hợp](project-management/evidence/uniform-dataset-trial-2026-10-21/integration-checks.json) · [Nguồn dữ liệu/weights](project-management/evidence/uniform-dataset-trial-2026-10-21/provenance.json).
