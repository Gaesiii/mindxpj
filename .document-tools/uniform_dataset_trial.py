"""Local external-dataset experiment; never imports/activates a school profile.

prepare runs in backend venv; train runs in isolated training venv; predict uses
OpenCV only. Images, manifests, weights and model output stay outside Git.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
LABELS = ['NON_UNIFORM', 'KV_UNIFORM']
SOURCE = 'https://www.kaggle.com/datasets/sanjukumargiri/kendriya-vidyalaya-school-uniform-vs-nonuniform'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def prepare(args):
    import cv2
    import numpy as np
    cv2.setNumThreads(1)
    # Reuse the real garment crop and quality rules without opening a database.
    spec = importlib.util.spec_from_file_location('trial_uniform_model', ROOT/'backend/school_app/vision/uniform_model.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    models = ROOT/'backend/vision_models'
    detector_file = next(models.glob('*yunet*.onnx'))
    detector = cv2.FaceDetectorYN.create(str(detector_file), '', (320, 320), .9, .3, 5000)
    source_dir = args.directory/'raw/Dataset/train'
    assert source_dir.is_dir(), 'Extract the source archive before prepare'
    source_files = sorted(source_dir.glob('*.jpg'))
    assert source_files, 'No labeled JPEG files in source directory'
    target = args.directory/'prepared'
    target.mkdir(exist_ok=True)
    rows, skipped = [], {}
    def skip(reason): skipped[reason] = skipped.get(reason, 0) + 1
    for number, path in enumerate(source_files):
        if number % 250 == 0: print('prepare', number, flush=True)
        label = 'KV_UNIFORM' if path.name.startswith('school.') else 'NON_UNIFORM' if path.name.startswith('normal.') else None
        if label is None:
            skip('UNRECOGNIZED_FILENAME_LABEL'); continue
        image = cv2.imdecode(np.frombuffer(path.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            skip('DECODE_FAILED'); continue
        # No artificial enlargement to make a low-resolution crop pass quality.
        if max(image.shape[:2]) > 960:
            image = cv2.resize(image, None, fx=960/max(image.shape[:2]), fy=960/max(image.shape[:2]))
        detector.setInputSize((image.shape[1], image.shape[0]))
        _, faces = detector.detect(image)
        if faces is None or len(faces) != 1:
            skip('NOT_EXACTLY_ONE_FACE'); continue
        crop = module.torso_crop(image, faces[0][:4])
        strict_runtime_crop = crop is not None
        if crop is None:
            # Separate low-resolution DATA PREPARATION policy. This is never
            # used by runtime inference or represented as passing its gate.
            x,y,w,h = map(float, faces[0][:4])
            left,right = max(0,int(x-.5*w)), min(image.shape[1],int(x+1.5*w))
            top,bottom = int(y+1.1*h), min(image.shape[0],int(y+3.5*h))
            if min(w,h)<12 or min(right-left,bottom-top)<24:
                skip('INSUFFICIENT_TRAINING_CROP'); continue
            crop=image[top:bottom,left:right]
            gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
            if gray.std()<8 or gray.mean()<20:
                skip('BLANK_OR_DARK_TRAINING_CROP'); continue
        # Crop starts below the sole detected face; detection remains fallible.
        ok, encoded = cv2.imencode('.png', crop)
        assert ok
        sha = hashlib.sha256(encoded.tobytes()).hexdigest()
        file = target/(sha+'.png')
        file.write_bytes(encoded.tobytes())
        small = cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (32,32)).astype(np.float32)
        low = cv2.dct(small)[:8,:8].reshape(-1)[1:]
        bits = sum(int(v > np.median(low)) << i for i,v in enumerate(low))
        rows.append({'path':file.name, 'source':path.name, 'source_sha256':digest(path),
                     'sha256':sha, 'label':label, 'phash':bits,
                     'passes_strict_runtime_crop':strict_runtime_crop})
    # Conservative approximate duplicate groups, not proof of independent people.
    parents = list(range(len(rows)))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]; i = parents[i]
        return i
    for i, a in enumerate(rows):
        for j in range(i):
            b = rows[j]
            if a['source_sha256'] == b['source_sha256'] or (a['phash'] ^ b['phash']).bit_count() <= 6:
                parents[find(i)] = find(j)
    groups = {}
    for i,row in enumerate(rows): groups.setdefault(find(i), []).append(row)
    kept = []
    for group in groups.values():
        if len({r['label'] for r in group}) != 1:
            skip('CONFLICTING_LABEL_GROUP'); continue
        kept.append(group[0])
    counts = {}
    randomizer = random.Random(2026)
    for label in LABELS:
        selected = sorted((r for r in kept if r['label']==label), key=lambda r:r['sha256'])
        randomizer.shuffle(selected)
        print(label,'independent approximate groups:',len(selected),flush=True)
        assert len(selected) >= 20, f'Only {len(selected)} eligible {label} crops'
        ntest = max(4, round(len(selected)*.15)); nval = ntest
        for i,row in enumerate(selected):
            row['split'] = 'test' if i < ntest else 'val' if i < ntest+nval else 'train'
            row['capture_group'] = row['sha256']
            del row['phash']
        counts[label] = {s:sum(r['split']==s for r in selected) for s in ['train','val','test']}
    manifest = {'schema_version':1, 'labels':LABELS, 'source':SOURCE,
                'source_license':'Unknown as reported by Kaggle; local experiment only; no redistribution',
                'source_archive_sha256':digest(args.directory/'source.zip'), 'seed':2026,
                'counts':counts, 'source_labeled_images':number+1,
                'unlabeled_source_test_images':len(list((args.directory/'raw/Dataset/test').glob('*.jpg'))),
                'eligible_crops_before_deduplication':len(rows), 'duplicate_rows_removed':len(rows)-len(kept),
                'strict_runtime_crop_counts':{label:sum(r['label']==label and r['passes_strict_runtime_crop'] for r in kept) for label in LABELS},
                'skipped':skipped, 'samples':kept,
                'limitations':['Binary external labels, not project SHIRT/SPORTS/OTHER.',
                               'Perceptual grouping does not establish different people/sessions.',
                               'Training crop allows low-resolution/clipped torso; stricter runtime crop is measured separately and unchanged.',
                               'Selection bias: only a single detected face and usable torso crops are retained.',
                               'Automatic face exclusion is fallible; retained crops need private human inspection.']}
    write(target/'manifest.json', manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k!='samples'}, indent=2), flush=True)


def blob(image):
    import cv2
    import numpy as np
    rgb = cv2.cvtColor(cv2.resize(image,(224,224)),cv2.COLOR_BGR2RGB).astype(np.float32)/255
    return ((rgb-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)).transpose(2,0,1)[None]


def train(args):
    import cv2
    import numpy as np
    import torch
    from torchvision.models import mobilenet_v3_small
    torch.set_num_threads(1); cv2.setNumThreads(1)
    torch.manual_seed(2026); np.random.seed(2026); random.seed(2026)
    torch.use_deterministic_algorithms(True)
    root = args.directory/'prepared'; output = args.directory/'output'; output.mkdir(exist_ok=True)
    manifest = json.loads((root/'manifest.json').read_text())
    assert manifest['labels'] == LABELS
    rows = manifest['samples']
    assert len({r['sha256'] for r in rows}) == len(rows)
    assert args.weights and args.weights_sha256 == digest(args.weights), 'Explicit verified local ImageNet weights required'
    model = mobilenet_v3_small(weights=None)
    model.load_state_dict(torch.load(args.weights, map_location='cpu', weights_only=True))
    for param in model.parameters(): param.requires_grad_(False)
    model.classifier = torch.nn.Linear(576,2)
    model.eval()
    features, targets = [], []
    start = time.perf_counter()
    for i,row in enumerate(rows):
        path = root/row['path']; assert digest(path)==row['sha256']
        image = cv2.imdecode(np.frombuffer(path.read_bytes(),np.uint8),cv2.IMREAD_COLOR)
        x = torch.from_numpy(blob(image))
        with torch.no_grad(): feature = model.avgpool(model.features(x)).flatten(1)
        features.append(feature[0]); targets.append(LABELS.index(row['label']))
        if i % 100 == 0: print('features',i,'/',len(rows),flush=True)
    x = torch.stack(features); y = torch.tensor(targets)
    indexes = {s:torch.tensor([i for i,r in enumerate(rows) if r['split']==s]) for s in ['train','val','test']}
    optimizer = torch.optim.Adam(model.classifier.parameters(), lr=.01, weight_decay=.001)
    lossfn = torch.nn.CrossEntropyLoss(); best = float('inf'); best_state = None
    for epoch in range(args.epochs):
        optimizer.zero_grad(); loss=lossfn(model.classifier(x[indexes['train']]),y[indexes['train']]); loss.backward(); optimizer.step()
        with torch.no_grad(): val_loss = float(lossfn(model.classifier(x[indexes['val']]),y[indexes['val']]))
        if val_loss < best:
            best=val_loss; best_state={k:v.detach().clone() for k,v in model.classifier.state_dict().items()}; best_epoch=epoch+1
    model.classifier.load_state_dict(best_state); model.eval()
    artifact = output/'external-kv-binary.onnx'
    torch.onnx.export(model, torch.zeros(1,3,224,224), str(artifact), opset_version=12,
                      input_names=['garment'],output_names=['binary_logits'],dynamo=False)
    net = cv2.dnn.readNetFromONNX(str(artifact))
    confusion = np.zeros((2,2),dtype=int); accepted = np.zeros((2,2),dtype=int)
    timings=[]; predictions=[]; max_parity=0.0
    net.setInput(np.zeros((1,3,224,224),np.float32));net.forward()
    with torch.no_grad():
        for i in indexes['test'].tolist():
            image=cv2.imdecode(np.frombuffer((root/rows[i]['path']).read_bytes(),np.uint8),cv2.IMREAD_COLOR)
            inputs=blob(image);net.setInput(inputs)
            before=time.perf_counter();logits=net.forward().reshape(-1);timings.append((time.perf_counter()-before)*1000)
            expected=model(torch.from_numpy(inputs)).numpy().reshape(-1)
            max_parity=max(max_parity,float(np.max(np.abs(logits-expected))))
            assert np.allclose(logits,expected,atol=1e-3,rtol=1e-3), 'ONNX parity mismatch'
            p=np.exp(logits-logits.max());p/=p.sum();pred=int(p.argmax());truth=int(y[i]);confidence=float(p[pred])
            confusion[truth,pred]+=1
            if confidence>=args.threshold: accepted[truth,pred]+=1
            predictions.append({'path':rows[i]['path'],'expected':LABELS[truth],'predicted':LABELS[pred],
                                'confidence':confidence,'decision':LABELS[pred] if confidence>=args.threshold else 'UNKNOWN'})
    metrics={label:{'precision_at_threshold':float(accepted[j,j]/max(1,accepted[:,j].sum())),
                    'recall_at_threshold':float(accepted[j,j]/max(1,confusion[j].sum())),
                    'test_count':int(confusion[j].sum())} for j,label in enumerate(LABELS)}
    report={'schema_version':1,'source':SOURCE,'source_license':manifest['source_license'],
            'experiment_only':True,'approved':False,'production_imported':False,
            'labels':LABELS,'architecture':'MobileNetV3 Small frozen ImageNet features + trained linear binary head',
            'weights_sha256':digest(args.weights),'manifest_sha256':digest(root/'manifest.json'),
            'model_sha256':digest(artifact),'model_bytes':artifact.stat().st_size,'seed':2026,
            'epochs':args.epochs,'best_validation_epoch':best_epoch,'threshold':args.threshold,
            'counts':manifest['counts'],'source_labeled_images':manifest['source_labeled_images'],
            'eligible_crops_before_deduplication':manifest['eligible_crops_before_deduplication'],
            'duplicate_rows_removed':manifest['duplicate_rows_removed'],'skipped':manifest['skipped'],
            'strict_runtime_crop_counts':manifest['strict_runtime_crop_counts'],
            'source_unlabeled_test_not_scored':manifest['unlabeled_source_test_images'],
            'confusion':confusion.tolist(),'accepted_confusion':accepted.tolist(),'metrics':metrics,
            'argmax_accuracy':float(np.trace(confusion)/confusion.sum()),
            'coverage':float(accepted.sum()/confusion.sum()),'opencv_forward_ms_p50':float(np.median(timings)),
            'opencv_forward_ms_p95':float(np.percentile(timings,95)),'max_onnx_abs_error':max_parity,
            'training_and_evaluation_seconds':time.perf_counter()-start,
            'versions':{'python':sys.version.split()[0],'torch':torch.__version__,'opencv':cv2.__version__,'numpy':np.__version__},
            'limitations':manifest['limitations']+['CPU forward-only warmed timing excludes detection, crop, preprocessing, HTTP and two-frame gating.',
                'Not a model for the target school; SPORTS class absent; license unresolved; cannot pass production school-profile import.']}
    write(output/'report.json',report);write(output/'private-test-predictions.json',predictions)
    torch.save(model.state_dict(),output/'external-kv-binary-state.pth')
    print(json.dumps(report,indent=2),flush=True)
    # Private browser contact sheet: garment crops only, no images embedded in Git evidence.
    import html
    cards=[]
    for row in predictions:
        text=html.escape(f"expected: {row['expected']} | prediction: {row['decision']} | confidence: {row['confidence']:.3f}")
        cards.append(f'<figure><img src="../prepared/{row["path"]}"><figcaption>{text}</figcaption></figure>')
    page='<meta charset="utf-8"><title>External KV uniform trial</title><style>body{font:16px sans-serif}main{display:flex;flex-wrap:wrap}figure{width:220px}img{max-width:220px;height:220px;object-fit:contain}</style><h1>External KV binary experiment</h1><p>Local experiment only. Not approved for school attendance. Labels: NON_UNIFORM / KV_UNIFORM; low confidence: UNKNOWN.</p><main>'+''.join(cards)+'</main>'
    (output/'test-results.html').write_text(page,encoding='utf-8')


def predict(args):
    import cv2
    import numpy as np
    report=json.loads((args.directory/'output/report.json').read_text())
    path=args.directory/'output/external-kv-binary.onnx'
    assert digest(path)==report['model_sha256']
    image=cv2.imdecode(np.frombuffer(args.image.read_bytes(),np.uint8),cv2.IMREAD_COLOR)
    if image is None: raise ValueError('Unreadable image')
    net=cv2.dnn.readNetFromONNX(str(path)); net.setInput(blob(image));logits=net.forward().reshape(-1)
    p=np.exp(logits-logits.max());p/=p.sum();i=int(p.argmax())
    print(json.dumps({'experiment_only':True,'input':'user-supplied garment crop; no automatic face association',
                      'decision':LABELS[i] if float(p[i])>=report['threshold'] else 'UNKNOWN',
                      'confidence':float(p[i]),'target_school_approved':False},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','train','predict'])
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--weights',type=Path)
    parser.add_argument('--weights-sha256')
    parser.add_argument('--epochs',type=int,default=150)
    parser.add_argument('--threshold',type=float,default=.95)
    parser.add_argument('--image',type=Path)
    args=parser.parse_args()
    if args.epochs<1 or not .8<=args.threshold<=1: parser.error('Invalid epochs or confidence threshold')
    if args.command=='predict' and not args.image:parser.error('--image required')
    {'prepare':prepare,'train':train,'predict':predict}[args.command](args)
