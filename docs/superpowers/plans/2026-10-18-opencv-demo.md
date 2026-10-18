> Follow-up18/10/2026: user explicitly authorized local demo UI before gate (“làm luôn UI để demo”); see 2026-10-18-local-demo-ui.md. Earlier UI-gate restrictions below describe the original plan. PM gate remains NOT_APPROVED; no automatic Finish? or deployment.

# OpenCV attendance implementation plan

> For agentic workers: use superpowers:executing-plans for the coupled backend tasks and superpowers:requesting-code-review before handover. Documentation may be delegated using superpowers:subagent-driven-development. Track technical completion separately from PM approval.

**Goal:** Replace the active QR path with local OpenCV face matching and uniform suggestions requiring staff confirmation; prepare testing and presentation material.

**Architecture:** New vision app owns private face samples and expiring scan proposals; existing attendance services remain the only attendance write mechanism. Vision adds source VISION, no destructive QR migrations. UI is requested (interpretation of “U”) but remains blocked by PM API gate; do all backend and presentation preparation now.

**Tech Stack:** Django 5.2/Python 3.12, OpenCV contrib headless 4.13.0.92, NumPy 2.2.6, Haar face detection, LBPH matching, configurable HSV uniform bands. No cloud/video storage/queues.

Workspace is a plain directory without .git and git is unavailable; edit in place, test against isolated databases and do not claim commits/worktrees.

## Tasks

- [x] 1. Update authoritative scope to v1.3, AGENTS.md, contracts and task tracker: keep original responsibilities, document UI gate, record QR as legacy. Prepare demo script and QA checklist. Do not mark PM approval or all tasks finished.
- [x] 2. Write `backend/tests/test_vision_engine.py` for valid/invalid images, zero/multiple/blurry faces, actual LBPH match/unknown/ambiguous and HSV SHIRT/SPORTS/UNKNOWN; run RED with `manage.py test tests.test_vision_engine`. Implement `vision/engine.py` using bundled Haar, normalized 128x128 grayscale crops, separate per-student LBPH distances, maximum distance and runner-up margin. Uniform UNKNOWN when torso clipped or no dominant configured color. Run GREEN.
- [x] 3. Write `backend/tests/test_vision_api.py`: staff scope; student cannot enroll/analyze/confirm; enrollment replaces 3–10 samples atomically; no image bytes returned; scan creates only PENDING; confirm identity/version/expiry/date checks; rollback invalid uniform; retry exactly once; close/manual/transfer/re-enrollment/deletion invalidate pending; report/XLSX/CSV reconciles VISION. Observe RED before implementing.
- [x] 4. Implement `vision/models.py`, migrations, `services.py`, `views.py`, `urls.py`. Endpoints: `GET/POST/DELETE students/{id}/face-samples`; `POST sessions/{id}/vision-scans` (single multipart image, Idempotency-Key); `GET sessions/{id}/vision-scans`; `POST vision-scans/{id}/confirm` or `/reject` (JSON, key). Store only normalized enrollment crops privately in DB; ephemeral scan frames never persist. Bind proposals to sample revision and attendance version; expiry 120s. Max 50 roster entries, rate limit 20 analysis/minute/actor, max frame 2MiB/4MP; aggregate enrollment 15MiB. Update source enum, attendance source migration, reports scan timestamp, manual supersede and close expiry.
- [x] 5. Disable active legacy QR endpoints by default with a clearly documented compatibility setting; retain existing migrations/history. Explicitly enable compatibility only in legacy QR tests, add a test asserting default QR is retired. Run focused tests, fix failures, then full regression.
- [x] 6. Validation: Django check, full tests, migrate fresh DB, migration drift, pip check. Run a reproducible HTTP scenario with CSRF on temporary DB and generated synthetic image data (mock only face detection, use real LBPH/HSV); export and reopen XLSX/CSV to compare. Record synthetic limits; real camera/accuracy remains a separate uncompleted acceptance item.
- [x] 7. Independent spec and quality review. Fix findings with regression tests, rerun relevant checks and final full suite if code changed. Save evidence and final status. UI templates/static are not created until explicit PM API gate approval; hand over concrete API acceptance review.

## Acceptance boundaries

OpenCV detection and matching tests prove algorithm execution on controlled inputs, not real-person accuracy or spoof resistance. Uniform logic distinguishes configured color bands only. Demo seed remains fictitious; no real biometrics are fabricated. No secrets in evidence. PM gate stays NOT_APPROVED until PM explicitly approves after reviewing new evidence.

## Kết quả kỹ thuật

149 test đạt; check/fresh migrate/upgrade v1.2/CSRF HTTP/report/XLSX/CSV/pip/migration drift đạt; review độc lập backend không còn finding bắt buộc sửa. Bằng chứng: docs/project-management/evidence/opencv-backend.md và opencv-validation.txt. Plan này ghi công việc kỹ thuật, không tick Finish? của tracker hay duyệt PM gate. UI vẫn blocked NOT_APPROVED, camera thật/accuracy chưa hoàn tất. PPTX7slide, Wordv1.3, JSON/CSV/XLSX/GS tracker đã tạo/kiểm tra nội dung. Workspace không có Git; không tạo commit/worktree.
