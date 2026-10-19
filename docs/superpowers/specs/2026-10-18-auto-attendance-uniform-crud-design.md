# Đề xuất v1.5: camera tự động, đồng phục và CRUD

Trạng thái: **APPROVED_FOR_IMPLEMENTATION — người dùng yêu cầu hoàn thành theo plan ngày19/10/2026**. Thiết kế chuẩn/AGENTS/contracts chuyển v1.5, giữ v1.4 làm lịch sử. Quyền triển khai không thay API_Gate/PM acceptance. Xem [evidence](../../project-management/evidence/v1.5/README.md) và phần thiếu ảnh trường.

## 1. Kết quả người dùng nhận được

- **Điểm danh tự động:** giáo viên chọn lớp/buổi, bật camera; học sinh đứng vào khung. Đủ điều kiện nhận diện thì hệ thống ghi có mặt và giờ đến ngay, không có nút xác nhận danh tính từng em.
- **Không gian Đồng phục:** một mục riêng trong sidebar, có camera, khung hướng dẫn thấy mặt và phần áo, kết quả loại/màu áo, yêu cầu của buổi và danh sách nghi sai đồng phục. Dùng chung engine với Điểm danh; mỗi thời điểm chỉ chạy một camera.
- **Giáo viên xử lý ngoại lệ:** học sinh khớp đúng đồng phục được xử lý tự động. Người nghi sai đồng phục vào danh sách để giáo viên chọn/ghi lý do, lưu một thao tác; không phải xác nhận điểm danh lần nữa. Trường hợp ảnh áo chưa rõ giữ “Chưa kiểm tra”, không tự tính là đúng hoặc vi phạm.
- **Quản lý Lớp/Học sinh:** danh sách, tìm kiếm, thêm, sửa, lưu trữ/khôi phục, chuyển lớp đúng quyền; sĩ số cập nhật từ danh sách học sinh thực tế. Thêm trường sức chứa có thể chỉnh, không cho sửa sĩ số bằng cách gõ một con số không khớp hồ sơ.

Không thêm SMS, phụ huynh, cloud ảnh, worker/queue, liveness hoặc cổng tự đăng ký tài khoản. Tiếp tục Django/OpenCV local và demo Vercel SQLite tạm.

## 2. Quyết định và các phương án

Phương án đề xuất dùng YuNet/SFace đang có cho mặt, classifier đồng phục ONNX được hiệu chỉnh bằng ảnh mẫu đúng trường; tách hai không gian UI nhưng chia sẻ camera controller/API nghiệp vụ. Huấn luyện/chuẩn bị model làm offline trong môi trường công cụ riêng, runtime chỉ nạp ONNX đã kiểm chứng, không đưa PyTorch/TensorFlow vào Vercel.

Hai phương án khác được cân nhắc: chỉ dùng HSV nhẹ nhưng không nhận biết đúng mẫu/logo nên không đáp ứng yêu cầu đã chốt; so ảnh mẫu bằng đặc trưng áo có thể làm baseline trước khi fine-tune classifier, nhưng cũng phải đánh giá áo khác trường có màu giống nhau. Không dùng embedding nhận diện mặt để phân loại áo. Không chạy hai camera/pipeline đồng thời.

Người dùng đã chốt **đúng mẫu đồng phục trường, cần bộ ảnh mẫu riêng**. Dữ liệu này hiện chưa được cung cấp, là dependency thực tế của việc nghiệm thu đồng phục; CRUD và auto-face có thể triển khai trước. Không hứa hoàn tất classifier trường bằng ảnh mạng chung hoặc chỉnh HSV.

Ứng viên benchmark đầu tiên: fine-tune MobileNetV3-Small rồi export ONNX, so với baseline so đặc trưng ảnh áo. [Tài liệu Torchvision](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.mobilenet_v3_small.html) mô tả kiến trúc nhỏ/ảnh224 và weights ImageNet; đây không phải model đồng phục có sẵn. [License code](https://github.com/pytorch/vision/blob/main/LICENSE) và quyền weights/dữ liệu phải kiểm tra riêng trong task chọn model. Chưa tải/chọn/hứa hiệu năng model này cho ứng dụng.

## 3. Ghi điểm danh tự động và giới hạn Vercel

Không dùng cách JavaScript tự bấm endpoint confirm cũ. Tạo service/API auto riêng để quyết định và ghi điểm danh tại server, không gửi `identity_confirmed=true` giả và không nhận student_id từ client.

1. Giáo viên đăng nhập, chọn buổi OPEN đúng ngày/khung giờ và thuộc quyền. Chọn “Bắt đầu quét”, có nút dừng rõ ràng. STUDENT không được gọi API.
2. Camera preview chạy liên tục trên trình duyệt; mỗi request gửi một cặp ảnh khác nhau của cùng lượt quan sát. Server phát hiện đúng một mặt rõ ở cả hai ảnh, so khớp trong đúng roster còn hoạt động và yêu cầu cùng một học sinh. Cặp ảnh giúp không phải lưu trạng thái quan sát giữa các instance Vercel; **không phải chống ảnh giả/liveness**.
3. Ngưỡng auto cấu hình riêng, dự kiến bắt đầu cosine0.60 và margin0.15, cần hiệu chỉnh bằng bộ ảnh tách enrollment trước nghiệm thu. Không dùng trực tiếp ngưỡng0.45 của luồng có người xác nhận làm bảo đảm cho auto. Mờ/nhiều mặt/không khớp/kết quả khác nhau giữa hai ảnh → không ghi, UI hướng dẫn đứng lại/quét lại.
4. Mỗi request hai ảnh, dự kiến ≤1MiB/ảnh, ≤2MiB tổng và ≤4MP/ảnh. Resize/nén phía client trước gửi; backend vẫn kiểm tra. Mặc định gửi tối đa một request/4giây, không request chồng nhau, dừng khi ẩn tab/đổi lớp/logout/mất camera. Giữ budget20analysis/phút/actor ban đầu;429 dùng Retry-After. Dedupe ở server, không dựa riêng vào cooldown browser.
5. Inference trước transaction; trước khi ghi phải kiểm tra lại quyền hiện tại, buổi còn OPEN, roster, học sinh còn trong lớp/active, phiên bản mẫu/model/quy tắc và version attendance. Atomic write + idempotency + unique roster attendance. Hai tab, retry mất phản hồi hay hai lượt quét không làm ghi lặp hoặc đổi giờ đến đầu tiên.
6. Chỉ tự ghi khi attendance còn UNMARKED. Không ghi đè chỉnh sửa MANUAL hoặc ABSENT đã do nhân sự đặt; buổi CLOSED không được ghi. Manual fallback theo quyền hiện tại vẫn dùng khi nhận diện không được, không buộc confirm cho những ca auto đạt điều kiện.

Đề xuất request: `POST /api/v1/sessions/:id/auto-attendance-scans`, multipart có đúng hai file cùng tên field `images`, `scan_mode=AUTO_ATTENDANCE|UNIFORM_ONLY`, `expected_session_version`, header Idempotency-Key; reject mọi field chọn danh tính. AUTO_ATTENDANCE tạo PRESENT; UNIFORM_ONLY chỉ kiểm tra đồng phục cho người đã PRESENT, chưa điểm danh thì trả NOT_PRESENT và hướng dẫn sang tab Điểm danh. Outcome: RECORDED/ALREADY_RECORDED/UNIFORM_UPDATED/NOT_PRESENT/UNKNOWN/AMBIGUOUS/RETRY; mutation201, các kết quả không ghi200, stale409, ảnh sai422, rate429. Scope lỗi theo quy ước hiện có.

Ghi thời gian server; source vẫn VISION nhưng có mode AUTO và scan status AUTO_RECORDED riêng. Không ghi `verified_by`/`verified_at` như thể giáo viên đã xác nhận danh tính. Actor vận hành camera được ghi bằng trường attribution/audit riêng. Lịch sử CONFIRMED cũ vẫn đọc đúng nghĩa. Không lưu frame video/ảnh quét; chỉ giữ metadata/điểm/version/audit cần thiết.

SQLite Vercel vẫn tạm trên từng instance: có thể mất mẫu/điểm danh và lệch dữ liệu giữa request. Cặp ảnh cùng request giải quyết ổn định quan sát, không giải quyết chia sẻ DB. Cam kết chống ghi lặp chỉ trong cùng DB; không tuyên bố exactly-once toàn deployment. Demo giữ kiến trúc tạm đã chọn; vận hành thật phải chốt DB dùng chung trong một scope riêng.

## 4. Đồng phục và ghi lý do

Quy tắc đồng phục theo lớp và buổi, có version; tên mẫu trường, loại áo yêu cầu, nhãn model, ngưỡng và hướng dẫn lấy vùng áo. Buổi đã mở dùng snapshot model/profile; đổi profile không âm thầm sửa lịch sử. Mặt phải gắn đúng cùng người với vùng áo; không gán áo người đứng cạnh. Thiếu phần thân, logo/chi tiết quá nhỏ hoặc hai ảnh kết quả không thống nhất → UNKNOWN.

Không gian Đồng phục có phần **Mẫu đồng phục trường** do SUPERVISOR quản lý: ảnh mẫu áo sơ mi/thể dục/biến thể theo quy định, tên/nhãn/version. Mẫu áo tách hoàn toàn FaceSample. Ảnh nguồn crop vùng áo, không lưu khuôn mặt trong dataset áo; endpoint ảnh/dataset riêng tư, có scope, không public URL. Thêm ảnh không tự huấn luyện trong request hoặc tạo worker: export bộ dữ liệu riêng tư → train/evaluate offline → import model/version/hash đã kiểm chứng → publish profile dùng cho buổi mới. Profile/model version đang dùng không bị ghi đè.

Mục tiêu thu thập ban đầu: khoảng100–200ảnh crop độc lập/mẫu áo cùng ảnh OTHER, gồm áo thường/đồng phục trường khác có màu giống, logo khác và ảnh thiếu/che logo. Đây là mục tiêu khởi đầu để đo, không bảo đảm đủ dữ liệu. Chia train/validation/test theo người và buổi chụp, không để bản augment/crop của cùng ảnh lọt sang test. Bộ test nên có ít nhất30ảnh độc lập/mẫu và60ảnh đối chứng khó; ghi số lượng thực tế nếu chưa đạt. Đánh giá confusion matrix, precision/recall từng mẫu, nhầm đồng phục trường khác thành đúng, tỷ lệ UNKNOWN, tốc độ/bundle. Mục tiêu ban đầu precision tự kết luận đúng ≥95% trên bộ test đó và công bố coverage; nếu không đạt thì tiếp tục thu thập/điều chỉnh, không hạ ngưỡng để tạo demo đẹp. Đây không phải cam kết accuracy toàn trường.

Nếu thiếu/hỏng/chưa duyệt model đồng phục thì không tự gán COMPLIANT; trả trạng thái chưa kiểm tra/bộ nhận diện chưa sẵn sàng. Auto-face vẫn có thể ghi có mặt, tách khỏi việc classifier áo chưa đủ điều kiện nghiệm thu. HSV cũ chỉ là thông tin phụ/baseline, không thay thế model trường.

Luồng đề xuất:

| Quan sát | Điểm danh | Đồng phục | Giáo viên làm gì |
| --- | --- | --- | --- |
| Mặt đạt điều kiện, áo khớp rõ | Tự PRESENT | COMPLIANT, nguồn AUTO | Không thao tác |
| Mặt đạt, áo nghi không khớp | Tự PRESENT | REVIEW_REQUIRED | Ghi/chọn lý do rồi lưu NON_COMPLIANT |
| Mặt đạt, không rõ áo | Tự PRESENT | NOT_CHECKED | Quét lại áo hoặc ghi vi phạm nếu quan sát thực tế thấy sai |
| Mặt không đạt | Không tự ghi | Không gán kết quả cho học sinh | Quét lại/manual fallback |

REVIEW_REQUIRED là trạng thái đề xuất mới, không đồng nghĩa vi phạm đã được xác nhận. Giáo viên chỉ phải ghi lý do cho ca thực sự vi phạm. Ca cảnh báo nhầm có thao tác bỏ cảnh báo/ghi đúng đồng phục; thao tác đó chỉ áp dụng ngoại lệ, không xuất hiện bắt buộc cho mọi học sinh. UI hiển thị ghi chú của giáo viên và nguồn auto/human khác nhau. Sau khi giáo viên sửa, quét tự động không được ghi đè lý do/kết quả đó.

Mẫu lý do đơn giản: không mặc áo theo quy định, mặc sai loại của buổi, áo khoác che đồng phục, lý do khác kèm mô tả; đây là danh sách lựa chọn UI, không tạo thêm module phê duyệt. NON_COMPLIANT bắt buộc có lý do. Không tự điền lời giải thích do hệ thống đoán như thể giáo viên đã nhập. Báo cáo tách confirmed violation / cần xem lại / chưa kiểm tra.

## 5. CRUD, sĩ số và lịch sử

Hiện tại đã có GET/POST lớp, PATCH lớp, GET/POST học sinh, GET/PATCH hồ sơ, chuyển lớp supervisor và ảnh/mẫu private. Cần mở rộng/giao diện, không làm lại toàn bộ.

| Đối tượng | Trường/chức năng dự kiến | Quyền |
| --- | --- | --- |
| Lớp | Mã, tên, khối, GVCN, sức chứa, active/version; chi tiết/sĩ số; tạo/sửa/lưu trữ/khôi phục | SUPERVISOR quản lý; GVCN đọc lớp được giao |
| Học sinh | Mã, họ tên, lớp, active/version; ảnh hồ sơ và enrollment tách nhau | GVCN thêm/sửa tên/trạng thái trong lớp; SUPERVISOR sửa mã/chuyển lớp/lưu trữ/khôi phục toàn phạm vi |
| Sĩ số | active_student_count và tổng hồ sơ tự tính; capacity chỉnh được | Không nhận `student_count` từ body để tạo sĩ số giả |

Demo ban đầu capacity tối đa50 khớp giới hạn face roster hiện tại; giảm capacity dưới sĩ số active trả409, không tự xóa học sinh. Mã lớp/học sinh phải unique. Version chống ghi đè khi hai người cùng sửa.

Xóa trong UI là lưu trữ có thể khôi phục, không hard-delete dữ liệu liên kết. Lớp còn học sinh active hoặc buổi OPEN không được lưu trữ trước khi xử lý; lịch sử, báo cáo và scope cũ vẫn đọc đúng. Học sinh inactive không vào nhận diện mới, scan chờ bị vô hiệu; crop không public và không tự xóa lịch sử điểm danh. Chuyển lớp kiểm tra cả nguồn/đích, sức chứa và quyền, không chuyển bởi GVCN; thay tên/lớp/mã không viết lại snapshot roster cũ.

Thêm học sinh mặc định áp dụng cho buổi mở sau. Có thao tác riêng **“Bổ sung vào buổi đang mở”** do SUPERVISOR thực hiện, với version buổi/sĩ số và audit: chỉ thêm roster+UNMARKED cho hồ sơ active đúng lớp, không rebuild/xóa/sửa các hàng đã điểm danh. Đây là ngoại lệ bổ sung có kiểm soát cho roster snapshot, phải được ghi rõ trong contracts trước triển khai.

API dự kiến bổ sung GET/PATCH/DELETE lớp chi tiết (DELETE=lưu trữ), PATCH khôi phục; PATCH/DELETE học sinh tương tự; endpoint bổ sung roster OPEN; uniform profile scoped và uniform review update. Tất cả read/write/photo/export vẫn kiểm tra role tại server, STUDENT dùng session cho chính mình, không được ghi danh tính tự chọn.

## 6. Thứ tự, nghiệm thu và ranh giới

Thứ tự: chốt contracts/schema → hoàn thiện CRUD backend → đồng phục và auto backend → CRUD/camera/ngoại lệ UI → report/export → test camera + Vercel/review. Member1 sở hữu accounts/academics/students/reports; Member2 sở hữu schedules/attendance/vision; core/enums/contracts và migration liên app chốt chung trước khi viết.

Nghiệm thu quan trọng: tự ghi đúng học sinh ngoài bộ mẫu mà không confirm; người lạ/nhiều người/không chắc không tự ghi; retry/concurrency chỉ một kết quả trên cùng DB; giáo viên chỉ ghi lý do vi phạm; UNKNOWN không thành đạt/vi phạm; teacher correction không bị auto đè; CRUD/sĩ số/chuyển lớp/archive không phá lịch sử; scope/CSRF/export đúng; API không cần secret/model network trong request. Không lấy bộ test hiện tại thay bằng chứng cho tính năng mới.

Thiết kế đã được cho triển khai; trạng thái từng task trong [task breakdown](../plans/2026-10-18-auto-attendance-uniform-crud.md) và tracker mới. Không thay PM acceptance và không deploy.
