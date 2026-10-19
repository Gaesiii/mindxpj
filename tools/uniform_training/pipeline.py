"""Offline only. Validate a private extracted dataset; optionally train in a separate env."""
import argparse
import hashlib
import json
import random
import time
from pathlib import Path

LABELS = ['SHIRT','SPORTS','OTHER']


def validate_manifest(root):
    root = Path(root).resolve()
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema_version') != 1 or manifest.get('labels') != LABELS:
        raise ValueError('Unsupported dataset schema or labels')
    groups, digests = {}, set()
    counts = {split:{label:0 for label in LABELS} for split in ['train','val','test']}
    for sample in manifest['samples']:
        path = (root/sample['path']).resolve()
        if not path.is_relative_to(root) or path.suffix.lower() != '.png':
            raise ValueError('Unsafe sample path')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != sample['sha256'] or digest in digests:
            raise ValueError('Integrity mismatch or duplicate image leakage')
        digests.add(digest)
        split,label,group = sample['split'],sample['label'],sample['capture_group']
        if not group or split not in counts or label not in LABELS:
            raise ValueError('Invalid split, label or capture group')
        if group in groups and groups[group] != split:
            raise ValueError('Capture group leakage across splits')
        groups[group] = split
        counts[split][label] += 1
    if any(count == 0 for row in counts.values() for count in row.values()):
        raise ValueError('Every label must have independent train/val/test samples')
    return manifest,counts


def train(root,output,epochs=20,seed=2026,threshold=.95,initial_weights=None,weights_sha256=None):
    manifest,counts = validate_manifest(root)
    # No dependency imported until the explicit offline train command.
    import numpy as np
    import torch
    from torch import nn
    from torchvision.models import mobilenet_v3_small
    from torchvision import transforms
    from PIL import Image
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    root,output = Path(root),Path(output)
    output.mkdir(parents=True,exist_ok=True)
    transform = transforms.Compose([transforms.Resize((224,224)),transforms.ToTensor(),
        transforms.Normalize([.485,.456,.406],[.229,.224,.225])])
    class Dataset(torch.utils.data.Dataset):
        def __init__(self,split): self.rows = [r for r in manifest['samples'] if r['split']==split]
        def __len__(self): return len(self.rows)
        def __getitem__(self,index):
            r=self.rows[index]
            with Image.open(root/r['path']) as im: tensor=transform(im.convert('RGB'))
            return tensor,LABELS.index(r['label'])
    model = mobilenet_v3_small(weights=None)  # Never downloads pretrained weights.
    if initial_weights:
        initial_weights=Path(initial_weights)
        if not weights_sha256 or hashlib.sha256(initial_weights.read_bytes()).hexdigest()!=weights_sha256:
            raise ValueError('Initial weights SHA-256 mismatch')
        model.load_state_dict(torch.load(initial_weights,map_location='cpu',weights_only=True))
    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features,3)
    optimizer = torch.optim.Adam(model.parameters(),lr=.001)
    lossfn = nn.CrossEntropyLoss()
    loader = torch.utils.data.DataLoader(Dataset('train'),batch_size=16,shuffle=True,
        generator=torch.Generator().manual_seed(seed))
    # Validation loss chooses the checkpoint; held-out test is used once afterwards.
    best,best_state = float('inf'),None
    for epoch in range(epochs):
        model.train()
        for x,y in loader:
            optimizer.zero_grad(); loss=lossfn(model(x),y); loss.backward(); optimizer.step()
        model.eval()
        with torch.no_grad():
            losses=[lossfn(model(x[None]),torch.tensor([y])).item() for x,y in Dataset('val')]
        val_loss = sum(losses)/len(losses)
        if val_loss < best:
            best=val_loss; best_state={k:v.detach().clone() for k,v in model.state_dict().items()}
    model.load_state_dict(best_state); model.eval()
    confusion=np.zeros((3,3),dtype=int); accepted=np.zeros((3,3),dtype=int); latencies=[]
    with torch.no_grad():
        for x,y in Dataset('test'):
            start=time.perf_counter(); probs=model(x[None]).softmax(1)[0]
            latencies.append((time.perf_counter()-start)*1000)
            pred=int(probs.argmax()); confusion[y,pred]+=1
            if float(probs[pred]) >= threshold: accepted[y,pred]+=1
    artifact=output/'uniform.onnx'
    torch.onnx.export(model,torch.zeros(1,3,224,224),str(artifact),opset_version=12,
        input_names=['garment'],output_names=['logits'],dynamo=False)
    metrics={}
    for i,label in enumerate(LABELS):
        metrics[label]={'precision':float(accepted[i,i]/max(1,accepted[:,i].sum())),
            'recall':float(accepted[i,i]/max(1,confusion[i].sum())),'test_count':int(confusion[i].sum())}
    # Measure the actual exported artifact in the runtime backend, not just PyTorch.
    import cv2
    net=cv2.dnn.readNetFromONNX(str(artifact)); exported_latency=[]
    for x,y in Dataset('test'):
        start=time.perf_counter(); net.setInput(x.numpy()[None]); logits=net.forward().reshape(-1)
        exported_latency.append((time.perf_counter()-start)*1000)
        with torch.no_grad(): expected=model(x[None]).numpy().reshape(-1)
        if not np.allclose(logits,expected,atol=1e-3,rtol=1e-3):
            raise ValueError('OpenCV ONNX parity failed')
    report={'schema_version':1,'architecture':'mobilenet_v3_small',
        'weights':'verified local torchvision weights' if initial_weights else 'random initialization baseline only',
        'initial_weights_sha256':weights_sha256 if initial_weights else None,
        'seed':seed,'epochs':epochs,'labels':LABELS,'threshold':threshold,'counts':counts,
        'manifest_sha256':hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(),
        'model_sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),
        'metrics':metrics,'confusion':confusion.tolist(),'accepted_confusion':accepted.tolist(),
        'coverage':float(accepted.sum()/confusion.sum()),'bytes':artifact.stat().st_size,
        'opencv_latency_ms_p50':float(np.median(exported_latency)),
        'opencv_latency_ms_p95':float(np.percentile(exported_latency,95)),
        'logo_occlusion_review':'PENDING','approved':False,
        'limitation':'Confidence is not visibility proof. Independent school logo/shape, wrong-school and occlusion review required.'}
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['validate','train'])
    parser.add_argument('dataset',type=Path)
    parser.add_argument('--output',type=Path,default=Path('private_uniform_output'))
    parser.add_argument('--epochs',type=int,default=20)
    parser.add_argument('--seed',type=int,default=2026)
    parser.add_argument('--threshold',type=float,default=.95)
    parser.add_argument('--initial-weights',type=Path)
    parser.add_argument('--weights-sha256')
    args=parser.parse_args()
    if args.epochs < 1 or not .8 <= args.threshold <= 1: parser.error('Invalid epochs or threshold')
    print(json.dumps(validate_manifest(args.dataset)[1] if args.command=='validate' else
        train(args.dataset,args.output,args.epochs,args.seed,args.threshold,args.initial_weights,args.weights_sha256),indent=2))
