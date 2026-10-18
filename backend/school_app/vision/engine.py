"""Bounded local YuNet/SFace processing. Cosine similarity is not a probability."""
import io
import warnings

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from django.conf import settings

from school_app.accounts.services import AccountError
from .sface_models import MODEL_KEY, get_runtime

MAX_BYTES = 2 * 1024 * 1024
MAX_PIXELS = 4_000_000


def decode_upload(upload):
    if upload is None or upload.size > MAX_BYTES:
        raise AccountError('INVALID_IMAGE', 'Image must be at most 2 MiB.', 422)
    raw = upload.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise AccountError('INVALID_IMAGE', 'Image must be at most 2 MiB.', 422)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in {'PNG','JPEG','WEBP'} or image.width * image.height > MAX_PIXELS:
                    raise ValueError('Image format or dimensions')
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                image = ImageOps.exif_transpose(image).convert('RGB')
                image.thumbnail((960, 960))
                return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise AccountError('INVALID_IMAGE', 'Use a valid JPEG/PNG/WebP of at most 4 million pixels.', 422) from None


def detect_faces(image):
    _validate_image(image)
    height, width = image.shape[:2]
    scale = min(1.0, 640 / max(height, width))
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    resized = cv2.resize(image, size, interpolation=cv2.INTER_AREA) if scale < 1 else image
    runtime = get_runtime()
    try:
        with runtime.lock:
            runtime.detector.setInputSize(size)
            _, rows = runtime.detector.detect(resized)
            if rows is None:
                return []
            rows = np.array(rows, dtype=np.float32, copy=True)
    except cv2.error as error:
        raise AccountError('VISION_UNAVAILABLE', 'Face detector unavailable.', 503) from error
    if rows.ndim != 2 or rows.shape[1] != 15 or not np.isfinite(rows).all():
        raise AccountError('VISION_UNAVAILABLE', 'Face detector returned invalid geometry.', 503)
    # Use actual resized dimensions, which can differ slightly after rounding.
    rows[:, 0:14:2] *= width / size[0]
    rows[:, 1:14:2] *= height / size[1]
    return rows


def _validate_image(image):
    if (not isinstance(image, np.ndarray) or image.dtype != np.uint8
            or image.ndim != 3 or image.shape[2] != 3 or min(image.shape[:2]) < 1
            or image.shape[0] * image.shape[1] > MAX_PIXELS):
        raise AccountError('INVALID_IMAGE', 'Use a valid color image.', 422)


def _validate_crop(crop):
    _validate_image(crop)
    if crop.shape != (112, 112, 3):
        raise AccountError('INVALID_IMAGE', 'Expected an aligned 112 pixel face.', 422)


def align_face(image, detection):
    row = np.asarray(detection, dtype=np.float32)
    if row.shape != (15,) or not np.isfinite(row).all():
        raise AccountError('INVALID_IMAGE', 'Face landmarks are invalid.', 422)
    runtime = get_runtime()
    try:
        with runtime.lock:
            crop = runtime.recognizer.alignCrop(image, row).copy()
    except cv2.error as error:
        raise AccountError('VISION_UNAVAILABLE', 'Face alignment unavailable.', 503) from error
    _validate_crop(crop)
    return crop


def extract_face(image):
    _validate_image(image)
    boxes = detect_faces(image)
    if len(boxes) == 0:
        raise AccountError('NO_FACE', 'No face detected. Retake or use manual attendance.', 422)
    if len(boxes) != 1:
        raise AccountError('MULTIPLE_FACES', 'Only one person may be in the frame.', 422)
    x,y,w,h = box = tuple(int(v) for v in boxes[0][:4])
    if min(x,y) < 0 or w <= 0 or h <= 0 or x+w > image.shape[1] or y+h > image.shape[0]:
        raise AccountError('INVALID_IMAGE', 'Keep the full face inside the frame.', 422)
    if min(w,h) < 80:
        raise AccountError('FACE_TOO_SMALL', 'Move closer to the camera.', 422)
    gray = cv2.cvtColor(image[y:y+h,x:x+w], cv2.COLOR_BGR2GRAY)
    quality = cv2.resize(gray, (112,112), interpolation=cv2.INTER_AREA)
    if cv2.Laplacian(quality, cv2.CV_64F).var() < getattr(settings, 'VISION_MIN_SHARPNESS', 50):
        raise AccountError('BLURRY_FACE', 'Face is blurry. Retake the image.', 422)
    return align_face(image, boxes[0]), box


def encode_face(crop):
    _validate_crop(crop)
    ok, data = cv2.imencode('.png', crop)
    if not ok:
        raise AccountError('VISION_UNAVAILABLE', 'Could not encode face.', 503)
    return data.tobytes()


def embed_face(crop):
    _validate_crop(crop)
    runtime = get_runtime()
    try:
        with runtime.lock:
            vector = np.array(runtime.recognizer.feature(crop), dtype=np.float32, copy=True)
    except cv2.error as error:
        raise AccountError('VISION_UNAVAILABLE', 'Face recognition unavailable.', 503) from error
    if vector.shape not in {(128,), (1,128)} or not np.isfinite(vector).all():
        raise AccountError('VISION_UNAVAILABLE', 'Invalid face feature.', 503)
    vector = vector.reshape(128)
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm <= 1e-12:
        raise AccountError('VISION_UNAVAILABLE', 'Invalid face feature.', 503)
    return (vector / norm).astype('<f4').tobytes()


def _decode_embedding(data):
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise AccountError('VISION_DATA_ERROR', 'Re-enroll invalid face samples.', 409)
    data = bytes(data)
    if len(data) != 512:
        raise AccountError('VISION_DATA_ERROR', 'Re-enroll invalid face samples.', 409)
    vector = np.frombuffer(data, dtype='<f4')
    if not np.isfinite(vector).all() or not np.isclose(np.linalg.norm(vector), 1.0, atol=1e-4, rtol=0):
        raise AccountError('VISION_DATA_ERROR', 'Re-enroll invalid face samples.', 409)
    return vector


def match_face(crop, samples):
    if not samples:
        return {'student_id':None, 'distance':None, 'cosine_score':None, 'reason':'NO_ENROLLMENT'}
    query = _decode_embedding(embed_face(crop))
    scores = []
    for student_id, encoded in samples.items():
        if not encoded:
            raise AccountError('VISION_DATA_ERROR', 'Re-enroll invalid face samples.', 409)
        score = max(float(np.clip(np.dot(query, _decode_embedding(data)), -1, 1)) for data in encoded)
        scores.append((score, str(student_id)))
    scores.sort(key=lambda item: (-item[0], item[1]))
    best, student_id = scores[0]
    reason = None
    if best < getattr(settings, 'VISION_FACE_MIN_COSINE', .45):
        reason = 'UNKNOWN_FACE'
    elif len(scores) > 1 and best - scores[1][0] < getattr(settings, 'VISION_FACE_MIN_COSINE_MARGIN', .10):
        reason = 'AMBIGUOUS_FACE'
    return {'student_id':student_id if reason is None else None, 'distance':round(1-best,6),
            'cosine_score':round(best,6), 'reason':reason}


def suggest_uniform(image, box):
    # Only a configured color heuristic on an estimated torso, not garment recognition.
    x,y,w,h = box
    left, right = int(x-.3*w), int(x+1.3*w)
    top, bottom = int(y+1.15*h), int(y+3.2*h)
    unknown = {'observed_uniform':'UNKNOWN', 'color_coverage':0.0}
    if left<0 or right>image.shape[1] or bottom>image.shape[0] or top>=bottom:
        return unknown
    hsv = cv2.cvtColor(image[top:bottom,left:right], cv2.COLOR_BGR2HSV)
    bands = getattr(settings, 'VISION_UNIFORM_HSV', {
        'SHIRT': [[0,0,160],[179,70,255]],
        'SPORTS': [[95,80,50],[135,255,255]],
    })
    scores = sorted([(float(np.mean(cv2.inRange(hsv, np.array(low,np.uint8), np.array(high,np.uint8))>0)), kind)
                     for kind, (low, high) in bands.items()], reverse=True)
    if len(scores)!=2 or scores[0][0]<.6 or scores[0][0]-scores[1][0]<.2:
        return unknown
    return {'observed_uniform':scores[0][1], 'color_coverage':round(scores[0][0],3)}
