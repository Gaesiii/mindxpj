"""Read-only comparison against a locally supplied desktop reference.

No Qt window/camera/database is opened. Reference methods run on injected images;
temporary reference enrollments are numeric arrays created by this script only.
Do not publish the reference folder, database, saved biometric arrays or images.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import textwrap
import time

ROOT = Path(__file__).resolve().parents[1]


def memory():
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[
            (name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize',
            'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi=ctypes.WinDLL('psapi',use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {'working_set_bytes':counters.WorkingSetSize,'peak_working_set_bytes':counters.PeakWorkingSetSize}


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def worker(args):
    start=time.perf_counter();cpu=time.process_time()
    import cv2
    import numpy as np
    cv2.setNumThreads(1)
    sys.path.insert(0,str(ROOT/'backend'))
    os.environ.update(DJANGO_SECRET_KEY='offline-comparison-only-no-user-secret',
                      DJANGO_SETTINGS_MODULE='config.settings',DJANGO_DB_PATH=':memory:')
    import django
    django.setup()
    from django.core.files.uploadedfile import SimpleUploadedFile
    from school_app.vision import engine
    from school_app.accounts.services import AccountError

    def read(path):
        return engine.decode_upload(SimpleUploadedFile(path.name,path.read_bytes()))

    enroll=sorted((args.images/'01-enroll').glob('*.jpg'))
    assert len(enroll)==3,'Expected the three independent authorized enrollment JPEGs'
    positives=[args.images/'demo/1753240560-trump-67651-width698height558.jpg',
               args.images/'demo/1f64783ac2712b2f7260.jpg']
    negatives=[args.images/'02-scan/unknown-person.jpg',
               args.images/'demo/qiamz8htjhpu1jluumkx832nphpje7pk20260926081546.jpg']
    original=[(f'positive_{i+1}','known','original',read(p)) for i,p in enumerate(positives)]
    original += [(f'negative_{i+1}','unknown','original',read(p)) for i,p in enumerate(negatives)]
    # Legacy filenames describe old Haar failures, NOT scene ground truth.
    original += [('legacy_partial_portrait','known','legacy_diagnostic',read(args.images/'02-scan/no-face.jpg')),
                 ('legacy_single_portrait','known','legacy_diagnostic',read(args.images/'02-scan/multiple-detections.jpg'))]
    blank=np.full((480,640,3),127,dtype=np.uint8)
    multiple=blank.copy()
    cascade_path=ROOT/'backend/.venv/Lib/site-packages/cv2/data/haarcascade_frontalface_default.xml'
    generator=cv2.CascadeClassifier(str(cascade_path))
    assert not generator.empty(),'Control generator requires the existing ASCII-path Haar asset'
    for image,size,left in [(read(enroll[0]),224,32),(read(negatives[0]),168,400)]:
        boxes=generator.detectMultiScale(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),1.1,5)
        assert len(boxes),'Cannot construct annotated multi-face control'
        x,y,w,h=max(boxes,key=lambda b:b[2]*b[3])
        multiple[96:96+size,left:left+size]=cv2.resize(image[y:y+h,x:x+w],(size,size))
    original += [('generated_blank','no_face','control',blank),
                 ('generated_two_faces','multiple','control',multiple)]
    probes=list(original)
    # Correlated stress views are reported separately, never as independent people.
    for label,truth,group,image in original[:4]:
        for factor in (.65,1.3):
            probes.append((f'{label}_light_{factor}',truth,'derived_stress',
                           cv2.convertScaleAbs(image,alpha=factor)))
        for degrees in (-12,12):
            h,w=image.shape[:2];matrix=cv2.getRotationMatrix2D((w/2,h/2),degrees,1)
            probes.append((f'{label}_roll_{degrees}',truth,'derived_stress',cv2.warpAffine(image,matrix,(w,h))))
        probes.append((label+'_blur',truth,'derived_stress',cv2.GaussianBlur(image,(11,11),0)))

    reference=None
    if args.worker!='current':
        sys.path.insert(0,str(args.reference))
        if args.worker=='reference_fallback':
            # Reproduce missing optional dependency without loading dlib models
            # first; otherwise fallback memory/startup numbers would be inflated.
            sys.modules['face_recognition']=None
        camera=load_module('comparison_reference_camera',args.reference/'camera.py')
        reference=load_module('comparison_reference_faces',args.reference/'utils/face_utils.py')
        if args.worker=='reference_fallback':
            camera.face_recognition=reference.face_recognition=None
        else:
            assert camera.face_recognition is not None and reference.face_recognition is not None,'dlib branch did not import'
        class FrameSource:
            def __init__(self,image):self.image=image
            def isOpened(self):return True
            def read(self):return True,self.image.copy()
        cascade=camera._load_cascade('haarcascade_frontalface_default.xml') if args.worker=='reference_fallback' else None
        def crop_reference(image):
            device=camera.FaceMeshCamera.__new__(camera.FaceMeshCamera)
            device.cap=FrameSource(image);device.camera_ready=True;device.face_cascade=cascade
            device.frame_counter=0;device.detect_interval=3;device.cached_face_rect=None
            device.frames_without_face=0;device.cached_landmarks=None
            _,_,crop=device.get_frame()
            return crop
        # Execute the original pure decision helper without importing Qt/database.
        attendance_source=(args.reference/'ui/attendance.py').read_text(encoding='utf-8-sig')
        tree=ast.parse(attendance_source)
        method=next(node for cls in tree.body if isinstance(cls,ast.ClassDef) and cls.name=='AttendancePage'
                    for node in cls.body if isinstance(node,ast.FunctionDef) and node.name=='_should_confirm_match')
        namespace={'np':np}
        exec(compile(textwrap.dedent(ast.get_source_segment(attendance_source,method)),'reference_history_helper','exec'),namespace)
        confirm=namespace['_should_confirm_match']

    initialized={'wall_ms':round((time.perf_counter()-start)*1000,3),
                 'cpu_ms':round((time.process_time()-cpu)*1000,3),'memory':memory()}
    begin=time.perf_counter();cpu=time.process_time()
    dimensions=[]
    with tempfile.TemporaryDirectory(prefix='mindx-comparison-enrollment-') as temporary:
        if args.worker=='current':
            vectors=[]
            for path in enroll:
                crop,_=engine.extract_face(read(path));vectors.append(engine.embed_face(crop))
            samples={'known':vectors};dimensions=[128]*len(vectors)
        else:
            selected=enroll if args.worker=='reference_dlib_distinct' else enroll[:1]
            crops=[crop_reference(read(path)) for path in selected]
            assert all(crop is not None for crop in crops),'Reference could not enroll the supplied original image'
            path=Path(temporary)/'anonymous.npy'
            source_crops=crops if len(crops)==3 else [crops[0]]*3
            for crop in source_crops:
                assert reference.save_face_encoding(str(path),crop),'Reference encoding failed'
            known=reference.load_face_encodings(str(path))
            assert known is not None
            dimensions=[int(known.shape[1])]*int(known.shape[0])
        enrollment={'wall_ms':round((time.perf_counter()-begin)*1000,3),
                    'cpu_ms':round((time.process_time()-cpu)*1000,3),
                    'dimensions':dimensions,'independent_photos':3 if args.worker in ('current','reference_dlib_distinct') else 1,
                    'stored_vectors':len(dimensions),'memory':memory()}

        def recognize(image):
            if args.worker=='current':
                try:
                    crop,_=engine.extract_face(image)
                    match=engine.match_face(crop,samples,min_cosine=.60,min_margin=.15)
                    return {'accepted':match['student_id'] is not None,'score':match['cosine_score'],
                            'reason':match['reason'],'encoding_dimension':128}
                except AccountError as exc:
                    return {'accepted':False,'score':None,'reason':exc.code,'encoding_dimension':None}
            crop=crop_reference(image)
            if crop is None:return {'accepted':False,'score':None,'reason':'NO_FACE','encoding_dimension':None}
            query=reference.encode_face_from_image(crop)
            distance=reference.compare_faces(query,known) if query is not None else None
            accepted=False
            if distance is not None and distance<1:
                history=type('History',(),{'match_history':[]})()
                # Stable identical evidence isolates the source's three-event gate;
                # this is not a video/physical-camera timing measurement.
                for _ in range(3):accepted=confirm(history,'known',distance,query is not None)
            return {'accepted':bool(accepted),'score':distance,'reason':None if accepted else 'UNKNOWN',
                    'encoding_dimension':int(np.asarray(query).size) if query is not None else None,
                    'mixed_encoding_dimensions':query is not None and np.asarray(query).size!=known.shape[1]}

        results=[]
        for label,truth,group,image in probes:
            wall=[];cpus=[];decision=None
            for _ in range(args.repeats):
                begin=time.perf_counter();cpu=time.process_time();decision=recognize(image)
                wall.append((time.perf_counter()-begin)*1000);cpus.append((time.process_time()-cpu)*1000)
            results.append({'probe':label,'truth':truth,'group':group,**decision,
                            'wall_ms_median':round(statistics.median(wall),3),
                            'wall_ms_samples':[round(x,3) for x in wall],
                            'cpu_ms_median':round(statistics.median(cpus),3)})
        def metrics(group):
            rows=[r for r in results if r['group']==group]
            known_rows=[r for r in rows if r['truth']=='known'];unknown=[r for r in rows if r['truth']=='unknown']
            return {'known_probes':len(known_rows),'correct_known_accepts':sum(r['accepted'] for r in known_rows),
                    'known_rejections':sum(not r['accepted'] for r in known_rows),'unknown_probes':len(unknown),
                    'false_unknown_accepts':sum(r['accepted'] for r in unknown),
                    'unsafe_control_accepts':sum(r['accepted'] for r in rows if r['truth'] in ('multiple','no_face'))}
        times=[x for r in results for x in r['wall_ms_samples']]
        pairs={}
        for label,names in [('held_out_known',['positive_1','positive_2']),('unseen_people',['negative_1','negative_2'])]:
            rows=[next(r for r in results if r['probe']==name) for name in names]
            pairs[label]={'all_recognized_as_known':all(r['accepted'] for r in rows),
                          'note':'Per-image consistency only; current API additionally rejects different identities and duplicate bytes.'}
        report={'variant':args.worker,'python':sys.version.split()[0],'opencv':cv2.__version__,
                'numpy':np.__version__,'opencv_threads':cv2.getNumThreads(),'initialization':initialized,
                'enrollment':enrollment,'metrics':{group:metrics(group) for group in ['original','control','derived_stress','legacy_diagnostic']},
                'latency_all_probes_ms':{'p50':round(float(np.percentile(times,50)),3),
                                         'p95':round(float(np.percentile(times,95)),3)},
                'pair_observations':pairs,'probes':results,'final_memory':memory(),
                'no_database_or_physical_camera_access':True}
        if reference is not None:
            report['face_recognition_imported']=reference.face_recognition is not None
            report['mixed_descriptor_probe_count']=sum(bool(r.get('mixed_encoding_dimensions')) for r in results)
            if reference.face_recognition is not None:
                import dlib
                report.update(dlib=dlib.__version__,face_recognition_module_version=reference.face_recognition.__version__)
        print(json.dumps(report,ensure_ascii=True))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--images',type=Path,required=True)
    parser.add_argument('--python314',type=Path)
    parser.add_argument('--worker',choices=['current','reference_dlib','reference_dlib_distinct','reference_fallback'])
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--output',type=Path,default=ROOT/'docs/project-management/evidence/face-comparison-2026-10-21/results.json')
    args=parser.parse_args();args.reference=args.reference.resolve();args.images=args.images.resolve()
    assert args.repeats>=1
    if args.worker:return worker(args)
    assert args.python314 and args.python314.is_file(),'Isolated Python314 required for bundled dlib ABI'
    variants=[('production_current',Path(sys.executable),'current'),
              ('shared_runtime_current',args.python314,'current'),
              ('reference_dlib',args.python314,'reference_dlib'),
              ('reference_dlib_distinct',args.python314,'reference_dlib_distinct'),
              ('reference_fallback',args.python314,'reference_fallback')]
    output={'schema_version':1,'baseline_commit':'94cee7e','runs':{},'source_sha256':{},
            'method':{'input':'Same decoded local photos, EXIF-normalized/max960px, per-engine original crop/matching.',
                      'dataset':'Three known enrollment photos; two independent held-out known photos; two unseen people; in-memory blank/two-face controls; 20 correlated stress derivatives and 2 legacy diagnostic portraits reported separately. Legacy filenames are not ground truth.',
                      'reference_stock_enrollment':'First enrollment crop encoded three times, as shipped.',
                      'reference_distinct_experiment':'Three different enrollment crops; experimental setup, not shipped UI.',
                      'latency':'Image decode excluded; actual detection/crop/encoding/matching included; fresh camera geometry per probe, no preview cache speedup. Single inference plus source history helper, not elapsed three-camera-frame confirmation.',
                      'scores':'SFace cosine and dlib/fallback Euclidean distances are not comparable numbers.',
                      'scope':'Small, one enrolled identity; no full-school accuracy, multi-roster ambiguity, physical camera or native Vercel claims.',
                      'python_runtime':'Shared314 runs reuse supplied binary dependencies with public dlib models in ASCII temporary path. Production312 current measured separately. No dependency changed in Django env.'}}
    for file in ['camera.py','utils/face_utils.py','ui/attendance.py','ui/touch_utils.py','requirements.txt']:
        output['source_sha256'][file]=hashlib.sha256((args.reference/file).read_bytes()).hexdigest()
    for name,python,variant in variants:
        command=[str(python),str(Path(__file__).resolve()),'--worker',variant,'--reference',str(args.reference),
                 '--images',str(args.images),'--repeats',str(args.repeats)]
        env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','DEMO_'))}
        before=time.perf_counter()
        run=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,encoding='utf-8',errors='replace',timeout=180)
        if run.returncode:raise RuntimeError(name+' failed: '+run.stderr[-4000:])
        report=json.loads(run.stdout.strip().splitlines()[-1]);report['child_total_wall_ms']=round((time.perf_counter()-before)*1000,3)
        output['runs'][name]=report
        print(name+': '+json.dumps({'metrics':report['metrics'],'latency':report['latency_all_probes_ms']}),flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Sanitized comparison written: '+str(args.output))


if __name__=='__main__':main()
