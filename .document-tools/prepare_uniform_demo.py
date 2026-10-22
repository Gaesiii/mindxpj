"""Copy the verified LOCAL KV trial into an ignored recording-demo bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]


def prepare(source,target):
    source,target=Path(source).resolve(),Path(target).resolve()
    if source==target or source in target.parents or target in source.parents:
        raise ValueError('Use separate source and target directories')
    report=json.loads((source/'output/report.json').read_text())
    manifest=json.loads((source/'prepared/manifest.json').read_text())
    predictions=json.loads((source/'output/private-test-predictions.json').read_text())
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    assert report['labels']==['NON_UNIFORM','KV_UNIFORM'] and report['approved'] is False
    model=source/'output/external-kv-binary.onnx'
    assert sha(model)==report['model_sha256']
    assert sha(source/'prepared/manifest.json')==report['manifest_sha256']
    selected=[]
    for label in report['labels']:
        selected.extend([p for p in predictions if p['expected']==label and p['decision']==label][:3])
    selected.extend([p for p in predictions if p['decision']=='UNKNOWN'][:2])
    assert len(selected)==8
    target.mkdir(parents=True,exist_ok=True)
    (target/'prepared').mkdir(exist_ok=True)
    for sample in manifest['samples']:
        path=(source/'prepared'/sample['path']).resolve()
        assert path.is_relative_to(source/'prepared') and sha(path)==sample['sha256']
        shutil.copy2(path,target/'prepared'/path.name)
    shutil.copy2(source/'prepared/manifest.json',target/'prepared/manifest.json')
    shutil.copy2(model,target/'model.onnx')
    shutil.copy2(source/'output/report.json',target/'report.json')
    shutil.copy2(source/'provenance.json',target/'provenance.json')
    entries=[]
    for i,p in enumerate(selected):
        path=target/'prepared'/p['path']
        title=('Mẫu khó' if p['decision']=='UNKNOWN' else 'Đồng phục KV' if p['expected']=='KV_UNIFORM' else 'Trang phục khác')+f' · {i+1:02}'
        entries.append({'id':f's{i+1:02}','title':title,'expected':p['expected'],
                        'path':'prepared/'+path.name,'sha256':sha(path)})
    data={'schema_version':1,'labels':report['labels'],'threshold':report['threshold'],
          'model_sha256':report['model_sha256'],'experiment_only':True,
          'dataset_count':len(manifest['samples']),'samples':entries}
    (target/'bundle.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Prepared {len(manifest["samples"])} local dataset crops, binary model, and {len(entries)} held-out gallery samples.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--target',type=Path,default=ROOT/'uniform-dataset/kv-demo')
    args=parser.parse_args();prepare(args.source,args.target)
