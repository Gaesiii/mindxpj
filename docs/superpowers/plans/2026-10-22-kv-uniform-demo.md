# KV uniform recording demo

User authorization: 22/10/2026 request to put data and sample photos into the demo for recording and PM review. Use existing local UI authorization; no external messages/deployment. Routine UI choices follow the requested demo scope.

Design: a local-only, staff-authenticated page `/uniform-demo/`, linked from the existing UI only when the launcher explicitly enables a private demo bundle. Binary KV classifier remains separate from school profiles/attendance. Gallery contains held-out garment crops, including uncertain results. Uploaded/camera garment crops are processed in memory and never stored. Camera uses a visible manual garment ROI; no identity/face association or liveness claim. CSRF, bounded image decode, model/sample hashes, loopback-only access, disabled on Vercel. No class/student photo endpoint changes.

Implementation order:

1. Add failing API tests: disabled/remote/student/anonymous denial, CSRF, sample allowlist/hash, invalid upload, real inference path without attendance writes, corrupt model failure.
2. Add bounded local demo runtime/views and explicit launcher flag; implement gallery, upload and serial camera UI with stop/cleanup.
3. Copy prepared dataset/model to ignored `uniform-dataset/kv-demo`; create curated held-out sample manifest and operator launch command. No model approval bypass.
4. Run API/regression tests, actual model/gallery/browser checks; start local demo and document a short PM recording script. Push code/docs only; keep photos/weights/model private.

Review evidence must distinguish fixture/software checks from real model results. Missing SPORTS, unresolved dataset license, out-of-distribution error and lack of independent people/session split remain visible in documentation; model approval/PM acceptance remain pending.
