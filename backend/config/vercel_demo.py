"""Build-seeded, instance-local demo storage. Never runs migrations at request time."""
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import tempfile
import threading

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

_thread_lock = threading.RLock()


@contextmanager
def storage_lock(path):
    """Coordinate threads and processes sharing this ephemeral filesystem."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _thread_lock, path.open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def ensure_database(template, database):
    template, database = Path(template), Path(database)
    with storage_lock(database.with_suffix('.bootstrap.lock')):
        if database.exists():
            return False
        if not template.is_file():
            raise ImproperlyConfigured('Vercel demo template missing; run backend/build_vercel.py during build.')
        descriptor, staging = tempfile.mkstemp(dir=database.parent, suffix='.sqlite3')
        os.close(descriptor)
        try:
            shutil.copyfile(template, staging)
            os.replace(staging, database)
            database.with_suffix('.sessions-date').unlink(missing_ok=True)
            return True
        finally:
            Path(staging).unlink(missing_ok=True)


def prepare_demo_rules():
    """Build-only: all-week, all-day rules using the existing staff scope."""
    from django.contrib.auth import get_user_model
    from school_app.academics.models import Classroom
    from school_app.schedules.models import ScheduleRule
    from school_app.schedules.services import save_rule
    from school_app.core.enums import Slot, RequiredUniform
    supervisor = get_user_model().objects.get(username='demo_supervisor')
    for classroom in Classroom.objects.filter(code__in=['DEMO10A', 'DEMO10B']):
        for weekday in range(7):
            for slot, uniform in [(Slot.MORNING, RequiredUniform.SHIRT), (Slot.AFTERNOON, RequiredUniform.SPORTS)]:
                rule = ScheduleRule.objects.filter(classroom=classroom, weekday=weekday, slot=slot).first()
                save_rule(supervisor, {'weekday': weekday, 'slot': slot, 'start_time': '00:00:00',
                          'close_time': '23:59:59', 'grace_minutes': 5, 'required_uniform': uniform},
                          classroom_id=classroom.pk, rule=rule)


def refresh_demo_sessions():
    """Open today's fictional rosters through the same services used by staff."""
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from django.utils import timezone
    from school_app.academics.models import Classroom
    from school_app.schedules.services import create_session, open_session
    from school_app.core.enums import Slot, SessionStatus
    with transaction.atomic():
        supervisor = get_user_model().objects.get(username='demo_supervisor')
        for classroom in Classroom.objects.filter(code__in=['DEMO10A', 'DEMO10B']):
            for slot in [Slot.MORNING, Slot.AFTERNOON]:
                session, _ = create_session(supervisor, {'class_id': str(classroom.pk),
                    'school_date': str(timezone.localdate()), 'slot': slot})
                if session.status == SessionStatus.PLANNED:
                    open_session(supervisor, session.pk, session.version)


class DemoBootstrapMiddleware:
    """Initialize only on real requests, before session/auth/database middleware."""
    def __init__(self, get_response):
        self.get_response = get_response
        self.prepared_date = None

    def __call__(self, request):
        from django.utils import timezone
        database = Path(settings.DATABASES['default']['NAME'])
        if ensure_database(settings.VERCEL_DEMO_TEMPLATE, database):
            self.prepared_date = None
        Path(settings.PRIVATE_MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
        Path(settings.FILE_UPLOAD_TEMP_DIR).mkdir(parents=True, exist_ok=True)
        today = timezone.localdate()
        if self.prepared_date != today:
            marker = database.with_suffix('.sessions-date')
            with storage_lock(database.with_suffix('.sessions.lock')):
                if not marker.exists() or marker.read_text() != str(today):
                    refresh_demo_sessions()
                    marker.write_text(str(today))
                self.prepared_date = today
        return self.get_response(request)
