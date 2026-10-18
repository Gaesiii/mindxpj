"""Temporary Vercel demo storage and security contracts."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from django.test import SimpleTestCase


class VercelSettingsTests(SimpleTestCase):
    def test_vercel_settings_use_secure_ephemeral_defaults(self):
        env = {**os.environ, 'VERCEL': '1', 'DJANGO_SECRET_KEY': secrets.token_urlsafe(48),
               'VERCEL_URL': 'preview-example.vercel.app', 'VERCEL_PROJECT_PRODUCTION_URL': 'demo.vercel.app'}
        env.pop('DJANGO_DEBUG', None)
        env.pop('DJANGO_DB_PATH', None)
        env.pop('DJANGO_ALLOWED_HOSTS', None)
        env.pop('VISION_ENROLLMENT_TOTAL_BYTES', None)
        code = "import config.settings as s,json; print(json.dumps([s.DEBUG,s.ALLOWED_HOSTS,s.SESSION_COOKIE_SECURE,s.CSRF_COOKIE_SECURE,s.SESSION_ENGINE,str(s.DATABASES['default']['NAME']),s.MIDDLEWARE[0],getattr(s,'VISION_ENROLLMENT_TOTAL_BYTES',None)]))"
        result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, check=True)
        values = json.loads(result.stdout)
        self.assertFalse(values[0])
        self.assertEqual(set(values[1]), {'preview-example.vercel.app', 'demo.vercel.app'})
        self.assertEqual(values[2:5], [True, True, 'django.contrib.sessions.backends.signed_cookies'])
        self.assertTrue(Path(values[5]).is_relative_to(Path(tempfile.gettempdir())))
        self.assertEqual(values[6], 'config.vercel_demo.DemoBootstrapMiddleware')
        self.assertEqual(values[7], 3 * 1024 * 1024)

    def test_vercel_still_requires_secret(self):
        env = {**os.environ, 'VERCEL': '1'}
        env.pop('DJANGO_SECRET_KEY', None)
        result = subprocess.run([sys.executable, '-c', 'import config.settings'], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Set DJANGO_SECRET_KEY', result.stderr)


class TemplateCopyTests(SimpleTestCase):
    def test_runtime_copies_once_and_preserves_warm_changes(self):
        from config.vercel_demo import ensure_database
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template, database = root / 'template.sqlite3', root / 'runtime' / 'db.sqlite3'
            template.write_bytes(b'build template')
            ensure_database(template, database)
            self.assertEqual(database.read_bytes(), b'build template')
            database.write_bytes(b'warm change')
            ensure_database(template, database)
            self.assertEqual(database.read_bytes(), b'warm change')

    def test_missing_template_fails_without_creating_database(self):
        from config.vercel_demo import ensure_database
        from django.core.exceptions import ImproperlyConfigured
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesMessage(ImproperlyConfigured, 'build_vercel.py'):
                ensure_database(root / 'missing', root / 'db.sqlite3')
            self.assertFalse((root / 'db.sqlite3').exists())


class VercelRequestTests(SimpleTestCase):
    def test_cold_start_login_csrf_scope_and_next_day_refresh(self):
        # A separate process exercises the actual middleware order, SQLite copy,
        # signed session and secure proxy configuration without the test DB.
        code = '''
import os, tempfile, secrets, json
from pathlib import Path
from unittest.mock import patch
from datetime import timedelta
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    template = root / 'template.sqlite3'
    os.environ['DJANGO_DB_PATH'] = str(template)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    os.environ['DEMO_PASSWORD'] = secrets.token_urlsafe(30)
    import django
    django.setup()
    from django.conf import settings
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    from django.core.management import call_command
    from django.db import connections
    from django.test import Client
    from django.utils import timezone
    from config.vercel_demo import prepare_demo_rules, refresh_demo_sessions
    from school_app.schedules.models import Session, ScheduleRule
    from school_app.attendance.models import Attendance
    call_command('migrate', interactive=False, verbosity=0)
    call_command('seed_demo', verbosity=0)
    prepare_demo_rules()
    refresh_demo_sessions()
    assert ScheduleRule.objects.count() == 28
    assert Session.objects.count() == 4
    assert Attendance.objects.filter(status='PRESENT').count() == 0
    connections.close_all()
    runtime = root / 'runtime.sqlite3'
    settings.DATABASES['default']['NAME'] = str(runtime)
    connections['default'].settings_dict['NAME'] = str(runtime)
    settings.VERCEL_DEMO_TEMPLATE = template
    settings.PRIVATE_MEDIA_ROOT = root / 'photos'
    settings.FILE_UPLOAD_TEMP_DIR = str(root / 'uploads')
    client = Client(enforce_csrf_checks=True, HTTP_HOST='demo.vercel.app', HTTP_X_FORWARDED_PROTO='https')
    response = client.get('/')
    assert response.status_code == 200
    assert runtime.is_file()
    assert response.cookies['csrftoken']['secure']
    payload = {'username': 'demo_supervisor', 'password': os.environ['DEMO_PASSWORD']}
    assert client.post('/api/v1/auth/login', json.dumps(payload), content_type='application/json').status_code == 403
    csrf = client.cookies['csrftoken'].value
    assert client.post('/api/v1/auth/login', json.dumps(payload), content_type='application/json', HTTP_X_CSRFTOKEN=csrf, HTTP_ORIGIN='https://evil.example').status_code == 403
    response = client.post('/api/v1/auth/login', json.dumps(payload), content_type='application/json', HTTP_X_CSRFTOKEN=csrf, HTTP_ORIGIN='https://demo.vercel.app')
    assert response.status_code == 200, response.content
    assert response.cookies['sessionid']['secure']
    assert client.get('/api/v1/classes').status_code == 200
    assert client.get('/api/v1/auth/me').status_code == 200
    # The same signed identity works against a fresh copy of the build template.
    connections.close_all()
    runtime.unlink()
    assert client.get('/api/v1/auth/me').status_code == 200
    tomorrow = timezone.localdate() + timedelta(days=1)
    with patch('django.utils.timezone.localdate', return_value=tomorrow):
        assert client.get('/').status_code == 200
        connections.close_all()
        runtime.unlink()
        assert client.get('/').status_code == 200
        assert Session.objects.filter(school_date=tomorrow, status='OPEN').count() == 4
    assert Session.objects.filter(school_date=tomorrow, status='OPEN').count() == 4
    assert Attendance.objects.filter(status='PRESENT').count() == 0
    student = Client(enforce_csrf_checks=True, HTTP_HOST='demo.vercel.app', HTTP_X_FORWARDED_PROTO='https')
    student.get('/')
    payload['username'] = 'demo_student_01'
    response = student.post('/api/v1/auth/login', json.dumps(payload), content_type='application/json', HTTP_X_CSRFTOKEN=student.cookies['csrftoken'].value, HTTP_ORIGIN='https://demo.vercel.app')
    assert response.status_code == 200
    assert student.get('/api/v1/classes').status_code == 403
    assert client.get('/', HTTP_HOST='evil.example').status_code == 400
    connections.close_all()
'''
        env = {**os.environ, 'VERCEL': '1', 'VERCEL_URL': 'demo.vercel.app',
               'DJANGO_SECRET_KEY': secrets.token_urlsafe(48)}
        env.pop('DJANGO_ALLOWED_HOSTS', None)
        result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class VercelBuildTests(SimpleTestCase):
    def test_missing_variable_is_named_without_exposing_configured_secret(self):
        secret = secrets.token_urlsafe(48)
        env = {**os.environ, 'DJANGO_SECRET_KEY': secret, 'VERCEL_ENV': 'production',
               'VERCEL_GIT_COMMIT_SHA': 'abcdef1234567890'}
        env.pop('DEMO_PASSWORD', None)
        result = subprocess.run([sys.executable, 'build_vercel.py'], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing build variables: DEMO_PASSWORD', result.stderr)
        self.assertIn('environment=production commit=abcdef123456', result.stdout)
        self.assertIn('DJANGO_SECRET_KEY=set DEMO_PASSWORD=missing', result.stdout)
        self.assertNotIn(secret, result.stdout + result.stderr)

    def test_both_missing_variables_fail_before_django_or_model_setup(self):
        env = os.environ.copy()
        for key in ('DJANGO_SECRET_KEY', 'DEMO_PASSWORD'):
            env.pop(key, None)
        result = subprocess.run([sys.executable, 'build_vercel.py'], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing build variables: DJANGO_SECRET_KEY, DEMO_PASSWORD', result.stderr)
        self.assertIn('Local .env.vercel is not loaded on Vercel', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_failed_seed_preserves_previous_template_and_removes_staging(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / '.vercel-demo' / 'template.sqlite3'
            target.parent.mkdir()
            target.write_bytes(b'previous working template')
            code = """
import sys, build_vercel
from django.core.management.base import CommandError
build_vercel.__file__ = sys.argv[1]
try:
    build_vercel.main()
except CommandError:
    pass
else:
    raise AssertionError('Weak build password was accepted')
"""
            env = {**os.environ, 'DJANGO_SECRET_KEY': secrets.token_urlsafe(48), 'DEMO_PASSWORD': '123'}
            result = subprocess.run([sys.executable, '-c', code, str(root / 'build_vercel.py')],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_bytes(), b'previous working template')
            self.assertEqual(list(target.parent.iterdir()), [target])


from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from unittest.mock import patch
from tests.test_schedule_api import WorkflowCase


class VercelEnrollmentBudgetTests(WorkflowCase):
    @override_settings(VISION_ENROLLMENT_TOTAL_BYTES=3 * 1024 * 1024)
    def test_rejects_over_budget_batch_before_decoding_or_replacing_samples(self):
        from school_app.vision import engine
        from school_app.vision.models import FaceSample
        url = f'/api/v1/students/{self.student.pk}/face-samples'
        images = [SimpleUploadedFile(f'{index}.jpg', b'x' * (1024 * 1024 + 1),
                                    content_type='image/jpeg') for index in range(3)]
        with patch('school_app.vision.engine.decode_upload', wraps=engine.decode_upload) as decode:
            result = self.client.post(url, {'images': images})
        self.assertEqual(result.status_code, 422)
        self.assertIn('3 MiB', result.json()['message'])
        decode.assert_not_called()
        self.assertEqual(FaceSample.objects.count(), 0)
