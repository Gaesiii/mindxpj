# Vercel API performance implementation plan

User scope: optimize existing API for manual Vercel deployment, then push to the authorized GitHub repository. No deployment. Continue approved architecture (native Django WSGI, build-seeded temporary SQLite, pinned local SFace, no cloud service). No public API/role/attendance behavior change.

- [x] Measure fresh-process ordinary API cold imports and scan SQL before change. Add failing regression: resolving ordinary URLs must not import cv2/numpy/openpyxl; scan embedding query must not SELECT crop image blobs. Use scoped real API test fixtures and captured SQL.
- [x] Lazy-load vision service modules in request handlers and export library in export handler after authorization; select only student_id+embedding in scan loop. Keep unauthorized/invalid requests fast and preserve scopes/errors.
- [x] Remove repeated per-request filesystem initialization/locks on warm Vercel requests; retain missing DB recopy and per-date session refresh under locks. Add meaningful tests proving warm calls skip copy/dir setup and DB-loss still reinitializes.
- [x] Validate actual native Vercel packaging/config and build-only models/template/static preparation. Document manual Root Directory/env/build settings and optional stable function region; no guessed resource settings or persistent SQLite claims.
- [x] Run focused RED/GREEN and full suite, local build/Vercel-mode CSRF+face scenario, independent review. Save measured evidence. Commit/fast-forward main without resetting current demo DB. Push main without force after device authentication; verify remote SHA matches local. Report authentication blocker if still pending.

Files: vision/views.py, vision/services.py, reports/views.py, config/vercel_demo.py, tests/test_vercel_api_performance.py, existing Vercel bootstrap tests, deployment guide and pyproject metadata. Root owns all implementation; use requesting-code-review for independent final review. Verification uses original workspace venv and cwd isolatedworktree/backend; model directory supplied from prepared original assets, never untracked private DB/credentials in Git.

Completed:206/206tests, actual build, real held-out browser workflow and independent review pass. GitHub device login completed asGaesiii. First push of main succeeded; remoteSHA verified equal locala8f15b5. No deployment. SQLite/user demo DB untouched by this performance task.
