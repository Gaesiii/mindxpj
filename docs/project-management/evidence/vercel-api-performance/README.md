# Vercel API performance verification — 18/10/2026

Public API behavior, role scope, score thresholds, enrollment versions and required staff confirmation are preserved. No deployment was created; the user will import GitHub and deploy manually.

Changes verified:

- Ordinary URL setup no longer imports `cv2`, `numpy` or `openpyxl`. Vision handlers import inference services when invoked; Excel export imports its writer after report authorization/filter validation.
- Scan SQL selects only `student_id` and compatible `embedding`, retaining active roster/model/sample-count filters. Private crop image BLOBs are not fetched for matching.
- Warm Vercel requests avoid repeated bootstrap file locks and directory creation. A cheap DB-file check preserves missing-DB recovery; cold copies and daily session refresh retain cross-process locks. No request migrations or model downloads.

`cold-import-before.json` / `cold-import-after.json`: five fresh Python processes each, local Windows CPU, Django setup + ordinary URL resolution. Median **373.17ms before /236.07ms after**. These are local import measurements, not Vercel request latency, network latency or a serverless cold-start guarantee. Actual model inference still loads OpenCV on its first use and reuses the verified locked model cache thereafter.

`backend-validation.txt`: **206/206 tests passed in64.588s**, check, fresh migration, migration-drift and pip checks passed. Three new performance regressions observed RED→GREEN: cold imports, scan SELECT excludes crop BLOBs, warm initialization skips work while recovering DB loss. Existing real Vercel subprocess tests cover secure signed-cookie login/CSRF, role scope, DB recopy and next-day roster initialization. The synthetic bootstrap test overrides DATABASES without opening it, which produces a harmless Django test warning.

`build-validation.txt`: actual build helper prepared verified models, seeded SQLite template and collected static successfully. Dependency/model bytes and native Django WSGI/CDN configuration remain as documented in [SFace evidence](../sface-upgrade/README.md). Live Vercel build, CDN and latency are not claimed.

`browser-real-face-validation.txt`: real browser/CSRF/HTTP/YuNet/SFace/SQLite scenario rerun after optimization: new-image match0.697729, different-person rejection, explicit confirmation only, enrollment metadata and resume persistence passed; zero JS errors. No inference or HTTP-response mocks in this scenario. Original user demo DB was not modified.

Independent spec/code review: no critical/important findings; reviewer independently reran10 focused performance+Vercel tests successfully. Manual deployment remains Root Directory `backend`, Django preset, `DJANGO_SECRET_KEY` + `DEMO_PASSWORD`. SQLite/biometrics remain temporary per instance and are not shared across instances; this work does not make SQLite durable or scalable.
