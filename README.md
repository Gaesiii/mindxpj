# Điểm danh học sinh — Django + OpenCV MVP v1.5

Hệ thống quản lý lớp/học sinh, lịch/buổi, tự điểm danh bằng YuNet + SFace, kiểm tra đồng phục và báo cáo Excel/CSV. Luồng hiện tại tự ghi có mặt khi cặp ảnh đủ điều kiện, không cần xác nhận từng học sinh; vẫn có nhập thủ công.

**Đọc trước:** [Báo cáo tổng quan và hướng dẫn sử dụng v1.5](docs/bao-cao-tong-quan-va-huong-dan-su-dung-v1.5.md) · [Tải bản Word](docs/bao-cao-tong-quan-va-huong-dan-su-dung-v1.5.docx).

Đợt kiểm chứng19/10/2026 ghi nhận **255 tests đạt**, browser/API với ảnh mặt thật, kiểm tra retry/concurrency và build Vercel local. [Evidence và giới hạn](docs/project-management/evidence/v1.5/README.md). Plan mới hoàn tất kỹ thuật21/26task; năm task còn lại cần bộ ảnh đồng phục trường/model và thiết bị thật. **Nhận diện đúng mẫu áo trường chưa được nghiệm thu**: thiếu model/ảnh không chắc giữ Chưa kiểm tra, không dùng HSV kết luận đúng logo.

Chạy demo từ thư mục gốc sau khi chuẩn bị Python3.12/virtualenv/dependencies:

```powershell
backend/.venv/Scripts/python.exe .document-tools/run_demo.py
```

Mở `http://127.0.0.1:8000/`, lấy tài khoản/mật khẩu từ file runtime launcher chỉ ra. Launcher mới tạo DB demo riêng; dùng `--resume-runtime` với đúng thư mục cũ để giữ dữ liệu. [Hướng dẫn cài đặt và thao tác](docs/bao-cao-tong-quan-va-huong-dan-su-dung-v1.5.md).

- [Thiết kế chuẩn v1.5](docs/thiet-ke-he-thong-diem-danh.md), [API contract](docs/api-contract.md), [backend setup](backend/README.md).
- [Kế hoạch/task v1.5](docs/superpowers/plans/2026-10-18-auto-attendance-uniform-crud.md), [tracker CSV](docs/project-management/auto-attendance-uniform-crud-tasks.csv).
- [Pipeline đồng phục offline](tools/uniform_training/README.md), [hướng dẫn demo](docs/huong-dan-demo-opencv.md), [PowerPoint7slide có notes](docs/thuyet-trinh-opencv.pptx).
- [Tự deploy Vercel](docs/deploy-vercel-demo.md): Root Directory `backend`, hai biến `DJANGO_SECRET_KEY`/`DEMO_PASSWORD`. SQLite/ảnh/mẫu tạm theo instance, không đồng bộ và có thể mất; không thay database bền vững.

GVCN chỉ lớp được giao; giám thị toàn phạm vi; STUDENT không dùng staff console. Ảnh hồ sơ, mẫu mặt và áo tách riêng/private; không lưu video/frame quét. QR mặc định tắt, giữ dữ liệu/migrations cũ. Cosine không phải phần trăm chính xác và không có liveness guarantee.

Member1: accounts/academics/students/reports; Member2: schedules/attendance/vision/QR legacy; core/config/contracts/migrations phối hợp chung. **API_Gate=NOT_APPROVED** là PM acceptance riêng. Người dùng đã cho phép UI local, triển khai plan, push repository và chuẩn bị Vercel; việc deploy thực không được thực hiện trong các lượt bàn giao này.

- [So sánh engine với source Face Attendance (21/10/2026)](docs/so-sanh-nhan-dien-face-attendance-2026-10-21.md): giữ YuNet + SFace theo kết quả benchmark local.

- [Khảo sát GitHub nhận diện đồng phục qua camera (21/10/2026)](docs/nghien-cuu-github-nhan-dien-dong-phuc-2026-10-21.md).

- [Thử nghiệm dataset đồng phục KV (21/10/2026)](docs/thu-nghiem-dataset-dong-phuc-kv-2026-10-21.md): dataset/model local, kết quả và cách test ảnh.

- [Demo đồng phục KV để quay gửi PM (22/10/2026)](docs/demo-dong-phuc-cho-pm-2026-10-22.md): UI local, ảnh mẫu, camera và kịch bản quay.

- [Ảnh mẫu face từ camera độ phân giải cao](docs/anh-mau-face-do-phan-giai-cao-2026-10-22.md): chọn ảnh gốc tới32MiB/120MP, UI tự tối ưu.
