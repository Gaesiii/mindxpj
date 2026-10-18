/**
 * Task tracker MVP: run createTaskSheet() once in Google Apps Script.
 * No sharing/invitations. Existing tracker is reused on subsequent runs.
 */
const TASKS = [
  {
    "id": "A01",
    "module": "Nền tảng",
    "phase": "API",
    "owner": 1,
    "start_day": 1,
    "end_day": 1,
    "hours": 5,
    "deps": [],
    "title": "Thiết lập project Django, custom User và quy ước API",
    "deliverable": "manage.py; config; accounts/models.py; requirements.txt",
    "acceptance": "Django check/migrate chạy trên DB rỗng; không dùng User mặc định rồi đổi sau"
  },
  {
    "id": "B01",
    "module": "Hợp đồng module",
    "phase": "API",
    "owner": 2,
    "start_day": 1,
    "end_day": 1,
    "hours": 5,
    "deps": [],
    "title": "Chốt v1.3 schema/vision/source VISION và migration chéo",
    "deliverable": "docs/api-contract.md; core/enums.py",
    "acceptance": "mem1/mem2 phối hợp scope/mẫu private, vision contract và migration; QR giữ lịch sử, gate NOT_APPROVED"
  },
  {
    "id": "A02",
    "module": "M01 Tài khoản",
    "phase": "API",
    "owner": 1,
    "start_day": 2,
    "end_day": 2,
    "hours": 6,
    "deps": [
      "A01",
      "B01"
    ],
    "title": "API login/logout/me và cấp tài khoản tối thiểu",
    "deliverable": "accounts/views.py; services.py; urls.py",
    "acceptance": "Đăng nhập 3 vai trò; STUDENT chỉ bản thân; logout thu hồi phiên; CSRF đúng"
  },
  {
    "id": "B02",
    "module": "M04 Lịch",
    "phase": "API",
    "owner": 2,
    "start_day": 2,
    "end_day": 2,
    "hours": 4,
    "deps": [
      "B01"
    ],
    "title": "Đặc tả lịch tuần, session và snapshot; viết ca kiểm chứng",
    "deliverable": "schedules/README.md; tests/test_schedules.py",
    "acceptance": "Có ca sáng/chiều, sơ mi/thể dục, mở buổi lặp; chưa phụ thuộc migration lớp"
  },
  {
    "id": "A03",
    "module": "M02 Khối/lớp",
    "phase": "API",
    "owner": 1,
    "start_day": 3,
    "end_day": 3,
    "hours": 6,
    "deps": [
      "A02"
    ],
    "title": "Model và API khối, lớp, gán một GVCN",
    "deliverable": "academics/models.py; services.py; views.py",
    "acceptance": "Một lớp một GVCN; giám thị quản lý tất cả; giáo viên chỉ lớp được giao"
  },
  {
    "id": "B03",
    "module": "M04 Lịch",
    "phase": "API",
    "owner": 2,
    "start_day": 3,
    "end_day": 3,
    "hours": 4,
    "deps": [
      "B02"
    ],
    "title": "Chốt đầu vào/đầu ra lịch với model lớp/học sinh",
    "deliverable": "docs/api-contract.md; schedules/forms.py",
    "acceptance": "Có class_id, weekday, slot, start_time, grace_minutes, uniform_type; không thêm module ngoài MVP"
  },
  {
    "id": "A04",
    "module": "M03 Học sinh",
    "phase": "API",
    "owner": 1,
    "start_day": 4,
    "end_day": 4,
    "hours": 5,
    "deps": [
      "A03"
    ],
    "title": "Model học sinh và API thêm/xem theo lớp",
    "deliverable": "students/models.py; services.py; views.py",
    "acceptance": "Họ tên, mã, lớp/khối; trùng tên được, trùng mã bị chặn; lớp ngoài quyền trả 403/404"
  },
  {
    "id": "B04",
    "module": "M04 Lịch",
    "phase": "API",
    "owner": 2,
    "start_day": 4,
    "end_day": 4,
    "hours": 6,
    "deps": [
      "A03",
      "B03"
    ],
    "title": "Model và API lịch tuần theo lớp",
    "deliverable": "schedules/models.py; services.py; views.py",
    "acceptance": "Lưu giờ vào học và SHIRT/SPORTS; không có hai rule trùng thứ/slot/lớp"
  },
  {
    "id": "A05",
    "module": "M03 Học sinh",
    "phase": "API",
    "owner": 1,
    "start_day": 5,
    "end_day": 5,
    "hours": 6,
    "deps": [
      "A04"
    ],
    "title": "API cập nhật, tìm kiếm và tài khoản học sinh theo session",
    "deliverable": "students/forms.py; accounts/services.py",
    "acceptance": "Sửa đúng phạm vi; student user liên kết một hồ sơ; không trả mật khẩu trong danh sách"
  },
  {
    "id": "B05",
    "module": "M04 Buổi học",
    "phase": "API",
    "owner": 2,
    "start_day": 5,
    "end_day": 5,
    "hours": 6,
    "deps": [
      "A04",
      "B04"
    ],
    "title": "Tạo buổi từ lịch theo ngày, lấy danh sách học sinh snapshot",
    "deliverable": "schedules/services.py; models.py",
    "acceptance": "Unique lớp/ngày/buổi; roster lấy học sinh active; sửa lịch không đổi snapshot buổi đã mở"
  },
  {
    "id": "A06",
    "module": "M03 Ảnh",
    "phase": "API",
    "owner": 1,
    "start_day": 6,
    "end_day": 6,
    "hours": 6,
    "deps": [
      "A05"
    ],
    "title": "Ảnh private và review enrollment metadata/scope học sinh",
    "deliverable": "students/services.py; views.py; core/storage.py",
    "acceptance": "Ảnh profile private; không tự enroll; sample GET không bytes, staff scope và DELETE/re-enroll làm proposal cũ vô hiệu"
  },
  {
    "id": "B06",
    "module": "M04 Buổi học",
    "phase": "API",
    "owner": 2,
    "start_day": 6,
    "end_day": 6,
    "hours": 5,
    "deps": [
      "B05",
      "A05"
    ],
    "title": "API mở/chốt buổi tối thiểu và tạo attendance UNMARKED",
    "deliverable": "schedules/services.py; attendance/models.py",
    "acceptance": "Mở lặp không nhân đôi; chốt có cảnh báo chưa ghi nhận; chốt giữ NOT_CHECKED"
  },
  {
    "id": "A07",
    "module": "M01–M03 Quyền",
    "phase": "API",
    "owner": 1,
    "start_day": 7,
    "end_day": 7,
    "hours": 5,
    "deps": [
      "A06",
      "A03"
    ],
    "title": "Kiểm chứng quyền tài khoản, lớp, học sinh và ảnh",
    "deliverable": "tests/test_permissions.py; test_students.py",
    "acceptance": "Teacher A không đọc/sửa/tải ảnh lớp B; student không đọc roster; supervisor được toàn trường"
  },
  {
    "id": "B07",
    "module": "M05 Điểm danh",
    "phase": "API",
    "owner": 2,
    "start_day": 7,
    "end_day": 7,
    "hours": 6,
    "deps": [
      "B06"
    ],
    "title": "API roster, điểm danh thủ công/vắng và thời gian đến",
    "deliverable": "attendance/services.py; views.py; forms.py",
    "acceptance": "PRESENT có arrived_at; đúng giờ/muộn theo server và snapshot; vắng không có giờ đến"
  },
  {
    "id": "A08",
    "module": "M07 Báo cáo",
    "phase": "API",
    "owner": 1,
    "start_day": 8,
    "end_day": 8,
    "hours": 5,
    "deps": [
      "B06",
      "A07"
    ],
    "title": "Viết query báo cáo bằng fixture, công thức tổng hợp",
    "deliverable": "reports/queries.py; tests/test_reports.py",
    "acceptance": "Phân biệt có mặt/vắng/chưa ghi nhận; không đếm buổi chưa mở; quyền lớp được lọc ở query"
  },
  {
    "id": "B08",
    "module": "M05 Điểm danh",
    "phase": "API",
    "owner": 2,
    "start_day": 8,
    "end_day": 8,
    "hours": 5,
    "deps": [
      "B07"
    ],
    "title": "Version, unique, retry chống điểm danh trùng và lỗi mạng",
    "deliverable": "attendance/services.py; core/idempotency.py; tests/test_attendance.py",
    "acceptance": "Retry cùng key không nhân đôi; 07:05:00 đúng giờ, 07:05:01 muộn; không báo lưu thành công nếu lỗi"
  },
  {
    "id": "A09",
    "module": "M07 Báo cáo",
    "phase": "API",
    "owner": 1,
    "start_day": 9,
    "end_day": 9,
    "hours": 5,
    "deps": [
      "A08",
      "B08"
    ],
    "title": "API báo cáo chi tiết/tổng hợp, lọc ngày/lớp/khối",
    "deliverable": "reports/views.py; forms.py; urls.py",
    "acceptance": "Bộ lọc ngoài quyền bị chặn; tổng đúng với dữ liệu attendance thực; mẫu số 0 hiển thị rõ"
  },
  {
    "id": "B09",
    "module": "M05 Vision",
    "phase": "API",
    "owner": 2,
    "start_day": 9,
    "end_day": 9,
    "hours": 6,
    "deps": [
      "B08",
      "A05"
    ],
    "title": "Engine Haar/LBPH/HSV và đăng ký mẫu private",
    "deliverable": "vision/engine.py; models; enrollment API; tests/test_vision_engine.py",
    "acceptance": "3–10 ảnh thay nguyên tử,128x128 private; LBPH match/unknown/ambiguous; HSV UNKNOWN khi thiếu vùng áo; không cam kết accuracy"
  },
  {
    "id": "A10",
    "module": "M07 Xuất XLSX",
    "phase": "API",
    "owner": 1,
    "start_day": 10,
    "end_day": 10,
    "hours": 6,
    "deps": [
      "A09"
    ],
    "title": "Xuất Excel chi tiết/tổng hợp bằng openpyxl",
    "deliverable": "reports/exporters.py; services.py",
    "acceptance": "Tối đa 5.000 dòng, đúng bộ lọc/quyền; không chạy formula do nội dung người dùng"
  },
  {
    "id": "B10",
    "module": "M05 Vision",
    "phase": "API",
    "owner": 2,
    "start_day": 10,
    "end_day": 10,
    "hours": 6,
    "deps": [
      "B09"
    ],
    "title": "API staff phân tích một ảnh theo roster và queue proposal",
    "deliverable": "vision scan POST/GET; tests/test_vision_api.py",
    "acceptance": "staff scope; STUDENT403; single image2MiB/4MP; roster50;20/phút; PENDING không PRESENT; expiry120s; Idempotency-Key"
  },
  {
    "id": "A11",
    "module": "M07 Xuất CSV",
    "phase": "API",
    "owner": 1,
    "start_day": 11,
    "end_day": 11,
    "hours": 5,
    "deps": [
      "A10"
    ],
    "title": "CSV UTF-8 BOM, endpoint download và metadata",
    "deliverable": "reports/exporters.py; views.py; core/storage.py",
    "acceptance": "Đúng dấu tiếng Việt/timezone; tải kiểm tra quyền; XLSX và CSV đối soát cùng dữ liệu"
  },
  {
    "id": "B11",
    "module": "M05 Vision xác minh",
    "phase": "API",
    "owner": 2,
    "start_day": 11,
    "end_day": 11,
    "hours": 6,
    "deps": [
      "B10"
    ],
    "title": "API confirm/reject proposal và manual fallback",
    "deliverable": "vision/services.py; confirm/reject; attendance source migration",
    "acceptance": "identity_confirmed bắt buộc; scan/attendance version, sample revision, OPEN/time; retry; manual/close/transfer/re-enroll/delete vô hiệu proposal"
  },
  {
    "id": "A12",
    "module": "M07 Báo cáo",
    "phase": "API",
    "owner": 1,
    "start_day": 12,
    "end_day": 12,
    "hours": 6,
    "deps": [
      "A11",
      "B11"
    ],
    "title": "Đối soát report VISION/manual và đồng phục",
    "deliverable": "tests/test_report_reconciliation.py; reports/queries.py",
    "acceptance": "PENDING không PRESENT; VISION arrived_at=scanned_at; JSON/XLSX/CSV khớp; QR chỉ lịch sử"
  },
  {
    "id": "B12",
    "module": "M06 Đồng phục",
    "phase": "API",
    "owner": 2,
    "start_day": 12,
    "end_day": 12,
    "hours": 6,
    "deps": [
      "B11"
    ],
    "title": "Uniform staff quyết định và confirm vision nguyên tử",
    "deliverable": "attendance/uniform_rules.py; forms.py; services.py",
    "acceptance": "HSV chỉ gợi ý; UNKNOWN không tự đạt/vi phạm; invalid uniform rollback cả confirm/attendance/log"
  },
  {
    "id": "A13",
    "module": "Tích hợp API",
    "phase": "API",
    "owner": 1,
    "start_day": 13,
    "end_day": 13,
    "hours": 6,
    "deps": [
      "A12",
      "B12"
    ],
    "title": "Kiểm chứng quyền xuyên suốt và tải file/ảnh",
    "deliverable": "tests/test_api_permissions.py; test_reports.py",
    "acceptance": "Học sinh không xuất data; giáo viên xuất lớp mình; đổi ID không vượt quyền; trường bắt buộc validate"
  },
  {
    "id": "B13",
    "module": "Tích hợp API",
    "phase": "API",
    "owner": 2,
    "start_day": 13,
    "end_day": 13,
    "hours": 6,
    "deps": [
      "B12"
    ],
    "title": "Kiểm chứng vision→staff confirm→uniform→close",
    "deliverable": "tests/test_full_flow.py; test_qr.py",
    "acceptance": "Mẫu/ảnh/scope/version/expiry/retry; manual fallback; QR mặc định tắt; migrate mới và nâng cấp"
  },
  {
    "id": "A14",
    "module": "API docs/seed",
    "phase": "API",
    "owner": 1,
    "start_day": 14,
    "end_day": 14,
    "hours": 5,
    "deps": [
      "A13"
    ],
    "title": "Dữ liệu giả và request collection cho PM nghiệm thu",
    "deliverable": "management command seed_demo; docs/api-contract.md; api-requests.http",
    "acceptance": "2 lớp/20 học sinh giả, tài khoản các vai trò; PM gọi API không cần giao diện"
  },
  {
    "id": "B14",
    "module": "API hoàn thiện",
    "phase": "API",
    "owner": 2,
    "start_day": 14,
    "end_day": 14,
    "hours": 5,
    "deps": [
      "B13"
    ],
    "title": "Sửa lỗi vision và viết hướng dẫn demo OpenCV",
    "deliverable": "docs/huong-dan-demo-opencv.md; api-requests.http; evidence",
    "acceptance": "Setup/enrollment/API/presentation5–7phút; synthetic không chứng minh camera/accuracy/liveness"
  },
  {
    "id": "A15",
    "module": "API gate",
    "phase": "API",
    "owner": 1,
    "start_day": 15,
    "end_day": 15,
    "hours": 4,
    "deps": [
      "A14",
      "B14"
    ],
    "title": "Review API gate với PM: auth/lớp/học sinh/report/export",
    "deliverable": "docs/api-acceptance.md; link evidence",
    "acceptance": "PM có test result, collection và file export; chưa mở frontend khi còn lỗi chặn luồng"
  },
  {
    "id": "B15",
    "module": "API gate",
    "phase": "API",
    "owner": 2,
    "start_day": 15,
    "end_day": 15,
    "hours": 4,
    "deps": [
      "B14",
      "A14"
    ],
    "title": "PM review API gate lịch/attendance/vision/uniform",
    "deliverable": "docs/api-acceptance.md; link evidence",
    "acceptance": "PM đọc evidence mới và giới hạn camera/HSV; không dùng126test QR cũ; gate NOT_APPROVED cho tới quyết định PM"
  },
  {
    "id": "A16",
    "module": "UI M01–M03",
    "phase": "FRONTEND_LATER",
    "owner": 1,
    "start_day": 16,
    "end_day": 16,
    "hours": 5,
    "deps": [
      "A15",
      "B15"
    ],
    "title": "Sau API gate: giao diện đăng nhập, lớp và học sinh tối thiểu",
    "deliverable": "Tạo frontend Django Templates sau PM duyệt",
    "acceptance": "Dùng API/service đã ổn định; không tạo frontend ở giai đoạn hiện tại"
  },
  {
    "id": "B16",
    "module": "UI M04–M05",
    "phase": "FRONTEND_LATER",
    "owner": 2,
    "start_day": 16,
    "end_day": 16,
    "hours": 5,
    "deps": [
      "A15",
      "B15"
    ],
    "title": "Sau API gate: giao diện lịch và danh sách điểm danh",
    "deliverable": "Tạo frontend Django Templates sau PM duyệt",
    "acceptance": "Hiển thị trạng thái và giờ từ server; không tính quyền/thời gian ở client"
  },
  {
    "id": "A17",
    "module": "UI M03/M07",
    "phase": "FRONTEND_LATER",
    "owner": 1,
    "start_day": 17,
    "end_day": 17,
    "hours": 6,
    "deps": [
      "A16"
    ],
    "title": "Sau API gate: upload ảnh, bộ lọc báo cáo và xuất file",
    "deliverable": "Templates học sinh/báo cáo sau PM duyệt",
    "acceptance": "Upload lỗi giữ ảnh cũ; đúng quyền lớp; xuất được XLSX/CSV"
  },
  {
    "id": "B17",
    "module": "UI Vision",
    "phase": "FRONTEND_LATER",
    "owner": 2,
    "start_day": 17,
    "end_day": 17,
    "hours": 6,
    "deps": [
      "B16"
    ],
    "title": "Sau API gate: camera chụp ảnh, gợi ý và queue vision",
    "deliverable": "Templates/JavaScript vision sau PM duyệt",
    "acceptance": "Chỉ sau gate; staff xác nhận bắt buộc, lỗi/từ chối camera có manual fallback; không tự PRESENT"
  },
  {
    "id": "A18",
    "module": "UI M07 hoàn thiện",
    "phase": "FRONTEND_LATER",
    "owner": 1,
    "start_day": 18,
    "end_day": 18,
    "hours": 5,
    "deps": [
      "A17"
    ],
    "title": "Sau API gate: tổng hợp báo cáo, lỗi và trạng thái đang lưu",
    "deliverable": "Templates báo cáo/học sinh sau PM duyệt",
    "acceptance": "Tổng khớp API; lỗi không báo thành công; mã/tên/lớp rõ"
  },
  {
    "id": "B18",
    "module": "UI M06 hoàn thiện",
    "phase": "FRONTEND_LATER",
    "owner": 2,
    "start_day": 18,
    "end_day": 18,
    "hours": 5,
    "deps": [
      "B17"
    ],
    "title": "Sau API gate: xác minh và đồng phục cùng form, chốt buổi",
    "deliverable": "Templates xác minh/đồng phục sau PM duyệt",
    "acceptance": "Không mặc định đạt; chốt cảnh báo pending/chưa ghi nhận; giữ NOT_CHECKED"
  },
  {
    "id": "A19",
    "module": "Nghiệm thu MVP",
    "phase": "QA",
    "owner": 1,
    "start_day": 19,
    "end_day": 19,
    "hours": 6,
    "deps": [
      "A18",
      "B18"
    ],
    "title": "Kiểm chứng luồng thật và quyền/report trên dữ liệu giả",
    "deliverable": "docs/mvp-acceptance.md; evidence",
    "acceptance": "Teacher/supervisor/student chạy đúng quyền; số liệu/file khớp; PM ghi comment từng lỗi"
  },
  {
    "id": "B19",
    "module": "Nghiệm thu MVP",
    "phase": "QA",
    "owner": 2,
    "start_day": 19,
    "end_day": 19,
    "hours": 6,
    "deps": [
      "A18",
      "B18"
    ],
    "title": "Kiểm chứng thiết bị OpenCV, đồng phục và fallback",
    "deliverable": "docs/mvp-acceptance.md; evidence",
    "acceptance": "Camera thật/quyền/mạng/retry, mặt lạ/mờ/nhiều người, áo bị che; log riêng enrollment/evaluation; không cam kết chống ảnh giả"
  },
  {
    "id": "A20",
    "module": "Bàn giao",
    "phase": "QA",
    "owner": 1,
    "start_day": 20,
    "end_day": 20,
    "hours": 4,
    "deps": [
      "A19",
      "B19"
    ],
    "title": "Sửa lỗi còn lại, README setup và kịch bản thi",
    "deliverable": "README.md; docs/demo-script.md; evidence",
    "acceptance": "Setup từ máy sạch theo README; migrations/seed/test có hướng dẫn; PM duyệt bàn giao"
  },
  {
    "id": "B20",
    "module": "Bàn giao",
    "phase": "QA",
    "owner": 2,
    "start_day": 20,
    "end_day": 20,
    "hours": 4,
    "deps": [
      "A19",
      "B19"
    ],
    "title": "Regression API/vision/uniform và chạy demo cuối",
    "deliverable": "docs/mvp-acceptance.md; evidence",
    "acceptance": "Full validation và independent review; report/export đối soát; chưa tick finish nếu real-device/PM review còn chờ"
  }
];
const HEADERS = ["ID","Module","Phase","Task","Owner","Reviewer","Start day","End day","Start date","Due date","Hours","Dependencies","Deliverable","Acceptance","Finish?","Status","Ready / Blocked","PM Comment","Evidence / PR","Actual Finish","Dev Note"];

function createTaskSheet() {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    const props = PropertiesService.getScriptProperties();
    const existingId = props.getProperty("MVP_TASK_SHEET_ID");
    if (existingId) {
      const existing = SpreadsheetApp.openById(existingId);
      console.log(existing.getUrl());
      return existing.getUrl();
    }
    const ss = SpreadsheetApp.create("MVP diem danh - 2 members - 1 month");
    ss.setSpreadsheetLocale("en_US");
    ss.setSpreadsheetTimeZone("Asia/Ho_Chi_Minh");
    const config = ss.getSheets()[0].setName("Config");
    const configRows = [
      ["Setting","Value","Notes"],
      ["Start date",new Date(2026,9,12),"Đổi ngày bắt đầu; lịch nghỉ thứ Bảy/Chủ Nhật"],
      ["Member 1","mem1","Đổi tên tại đây"],
      ["Member 2","mem2","Đổi tên tại đây"],
      ["PM","PM","Người review/ghi comment"],
      ["API_Gate","NOT_APPROVED","PM chọn APPROVED sau khi toàn bộ API có evidence"],
      ["Capacity hours/day",6,"Giả định mỗi người; không tự cộng giờ khi đổi giá trị"],
      ["Working days",20,"Khung một tháng"],
      ["Scope","MVP only","v1.3; local UI user-authorized before gate; PM NOT_APPROVED"]
    ];
    config.getRange(1,1,configRows.length,3).setValues(configRows);
    config.getRange("B2").setNumberFormat("dd/MM/yyyy");
    config.getRange("B6").setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(["NOT_APPROVED","APPROVED"],true).setAllowInvalid(false).build());
    config.getRange("D1").setValue("Holidays (optional)");
    config.getRange("D2:D30").setNumberFormat("dd/MM/yyyy");
    styleHeader_(config,3);
    config.setColumnWidths(1,3,220);
    const sheet = ss.insertSheet("Tasks");
    sheet.getRange(1,1,1,HEADERS.length).setValues([HEADERS]);
    const n = TASKS.length;
    const end = n + 1;
    const data = TASKS.map((t,i) => {
      const r = i + 2;
      const owner = t.owner === 1 ? "=Config!$B$3" : "=Config!$B$4";
      const reviewer = t.start_day >= 15 && t.phase !== "FRONTEND_LATER" ? "=Config!$B$5" : (t.owner === 1 ? "=Config!$B$4" : "=Config!$B$3");
      return [t.id,t.module,t.phase,t.title,owner,reviewer,t.start_day,t.end_day,
        '=WORKDAY(Config!$B$2-1,G'+r+',Config!$D$2:$D$30)',
        '=WORKDAY(Config!$B$2-1,H'+r+',Config!$D$2:$D$30)',
        t.hours,t.deps.join(", "),t.deliverable,t.acceptance,false,
        '=IF(OR(O'+r+'=TRUE,O'+r+'="TRUE"),"finish","unfinish")',
        readyFormula_(t,r,end),"","","",""];
    });
    sheet.getRange(2,1,n,HEADERS.length).setValues(data);
    sheet.getRange(2,15,n,1).insertCheckboxes();
    sheet.getRange(2,9,n,2).setNumberFormat("dd/MM/yyyy");
    sheet.getRange(2,20,n,1).setNumberFormat("dd/MM/yyyy HH:mm");
    styleHeader_(sheet,HEADERS.length);
    sheet.setFrozenColumns(4);
    sheet.getRange(1,1,end,HEADERS.length).createFilter();
    sheet.getRange(2,1,n,HEADERS.length).setWrap(true).setVerticalAlignment("top");
    sheet.setColumnWidths(1,HEADERS.length,130);
    [4,13,14,18,19,21].forEach(c => sheet.setColumnWidth(c,330));
    sheet.setColumnWidth(1,65);
    sheet.setColumnWidth(15,80);
    const rows = sheet.getRange(2,1,n,HEADERS.length);
    const rules = [
      SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied('=$P2="finish"').setBackground("#DCFCE7").setRanges([rows]).build(),
      SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied('=AND($P2="unfinish",$J2<TODAY())').setBackground("#FEE2E2").setRanges([rows]).build(),
      SpreadsheetApp.newConditionalFormatRule().whenFormulaSatisfied('=$Q2="blocked"').setBackground("#FFF7ED").setRanges([sheet.getRange(2,17,n,1)]).build()
    ];
    sheet.setConditionalFormatRules(rules);
    ["E2:F"+end,"I2:J"+end,"P2:Q"+end].forEach(a1 => sheet.getRange(a1).protect().setDescription("Formula - edit Config / Finish instead").setWarningOnly(true));
    const dashboard = ss.insertSheet("Dashboard");
    dashboard.getRange("A1:B1").setValues([["Metric","Value"]]);
    const metrics = [
      ["Total tasks",'=COUNTA(Tasks!A2:A'+end+')'],
      ["Finish",'=COUNTIF(Tasks!P2:P'+end+',"finish")'],
      ["Unfinish",'=COUNTIF(Tasks!P2:P'+end+',"unfinish")'],
      ["Overall progress",'=IFERROR(B3/B2,0)'],
      ["API tasks",'=COUNTIF(Tasks!C2:C'+end+',"API")'],
      ["API finish",'=COUNTIFS(Tasks!C2:C'+end+',"API",Tasks!P2:P'+end+',"finish")'],
      ["API progress",'=IFERROR(B7/B6,0)'],
      ["Frontend planned",'=COUNTIF(Tasks!C2:C'+end+',"FRONTEND_LATER")'],
      ["API_Gate",'=Config!B6'],
      ["Frontend unlocked",'=IF(AND(B7=B6,B6>0,Config!B6="APPROVED"),"YES","NO")'],
      ["Owner","Progress"],
      ["=Config!B3",'=IFERROR(COUNTIFS(Tasks!E2:E'+end+',A13,Tasks!P2:P'+end+',"finish")/COUNTIF(Tasks!E2:E'+end+',A13),0)'],
      ["=Config!B4",'=IFERROR(COUNTIFS(Tasks!E2:E'+end+',A14,Tasks!P2:P'+end+',"finish")/COUNTIF(Tasks!E2:E'+end+',A14),0)'],
      ["mem1 planned hours",'=SUMIF(Tasks!E2:E'+end+',Config!B3,Tasks!K2:K'+end+')'],
      ["mem2 planned hours",'=SUMIF(Tasks!E2:E'+end+',Config!B4,Tasks!K2:K'+end+')'],
      ["Note","Tick finish only after tests + review + evidence. API gate is PM decision."]
    ];
    dashboard.getRange(2,1,metrics.length,2).setValues(metrics);
    ["B5","B8","B13:B14"].forEach(a1 => dashboard.getRange(a1).setNumberFormat("0.0%"));
    styleHeader_(dashboard,2);
    dashboard.setColumnWidths(1,2,350);
    const modules = ss.insertSheet("Modules");
    modules.getRange(1,1,8,3).setValues([
      ["Module","Owner","Scope"],
      ["Accounts","=Config!B3","Auth/session/role/scope"],
      ["Academics","=Config!B3","Grade/class/one homeroom teacher"],
      ["Students","=Config!B3","Profile/class/private photo"],
      ["Reports","=Config!B3","Scoped summaries/XLSX/CSV"],
      ["Schedules","=Config!B4","Weekly rules/session/roster snapshot"],
      ["Attendance / Uniform","=Config!B4","Arrival/manual/verification/uniform/close"],
      ["Vision / QR legacy","=Config!B4","OpenCV staff confirm; QR disabled by default"]
    ]);
    styleHeader_(modules,3);
    modules.setColumnWidths(1,3,280);
    installEditTrigger_(ss);
    SpreadsheetApp.flush();
    props.setProperty("MVP_TASK_SHEET_ID", ss.getId());
    console.log(ss.getUrl());
    return ss.getUrl();
  } finally {
    lock.releaseLock();
  }
}

function readyFormula_(task,row,end) {
  const conditions = task.deps.map(id => 'COUNTIFS($A$2:$A$'+end+',"'+id+'",$P$2:$P$'+end+',"finish")=1');
  if (task.phase !== "API") {
    conditions.push('Config!$B$6="APPROVED"');
    conditions.push('COUNTIFS($C$2:$C$'+end+',"API",$P$2:$P$'+end+',"unfinish")=0');
    conditions.push('COUNTIF($C$2:$C$'+end+',"API")>0');
  }
  const ready = conditions.length ? 'AND('+conditions.join(",")+')' : 'TRUE';
  return '=IF(OR(O'+row+'=TRUE,O'+row+'="TRUE"),"done",IF('+ready+',"ready","blocked"))';
}

function styleHeader_(sheet,cols) {
  sheet.setFrozenRows(1);
  sheet.getRange(1,1,1,cols).setBackground("#17365D").setFontColor("#FFFFFF").setFontWeight("bold").setWrap(true);
}

function installEditTrigger_(ss) {
  const exists = ScriptApp.getProjectTriggers().some(t => t.getHandlerFunction()==="handleTaskEdit" && t.getTriggerSourceId()===ss.getId());
  if (!exists) ScriptApp.newTrigger("handleTaskEdit").forSpreadsheet(ss).onEdit().create();
}

/** Use after importing the XLSX: paste script in Extensions > Apps Script, run this function. */
function setupImportedSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  if (!ss || !ss.getSheetByName("Tasks") || !ss.getSheetByName("Config")) throw new Error("Open the imported tracker and use its bound Apps Script.");
  const sheet = ss.getSheetByName("Tasks");
  const range = sheet.getRange(2,15,TASKS.length,1);
  const previous = range.getValues().map(r => [r[0]===true || String(r[0]).toUpperCase()==="TRUE"]);
  range.insertCheckboxes().setValues(previous);
  installEditTrigger_(ss);
  console.log(ss.getUrl());
}

/** Installed trigger: timestamps and dependency gate; never overwrites PM comments. */
function handleTaskEdit(e) {
  if (!e || e.range.getSheet().getName()!=="Tasks") return;
  const range = e.range;
  if (range.getColumn()>15 || range.getLastColumn()<15) return;
  const ss = e.source;
  const sheet = range.getSheet();
  const n = TASKS.length;
  const values = sheet.getRange(2,1,n,21).getValues();
  const finished = {};
  values.forEach(r => finished[r[0]]=r[14]===true);
  const apiDone = values.filter(r => r[2]==="API").every(r => r[14]===true);
  const approved = ss.getSheetByName("Config").getRange("B6").getValue()==="APPROVED";
  for (let row=Math.max(2,range.getRow()); row<=Math.min(n+1,range.getLastRow()); row++) {
    const value = values[row-2];
    const checked = value[14]===true;
    const deps = String(value[11] || "").split(",").map(x=>x.trim()).filter(Boolean);
    const allowed = deps.every(id=>finished[id]) && (value[2]==="API" || (apiDone && approved));
    if (checked && !allowed) {
      sheet.getRange(row,15).setValue(false);
      sheet.getRange(row,20).clearContent();
      ss.toast("Task "+value[0]+" còn dependencies hoặc API gate chưa đạt.","Chưa được finish",8);
    } else if (checked) {
      if (!value[19]) sheet.getRange(row,20).setValue(new Date());
    } else {
      sheet.getRange(row,20).clearContent();
    }
  }
}
