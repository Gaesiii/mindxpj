> Tracker v1.3: QR hoạt động đã đổi thành vision với staff confirm; giữ 40 ID/ngày/giờ cũ để truy vết, ước lượng tạm chờ thử ảnh thật và PM đánh giá lại. JSON là nguồn task; CSV/XLSX/Apps Script đã đồng bộ. Finish? vẫn FALSE và API_Gate NOT_APPROVED. UI local đã được người dùng cho phép trước gate ngày18/10/2026 (“làm luôn UI để demo”), không phải PM API approval. FRONTEND_LATER và công thức gate là baseline lịch sử; không tick Finish? tự động. Evidence QR126test cũ là lịch sử, không chứng minh vision đạt. Chưa chạy Apps Script trên Google Sheets và không có chia sẻ ngoài.

# Bảng phân công Google Sheets

Nguồn task: tasks.json. Có 40 task, mem1/mem2, 20 ngày làm việc từ 12/10/2026 đến 06/11/2026. Tất cả task nghiệp vụ khởi tạo unfinish. File XLSX và Apps Script dùng cùng task/owner/dependency/acceptance.

## Cách 1 — Tạo Google Sheets bằng mã đã chuẩn bị

1. Mở https://script.google.com/ bằng tài khoản Google của PM, tạo New project.
2. Dán toàn bộ create_task_sheet.gs vào Code.gs.
3. Chọn hàm createTaskSheet và Run; cho phép Google truy cập bảng tính/trigger của tài khoản khi được hỏi.
4. Execution log trả link Google Sheets mới có Config, Tasks, Dashboard, Modules và checkbox Finish?. Script không tự chia sẻ hoặc mời ai.
5. Chỉnh tên mem1/mem2, ngày bắt đầu và ngày nghỉ tại Config; PM chọn API_Gate APPROVED sau nghiệm thu API. Chia sẻ bảng với hai thành viên bằng giao diện Google.

Chạy lại createTaskSheet trả link bảng cũ đã lưu trong Script Properties, không tạo lại hay ghi đè tiến độ/comment. Nếu muốn tạo bảng khác, dùng một Apps Script project mới. API tạo bảng: https://developers.google.com/apps-script/reference/spreadsheet/spreadsheet-app. Checkbox: https://developers.google.com/apps-script/reference/spreadsheet/range#insertcheckboxes.

## Cách 2 — Nhập file XLSX vào Google Sheets

1. Upload task-tracker.xlsx lên Google Drive và mở bằng Google Sheets; lưu thành Google Sheets.
2. Dùng Extensions > Apps Script, dán create_task_sheet.gs vào Code.gs.
3. Chạy setupImportedSheet để chuyển TRUE/FALSE thành checkbox và cài trigger timestamp/dependency. Các giá trị đã tick được giữ nguyên.
4. Chỉnh Config và dùng như cách 1. Không chạy createTaskSheet nếu muốn giữ bảng đã nhập.

Trong XLSX, Finish? dùng TRUE/FALSE vì checkbox Google chỉ được tạo trong Google Sheets. Status tự tính finish/unfinish. CSV tasks-import.csv chỉ mang dữ liệu thô, không mang nhiều sheet/checkbox/công thức; ưu tiên XLSX hoặc Apps Script.

## Các cột

ID, Module, Phase, Task, Owner, Reviewer, ngày làm việc bắt đầu/kết thúc, ngày thực, Hours, Dependencies, Deliverable, Acceptance, Finish?, Status, Ready/Blocked, PM Comment, Evidence/PR, Actual Finish, Dev Note.

Tick Finish? sau khi code/test/review hoàn tất; bỏ tick đổi thành unfinish. Trigger ghi ngày hoàn tất, xóa khi bỏ tick và từ chối tick nếu dependencies/API gate chưa đạt. Khi PM bỏ tick một dependency về sau, các task chưa hoàn thành sẽ trở lại blocked; task đã hoàn thành không bị xóa lịch sử tự động, PM rà lại bằng comment.

PM Comment là cột nhận xét, không tự gán quyền chỉ PM theo email. Các cột công thức được cảnh báo khi sửa, không khóa quyền PM/member tuyệt đối. PM cấu hình quyền chia sẻ/protected ranges theo email nếu cần.

Ngày dự kiến dùng WORKDAY, nghỉ cuối tuần và Config!D2:D30 nếu PM nhập ngày nghỉ. Pha FRONTEND_LATER là lịch gốc ngày16–18, công thức vẫn giữ gate cho baseline; ngoại lệ UI local được người dùng yêu cầu không tự đổi pha hoặc checkbox/gate. 4 task QA cuối tháng cũng chờ gate và frontend dependencies.

## Trạng thái bàn giao

Backend A02–A14/B02–B14 v1.2 đã có evidence lịch sử theo yêu cầu14/10/2026. Vision v1.3 cần evidence mới; hồ sơ PM hiện hành ở ../api-acceptance.md và ../api-contract.md. Bàn giao/ZIP A01/B01 là nền lịch sử. Đã cập nhật nội dung task v1.3 trong JSON/XLSX/CSV/Apps Script nhưng không tự tick checkbox; PM và thành viên review trước tick Finish?. API_Gate vẫn NOT_APPROVED.

Chưa tạo link Google Sheets trong tài khoản người dùng vì Google Drive chưa kết nối. Mã đã chuẩn bị tạo bảng khi người dùng chạy trong tài khoản Google; cú pháp và dữ liệu được kiểm tra tại workspace, chưa thực thi trong Google Apps Script. File XLSX đã được tạo và kiểm tra cấu trúc/công thức; cần mở bằng Excel/Google Sheets để tính giá trị công thức.


Tạo lại artifacts local:

```powershell
backend/.venv/Scripts/python.exe .document-tools/build_task_tracker.py
backend/.venv/Scripts/python.exe .document-tools/verify_task_tracker.py
node .document-tools/verify_task_script.js
```

Verifier chỉ kiểm tra cấu trúc/task/công thức và mô phỏng gate offline; không chứng minh API đạt hoặc camera thật. Chạy lại Apps Script với spreadsheet cũ chỉ trả link cũ, không tự migrate nội dung task; để cập nhật bảng hiện có PM cần nhập/đối chiếu thủ công, giữ comments/evidence/checkbox trước khi đổi. Chưa có bảng Google thật nào được tạo/cập nhật trong đợt này.
