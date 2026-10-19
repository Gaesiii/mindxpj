import numpy as np
from django.test import SimpleTestCase, TestCase, RequestFactory


class UniformInferenceTests(SimpleTestCase):
    def test_controlled_logits_require_body_confidence_and_consistency(self):
        # Contract tests only: fake logits are not school-model acceptance evidence.
        from unittest.mock import patch
        from school_app.vision.uniform_model import evaluate_pair
        class Net:
            def __init__(self,outputs): self.outputs=iter(outputs)
            def setInput(self,blob): pass
            def forward(self): return np.asarray(next(self.outputs),np.float32)
        image=np.random.default_rng(42).integers(20,230,(500,500,3),dtype=np.uint8)
        snap={'version':1,'labels':['SHIRT','SPORTS','OTHER'],'threshold':.95,'required_uniform':'SHIRT'}
        cases=[([[0,0,0],[0,0,0]],'UNKNOWN','NOT_CHECKED'),
               ([[10,0,0],[0,10,0]],'UNKNOWN','NOT_CHECKED'),
               ([[0,10,0],[0,10,0]],'SPORTS','REVIEW_REQUIRED'),
               ([[10,0,0],[10,0,0]],'SHIRT','COMPLIANT')]
        for outputs,observed,status in cases:
            with patch('school_app.vision.uniform_model.runtime',return_value=Net(outputs)):
                result=evaluate_pair([image,image],[(200,20,80,80)]*2,snap)
            self.assertEqual(result['observed_uniform'],observed)
            self.assertEqual(result['uniform_status'],status)
        with patch('school_app.vision.uniform_model.runtime',return_value=Net([])):
            result=evaluate_pair([image[:100],image[:100]],[(200,20,80,80)]*2,snap)
        self.assertEqual(result['uniform_status'],'NOT_CHECKED')

    def test_missing_model_never_suggests_compliance(self):
        from school_app.vision.uniform_model import evaluate_pair
        result = evaluate_pair([np.zeros((400,400,3),np.uint8)]*2, [(100,20,80,80)]*2, None)
        self.assertEqual(result['observed_uniform'], 'UNKNOWN')
        self.assertEqual(result['uniform_status'], 'NOT_CHECKED')

    def test_artifact_path_rejects_traversal(self):
        from school_app.vision.uniform_model import artifact_path
        for key in ['../model.onnx','C:\\model.onnx','sub/model.onnx','model.pkl']:
            with self.assertRaises(ValueError): artifact_path(key)


class UniformScopeTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from school_app.academics.models import Grade, Classroom
        from school_app.vision.uniform_models import SchoolUniformSample
        U = get_user_model()
        self.supervisor = U.objects.create_user(username='uniform-supervisor',role='SUPERVISOR')
        self.teacher = U.objects.create_user(username='uniform-teacher',role='HOMEROOM_TEACHER')
        self.other = U.objects.create_user(username='uniform-other',role='HOMEROOM_TEACHER')
        self.student = U.objects.create_user(username='uniform-student',role='STUDENT')
        grade = Grade.objects.create(code='UN',name='Uniform')
        self.classroom = Classroom.objects.create(code='UN1',name='Uniform',grade=grade,teacher=self.teacher)
        self.sample = SchoolUniformSample.objects.create(classroom=self.classroom,image=b'private-garment',digest='1'*64,
            label='SHIRT',capture_group='group1',split='train',created_by=self.supervisor)

    def test_private_image_scope(self):
        from school_app.vision.uniform_views import uniform_sample_image
        for user,status in [(self.teacher,200),(self.other,404),(self.student,403)]:
            req = RequestFactory().get('/image'); req.user = user
            response = uniform_sample_image(req,self.sample.pk)
            self.assertEqual(response.status_code,status)
            if status == 200:
                self.assertIn('no-store',response['Cache-Control'])

    def test_teacher_cannot_export_or_delete(self):
        from school_app.vision.uniform_views import uniform_dataset_export,uniform_sample_image
        req = RequestFactory().get('/export'); req.user = self.teacher
        self.assertEqual(uniform_dataset_export(req,self.classroom.pk).status_code,403)
        req = RequestFactory().delete('/image'); req.user = self.teacher
        self.assertEqual(uniform_sample_image(req,self.sample.pk).status_code,403)

    def test_teacher_cannot_upload_or_select_profile(self):
        from school_app.vision.uniform_services import add_sample,select_profile
        from school_app.accounts.services import AccountError
        for operation in [lambda:add_sample(self.teacher,self.classroom.pk,None,{}),
                          lambda:select_profile(self.teacher,self.classroom.pk,{'profile_id':None})]:
            with self.assertRaises(AccountError) as exc: operation()
            self.assertEqual(exc.exception.status,403)

    def test_missing_roi_rejected_before_image_processing(self):
        from school_app.vision.uniform_services import add_sample
        from school_app.accounts.services import AccountError
        with self.assertRaises(AccountError) as exc:
            add_sample(self.supervisor,self.classroom.pk,None,{'label':'SHIRT','split':'train','capture_group':'g'})
        self.assertEqual(exc.exception.status,422)

    def test_face_pixels_are_excluded_from_stored_crop(self):
        # Detector geometry is stubbed to test storage/privacy, not real model accuracy.
        import cv2
        from unittest.mock import patch
        from school_app.vision.uniform_services import add_sample
        from school_app.vision.uniform_models import SchoolUniformSample
        image=np.zeros((400,300,3),np.uint8)
        image[:100]=[0,0,255]; image[150:300,50:200]=[255,0,0]
        with patch('school_app.vision.engine.decode_upload',return_value=image), patch(
            'school_app.vision.engine.detect_faces',side_effect=[np.array([[50,10,80,80]]),[]]):
            result=add_sample(self.supervisor,self.classroom.pk,None,
                {'label':'SPORTS','split':'test','capture_group':'private-g2','roi':'[50,150,150,150]'})
        sample=SchoolUniformSample.objects.get(pk=result['id'])
        stored=cv2.imdecode(np.frombuffer(bytes(sample.image),np.uint8),cv2.IMREAD_COLOR)
        self.assertEqual(stored.shape,(150,150,3))
        self.assertTrue(np.all(stored==[255,0,0]))

    def test_roi_crossing_face_is_rejected_without_storage(self):
        from unittest.mock import patch
        from school_app.vision.uniform_services import add_sample
        from school_app.vision.uniform_models import SchoolUniformSample
        from school_app.accounts.services import AccountError
        with patch('school_app.vision.engine.decode_upload',return_value=np.zeros((400,300,3),np.uint8)), patch(
            'school_app.vision.engine.detect_faces',return_value=np.array([[50,10,80,80]])):
            with self.assertRaises(AccountError):
                add_sample(self.supervisor,self.classroom.pk,None,
                    {'label':'SPORTS','split':'test','capture_group':'private-g2','roi':'[50,50,150,150]'})
        self.assertEqual(SchoolUniformSample.objects.count(),1)

    def test_archived_class_write_rejected(self):
        from school_app.vision.uniform_services import select_profile
        from school_app.accounts.services import AccountError
        self.classroom.active=False; self.classroom.save()
        with self.assertRaises(AccountError) as exc:
            select_profile(self.supervisor,self.classroom.pk,{'profile_id':None})
        self.assertEqual(exc.exception.status,409)

    def test_archive_during_crop_inference_prevents_sample_write(self):
        from unittest.mock import patch
        from school_app.vision.uniform_services import add_sample
        from school_app.vision.uniform_models import SchoolUniformSample
        from school_app.accounts.services import AccountError
        from school_app.academics.models import Classroom
        def detector(image):
            Classroom.objects.filter(pk=self.classroom.pk).update(active=False)
            return np.array([[50,10,80,80]]) if image.shape[0]==400 else []
        with patch('school_app.vision.engine.decode_upload',return_value=np.zeros((400,300,3),np.uint8)), patch(
            'school_app.vision.engine.detect_faces',side_effect=detector):
            with self.assertRaises(AccountError) as exc:
                add_sample(self.supervisor,self.classroom.pk,None,
                    {'label':'SHIRT','split':'test','capture_group':'racing','roi':'[50,150,150,150]'})
        self.assertEqual(exc.exception.status,409)
        self.assertEqual(SchoolUniformSample.objects.count(),1)

    def test_operator_revocation_during_crop_inference_prevents_write(self):
        from unittest.mock import patch
        from django.contrib.auth import get_user_model
        from school_app.vision.uniform_services import add_sample
        from school_app.vision.uniform_models import SchoolUniformSample
        from school_app.accounts.services import AccountError
        def detector(image):
            get_user_model().objects.filter(pk=self.supervisor.pk).update(is_active=False)
            return np.array([[50,10,80,80]]) if image.shape[0]==400 else []
        with patch('school_app.vision.engine.decode_upload',return_value=np.zeros((400,300,3),np.uint8)), patch(
            'school_app.vision.engine.detect_faces',side_effect=detector):
            with self.assertRaises(AccountError) as exc:
                add_sample(self.supervisor,self.classroom.pk,None,
                    {'label':'SHIRT','split':'test','capture_group':'revoked','roi':'[50,150,150,150]'})
        self.assertEqual(exc.exception.status,401)
        self.assertEqual(SchoolUniformSample.objects.count(),1)

    def test_profile_from_other_class_cannot_be_selected(self):
        from school_app.vision.uniform_services import select_profile
        from school_app.vision.uniform_models import SchoolUniformProfile
        from school_app.academics.models import Classroom
        from school_app.accounts.services import AccountError
        other_class=Classroom.objects.create(code='UN2',name='Other',grade=self.classroom.grade,teacher=self.other)
        profile=SchoolUniformProfile.objects.create(classroom=other_class,version=1,model_key='test.onnx',model_sha256='a'*64,created_by=self.supervisor)
        with self.assertRaises(AccountError) as exc:
            select_profile(self.supervisor,self.classroom.pk,{'profile_id':str(profile.pk)})
        self.assertEqual(exc.exception.status,404)


    def test_dataset_export_contains_only_garment_samples(self):
        import io,json,zipfile
        from school_app.vision.uniform_services import export_dataset
        with zipfile.ZipFile(io.BytesIO(export_dataset(self.supervisor,self.classroom.pk))) as z:
            manifest = json.loads(z.read('manifest.json'))
            self.assertEqual(len(manifest['samples']),1)
            self.assertEqual(z.read(manifest['samples'][0]['path']),b'private-garment')

    def test_vercel_export_rejects_oversize_before_building_archive(self):
        from django.test import override_settings
        from school_app.vision.uniform_services import export_dataset
        from school_app.accounts.services import AccountError
        self.sample.image=b'x'*(4*1024*1024)
        self.sample.save(update_fields=['image'])
        with override_settings(VERCEL_DEMO=True):
            with self.assertRaises(AccountError) as exc:
                export_dataset(self.supervisor,self.classroom.pk)
        self.assertEqual(exc.exception.code,'EXPORT_LIMIT_EXCEEDED')

    def test_profile_snapshot_and_immutable_versions(self):
        from django.core.exceptions import ValidationError
        from school_app.vision.uniform_models import SchoolUniformProfile,SchoolUniformSelection
        from school_app.vision.uniform_services import snapshot_for_class
        self.assertIsNone(snapshot_for_class(self.classroom.pk))
        profile = SchoolUniformProfile.objects.create(classroom=self.classroom,version=1,model_key='test.onnx',
            model_sha256='a'*64,labels=['SHIRT','SPORTS','OTHER'],accepted_labels=['SHIRT'],created_by=self.supervisor)
        SchoolUniformSelection.objects.create(classroom=self.classroom,profile=profile)
        snap = snapshot_for_class(self.classroom.pk)
        self.assertEqual(snap['version'],1)
        profile.threshold = .5
        with self.assertRaises(ValidationError): profile.save()
        self.assertEqual(snap['threshold'],.95)

    def test_cropped_body_is_unknown(self):
        from school_app.vision.uniform_model import torso_crop
        self.assertIsNone(torso_crop(np.zeros((100,100,3),np.uint8), (20,20,60,60)))

    def test_missing_artifact_is_not_checked(self):
        from school_app.vision.uniform_model import evaluate_pair
        result = evaluate_pair([np.zeros((500,500,3),np.uint8)]*2, [(200,20,80,80)]*2,
            {'version':1,'model_key':'missing.onnx','model_sha256':'0'*64,'threshold':.95,
             'labels':['SHIRT','SPORTS','OTHER'],'required_uniform':'SHIRT'})
        self.assertEqual(result['uniform_status'], 'NOT_CHECKED')
        self.assertEqual(result['reason'],'MODEL_UNAVAILABLE')


class OfflineManifestTests(SimpleTestCase):
    def test_importer_rejects_unapproved_or_tampered_reports(self):
        import importlib.util,json,hashlib,copy
        from pathlib import Path
        path=Path(__file__).resolve().parents[2]/'tools/uniform_training/import_artifact.py'
        spec=importlib.util.spec_from_file_location('uniform_importer',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        data=b'fake-contract-only'
        report={'model_sha256':hashlib.sha256(data).hexdigest(),'labels':['SHIRT','SPORTS','OTHER'],
            'threshold':.95,'metrics':{s:{'precision':.99} for s in ['SHIRT','SPORTS','OTHER']}}
        raw=json.dumps(report).encode()
        review={'report_sha256':hashlib.sha256(raw).hexdigest(),'supervisor_id':'supervisor',
            'approved':True,'school_logo_shape_reviewed':True,'wrong_school_hard_negatives_reviewed':True,
            'occlusion_unknown_behavior_reviewed':True,'evidence_reference':'private-review'}
        # Validation success here checks metadata only, never ONNX import/accuracy.
        module.validate_review(data,report,review,raw,'supervisor')
        cases=[(b'tampered',report,review,raw),(data,report,{},raw),
               (data,report,review,b'tampered-report')]
        low=copy.deepcopy(report); low['metrics']['SHIRT']['precision']=.7
        cases.append((data,low,review,raw))
        low=copy.deepcopy(report); low['threshold']=.2
        cases.append((data,low,review,raw))
        for artifact,rep,rev,raw_report in cases:
            with self.assertRaises(ValueError): module.validate_review(artifact,rep,rev,raw_report,'supervisor')

    def test_capture_group_leakage_is_rejected(self):
        import importlib.util, json, hashlib, tempfile
        from pathlib import Path
        path=Path(__file__).resolve().parents[2]/'tools/uniform_training/pipeline.py'
        spec=importlib.util.spec_from_file_location('uniform_pipeline',path)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); rows=[]
            for index,split in enumerate(['train','val']):
                data=f'image{index}'.encode(); (root/f'{index}.png').write_bytes(data)
                rows.append({'path':f'{index}.png','sha256':hashlib.sha256(data).hexdigest(),
                    'capture_group':'same','split':split,'label':'SHIRT'})
            (root/'manifest.json').write_text(json.dumps({'schema_version':1,'labels':['SHIRT','SPORTS','OTHER'],'samples':rows}))
            with self.assertRaisesRegex(ValueError,'leakage'): module.validate_manifest(root)
