"""Pinned upstream weights; downloads are opt-in build/CLI operations only."""
import hashlib
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.request

from school_app.accounts.services import AccountError

REVISION = 'd4938dfc9d4ec5d098bfa33e98b3f3345a236586'
_BASE = f'https://huggingface.co/opencv/opencv_zoo/resolve/{REVISION}/models'
MODELS = [
    {'filename': 'face_detection_yunet_2023mar.onnx', 'size': 232589,
     'sha256': '8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4',
     'source': _BASE + '/face_detection_yunet/face_detection_yunet_2023mar.onnx'},
    {'filename': 'face_recognition_sface_2021dec.onnx', 'size': 38696353,
     'sha256': '0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79',
     'source': _BASE + '/face_recognition_sface/face_recognition_sface_2021dec.onnx'},
]


def _valid(path, model):
    if not path.is_file() or path.stat().st_size != model['size']:
        return False
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() == model['sha256']


def ensure_models(directory, *, download=False):
    """Validate all files; runtime calls must leave download=False."""
    directory = Path(directory)
    paths = []
    for model in MODELS:
        target = directory / model['filename']
        if not _valid(target, model):
            if not download:
                raise AccountError('VISION_UNAVAILABLE',
                                   'Face model missing or corrupt. Run manage.py prepare_vision_models.', 503)
            directory.mkdir(parents=True, exist_ok=True)
            descriptor, staging = tempfile.mkstemp(dir=directory, suffix='.download')
            try:
                with os.fdopen(descriptor, 'wb') as stream:
                    request = urllib.request.Request(model['source'], headers={'User-Agent': 'MindXDemo/1.0'})
                    with urllib.request.urlopen(request, timeout=90) as response:
                        remaining = model['size'] + 1
                        while remaining:
                            chunk = response.read(min(65536, remaining))
                            if not chunk:
                                break
                            stream.write(chunk)
                            remaining -= len(chunk)
                if not _valid(Path(staging), model):
                    raise AccountError('VISION_UNAVAILABLE', 'Downloaded face model failed integrity check.', 503)
                os.replace(staging, target)
            except (OSError, urllib.error.URLError) as error:
                raise AccountError('VISION_UNAVAILABLE', 'Could not prepare face models; retry the build command.', 503) from error
            finally:
                Path(staging).unlink(missing_ok=True)
        paths.append(target)
    return paths
