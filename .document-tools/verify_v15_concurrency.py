"""Standalone local SQLite races; inference mocks verify workflow, never accuracy.

Run with the project's Python environment. Only temporary fixture data is written;
the optional --output path receives a sanitized JSON report. This does not verify
HTTP middleware, production DB backends or distributed/serverless coordination.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time as day_time, timezone as utc_timezone
import json
import os
from pathlib import Path
import secrets
import sys
from tempfile import TemporaryDirectory
import threading
import time
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def verify(database):
    # This standalone process cannot reuse any development or deployed database.
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    os.environ['DJANGO_SECRET_KEY'] = secrets.token_urlsafe(48)
    os.environ['DJANGO_DB_PATH'] = str(database)
    os.environ.pop('VERCEL', None)
    sys.path.insert(0, str(ROOT / 'backend'))
    import django
    django.setup()
    import cv2
    import numpy as np
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.core.management import call_command
    from django.db import connections, connection, OperationalError
    from django.utils import timezone
    from school_app.accounts.services import AccountError
    from school_app.academics.models import Classroom, Grade
    from school_app.attendance.models import Attendance
    from school_app.core.models import ChangeLog, IdempotencyRequest
    from school_app.schedules.models import Session, SessionRoster
    from school_app.students.models import Student
    from school_app.students.services import create_student
    from school_app.vision import engine
    from school_app.vision.auto_attendance import analyze_auto
    from school_app.vision.models import FaceSample, VisionScan

    assert Path(settings.DATABASES['default']['NAME']) == database
    # Short bounded DB waits make lock contention visible; retries are callers'
    # responsibility here, as in the API's DATABASE_BUSY contract.
    settings.DATABASES['default']['OPTIONS'] = {'timeout': .25}
    call_command('migrate', verbosity=0, interactive=False)
    User = get_user_model()
    teacher = User.objects.create_user(username='race-teacher', role='HOMEROOM_TEACHER')
    supervisor = User.objects.create_user(username='race-supervisor', role='SUPERVISOR')
    grade = Grade.objects.create(code='RACE', name='Concurrency fixtures')
    classroom = Classroom.objects.create(code='ONE', name='Capacity one', grade=grade,
        teacher=teacher, capacity=1)

    def race(sql_prefix, operation):
        barrier = threading.Barrier(2, timeout=15)
        reached = []
        underlying_connections = []
        lock = threading.Lock()

        def worker(index):
            connections.close_all()
            connection.ensure_connection()
            with lock:
                underlying_connections.append(connection.connection)
            synchronized = False
            busy = 0

            def synchronize(execute, sql, params, many, context):
                nonlocal synchronized
                if not synchronized and sql.lstrip().upper().startswith(sql_prefix):
                    synchronized = True
                    with lock:
                        reached.append(index)
                    barrier.wait()  # Both real SQL writes are ready before either runs.
                return execute(sql, params, many, context)

            try:
                with connection.execute_wrapper(synchronize):
                    for attempt in range(30):
                        try:
                            result = operation(index)
                            return {'result': result, 'busy_retries': busy}
                        except OperationalError as exc:
                            if not any(word in str(exc).lower() for word in ('locked', 'busy')):
                                raise
                            busy += 1
                        except AccountError as exc:
                            if exc.code != 'DATABASE_BUSY':
                                raise
                            busy += 1
                        # The service transaction has rolled back before retry.
                        connection.close()
                        time.sleep(.025 * (1 + index) + min(attempt, 5) * .01)
                    raise AssertionError('Bounded database-busy retry exhausted')
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, i) for i in range(2)]
            results = [future.result(timeout=45) for future in futures]
        assert sorted(reached) == [0, 1], 'Both first write attempts must reach the barrier'
        assert len(underlying_connections) == 2
        assert underlying_connections[0] is not underlying_connections[1]
        return results

    try:
        def create(index):
            actor = User.objects.get(pk=supervisor.pk)
            try:
                create_student(actor, {'student_code': f'RACE{index}',
                    'full_name': 'Synthetic capacity fixture', 'class_id': str(classroom.pk)})
                return 'CREATED'
            except AccountError as exc:
                if exc.code != 'CAPACITY_CONFLICT':
                    raise
                return exc.code

        capacity = race('UPDATE "ACADEMICS_CLASSROOM"', create)
        assert sorted(item['result'] for item in capacity) == ['CAPACITY_CONFLICT', 'CREATED']
        assert classroom.students.filter(active=True).count() == 1
        assert ChangeLog.objects.filter(entity_type='Student', action='CREATE').count() == 1

        pupil = Student.objects.get(classroom=classroom)
        today = timezone.localdate()
        start = timezone.make_aware(datetime.combine(today, day_time.min))
        close = timezone.make_aware(datetime.combine(today, day_time.max))
        session = Session.objects.create(classroom=classroom, school_date=today,
            slot='MORNING', status='OPEN', start_at=start, late_cutoff_at=close,
            close_at=close, required_uniform_snapshot='SHIRT', version=1)
        roster = SessionRoster.objects.create(session=session, student=pupil,
            student_code_snapshot=pupil.student_code, full_name_snapshot=pupil.full_name,
            class_code_snapshot=classroom.code, class_name_snapshot=classroom.name,
            grade_code_snapshot=grade.code, grade_name_snapshot=grade.name)
        attendance = Attendance.objects.create(roster=roster)
        for i in range(3):
            FaceSample.objects.create(student=pupil, image=b'synthetic-fixture',
                embedding=np.ones(128, dtype=np.float32).tobytes(),
                model_key=engine.MODEL_KEY, digest=f'synthetic-{i}', created_by=teacher)
        raw_frames = []
        for seed in (1, 2):
            image = np.random.default_rng(seed).integers(0, 256, (240, 320, 3), dtype=np.uint8)
            ok, encoded = cv2.imencode('.png', image)
            assert ok
            raw_frames.append(encoded.tobytes())

        def scan(key):
            uploads = [SimpleUploadedFile('synthetic.png', raw, content_type='image/png')
                       for raw in raw_frames]
            return analyze_auto(User.objects.get(pk=teacher.pk), session.pk, uploads,
                                'AUTO_ATTENDANCE', 1, key)

        def extract(image):
            # decode_upload is intentionally real, so this also checks its output.
            assert image.shape == (240, 320, 3) and image.dtype == np.uint8
            return image[20:140, 80:200], (80, 20, 120, 120)

        def match(crop, samples, **thresholds):
            assert len(samples[str(pupil.pk)]) == 3
            assert thresholds['min_cosine'] == settings.VISION_AUTO_MIN_COSINE
            return {'student_id': str(pupil.pk), 'cosine_score': .9,
                    'distance': .1, 'reason': None}

        with patch.object(engine, 'extract_face', side_effect=extract), \
             patch.object(engine, 'match_face', side_effect=match):
            automatic = race('INSERT INTO "CORE_IDEMPOTENCYREQUEST"',
                             lambda index: scan('concurrent-same-key'))
            first_body, first_status = automatic[0]['result']
            assert automatic[1]['result'] == (first_body, first_status)
            assert first_status == 201 and first_body['outcome'] == 'RECORDED'
            attendance.refresh_from_db()
            first_arrival = attendance.arrived_at
            assert first_arrival is not None
            assert datetime.fromisoformat(first_body['attendance']['arrived_at'].replace('Z', '+00:00')) == first_arrival
            assert attendance.status == 'PRESENT' and attendance.version == 1
            assert attendance.recognition_mode == 'AUTO'
            assert attendance.verified_by_id is None and attendance.verified_at is None
            assert IdempotencyRequest.objects.filter(operation='vision.auto:'+str(session.pk),
                key='concurrent-same-key').count() == 1
            assert VisionScan.objects.filter(roster=roster, status='AUTO_RECORDED').count() == 1
            assert ChangeLog.objects.filter(entity_id=attendance.pk, action='AUTO_ATTENDANCE').count() == 1
            assert scan('concurrent-same-key') == (first_body, first_status)
            subsequent_body, subsequent_status = scan('later-new-key')
            assert subsequent_status == 200 and subsequent_body['outcome'] == 'ALREADY_RECORDED'
            attendance.refresh_from_db()
            assert attendance.arrived_at == first_arrival and attendance.version == 1
            assert VisionScan.objects.filter(roster=roster).count() == 1
            assert ChangeLog.objects.filter(entity_id=attendance.pk, action='AUTO_ATTENDANCE').count() == 1

        return {
            'status': 'PASS',
            'checked_at_utc': datetime.now(utc_timezone.utc).isoformat(),
            'database': 'isolated temporary file-backed SQLite; migrated from zero',
            'execution': 'two threads, separate DB connections, real SQL write barriers',
            'capacity_race': {'workers': 2, 'capacity': 1, 'created': 1,
                'capacity_conflicts': 1, 'active_students': 1,
                'busy_retries': sum(item['busy_retries'] for item in capacity)},
            'same_key_auto_race': {'workers': 2, 'equal_response_body_and_status': True,
                'response_status': first_status, 'idempotency_claims': 1,
                'attendance_version': 1, 'auto_recorded_scans': 1,
                'auto_attendance_audits': 1, 'arrival_preserved_on_replay_and_new_key': True,
                'busy_retries': sum(item['busy_retries'] for item in automatic)},
            'real_components': ['PNG decoding', 'scope/session/version checks',
                'database transactions', 'unique idempotency claim', 'attendance write',
                'scan and audit writes', 'uniform fallback without approved model'],
            'controlled_workflow_mocks': ['face extraction', 'face matching'],
            'limitations': ['No face or uniform accuracy claim; synthetic frames and controlled identity.',
                'Threads in one process with local SQLite; not global serverless or multi-host persistence.',
                'Service calls with bounded client-style busy retry; HTTP middleware is not exercised.'],
        }
    finally:
        connections.close_all()  # Required before TemporaryDirectory cleanup on Windows.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix='mindx-v15-concurrency-') as temporary:
        report = verify(Path(temporary) / 'concurrency.sqlite3')
    report['temporary_database_removed'] = not Path(temporary).exists()
    assert report['temporary_database_removed']
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding='utf-8')
    print(rendered, end='')


if __name__ == '__main__':
    main()
