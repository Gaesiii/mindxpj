from datetime import datetime, time
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from unittest.mock import patch

import cv2
from django.db import connection
from django.test import SimpleTestCase, override_settings, RequestFactory
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from tests import test_vision_api as fixtures


class ColdImportTests(SimpleTestCase):
    def test_resolving_ordinary_urls_does_not_load_inference_or_excel_libraries(self):
        code = """
import django,sys
django.setup()
from django.urls import resolve
for url in ('/','/api/v1/auth/login','/api/v1/classes','/api/v1/reports/summary'):
    resolve(url)
assert not {'cv2','numpy','openpyxl'}.intersection(sys.modules), sorted({'cv2','numpy','openpyxl'}.intersection(sys.modules))
"""
        env = {**os.environ, 'DJANGO_SETTINGS_MODULE':'config.settings',
               'DJANGO_SECRET_KEY':secrets.token_urlsafe(48)}
        result = subprocess.run([sys.executable, '-c', code], cwd=Path(__file__).resolve().parents[1],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class ScanQueryTests(fixtures.WorkflowCase):
    def test_analysis_fetches_embeddings_without_crop_image_blobs(self):
        clock = timezone.make_aware(datetime.combine(self.day,time(7,4)))
        with patch('django.utils.timezone.now',return_value=clock), \
             patch('school_app.vision.engine.extract_face',side_effect=lambda image:(cv2.resize(image[50:170,200:320],(112,112)),fixtures.BOX)), \
             patch('school_app.vision.engine.embed_face',side_effect=fixtures.VisionApiTests.synthetic_embedding):
            self.open()
            result=self.client.post(f'/api/v1/students/{self.student.pk}/face-samples',
                {'images':[fixtures.upload(fixtures.frame(seed)) for seed in (1,2,3)]})
            self.assertEqual(result.status_code,201,result.content)
            with CaptureQueriesContext(connection) as captured:
                result=self.client.post(f'/api/v1/sessions/{self.session.pk}/vision-scans',
                    {'image':fixtures.upload()},HTTP_IDEMPOTENCY_KEY='perf-scan')
            self.assertEqual(result.status_code,201,result.content)
            biometric_selects=[q['sql'] for q in captured if 'SELECT' in q['sql'].upper() and 'vision_facesample' in q['sql']]
            self.assertTrue(any('embedding' in sql for sql in biometric_selects))
            self.assertFalse(any('"vision_facesample"."image"' in sql for sql in biometric_selects), biometric_selects)


class WarmBootstrapTests(SimpleTestCase):
    def test_warm_requests_skip_copy_locks_and_directory_creation_but_recover_database_loss(self):
        from config.vercel_demo import DemoBootstrapMiddleware
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);database=root/'runtime/db.sqlite3';template=root/'template.sqlite3'
            template.write_bytes(b'fixture template')
            with override_settings(DATABASES={'default':{'NAME':str(database)}},
                VERCEL_DEMO_TEMPLATE=template,PRIVATE_MEDIA_ROOT=root/'private',FILE_UPLOAD_TEMP_DIR=str(root/'uploads')), \
                patch('config.vercel_demo.refresh_demo_sessions') as refresh:
                middleware=DemoBootstrapMiddleware(lambda request:'ok')
                self.assertEqual(middleware(RequestFactory().get('/')),'ok')
                with patch('config.vercel_demo.ensure_database',side_effect=AssertionError('warm copy lock')), \
                     patch.object(Path,'mkdir',side_effect=AssertionError('warm mkdir')):
                    self.assertEqual(middleware(RequestFactory().get('/')),'ok')
                database.unlink()
                self.assertEqual(middleware(RequestFactory().get('/')),'ok')
                self.assertTrue(database.is_file())
                self.assertEqual(refresh.call_count,2)
