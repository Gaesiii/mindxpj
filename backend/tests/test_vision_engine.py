import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from school_app.accounts.services import AccountError
from school_app.vision import engine, sface_models


BOX = (200, 50, 120, 120)


def frame(seed=1, color=(255, 255, 255)):
    image = np.full((480, 640, 3), color, dtype=np.uint8)
    rng = np.random.default_rng(seed)
    image[50:170, 200:320] = rng.integers(0, 256, (120, 120, 3), dtype=np.uint8)
    return image


def upload(image=None, name='image.png'):
    ok, encoded = cv2.imencode('.png', frame() if image is None else image)
    assert ok
    return SimpleUploadedFile(name, encoded.tobytes(), content_type='image/png')


class VisionEngineTests(SimpleTestCase):
    def test_runtime_sets_bounded_threads_and_verifies_before_loading_models(self):
        calls = []
        with patch('school_app.vision.model_assets.ensure_models', side_effect=lambda directory,download:calls.append(('verified', download))), \
             patch.object(cv2, 'setNumThreads', side_effect=lambda count:calls.append(('threads',count))), \
             patch.object(cv2.FaceDetectorYN, 'create', side_effect=lambda *args,**kwargs:calls.append(('detector',None))), \
             patch.object(cv2.FaceRecognizerSF, 'create', side_effect=lambda *args,**kwargs:calls.append(('recognizer',None))):
            sface_models.ModelRuntime(Path('unused-local-model-path'))
        self.assertEqual(calls, [('verified',False),('threads',1),('detector',None),('recognizer',None)])

    def test_runtime_cache_reuses_models_for_same_resolved_directory(self):
        with TemporaryDirectory() as directory, override_settings(VISION_MODEL_DIR=directory), \
             patch.object(sface_models, 'ModelRuntime') as constructor:
            try:
                first = sface_models.get_runtime()
                self.assertIs(sface_models.get_runtime(),first)
                constructor.assert_called_once_with(Path(directory).resolve())
            finally:
                sface_models._cache.pop(Path(directory).resolve(),None)

    def test_missing_models_fail_closed_without_network(self):
        with TemporaryDirectory() as directory, override_settings(VISION_MODEL_DIR=directory), \
             patch('urllib.request.urlopen',side_effect=AssertionError('Request must not download')) as request:
            with self.assertRaises(AccountError) as caught:
                sface_models.get_runtime()
            self.assertEqual(caught.exception.code,'VISION_UNAVAILABLE')
            request.assert_not_called()

    def test_shared_detector_alignment_and_feature_operations_hold_runtime_lock(self):
        lock = threading.RLock()
        row=np.array([200,50,120,120,225,80,285,80,255,110,235,140,275,140,.99],np.float32)
        aligned=cv2.resize(frame()[50:170,200:320],(112,112))
        def locked(value):
            self.assertTrue(lock._is_owned())
            return value
        runtime=SimpleNamespace(lock=lock,
            detector=SimpleNamespace(setInputSize=lambda size:locked(None), detect=lambda image:locked((None,np.array([row])))),
            recognizer=SimpleNamespace(alignCrop=lambda image,detection:locked(aligned),feature=lambda crop:locked(np.ones((1,128),np.float32))))
        with patch.object(engine,'get_runtime',return_value=runtime):
            crop,_=engine.extract_face(frame())
            self.assertEqual(len(engine.embed_face(crop)),512)

    def test_decode_checks_content_size_and_dimensions(self):
        self.assertEqual(engine.decode_upload(upload()).shape, (480, 640, 3))
        for file in [SimpleUploadedFile('x.jpg', b'not image'),
                     SimpleUploadedFile('x.png', b'x' * (2*1024*1024+1)),
                     upload(np.zeros((2100, 2100, 3), np.uint8))]:
            with self.assertRaises(AccountError):
                engine.decode_upload(file)

    def test_real_detector_rejects_blank_frame(self):
        with self.assertRaises(AccountError) as error:
            engine.extract_face(np.zeros((480, 640, 3), np.uint8))
        self.assertEqual(error.exception.code, 'NO_FACE')

    def test_one_face_normalized_multiple_blurry_and_small_rejected(self):
        with patch.object(engine, 'detect_faces', return_value=[BOX]):
            with patch.object(engine, 'align_face', return_value=cv2.resize(frame()[50:170,200:320], (112,112)), create=True):
                crop, box = engine.extract_face(frame())
            self.assertEqual(crop.shape, (112, 112, 3))
            self.assertEqual(box, BOX)
            with self.assertRaises(AccountError) as error:
                engine.extract_face(np.full((480, 640, 3), 128, np.uint8))
            self.assertEqual(error.exception.code, 'BLURRY_FACE')
        for boxes, code in [([BOX, BOX], 'MULTIPLE_FACES'), ([(10,10,30,30)], 'FACE_TOO_SMALL')]:
            with patch.object(engine, 'detect_faces', return_value=boxes):
                with self.assertRaises(AccountError) as error:
                    engine.extract_face(frame())
                self.assertEqual(error.exception.code, code)

    def test_cosine_match_unknown_ambiguous_and_best_sample_per_identity(self):
        first = np.eye(128, dtype='<f4')[0].tobytes()
        second = np.eye(128, dtype='<f4')[1].tobytes()
        with patch.object(engine, 'embed_face', return_value=first, create=True):
            result = engine.match_face(np.zeros((112,112,3), np.uint8), {'first':[second, first], 'second':[second]})
            self.assertEqual(result['student_id'], 'first')
            self.assertAlmostEqual(result['cosine_score'], 1)
            self.assertAlmostEqual(result['distance'], 0)
            self.assertEqual(engine.match_face(None, {})['reason'], 'NO_ENROLLMENT')
            self.assertEqual(engine.match_face(None, {'a':[first], 'b':[first]})['reason'], 'AMBIGUOUS_FACE')
            self.assertEqual(engine.match_face(None, {'a':[second]})['reason'], 'UNKNOWN_FACE')

    def test_matching_rejects_invalid_stored_vectors(self):
        first = np.eye(128, dtype='<f4')[0].tobytes()
        invalid = [b'bad', bytes(512), np.full(128,np.nan,dtype='<f4').tobytes(),
                   np.full(128,np.inf,dtype='<f4').tobytes(), np.ones(128,dtype='<f4').tobytes(),
                   memoryview(np.full(512, 1/np.sqrt(512),dtype='<f4'))]
        with patch.object(engine, 'embed_face', return_value=first, create=True):
            for data in invalid:
                with self.subTest(data_length=len(data)), self.assertRaises(AccountError) as caught:
                    engine.match_face(None, {'a':[data]})
                self.assertEqual(caught.exception.code, 'VISION_DATA_ERROR')

    def test_embedding_is_normalized_little_endian_128_floats(self):
        runtime = SimpleNamespace(lock=threading.RLock(), recognizer=SimpleNamespace(feature=lambda crop: np.arange(1,129,dtype=np.float32).reshape(1,128)))
        crop = cv2.resize(frame()[50:170,200:320], (112,112))
        with patch.object(engine, 'get_runtime', return_value=runtime, create=True):
            data = engine.embed_face(crop)
            self.assertEqual(len(data),512)
            vector = np.frombuffer(data,dtype='<f4')
            self.assertAlmostEqual(float(np.linalg.norm(vector)),1,places=6)
            self.assertGreater(vector[-1], vector[0])
            self.assertEqual(cv2.imdecode(np.frombuffer(engine.encode_face(crop),np.uint8),cv2.IMREAD_COLOR).shape,(112,112,3))
            for bad in [None, np.zeros((112,112),np.uint8), np.zeros((113,112,3),np.uint8), np.zeros((112,112,3),np.float32)]:
                with self.assertRaises(AccountError):
                    engine.embed_face(bad)

    def test_detector_bounds_resize_and_maps_all_landmarks(self):
        row = np.array([[100,20,100,100,120,40,180,40,150,60,130,90,170,90,.99]],np.float32)
        seen = []
        detector = SimpleNamespace(setInputSize=lambda size:seen.append(size), detect=lambda image:(None,row.copy()))
        runtime = SimpleNamespace(lock=threading.RLock(), detector=detector)
        with patch.object(engine,'get_runtime',return_value=runtime,create=True):
            detected = engine.detect_faces(np.zeros((960,1280,3),np.uint8))
        self.assertEqual(seen,[(640,480)])
        np.testing.assert_allclose(detected[0][:14], row[0][:14]*2)
        self.assertAlmostEqual(detected[0][14], .99, places=5)

    def test_uniform_colors_ambiguity_and_clipping(self):
        self.assertEqual(engine.suggest_uniform(frame(color=(255,255,255)), BOX)['observed_uniform'], 'SHIRT')
        self.assertEqual(engine.suggest_uniform(frame(color=(255,0,0)), BOX)['observed_uniform'], 'SPORTS')
        self.assertEqual(engine.suggest_uniform(frame(color=(0,255,0)), BOX)['observed_uniform'], 'UNKNOWN')
        self.assertEqual(engine.suggest_uniform(frame(), (200,400,120,120))['observed_uniform'], 'UNKNOWN')
        half=frame(); half[180:,260:]=(255,0,0)
        self.assertEqual(engine.suggest_uniform(half, BOX)['observed_uniform'], 'UNKNOWN')
