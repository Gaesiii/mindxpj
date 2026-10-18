# Django local demo UI plan

**Approved scope:** user's “làm luôn UI để demo” authorizes local UI now as a narrow exception to the previous frontend gate. PM acceptance remains NOT_APPROVED. No deployment, external sharing, account bypass, fabricated recognition or identity from student payloads.

**Design:** Vietnamese staff console with a light workspace, navy sidebar, teal primary actions and clear status badges. Login first; overview/attendance/students/reports tabs. A shared class/session selector drives scoped data. Attendance has roster, camera/upload, proposal confirmation/rejection and manual fallback. Students offers profile list and3–10sample enrollment/deletion. Reports filters date/class and downloads existing protected XLSX/CSV. Small screens stack controls and table scrolls inside its panel.

**Architecture:** Django-rendered shell at `/`, session/CSRF APIs unchanged; new `school_app.demo_ui` templates/static. No endpoint grants authority based on frontend role hiding. Unknown/expired sessions clear sensitive client state; camera stops on logout/navigation. External CDN/fonts are not needed. JS uses DOM textContent for untrusted names/errors. Idempotency keys retained for uncertain writes and replaced after resolved errors/success. Shared async guards prevent stale class/session responses overwriting another selection.

**Files:** `demo_ui/views.py`, `templates/demo_ui/index.html`, `static/demo_ui/{app.css,app.js}`, config settings/urls; `tests/test_demo_ui.py`. Browser evidence in docs/project-management/evidence. Update gate docs/tracker to record authorized exception without marking PM approval. A separate ignored local runtime DB supplies20fake students and an all-day demo-only schedule without changing existing operational data.

## Steps

- [x] Write tests for GET shell/CSRF bootstrap, no credentials/biometrics embedded, static assets, staff APIs, student UI restriction and unknown API JSON preservation; run RED.
- [x] Build semantic responsive shell and styles; add Django template/static configuration and route. Run focused tests GREEN.
- [x] Implement login/logout, scoped classes/students/schedules/sessions/roster loading, rule/session create/open/close with version, dashboard counts and reports.
- [x] Implement camera lifecycle and upload bounds, preview/capture/analyze with key retry, current proposal details and explicit identity/uniform/reason confirmation; reject/manual fallback and private enrollment/delete flows. Keep UNKNOWN unchecked.
- [x] Test real browser locally: login, create/open actual session, manual/uniform/close, exports, permission denial, expired session/login errors, camera denied/upload/no-face, mobile layout and console errors. No fake detector in interactive UI. Existing synthetic OpenCV backend tests remain clearly labeled.
- [x] Full regression and independent review; fix findings, record logs/screenshots, update demo guide and start local server for user.

User does not need another permission round for local UI. Existing API acceptance is distinct from authorization to build this UI demo.

## Technical handover

153 Django tests passed; fresh migrate, check, drift and pip checks exit0. Real Edge browser QA passes desktop/mobile, CSRF login/scope, schedule/session create/open, manual/uniform/close/export, upload/no-face, stale-response guards, same-key retry after committed-body loss and logout401 cleanup. Synthetic camera stream and mocked proposal contract are disclosed fixtures only. Independent re-review approved; no blocking findings. See docs/project-management/evidence/ui-demo/README.md. User demo runs locally with its own fresh fictitious DB. PM acceptance and physical-camera/accuracy remain pending; no deployment.
