import io
from unittest.mock import patch

import cv2
import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from school_app.accounts.services import AccountError
from school_app.vision import engine


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
            crop, box = engine.extract_face(frame())
            self.assertEqual(crop.shape, (128, 128))
            self.assertEqual(box, BOX)
            with self.assertRaises(AccountError) as error:
                engine.extract_face(np.full((480, 640, 3), 128, np.uint8))
            self.assertEqual(error.exception.code, 'BLURRY_FACE')
        for boxes, code in [([BOX, BOX], 'MULTIPLE_FACES'), ([(10,10,30,30)], 'FACE_TOO_SMALL')]:
            with patch.object(engine, 'detect_faces', return_value=boxes):
                with self.assertRaises(AccountError) as error:
                    engine.extract_face(frame())
                self.assertEqual(error.exception.code, code)

    def test_actual_lbph_matches_rejects_unknown_and_ambiguous(self):
        with patch.object(engine, 'detect_faces', return_value=[BOX]):
            first, _ = engine.extract_face(frame(1))
            second, _ = engine.extract_face(frame(2))
        samples = {'first': [engine.encode_face(first)], 'second': [engine.encode_face(second)]}
        result = engine.match_face(first, samples)
        self.assertEqual(result['student_id'], 'first')
        self.assertAlmostEqual(result['distance'], 0)
        self.assertIsNone(engine.match_face(first, {})['student_id'])
        self.assertIsNone(engine.match_face(first, {'a': samples['first'], 'b': samples['first']})['student_id'])
        with override_settings(VISION_FACE_MAX_DISTANCE=0.1):
            self.assertIsNone(engine.match_face(second, {'first': samples['first']})['student_id'])

    def test_uniform_colors_ambiguity_and_clipping(self):
        self.assertEqual(engine.suggest_uniform(frame(color=(255,255,255)), BOX)['observed_uniform'], 'SHIRT')
        self.assertEqual(engine.suggest_uniform(frame(color=(255,0,0)), BOX)['observed_uniform'], 'SPORTS')
        self.assertEqual(engine.suggest_uniform(frame(color=(0,255,0)), BOX)['observed_uniform'], 'UNKNOWN')
        self.assertEqual(engine.suggest_uniform(frame(), (200,400,120,120))['observed_uniform'], 'UNKNOWN')
        half=frame(); half[180:,260:]=(255,0,0)
        self.assertEqual(engine.suggest_uniform(half, BOX)['observed_uniform'], 'UNKNOWN')
