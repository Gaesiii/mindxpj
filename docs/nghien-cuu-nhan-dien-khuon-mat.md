# Nghiên cứu thay LBPH — 18/10/2026

Ghi chú sau phê duyệt: bản YuNet + SFace FP32 đã được tích hợp theo nghiên cứu này; xem [kết quả triển khai](project-management/evidence/sface-upgrade/README.md). Các trạng thái “chưa tích hợp/đề xuất” bên dưới được giữ như bản ghi tại thời điểm nghiên cứu, trước khi người dùng duyệt.

**Khuyến nghị cho dự án này: YuNet + SFace FP32 từ OpenCV Zoo.** Đã tải mô hình ONNX từ kho chính thức trên Hugging Face, đối chiếu SHA-256 với Git LFS của GitHub, chạy CPU bằng OpenCV4.13 hiện có. Chưa tích hợp vào ứng dụng; không sửa DB demo hay nâng ngưỡng LBPH.

## Vấn đề thực tế

DB demo đang chạy lưu đúng3 mẫu của DEMOHS01. File người dùng tại `demo-images/demo/1753240560-trump-67651-width698height558.jpg` được Haar phát hiện mặt nhưng LBPH distance101.695, vượt ngưỡng55. Ảnh người khác có distance86.378, nên chỉ nâng ngưỡng sẽ nhận nhầm. Giữ từng ảnh đăng ký ra ngoài rồi kiểm tra bằng hai ảnh còn lại cũng thất bại ở cả3 lượt. Ảnh mới phải là tiêu chí kiểm thử, không chỉ upload lại ảnh đã enrollment.

## Các hướng đã kiểm tra

| Hướng | Điểm phù hợp | Đánh đổi và quyết định |
| --- | --- | --- |
| YuNet + SFace FP32 | Phát hiện5 landmark, căn chỉnh mặt, embedding128 chiều; chạy bằng OpenCV đang cài, không thêm ML framework; model nhận diện38,696,353bytes, detector232,589bytes | Ưu tiên cho demo hiện tại; đã thử trên đúng ảnh người dùng |
| YuNet + SFace INT8 | Model nhận diện9,896,933bytes; cùng API OpenCV | Giảm dung lượng khoảng74%; đã thử nhưng không nhanh hơn FP32 trong lượt đo local, nên không mặc định chọn chỉ vì INT8 |
| InsightFace/ArcFace pretrained | Thư viện đã có pipeline detection/alignment/embedding | Code MIT nhưng pretrained weights công bố giới hạn non-commercial research. Không mặc nhiên coi license code là license weights; không cần thêm dependency cho demo OpenCV hiện có |
| AuraFace-v1 | Model card của fal khai báo Apache2.0, dựa trên ArcFace/ResNet100 | Riêng `glintr100.onnx`260,694,151bytes; cộng khoảng267.4MiB wheels hiện tại là khoảng516MiB trước source/runtime, không phù hợp mục tiêu bundle Vercel hiện tại. Chưa benchmark model này |
| DeepFace | Wrapper nhiều model, có API verify/find sẵn | Hữu ích tham khảo pipeline; thêm lớp dependency/framework không cần thiết khi dùng trực tiếp SFace. Không coi wrapper là một thuật toán độc lập hoặc suy ra license mọi weights từ MIT của wrapper |

Nguồn: [OpenCV GitHub SFace](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface), [YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet), [OpenCV Hugging Face](https://huggingface.co/opencv/opencv_zoo/tree/main/models/face_recognition_sface), [InsightFace license](https://github.com/deepinsight/insightface/blob/master/python-package/docs/model_zoo.md), [AuraFace card](https://huggingface.co/fal/AuraFace-v1), [AuraFace files](https://huggingface.co/fal/AuraFace-v1/tree/main), [DeepFace](https://github.com/serengil/deepface).

## Kết quả thực nghiệm local

Đọc ảnh, sửa EXIF/giới hạn cạnh960 như ứng dụng; detector YuNet chạy ảnh cạnh tối đa640, confidence0.9, NMS0.3. Căn chỉnh trên ảnh màu theo5 landmark rồi trích xuất SFace. Mỗi ảnh đăng ký khi được đánh giá được loại khỏi bộ tham chiếu của chính nó. Ảnh người dùng chưa nằm trong enrollment. Không mock detector/matcher; không gọi dịch vụ nhận diện ngoài.

| Ca thử | LBPH hiện tại | SFace FP32 | SFace INT8 |
| --- | --- | --- | --- |
| Ảnh người dùng ngoài bộ đăng ký | UNKNOWN_FACE, distance101.695 | cosine0.688063, khớp | cosine0.669067, khớp |
| Ảnh người khác | UNKNOWN_FACE, distance86.378 | cosine0.287265, từ chối | cosine0.271584, từ chối |
| Lần lượt giữ ngoài từng ảnh đăng ký | 0/3 khớp | 3/3 khớp, best0.757–0.800 | 3/3 khớp, best0.770–0.813 |
| Trung vị12 lượt detect+align+embedding của ảnh người dùng | Không đo lại | 43.49ms | 47.49ms |
| Nạp model nhận diện trong lượt đo | Không đo | 162.74ms | 31.69ms |

Cosine càng cao càng giống, **không phải xác suất hay phần trăm tin cậy**. Dùng ngưỡng demo upstream0.363 cho thí nghiệm, không điều chỉnh để khớp riêng ảnh người dùng. [OpenCV tutorial](https://docs.opencv.org/4.13.0/d0/dd4/tutorial_dnn_face.html) đưa ngưỡng này cho LFW; không mặc định đó là ngưỡng tốt nhất cho tìm kiếm1:N trong lớp học. Cần hiệu chỉnh với nhiều người/camera và kiểm tra chênh lệch ứng viên đứng thứ hai.

Đo trên Windows CPU local, một thread OpenCV; không phải latency HTTP/Vercel và chưa đo tải đồng thời. Bộ ảnh chỉ có một danh tính dương và một danh tính âm; kết quả đủ chọn hướng cải thiện lỗi đang gặp, **chưa phải accuracy tổng quát**. FP32 chạy trước INT8; muốn kết luận hiệu năng rộng hơn cần đảo thứ tự, nhiều lượt và máy Linux/Vercel thật.

YuNet tìm đúng một vùng mặt trong hai ảnh trước đây Haar báo NO_FACE/MULTIPLE_FACES. Không được giữ tên file đó như nhãn ground-truth lỗi bắt buộc cho thuật toán mới; ảnh nhóm thật và ảnh không có mặt thật cần được bổ sung riêng.

Bằng chứng: [benchmark.json](project-management/evidence/face-research/benchmark.json), [manifest model/hash](project-management/evidence/face-research/model-manifest.json), [kích thước file AuraFace](project-management/evidence/face-research/aura-file-sizes.json). Mô hình tải về đang nằm trong thư mục tạm local `mindx-face-research`, chưa đưa vào repo hoặc function bundle. GitHub revision `47534e27c9851bb1128ccc0102f1145e27f23f98`; Hugging Face revision `d4938dfc9d4ec5d098bfa33e98b3f3345a236586`.

## License và ghi công

README của từng thư mục OpenCV Zoo công bố YuNet là MIT, SFace là Apache2.0 cho các file trong thư mục. Khi dùng lại phải mang theo LICENSE, copyright/NOTICE liên quan, nguồn và revision; chỉ ghi rõ phần tích hợp do nhóm viết, không tuyên bố tự phát minh hoặc tự huấn luyện model. Không cần fork toàn bộ Zoo hoặc copy các phần nhận diện tuổi/giới tính/cảm xúc.

Về vận hành thương mại sau này, [issue upstream313](https://github.com/opencv/opencv_zoo/issues/313) còn hỏi làm rõ provenance dữ liệu và quyền weights. Báo cáo ghi nhận tuyên bố license hiện tại của repository, không coi đó là xác nhận độc lập mọi quyền đối với dữ liệu huấn luyện. Deliverable hiện tại vẫn là demo giáo dục local.

## Thiết kế tích hợp được đề xuất

Thay riêng engine phát hiện/so khớp mặt bằng YuNet2023mar + SFace2021dec FP32, giữ Django, scoped APIs, UI demo, SQLite tạm, HSV gợi ý đồng phục và xác nhận nhân sự bắt buộc. Pipeline: ảnh màu → phát hiện đúng một mặt → chất lượng tối thiểu → căn chỉnh112×112 → embedding128float → cosine với mẫu trong đúng roster → ngưỡng + khoảng cách ứng viên thứ hai → proposal. Không tự ghi PRESENT và không tuyên bố chống ảnh giả.

Mẫu LBPH128×128 grayscale hiện tại không có đủ màu/landmark để chuyển đổi tương đương pipeline mới. Bổ sung version/model key và embedding cho mẫu mới; đánh dấu mẫu cũ cần enrollment lại. Không xóa ngầm lịch sử/mẫu cũ hoặc tự gán ảnh mạng cho học sinh. UI phải báo rõ số mẫu dùng được và yêu cầu đăng ký lại. Lưu private aligned crop/embedding, không lưu frame quét; đổi mẫu tiếp tục vô hiệu proposal đang chờ theo cơ chế hiện có.

Phân biệt metric/model version trong bản ghi quét và API/UI để không trộn LBPH distance với cosine. Lịch sử LBPH và báo cáo vẫn đọc được. Models được pin revision/hash, đóng gói khi build, kiểm tra thiếu/hỏng rõ ràng; không tải network ở request. Cache model trong process với khóa bảo vệ DNN khi truy cập đồng thời; giới hạn kích thước ảnh và CPU threads. FP32+detector thêm khoảng37.1MiB, ước tính tổng cùng wheels hiện tại khoảng304.5MiB trước source/runtime: còn phù hợp mục tiêu bundle; vẫn cần kiểm chứng build Linux/Vercel thực tế.

Kiểm chứng trước bàn giao: unit tests ngưỡng/margin/model version/invalid embedding; migration giữ lịch sử và báo mẫu legacy; API real Haar-replacement/embedding trên ảnh ngoài mẫu người dùng và ảnh người khác; no-face/multi-face thật; CSRF/role scope/idempotency/version; full suite và UI re-enrollment→scan→confirm; review. Giữ nguyên DB demo đang chạy cho đến khi có kế hoạch nâng cấp và thông báo phải đăng ký lại mẫu. Trạng thái: **đề xuất chờ duyệt**, chưa tích hợp.
