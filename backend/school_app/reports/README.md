# M07 — Reports (A08–A12)

GET `/api/v1/reports/attendance`, `/api/v1/reports/summary`, and
`/api/v1/reports/export` require an active HOMEROOM_TEACHER or SUPERVISOR.
Teachers read only classrooms assigned to them now, including historical
sessions; reassignment immediately removes the former teacher's access.
Students cannot read or export reports. Explicit class filters outside scope,
and teacher grade filters outside their assigned grades, return 403.

All endpoints require ISO `date_from` and `date_to` (inclusive). Optional
`class_id`, `grade_id`, `slot=MORNING|AFTERNOON`, and
`status=PRESENT|ABSENT|UNMARKED` filter the same rows. Dates must be ordered;
unknown/repeated parameters, invalid UUIDs, and invalid choices return 422.
Export additionally requires `format=xlsx|csv`.

`queries.canonical_rows` materializes one student-session row list from
OPEN/CLOSED sessions, roster snapshots and Attendance. PLANNED and pending QR
scans never count as present. No live Student label or photo is read. Current
Classroom determines permission and class/grade filtering; historical
class/grade/name/code labels and required uniform come from immutable snapshots.
The schema has no historical grade UUID snapshot. Arrival is ON_TIME at the
inclusive snapshot cutoff. A scanned time is included only for current QR
attendance with a CONFIRMED scan matching its official arrived_at; rejected,
pending, and older confirmed scans are not used as the current arrival.

Detail returns `{items, metadata}`. Each row includes entity IDs, snapshot
labels, school_date/slot/session_status, attendance status/source/times,
arrival_status, required_uniform_snapshot, observed_uniform/uniform_status,
absence/uniform reasons and note, and checker identity/time. Datetimes in JSON
are aware ISO UTC. Metadata contains generated_at, timezone, filters, and role
plus authorized class IDs.

Summary is a flat object with counts `expected`, `present`, `absent`, `unmarked`,
`on_time`, `late`, `compliant`, `non_compliant`, `not_checked`, `checked`, plus
`presence_rate`, `late_rate`, `violation_rate`, and `check_coverage`. Rates are
0–1; a zero denominator returns null. Status filters change the row set and
therefore the denominator. Counts are student-session counts, not unique pupils.

Export materializes at most 5,001 rows, rejects more than 5,000 with
`422 EXPORT_LIMIT_EXCEEDED`, and instructs the caller to split the period/class.
A read transaction keeps scope and attendance/scans consistent; rendering
occurs after materialization. SQLite is for the documented small demo.

XLSX contains `Chi_tiet`, `Tong_hop`, and `Thong_tin`; the latter holds generated
at/timezone/filter/scope metadata. CSV is a rectangular detail table with UTF-8
BOM. CSV metadata accompanies it in `X-Report-Generated-At`, `X-Report-Timezone`,
`X-Report-Filters`, and `X-Report-Scope` download headers. Exported times are
Asia/Ho_Chi_Minh ISO strings. Filenames are fixed attendance.xlsx/attendance.csv.
All string cells neutralize initial =,+,-,@, including whitespace/control/format
prefixes; XML-invalid characters are removed before checking the resulting
prefix. Neither format includes passwords, photos, private paths, or QR tokens.

Tests: `tests.test_reports` verifies the documented 40-roster fixture, actual
scoped database rows, teacher reassignment, status/date/ID filters, confirmed
scan selection, Unicode/formula defenses, both file formats, and actual
5,000/5,001 export boundaries. `tests.test_report_reconciliation` exercises real
manual/QR/uniform/close APIs and reconciles detail/summary/XLSX/CSV. Run from
backend with the local venv and a process-only DJANGO_SECRET_KEY. PM approval
and frontend gate remain separate.

A12 integration is implemented and reconciled: ten report tests pass against
a freshly migrated test database. The real API workflow checks two pending
scans without increasing present, confirms QR using scanned_at rather than the
later verification time, records manual presence and a uniform violation, and
closes the session. Its four rows finish as three present and one absent, with
one compliant, one non-compliant and one not checked; detail, summary, XLSX and
CSV agree. Fresh evidence is in
`docs/project-management/evidence/report-reconciliation-green.txt`.
