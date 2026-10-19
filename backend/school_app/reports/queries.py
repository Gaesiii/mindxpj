"""A single scoped, immutable-label row set shared by all report consumers."""
from django.db.models import Prefetch
from school_app.schedules.models import SessionRoster
from school_app.qr.models import QrScan
from school_app.vision.models import VisionScan


def iso(value):
    return value.isoformat() if value is not None else None


def canonical_rows(classes, filters, *, limit=None):
    queryset = SessionRoster.objects.filter(session__classroom__in=classes,
        session__status__in=['OPEN', 'CLOSED'], session__school_date__gte=filters['date_from'],
        session__school_date__lte=filters['date_to']).select_related('session', 'attendance', 'attendance__checked_by')
    for name, lookup in (('class_id', 'session__classroom_id'), ('grade_id', 'session__classroom__grade_id'),
                         ('slot', 'session__slot'), ('status', 'attendance__status')):
        if filters.get(name):
            queryset = queryset.filter(**{lookup: filters[name]})
    queryset = queryset.order_by('session__school_date', 'session__slot', 'class_code_snapshot',
                                 'student_code_snapshot', 'id').prefetch_related(Prefetch('scans',
        queryset=QrScan.objects.filter(status='CONFIRMED').order_by('-resolved_at', '-scanned_at'),
        to_attr='confirmed_scans'), Prefetch('vision_scans',
        queryset=VisionScan.objects.filter(status__in=['CONFIRMED','AUTO_RECORDED']).order_by('-resolved_at','-scanned_at'),
        to_attr='confirmed_vision_scans'))
    if limit is not None:
        queryset = queryset[:limit]
    result = []
    for roster in queryset:
        session, attendance = roster.session, roster.attendance
        arrival = 'NOT_APPLICABLE'
        if attendance.status == 'PRESENT':
            arrival = 'ON_TIME' if attendance.arrived_at <= session.late_cutoff_at else 'LATE'
        scanned_at = None
        if attendance.source == 'QR' and attendance.status == 'PRESENT':
            scanned_at = next((scan.scanned_at for scan in roster.confirmed_scans
                               if scan.scanned_at == attendance.arrived_at), None)
        if attendance.source == 'VISION' and attendance.status == 'PRESENT':
            scanned_at = next((scan.scanned_at for scan in roster.confirmed_vision_scans
                               if scan.scanned_at == attendance.arrived_at), None)
        row = {name: getattr(roster, name) for name in ('student_code_snapshot', 'full_name_snapshot',
            'class_code_snapshot', 'class_name_snapshot', 'grade_code_snapshot', 'grade_name_snapshot')}
        row.update({name: str(value) for name, value in (
            ('roster_id', roster.id), ('student_id', roster.student_id), ('session_id', session.id),
            ('class_id', session.classroom_id), ('attendance_id', attendance.id))})
        row.update(school_date=session.school_date.isoformat(), slot=session.slot, session_status=session.status,
            status=attendance.status, arrival_status=arrival, source=attendance.source,
            recognition_mode=attendance.recognition_mode, uniform_source=attendance.uniform_source,
            recorded_by_id=str(attendance.recorded_by_id) if attendance.recorded_by_id else None,
            scanned_at=iso(scanned_at), arrived_at=iso(attendance.arrived_at), verified_at=iso(attendance.verified_at),
            required_uniform_snapshot=session.required_uniform_snapshot, observed_uniform=attendance.observed_uniform,
            uniform_status=attendance.uniform_status, absence_reason=attendance.absence_reason,
            uniform_reason=attendance.uniform_reason, uniform_note=attendance.uniform_note,
            checked_by_id=str(attendance.checked_by_id) if attendance.checked_by_id else None,
            checked_by_username=attendance.checked_by.username if attendance.checked_by_id else None,
            checked_at=iso(attendance.checked_at))
        result.append(row)
    return result
