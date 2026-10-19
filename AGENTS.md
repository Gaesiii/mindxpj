# Project instructions

- Follow the user's MVP only. Authoritative scope: docs/thiet-ke-he-thong-diem-danh.md v1.5, with the approved 19/10/2026 auto-attendance/uniform/CRUD plan; v1.4 remains archived.
- Python/Django backend first. Implement the authorized OpenCV backend/demo preparation; technical evidence and PM approval remain separate.
- Local demo UI is explicitly authorized by the user's 18/10/2026 request “làm luôn UI để demo”, as an exception to the prior frontend gate. Implement it against existing APIs; PM API_Gate remains NOT_APPROVED until actual review. No deployment is authorized.
- Member 1 owns accounts, academics, students, reports; Member 2 owns schedules, attendance, vision and legacy qr.
- Coordinate core/config/contracts and cross-app migrations before modifying shared interfaces.
- Preserve role scope on every read/write/export/photo endpoint. Student identity comes from session, never the request body.
- The user's 19/10/2026 request to complete the plan authorizes automatic PRESENT from qualified two-frame local face matching, dedicated school-uniform camera/dataset, and class/student CRUD. Keep manual fallback and legacy confirmed history. Exact-school uniform recognition needs a separately evaluated local model; missing/uncertain evidence stays NOT_CHECKED. No liveness guarantee, external AI services, SMS, parent portal, cloud storage, workers, queues or correction-approval module.
- Keep backend/tests cases meaningful. Empty skeleton test files do not prove an API passes.
- Task completion requires implementation, validation evidence and review; do not tick finish merely because files exist.
- No external sharing/email invitations or deployments without a separate request.
- The user explicitly authorized pushing this project to https://github.com/Gaesiii/mindxpj.git and preparing a minimal Vercel demo with temporary SQLite. Do not publish secrets/runtime databases or installers. Vercel compatibility work is authorized; actual deployment is not requested by this instruction.
