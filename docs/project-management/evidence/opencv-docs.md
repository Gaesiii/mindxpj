# Documentation validation — OpenCV v1.3

Date: 2026-10-18. Scope: documentation/task artifacts only; this record does not assert backend/API/camera acceptance. API_Gate remains NOT_APPROVED, all tracker Finish? FALSE.

- `backend/.venv/Scripts/python.exe .document-tools/build_task_tracker.py`: exit0, generated CSV/XLSX from40-task JSON.
- `backend/.venv/Scripts/python.exe .document-tools/verify_task_tracker.py`: exit0;40 IDs, acyclic dependencies,30API/6FRONTEND_LATER/4QA; provisional baseline capacity≤6h/member/day; XLSX formulas/owners/flags/gate and CSV title/deliverable/acceptance parity; no frontend project folders/assets.
- `node .document-tools/verify_task_script.js`: exit0; embedded TASKS match JSON; offline edit simulation blocks unmet dependencies/unapproved gate, timestamps allowed ready edits. No live Google execution.
- `py -3.9 .document-tools/build_documents.py`: exit0; v1.3 Word generated from48-line current design (1table,25paragraphs), copied to current unversioned design DOCX. Reopened DOCX with python-docx and checked1.3/NOT_APPROVED/128x128. Existing v1.2 DOCX retained. Python3.9 is for local document-tool lxml dependency only, backend remains3.12.
- One-off Markdown relative-link validation:22 links resolve across README/design/contract/acceptance/demo/proposal.13 single-line JSON HTTP bodies parse; enrollment multipart3 repeated images, one analysis image and confirm/reject endpoints checked. Local face-image paths intentionally require authorized local files, not shipped data.

Original v1.2 Markdown design/API contract/API acceptance archived before replacement. Active design/AGENTS/contracts agree on staff-operated vision, no automatic PRESENT, heuristic HSV, mandatory identity confirmation/manual fallback, QR legacy disabled, sample privacy and UI blocked by gate.

The tracker verifier was updated to validate task/source/artifact parity and source frontend absence. It no longer crawls installed virtualenv packages or claims skeleton/API test status. Root agent owns backend check/test/migration evidence and independent review. Capacity/calendar remain baseline provisional estimates pending face-data trial and PM review. Formulas still require spreadsheet recalculation; camera/accuracy/liveness/real-device checklist remain uncompleted.


## Presentation and consistency review follow-up

- Added docs/thuyet-trinh-opencv.pptx and reusable .document-tools/build_opencv_presentation.py:7 Vietnamese slides with timing/speaker notes for5–7minutes, API live sequence, architecture/privacy, fallback, validation and limitations; no unverified accuracy/test results.
- Installed python-pptx1.0.2 and its dependencies only into .document-tools/presentation-deps via backend Python3.12 -m pip --target. No backend runtime requirement changes.
- Builder exit0; reopened PPTX and checked every authored title/subtitle/card line and all speaker notes on7 slides. No PowerPoint rendering/live camera claim.
- Documentation consistency review corrected inclusive start_at<=now<=close_at, SESSION_TIME409 and fixed-minute per-actor cache quota limitation (per process, not rolling/global). Root owns backend retry behavior correction and API regression.
- Remaining acceptance: real camera/accuracy/spoof checks, PM gate approval, UI implementation after gate, PowerPoint rendering on the presentation machine. None marked complete.

## Current design verifier

- Updated .document-tools/verify_documents.py to target v1.3 and its actual5sections/1ownership table. Kept ZIP integrity, all XML parsing, Vietnamese Unicode, code-fence, unfinished-placeholder, old-stack exclusion and every source-content fragment parity checks. Added exact heading-text/style parity and required vision/gate/privacy/time constraints.
- `py -3.9 .document-tools/verify_documents.py`: exit0;32source fragments preserved,5numbered headings match,1table; archived v1.2 Markdown and Word exist and Word packages parse; current unversioned Word is byte-identical to v1.3 Word. This validates content/structure, not Word visual rendering.

## User-authorized local UI exception — 2026-10-18 follow-up

User explicitly requested “làm luôn UI để demo”, authorizing local Django UI before the previously required gate. Current design/contracts/acceptance/rootREADME/demo/proposal/project-managementREADME record this narrow exception. API_Gate remains NOT_APPROVED, Finish? values unchanged; no deployment authorized. Earlier no-frontend/backend-only statements in this evidence describe prior checkpoints, not current UI scope.

- UI documented at `/`: staff login/dashboard/attendance/students/reports, schedules/session create/open/close, camera/upload with mandatory confirmation,3–10photo enrollment, manual/uniform and exports. STUDENT console rejection and API scope remain requirements. API endpoints unchanged. Browser/full-suite/real-device outcomes belong to root UI evidence, not this document validation.
- Preserved40task IDs, original FRONTEND_LATER phases/dependencies/formulas and unchecked Finish? as historical planning. tasks.json scope_note and spreadsheet Config explain the exception; generator regenerated CSV/XLSX without approving gate. Existing Apps Script embedded task data unchanged and still matches source.
- verify_task_tracker.py now checks actual Django shell/CSS/JS paths, user authorization text and historical planning note, while retaining dependency, capacity, content/artifact parity and NOT_APPROVED/FALSE checks. Run exit0.
- verify_documents.py now checks local UI exception text rather than absence of frontend. Generated current/v1.3Word, then verifier exit0:32source fragments,5headings/1table, all ZIP/XML/Unicode/content checks preserved, archive retained, current Word byte-identical to v1.3.
- Presentation builder updated to UI live-demo sequence and explicit exception before gate; regenerated7slides, reopened and validated every title/card line/speaker note. No real-camera accuracy/liveness or unverified test-count claims. PowerPoint rendering remains unchecked.
- Offline Apps Script verifier exit0. Current document relative links checked successfully after updates. No backend code/templates/styles/scripts edited by documentation agent.
