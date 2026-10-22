"""Explicit local KV experiment. No student/profile/attendance model access."""
import hashlib
import json
from pathlib import Path
import threading
import time

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from school_app.accounts.services import AccountError
from school_app.academics.services import staff_user
from school_app.core.api import api_view, json_response

LABELS=['NON_UNIFORM','KV_UNIFORM']
_lock=threading.RLock()
_cache={}


def available(request):
    return (bool(getattr(settings,'UNIFORM_DEMO_ROOT',''))
            and not getattr(settings,'VERCEL_DEMO',False)
            and request.META.get('REMOTE_ADDR') in ('127.0.0.1','::1'))


def require_local(request):
    if not available(request):
        raise AccountError('NOT_FOUND','Demo local chưa được bật.',404)


def inside(root,name):
    path=(root/name).resolve()
    if not path.is_relative_to(root) or path==root:
        raise ValueError('Outside bundle')
    return path


def bundle(request):
    require_local(request)
    staff_user(request.user)
    try:
        root=Path(settings.UNIFORM_DEMO_ROOT).resolve()
        data=json.loads((root/'bundle.json').read_text(encoding='utf-8'))
        if data['schema_version']!=1 or data['labels']!=LABELS or not .8<=data['threshold']<=1:
            raise ValueError('Invalid contract')
        model=inside(root,'model.onnx')
        if model.stat().st_size>32*1024*1024 or hashlib.sha256(model.read_bytes()).hexdigest()!=data['model_sha256']:
            raise ValueError('Model changed')
        return root,data
    except (OSError,ValueError,KeyError,TypeError):
        raise AccountError('DEMO_UNAVAILABLE','Bộ demo thiếu hoặc đã thay đổi; chạy lại bước chuẩn bị.',503) from None


@api_view('GET')
@ensure_csrf_cookie
def page(request):
    require_local(request)
    staff_user(request.user)
    return render(request,'demo_ui/uniform_demo.html')


@api_view('GET')
def metadata(request):
    _,data=bundle(request)
    return json_response({'experiment_only':True,'threshold':data['threshold'],
        'labels':LABELS,'samples':[{k:s[k] for k in ['id','title','expected']} for s in data['samples']]})


@api_view('GET')
def sample(request,sample_id):
    root,data=bundle(request)
    row=next((s for s in data['samples'] if s['id']==sample_id),None)
    if row is None: raise AccountError('NOT_FOUND','Không có ảnh mẫu này.',404)
    try:
        path=inside(root,row['path'])
        if path.suffix!='.png' or path.stat().st_size>2*1024*1024:raise ValueError('Invalid sample')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('Sample changed')
    except (OSError,ValueError,KeyError):
        raise AccountError('DEMO_UNAVAILABLE','Ảnh mẫu thiếu hoặc đã thay đổi.',503) from None
    return HttpResponse(raw,content_type='image/png',headers={'X-Content-Type-Options':'nosniff'})


def forward(root,data,image):
    import cv2
    import numpy as np
    rgb=cv2.cvtColor(cv2.resize(image,(224,224)),cv2.COLOR_BGR2RGB).astype(np.float32)/255
    blob=((rgb-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)).transpose(2,0,1)[None]
    with _lock:
        key=(str(root),data['model_sha256'])
        if key not in _cache:
            _cache.clear()
            raw=(root/'model.onnx').read_bytes()
            if hashlib.sha256(raw).hexdigest()!=data['model_sha256']:raise ValueError('Model changed')
            _cache[key]=cv2.dnn.readNetFromONNX(np.frombuffer(raw,dtype=np.uint8))
        net=_cache[key];net.setInput(blob)
        return net.forward().reshape(-1)


@api_view('POST')
def predict(request):
    root,data=bundle(request)
    if request.GET or request.POST or set(request.FILES)!={'image'} or len(request.FILES.getlist('image'))!=1:
        raise AccountError('VALIDATION_ERROR','Chỉ gửi một ảnh vùng áo.',422)
    import cv2
    import numpy as np
    from school_app.vision.engine import decode_upload
    image=decode_upload(request.FILES['image'])
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    result={'experiment_only':True,'attendance_saved':False,'decision':'UNKNOWN','confidence':None,
            'reason':'INSUFFICIENT_GARMENT_IMAGE','inference_ms':None}
    if min(image.shape[:2])<24 or gray.std()<8 or gray.mean()<20:
        return json_response(result)
    try:
        start=time.perf_counter();logits=np.asarray(forward(root,data,image))
        if logits.shape!=(2,) or not np.isfinite(logits).all():raise ValueError('Invalid output')
        probs=np.exp(logits-logits.max());probs/=probs.sum();idx=int(probs.argmax());confidence=float(probs[idx])
        result.update(confidence=confidence,inference_ms=round((time.perf_counter()-start)*1000,2),reason='LOW_CONFIDENCE')
        if confidence>=data['threshold']:result.update(decision=LABELS[idx],reason='BINARY_KV_EXPERIMENT')
    except (OSError,ValueError,cv2.error):
        raise AccountError('DEMO_UNAVAILABLE','Model thử nghiệm không xử lý được ảnh.',503) from None
    return json_response(result)
