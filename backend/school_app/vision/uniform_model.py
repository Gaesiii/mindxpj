"""Private, hash-pinned OpenCV DNN inference. Never downloads or trains."""
import hashlib
import threading
from pathlib import Path
import cv2
import numpy as np
from django.conf import settings

LABELS = ['SHIRT', 'SPORTS', 'OTHER']
_cache = {}
_lock = threading.RLock()


def artifact_root():
    return Path(getattr(settings, 'UNIFORM_MODEL_ROOT', settings.BASE_DIR / 'private_uniform_models')).resolve()


def artifact_path(key):
    if not isinstance(key, str) or Path(key).name != key or not key.endswith('.onnx') or '/' in key or '\\' in key:
        raise ValueError('Invalid artifact key')
    path = (artifact_root() / key).resolve()
    if path.parent != artifact_root():
        raise ValueError('Artifact outside private root')
    return path


def runtime(snapshot):
    path = artifact_path(snapshot['model_key'])
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('Artifact too large')
    # Verify on each acquisition; cache does not hide replaced files.
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != snapshot['model_sha256']:
        raise ValueError('Artifact integrity mismatch')
    with _lock:
        if digest not in _cache:
            _cache.clear()
            _cache[digest] = cv2.dnn.readNetFromONNX(np.frombuffer(data,dtype=np.uint8))
        return _cache[digest]


def torso_crop(image, box):
    """Require full conservative upper torso; never extend above the face bottom."""
    try:
        x,y,w,h = map(float, box[:4])
        if not np.isfinite([x,y,w,h]).all() or min(w,h) < 40 or min(x,y) < 0:
            return None
        left,right,top,bottom = int(x-.5*w),int(x+1.5*w),int(y+1.1*h),int(y+3.5*h)
        if left < 0 or right > image.shape[1] or bottom > image.shape[0] or bottom-top < 96:
            return None
        crop = image[top:bottom,left:right]
        # Blank/dark/blurred frames cannot substantiate visible garments.
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        if gray.std() < 8 or gray.mean() < 20 or cv2.Laplacian(gray, cv2.CV_64F).var() < 12:
            return None
        return crop
    except (TypeError, ValueError, IndexError, cv2.error):
        return None


def evaluate_pair(images, boxes, profile_snapshot):
    result = {'observed_uniform':'UNKNOWN','uniform_status':'NOT_CHECKED','confidence':None,
              'reason':'NO_APPROVED_MODEL','profile_version':None}
    if not profile_snapshot:
        return result
    result['profile_version'] = profile_snapshot.get('version')
    if profile_snapshot.get('required_uniform') not in ['SHIRT','SPORTS']:
        result['reason'] = 'NO_REQUIRED_UNIFORM'
        return result
    try:
        if profile_snapshot['labels'] != LABELS or not .8 <= float(profile_snapshot['threshold']) <= 1:
            raise ValueError('Invalid model contract')
        net = runtime(profile_snapshot)
    except (OSError, ValueError, KeyError, cv2.error):
        result['reason'] = 'MODEL_UNAVAILABLE'
        return result
    result.update(reason='INSUFFICIENT_BODY_EVIDENCE')
    if len(images) != 2 or len(boxes) != 2:
        return result
    crops = [torso_crop(image, box) for image,box in zip(images,boxes)]
    if any(crop is None for crop in crops):
        return result
    scores = []
    try:
        for crop in crops:
            # Training/export contract: RGB [0,1], ImageNet normalization.
            rgb = cv2.cvtColor(cv2.resize(crop,(224,224)),cv2.COLOR_BGR2RGB).astype(np.float32)/255
            blob = ((rgb-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)).transpose(2,0,1)[None]
            with _lock:
                net.setInput(blob)
                logits = np.asarray(net.forward()).reshape(-1)
            if logits.size != 3 or not np.isfinite(logits).all():
                raise ValueError('Invalid model output')
            probability = np.exp(logits-logits.max()); probability /= probability.sum()
            scores.append(probability)
    except (ValueError, cv2.error):
        result.update(uniform_status='NOT_CHECKED',reason='MODEL_UNAVAILABLE')
        return result
    indexes = [int(score.argmax()) for score in scores]
    confidence = min(float(score[index]) for score,index in zip(scores,indexes))
    result['confidence'] = confidence
    if indexes[0] != indexes[1] or confidence < float(profile_snapshot['threshold']):
        result['reason'] = 'INCONSISTENT_OR_LOW_CONFIDENCE'
        return result
    result.update(observed_uniform=LABELS[indexes[0]],reason='WRONG_UNIFORM_TYPE')
    # Compliance is only a suggestion; OTHER always requires staff review.
    result['uniform_status'] = 'REVIEW_REQUIRED'
    if result['observed_uniform'] == profile_snapshot.get('required_uniform'):
        result['uniform_status'] = 'COMPLIANT'
        result['reason'] = 'MATCHED_REQUIRED_UNIFORM'
    return result
