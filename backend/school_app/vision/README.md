# OpenCV proposals

Staff role and current classroom scope are checked before image work and before
idempotent replay. Enrollment is independent of profile photos; crops reside in
private DB BinaryFields and no API serves their bytes. Deletion/re-enrollment
supersedes pending proposals. Camera frames are never stored.

`engine.py` owns image bounds, Haar detection, blur filtering, grayscale LBPH
distance and configurable HSV color suggestions. `enrollment.py` owns replacement,
revision and deletion; `services.py` owns expiring, scoped proposals and confirmation.
`views.py` accepts strict multipart/JSON payloads. Models and migrations preserve QR
history. Source VISION is written only after staff confirms identity.

Analyze and confirm require the session OPEN, today, and within start_at/close_at
(inclusive). Proposals expire after120s, bind sample revision and attendance version,
and never mark presence on capture. Confirm may omit uniform, keeping NOT_CHECKED;
an explicit UNKNOWN uniform cannot be marked compliant/non-compliant. Staff may
inspect and supply a known observed type with the existing uniform rules.

Exact-key successful retries can replay after close; scope is checked again.
Invalid/stale/unrecognized images never produce an attendance write. Manual entry
supersedes pending proposals; close expires them. Closed-session corrections use
the existing supervisor/manual reason flow.

Defaults: 2MiB/4MP per image,3–10 distinct enrollment crops,15MiB aggregate,
50 active/current-class roster students,20 analyses per fixed minute per actor in
process-local cache. Boundary bursts and multiple processes are not globally limited.
No workload or real-person accuracy claims follow from synthetic tests. No liveness.

Run `manage.py test tests.test_vision_engine tests.test_vision_api` from backend;
run `.document-tools/verify_opencv.py` from the root with the backend venv to reproduce
full checks, schema upgrade, CSRF HTTP workflow and XLSX/CSV reconciliation on temp DBs.
See docs/api-contract.md, docs/huong-dan-demo-opencv.md and evidence/opencv-backend.md.

Algorithm references: [OpenCV LBPH](https://docs.opencv.org/4.13.0/df/d25/classcv_1_1face_1_1LBPHFaceRecognizer.html),
[Haar detection](https://docs.opencv.org/4.13.0/d7/d8b/tutorial_py_face_detection.html),
[HSV inRange](https://docs.opencv.org/4.13.0/da/d97/tutorial_threshold_inRange.html).
