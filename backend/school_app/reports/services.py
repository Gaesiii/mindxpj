"""M07 canonical-row aggregation; report counts are student-session counts."""
from django.db import transaction
from django.utils import timezone
from school_app.academics.services import scoped_classes
from school_app.accounts.services import AccountError
from school_app.core.enums import Role


def summarize(rows):
    counts = dict.fromkeys(('expected', 'present', 'absent', 'unmarked', 'on_time', 'late',
                            'compliant', 'non_compliant', 'not_checked'), 0)
    for row in rows:
        counts['expected'] += 1
        counts[row['status'].lower()] += 1
        if row['status'] == 'PRESENT':
            counts[row['arrival_status'].lower()] += 1
            counts[row['uniform_status'].lower()] += 1
    counts['checked'] = counts['compliant'] + counts['non_compliant']
    for key, numerator, denominator in (
            ('presence_rate', 'present', 'expected'), ('late_rate', 'late', 'present'),
            ('violation_rate', 'non_compliant', 'checked'), ('check_coverage', 'checked', 'present')):
        counts[key] = counts[numerator] / counts[denominator] if counts[denominator] else None
    return counts


def report(user, filters, *, export=False):
    from school_app.reports.queries import canonical_rows
    # One read transaction includes scope, attendance and confirmed scans. Export
    # renders the materialized result outside the transaction.
    with transaction.atomic():
        classes = scoped_classes(user)
        if filters.get('class_id') and not classes.filter(pk=filters['class_id']).exists():
            raise AccountError('FORBIDDEN', 'Classroom filter is outside your scope.', 403)
        if filters.get('grade_id'):
            if user.role == Role.HOMEROOM_TEACHER and not classes.filter(grade_id=filters['grade_id']).exists():
                raise AccountError('FORBIDDEN', 'Grade filter is outside your scope.', 403)
        rows = canonical_rows(classes, filters, limit=5001 if export else None)
        if export and len(rows) > 5000:
            raise AccountError('EXPORT_LIMIT_EXCEEDED', 'Tối đa 5.000 dòng; hãy chia khoảng ngày hoặc lớp.', 422,
                               {'limit': 5000})
        scope = {'role': user.role, 'class_ids': [str(value) for value in classes.values_list('id', flat=True)]}
    return {'items': rows, 'summary': summarize(rows), 'metadata': {
        'generated_at': timezone.now().isoformat(), 'timezone': 'Asia/Ho_Chi_Minh',
        'filters': {key: str(value) for key, value in filters.items() if value is not None and value != ''},
        'scope': scope}}
