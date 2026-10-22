import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import cv2
import numpy as np
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings


class UniformDemoTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.settings_override = override_settings(UNIFORM_DEMO_ROOT=str(self.root), VERCEL_DEMO=False)
        self.settings_override.enable(); self.addCleanup(self.settings_override.disable)
        rng=np.random.default_rng(22)
        ok,encoded=cv2.imencode('.png',rng.integers(0,255,(224,224,3),np.uint8)); self.assertTrue(ok)
        self.image=encoded.tobytes(); (self.root/'sample.png').write_bytes(self.image)
        (self.root/'model.onnx').write_bytes(b'controlled-test-model')
        self.manifest={'schema_version':1,'model_sha256':hashlib.sha256(b'controlled-test-model').hexdigest(),
            'labels':['NON_UNIFORM','KV_UNIFORM'],'threshold':.95,'samples':[
                {'id':'s1','path':'sample.png','sha256':hashlib.sha256(self.image).hexdigest(),
                 'expected':'KV_UNIFORM','title':'Mẫu test'}]}
        self.save_manifest()
        self.staff=get_user_model().objects.create_user(username='demo_staff',role='SUPERVISOR')
        self.student=get_user_model().objects.create_user(username='demo_student',role='STUDENT')
        self.client.force_login(self.staff)

    def save_manifest(self):
        (self.root/'bundle.json').write_text(json.dumps(self.manifest),encoding='utf-8')

    def test_disabled_remote_vercel_and_roles(self):
        with override_settings(UNIFORM_DEMO_ROOT=''):
            self.assertEqual(self.client.get('/api/v1/demo/uniform').status_code,404)
        with override_settings(VERCEL_DEMO=True):
            self.assertEqual(self.client.get('/api/v1/demo/uniform').status_code,404)
        self.assertEqual(self.client.get('/api/v1/demo/uniform',REMOTE_ADDR='203.0.113.5').status_code,404)
        self.client.logout()
        self.assertEqual(self.client.get('/uniform-demo/').status_code,401)
        self.assertEqual(self.client.get('/api/v1/demo/uniform').status_code,401)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get('/uniform-demo/').status_code,403)
        self.assertEqual(self.client.get('/api/v1/demo/uniform').status_code,403)
        self.assertEqual(self.client.get('/api/v1/demo/uniform/samples/s1').status_code,403)

    def test_sample_allowlist_private_cache_and_integrity(self):
        response=self.client.get('/api/v1/demo/uniform')
        self.assertEqual(response.status_code,200)
        self.assertNotIn('path',response.json()['samples'][0])
        response=self.client.get('/api/v1/demo/uniform/samples/s1')
        self.assertEqual(response.content,self.image)
        self.assertIn('no-store',response.headers['Cache-Control'])
        self.assertEqual(self.client.get('/api/v1/demo/uniform/samples/not-listed').status_code,404)
        self.manifest['samples'][0]['path']='../outside.png'; self.save_manifest()
        self.assertEqual(self.client.get('/api/v1/demo/uniform/samples/s1').status_code,503)

    def test_invalid_upload_and_csrf(self):
        self.assertEqual(self.client.post('/api/v1/demo/uniform/predict',{}).status_code,422)
        self.assertEqual(self.client.post('/api/v1/demo/uniform/predict',{'image':SimpleUploadedFile('x.png',b'bad')}).status_code,422)
        secure=Client(enforce_csrf_checks=True);secure.force_login(self.staff)
        self.assertEqual(secure.post('/api/v1/demo/uniform/predict',{}).status_code,403)

    def test_inference_reads_pixels_not_expected_label_and_never_marks_attendance(self):
        from school_app.attendance.models import Attendance
        before=Attendance.objects.count()
        with patch('school_app.demo_ui.uniform_demo.forward',return_value=np.array([10.,-10.])) as inference:
            response=self.client.post('/api/v1/demo/uniform/predict',{'image':SimpleUploadedFile('crop.png',self.image)})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['decision'],'NON_UNIFORM')
        self.assertTrue(response.json()['experiment_only'])
        self.assertFalse(response.json()['attendance_saved'])
        self.assertEqual(inference.call_count,1)
        self.assertEqual(Attendance.objects.count(),before)

    def test_changed_model_fails_closed_and_blank_is_unknown(self):
        ok,blank=cv2.imencode('.png',np.zeros((224,224,3),np.uint8));self.assertTrue(ok)
        response=self.client.post('/api/v1/demo/uniform/predict',{'image':SimpleUploadedFile('blank.png',blank.tobytes())})
        self.assertEqual(response.json()['decision'],'UNKNOWN')
        (self.root/'model.onnx').write_bytes(b'replaced')
        response=self.client.post('/api/v1/demo/uniform/predict',{'image':SimpleUploadedFile('crop.png',self.image)})
        self.assertEqual(response.status_code,503)
