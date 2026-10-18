"""Bounded local image processing. LBPH distance is not a probability."""
import io
import warnings

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from django.conf import settings

from school_app.accounts.services import AccountError

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
    classifier = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    if classifier.empty():
        raise AccountError('VISION_UNAVAILABLE', 'Face detector unavailable.', 503)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return classifier.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40,40))


def extract_face(image):
    boxes = detect_faces(image)
    if len(boxes) == 0:
        raise AccountError('NO_FACE', 'No face detected. Retake or use manual attendance.', 422)
    if len(boxes) != 1:
        raise AccountError('MULTIPLE_FACES', 'Only one person may be in the frame.', 422)
    x,y,w,h = box = tuple(int(v) for v in boxes[0])
    if min(w,h) < 80:
        raise AccountError('FACE_TOO_SMALL', 'Move closer to the camera.', 422)
    gray = cv2.cvtColor(image[y:y+h,x:x+w], cv2.COLOR_BGR2GRAY)
    crop = cv2.resize(gray, (128,128), interpolation=cv2.INTER_AREA)
    if cv2.Laplacian(crop, cv2.CV_64F).var() < getattr(settings, 'VISION_MIN_SHARPNESS', 50):
        raise AccountError('BLURRY_FACE', 'Face is blurry. Retake the image.', 422)
    return cv2.equalizeHist(crop), box


def encode_face(crop):
    ok, data = cv2.imencode('.png', crop)
    if not ok:
        raise AccountError('VISION_UNAVAILABLE', 'Could not encode face.', 503)
    return data.tobytes()


def match_face(crop, samples):
    distances = []
    for student_id, encoded in samples.items():
        faces = [cv2.imdecode(np.frombuffer(bytes(data), np.uint8), cv2.IMREAD_GRAYSCALE) for data in encoded]
        if not faces or any(face is None or face.shape != (128,128) for face in faces):
            raise AccountError('VISION_DATA_ERROR', 'Re-enroll invalid face samples.', 409)
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, np.zeros(len(faces), dtype=np.int32))
        _, distance = recognizer.predict(crop)
        distances.append((float(distance), str(student_id)))
    distances.sort()
    if not distances:
        return {'student_id':None, 'distance':None, 'reason':'NO_ENROLLMENT'}
    best, student_id = distances[0]
    if best > getattr(settings, 'VISION_FACE_MAX_DISTANCE', 55):
        return {'student_id':None, 'distance':round(best,3), 'reason':'UNKNOWN_FACE'}
    if len(distances)>1 and distances[1][0]-best < getattr(settings, 'VISION_FACE_MIN_MARGIN', 10):
        return {'student_id':None, 'distance':round(best,3), 'reason':'AMBIGUOUS_FACE'}
    return {'student_id':student_id, 'distance':round(best,3), 'reason':None}


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
