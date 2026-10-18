"""Verified, process-local OpenCV models. Requests never download assets."""
from pathlib import Path
import threading

import cv2
from django.conf import settings

from school_app.accounts.services import AccountError

MODEL_KEY = 'sface-2021dec-fp32'
_cache = {}
_cache_lock = threading.RLock()


class ModelRuntime:
    def __init__(self, directory):
        # Imported lazily so the upload/HSV helpers do not require model assets.
        from .model_assets import ensure_models

        ensure_models(directory, download=False)
        cv2.setNumThreads(1)
        self.lock = threading.RLock()
        self.detector = cv2.FaceDetectorYN.create(
            str(directory / 'face_detection_yunet_2023mar.onnx'), '', (640, 640),
            score_threshold=0.9, nms_threshold=0.3, top_k=5000,
            backend_id=cv2.dnn.DNN_BACKEND_OPENCV, target_id=cv2.dnn.DNN_TARGET_CPU,
        )
        self.recognizer = cv2.FaceRecognizerSF.create(
            str(directory / 'face_recognition_sface_2021dec.onnx'), '',
            backend_id=cv2.dnn.DNN_BACKEND_OPENCV, target_id=cv2.dnn.DNN_TARGET_CPU,
        )


def get_runtime():
    directory = Path(settings.VISION_MODEL_DIR).resolve()
    with _cache_lock:
        if directory not in _cache:
            try:
                _cache[directory] = ModelRuntime(directory)
            except (OSError, ValueError, RuntimeError, cv2.error) as error:
                raise AccountError('VISION_UNAVAILABLE', 'Verified local face models are unavailable.', 503) from error
        return _cache[directory]
