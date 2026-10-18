# Vercel demo preparation evidence — 18/10/2026

- `backend-validation.txt`: 161/161 passing full Django suite (60.384s), system check, migration drift and installed dependency checks. Use the actual test count/result in this log.
- `linux-wheel-size.json`: all pinned dependencies downloaded as Linux Python3.12 binary wheels. Unpacked wheel content totals approximately267.4MiB. This estimate excludes source/runtime overhead; it is not an actual Vercel bundle measurement.
- `backend/tests/test_vercel_demo.py`: isolated settings, atomic copy-once/preserve/missing-template, actual migrated/seeded SQLite, secure signed-session login, same-origin CSRF/malicious-origin denial, role scope, template recopy and next-day session refresh; failed build preserves previous template and cleans staging.
- `backend/tests/test_vision_api.py`: configured3MiB enrollment budget rejects oversized multipart before decode/persistence. UI shell test verifies matching displayed budget.
- Actual `build_vercel.py` completed locally with generated process-only credentials and collected static. DB/password hashes remain ignored runtime artifacts.
- Browser QA rerun after budget UI changes: all13 scenarios passed, zero uncaught JavaScript errors; see [UI evidence](../ui-demo/README.md). Camera recognition positives remain synthetic/mocked as disclosed there.
- Independent read-only review: no critical/important findings; reviewer reran7 Vercel tests successfully.

Prepared native Django/WSGI configuration, static CDN collection,60s function budget and temporary private storage. No live Vercel build/deployment, CDN or physical camera accuracy has been verified. SQLite mutations and new face samples are per instance, can disappear/reset or differ between consecutive requests. Signed cookies expire after1h; logout clears the browser cookie without global revocation of copied cookies. PM API acceptance remains NOT_APPROVED.

See [deployment guide](../../../deploy-vercel-demo.md) for environment setup and official platform references.

Git preparation: 245 tracked source/doc/evidence files, approximately2.0MiB; no staged DB, private media, runtime credentials, virtualenvs, downloaded tool packages or installers. Token/private-key patterns checked across text and Office XML; no findings. GitHub push awaits device authentication.
