# Backend MVP A02–A15/B02–B15

> **For agentic workers:** Use superpowers:subagent-driven-development with TDD and independent spec/quality review. User explicitly selected the whole backend on 14/10/2026. Source scope: MVP v1.2; api-contract.md; ke-hoach-1-thang.md. Frontend requires a separate request after PM API gate.

**Goal:** Deliver all MVP backend APIs, meaningful tests, seed/request collection and acceptance evidence for PM A15/B15 review.

**Architecture:** One Django project, Forms/services/JSON views, session+CSRF, private local photos, atomic snapshot/attendance/QR services with CAS versions and idempotency, synchronous report exports. SQLite demo limits documented. No Git present; no commits/deploys/sharing. Student identity only from session.

**Tech Stack:** Existing Python3.12/Django5.2/Pillow/qrcode/openpyxl pins; no extra infrastructure.

## Ownership and shared interfaces

Mem1 agent owns accounts/academics/students, migrations in those apps and tests for A02–A07/A13. Mem2 agent owns schedules/attendance/qr, core idempotency/log models for B08, associated migrations/tests B04–B14. Root integrates config/routes and shared core/api JSON wrapper, docs/evidence; reports implementer owns reports/A08–A12 after mem2 schema coordination. Review agents perform read-only checks. No concurrent edits to same files.

Shared service errors reuse accounts.services.AccountError(code,message,status,details). Shared wrapper core.api.api_view handles errors/JSON/methods/SQLite busy. Accounts permissions require_authenticated(request), require_roles(request,*roles), require_student(request). Academics.services scoped_classes(user), require_class(user,id)404 and assert_class_filter(user,id)403 enforce active/role/current teacher scope. Dictionary/migration graph stays contract B01, no implicit superuser bypass. All API serialization uses class_id, model classroom.

## Execution checklist

- [x] A02/B02/B03: auth+CSRF/provision service+CLI; strict schedule forms and scenario matrix. Run RED then GREEN; independent review and regressions.
- [x] A03: Grade/Classroom UUID, PROTECT grade/teacher, one current GVCN per class, scoped APIs/services; test duplicate/scope/student teacher rejection/reassignment.
- [x] A04–A05: Student UUID unique code, classroom/active; create/read/search/update; User.student protected OneToOne new migration after students. Provision STUDENT link, no public signup/password lists. Test duplicate-name/code, class transfer supervisor only, session identity and reassignment.
- [x] A06–A07: private Pillow JPEG/PNG/WebP <=5MB and pixel cap, EXIF stripped; failed replace keeps old; protected photo downloads. Test fake/oversize content and all role scopes.
- [x] B04–B06: ScheduleRule, Session, SessionRoster, Attendance models after coordinated A03/A04; create/open/close transactions, snapshots, CAS and retry, active roster; rollback/unique/version/scope tests.
- [x] B07–B08: roster/manual/absence, arrival cutoff inclusive, no future/naive dates, reason for retrospective; manual supersedes pending. Core ChangeLog/IdempotencyRequest; canonical payload hash + actor/operation/key TTL24h, retry scope rechecked before replay; atomic responses/version/log; DB busy409. Test retry/conflict/closed supervisor reason and rollback.
- [x] B09–B12: QR token hash/60s/refresh30 via API, PNG; student-session scan PENDING/expiry15m/no instant PRESENT; pending retry timestamp and unique; supervisor/teacher queue confirm/reject, arrived_at=scanned_at; uniform validations and combined atomic rollback. Test two students same challenge, wrong class/expired/identity spoof, stale version, manual supersede, NOT_CHECKED preserved.
- [x] A08–A12: one scoped snapshot row query for details/summary/export, date/class/grade/slot/status filters; OPEN/CLOSED only; count identities/formulas/null denominator; XLSX3sheets/CSV BOM/formula defense/5000 max and Vietnamese local times. Reconcile actual QR/manual/uniform flows, no raw password/photo/token.
- [x] A13/B13: end-to-end role/scope/photo/export/manual/QR/uniform/close tests; endpoint schema failures and retry after close/reassignment. Fix findings with regressions.
- [x] A14/B14: seed_demo command 2 classes/20 fictional students and 3 role accounts with safe local password handling; request collection covering workflow and expected failures; update module/API/setup docs.
- [x] A15/B15: independent requirement+quality review, checks/migration from fresh DB/test/pip check; evidence files and docs/api-acceptance.md for PM. Do not claim PM approval, tick task Finish?, or set API_Gate.

Tests run in backend cwd with .venv/Scripts/python.exe and process-only generated DJANGO_SECRET_KEY; tests against Django test DB, fresh migration using temporary DJANGO_DB_PATH. Keep current DB/photos untouched. Record test counts/results per evidence rather than assuming skeleton passes. No frontend files/assets/Admin UI required for this backend deliverable; account CLI/service handles provisioning.

## Kết quả thực thi

Các checkbox trên ghi nhận công việc kỹ thuật đã triển khai, kiểm chứng và review; không phải Finish? của tracker hoặc PM phê duyệt. Phạm vi đợt đầu đã được mở rộng theo lựa chọn toàn bộ backend của người dùng. Xem docs/project-management/evidence/backend-api.md: 126 test đạt, toàn bộ kiểm chứng cuối exit 0.

- [ ] PM/member review A15/B15 và quyết định API gate (chờ PM, không tự xác nhận).
