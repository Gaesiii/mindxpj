# Điểm danh học sinh — Django + OpenCV MVP

Bản nâng cấp YuNet + SFace: **203 test đạt**, kiểm thử trình duyệt thật nhận đúng ảnh ngoài bộ mẫu và từ chối ảnh người khác. [Bằng chứng và giới hạn](docs/project-management/evidence/sface-upgrade/README.md). Mẫu LBPH cũ cần đăng ký lại3–10ảnh.

Chạy giao diện demo: `backend/.venv/Scripts/python.exe .document-tools/run_demo.py`, mở `http://127.0.0.1:8000/`; lấy đăng nhập trong file local launcher chỉ ra. [Kiểm chứng UI phiên bản trước](docs/project-management/evidence/ui-demo/README.md). DB demo riêng, không thay dữ liệu gốc.

Nguồn chuẩn là [thiết kế v1.4](docs/thiet-ke-he-thong-diem-danh.md), thay đường QR hoạt động bằng nhận diện mặt YuNet + SFace FP32 và gợi ý đồng phục HSV OpenCV có nhân sự xác nhận bắt buộc. Scan không tự ghi PRESENT; manual là phương án dự phòng. QR giữ lịch sử và migrations, mặc định tắt qua QR_ENABLED=false.

Demo Vercel: [hướng dẫn setup](docs/deploy-vercel-demo.md), Root Directory `backend`, chỉ cần `DJANGO_SECRET_KEY` và `DEMO_PASSWORD`. SQLite tạm tự tạo, không cần dịch vụ database; dữ liệu mới không đồng bộ giữa các instance và có thể mất khi khởi động lại.

- [Hợp đồng API](docs/api-contract.md), [request collection](api-requests.http), [backend setup](backend/README.md).
- [Hướng dẫn demo, đăng ký mẫu và checklist](docs/huong-dan-demo-opencv.md), [PowerPoint 7 slide có speaker notes](docs/thuyet-trinh-opencv.pptx).
- [Kế hoạch OpenCV](docs/superpowers/plans/2026-10-18-opencv-demo.md), [tracker](docs/project-management/README.md), [PM acceptance](docs/api-acceptance.md).
- [Thiết kế v1.2 lịch sử](docs/archive/thiet-ke-he-thong-diem-danh-v1.2.md); evidence backend QR cũ không thay kết quả vision mới.

mem1 giữ accounts/academics/students/photos/reports; mem2 giữ schedules/attendance/vision và QR legacy. Mẫu nhận diện là crop màu112x112 và embedding128chiều private trong DB, không phải ảnh hồ sơ; không lưu frame scan/video. Chưa có bằng chứng camera thật, accuracy hay chống ảnh giả.

API_Gate = **NOT_APPROVED**. UI local tại `/` đã triển khai theo yêu cầu18/10/2026 “làm luôn UI để demo”, ngoại lệ trước gate; đây không phải PM phê duyệt API. Có staff console đăng nhập, tổng quan, điểm danh, học sinh/enrollment, lịch/buổi, camera/upload/xác nhận, manual/uniform và báo cáo/export. STUDENT không được dùng console, API scope giữ nguyên. Browser/full-suite và thiết bị thật cần evidence riêng; không suy hoàn tất từ việc có UI. Task chỉ hoàn tất khi có implementation, validation và review; không tự tick Finish?. Không deploy/chia sẻ ngoài/gửi lời mời. GitHub push to Gaesiii/mindxpj and Vercel demo preparation are authorized; live deployment is a separate action.


Nâng cấp SFace v1.4: chạy `manage.py prepare_vision_models` trong backend (launcher tự chuẩn bị model); model pin hash tải trước khi chạy/build, không tải ở request. Mẫu LBPH cũ cần đăng ký lại3–10ảnh; kiểm tra usable_sample_count/requires_reenrollment. DB local hiện có được backup/migrate, không seed lại; dùng tài khoản cũ để enrollment. Cosine không phải phần trăm chính xác; không bảo đảm liveness. [Kế hoạch nâng cấp](docs/superpowers/plans/2026-10-18-sface-upgrade.md) và [nghiên cứu](docs/nghien-cuu-nhan-dien-khuon-mat.md) là nguồn bối cảnh; evidence trước SFace không chứng minh bản nâng cấp đã hoàn tất. Giữ license model trong backend/third_party/opencv_zoo.
