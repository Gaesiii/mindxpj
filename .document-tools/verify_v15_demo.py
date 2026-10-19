"""Real browser + CSRF HTTP + local YuNet/SFace, disposable fictitious DB only.

Photo arguments remain local. No inference or HTTP mocks; not a liveness test.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,os.environ.get('BROWSER_TOOL_DEPS',str(ROOT/'.document-tools/browser-deps')))
from playwright.sync_api import sync_playwright, expect


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--images',type=Path,required=True)
    parser.add_argument('--query',type=Path,nargs=2,required=True)
    parser.add_argument('--port',type=int,default=8003)
    args=parser.parse_args()
    out=ROOT/'docs/project-management/evidence/v1.5'
    out.mkdir(parents=True,exist_ok=True)
    def assets(paths):
        return [{'name':p.name,'data':base64.b64encode(p.read_bytes()).decode()} for p in paths]
    with tempfile.TemporaryDirectory(prefix='mindx-v15-qa-',ignore_cleanup_errors=True) as temporary:
        ready=Path(temporary)/'ready.json'
        with (Path(temporary)/'server.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen([sys.executable,str(ROOT/'.document-tools/run_demo.py'),
                '--port',str(args.port),'--ready-file',str(ready)],cwd=ROOT,stdout=log,stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                deadline=time.monotonic()+90
                while not ready.exists():
                    if process.poll() is not None: raise RuntimeError('QA server startup failed')
                    if time.monotonic()>deadline: raise TimeoutError('QA server startup timeout')
                    time.sleep(.2)
                info=json.loads(ready.read_text(encoding='utf-8'))
                values=dict(line.split(': ',1) for line in Path(info['credentials']).read_text(encoding='utf-8').splitlines() if ': ' in line)
                while True:
                    try:
                        urllib.request.urlopen(info['url'],timeout=2).close();break
                    except OSError:
                        if time.monotonic()>deadline: raise
                        time.sleep(.2)
                with sync_playwright() as driver:
                    browser=driver.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
                    page=browser.new_page(viewport={'width':1440,'height':1050})
                    errors=[]
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    page.goto(info['url'])
                    page.locator('#login-username').fill(values['Username'])
                    page.locator('#login-password').fill(values['Password'])
                    page.locator('#login-form button[type=submit]').click()
                    expect(page.locator('#workspace')).to_be_visible()
                    expect(page.locator('#class-select option')).to_have_count(2)
                    def call(path,method='GET',body=None):
                        return page.evaluate('''async ({path,method,body})=>{
                          const token=decodeURIComponent(document.cookie.split('; ').find(c=>c.startsWith('csrftoken='))?.slice(10)||'');
                          const r=await fetch('/api/v1'+path,{method,headers:{'Content-Type':'application/json','X-CSRFToken':token,'Idempotency-Key':crypto.randomUUID()},...(body===null?{}:{body:JSON.stringify(body)})});
                          return {status:r.status,body:await r.json()};
                        }''',{'path':path,'method':method,'body':body})
                    classes=call('/classes')['body']['items']
                    classroom=next(c for c in classes if c['code']=='DEMO10A')
                    students=call('/students?class_id='+classroom['id'])['body']['items']
                    student=next(s for s in students if s['student_code']=='DEMOHS01')
                    sessions=call('/sessions?class_id='+classroom['id'])['body']['items']
                    session=next(s for s in sessions if s['status']=='OPEN')
                    def multipart(path,photos,fields=None,key=None):
                        return page.evaluate('''async ({path,photos,fields,key})=>{
                          const form=new FormData();for(const photo of photos){const bytes=Uint8Array.from(atob(photo.data),c=>c.charCodeAt(0));form.append('images',new File([bytes],photo.name,{type:'image/jpeg'}));}
                          for(const [name,value] of Object.entries(fields||{}))form.append(name,value);
                          const token=decodeURIComponent(document.cookie.split('; ').find(c=>c.startsWith('csrftoken='))?.slice(10)||'');
                          const r=await fetch('/api/v1'+path,{method:'POST',headers:{'X-CSRFToken':token,'Idempotency-Key':key||crypto.randomUUID()},body:form});return {status:r.status,body:await r.json()};
                        }''',{'path':path,'photos':assets(photos),'fields':fields,'key':key})
                    enroll=multipart('/students/'+student['id']+'/face-samples',sorted((args.images/'01-enroll').glob('*.jpg')))
                    assert enroll['status']==201,enroll
                    scanpath='/sessions/'+session['id']+'/auto-attendance-scans'
                    fields={'scan_mode':'AUTO_ATTENDANCE','expected_session_version':str(session['version'])}
                    negative=multipart(scanpath,[args.images/'02-scan/unknown-person.jpg',args.images/'demo/qiamz8htjhpu1jluumkx832nphpje7pk20260926081546.jpg'],fields)
                    assert negative['status']==200 and negative['body']['outcome']=='UNKNOWN',negative
                    key=secrets.token_urlsafe(20)
                    positive=multipart(scanpath,args.query,fields,key)
                    assert positive['status']==201 and positive['body']['outcome']=='RECORDED',positive
                    a=positive['body']['attendance']
                    assert a['recognition_mode']=='AUTO' and a['verified_by_id'] is None and a['verified_at'] is None,a
                    assert a['uniform_status']=='NOT_CHECKED',a
                    replay=multipart(scanpath,args.query,fields,key)
                    assert replay==positive
                    again=multipart(scanpath,args.query,fields)
                    assert again['body']['outcome']=='ALREADY_RECORDED' and again['body']['attendance']['arrived_at']==a['arrived_at'],again
                    # Exercise real UI CRUD against actual scoped APIs, not fixture responses.
                    page.locator('#class-select').select_option(classroom['id'])
                    page.locator('[data-view=students]').click()
                    expect(page.locator('#students-table')).to_contain_text('DEMOHS01')
                    page.locator('#student-create-button').click()
                    page.locator('#student-code').fill('V15QA')
                    page.locator('#student-name').fill('Demo QA pupil')
                    page.locator('#student-class').select_option(classroom['id'])
                    page.locator('#student-editor-form button[type=submit]').click()
                    expect(page.locator('#student-editor-dialog')).not_to_be_visible()
                    created=next(s for s in call('/students?class_id='+classroom['id'])['body']['items'] if s['student_code']=='V15QA')
                    updated=call('/students/'+created['id'],'PATCH',{'expected_version':created['version'],'full_name':'Renamed QA pupil'})
                    assert updated['status']==200,updated
                    archived=call('/students/'+created['id'],'DELETE',{'expected_version':updated['body']['version']})
                    assert archived['status']==200 and not archived['body']['active'],archived
                    page.locator('[data-view=attendance]').click()
                    page.locator('#refresh-button').click()
                    expect(page.locator('#stat-present')).to_have_text('1')
                    assert not errors,errors
                    page.screenshot(path=str(out/'automatic-attendance.png'),full_page=True)
                    report={'browser':'headless Edge','inference':'real local YuNet/SFace; no inference or HTTP mocks',
                        'enrolled_images':enroll['body']['usable_sample_count'],'held_out_images':2,
                        'negative_outcome':negative['body']['outcome'],'positive_outcome':positive['body']['outcome'],
                        'automatic_recognition_mode':a['recognition_mode'],'verified_by':None,
                        'uniform_without_school_model':a['uniform_status'],'same_key_replay':'PASS',
                        'new_key_first_arrival_preserved':'PASS','real_backend_ui_create':'PASS',
                        'real_backend_edit_archive':'PASS','uncaught_page_errors':errors,
                        'limitations':'Only these fixture photos. No physical camera, liveness or population accuracy claim. School uniform training awaits private dataset.'}
                    browser.close()
                (out/'real-face-browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                print(json.dumps(report,ensure_ascii=True))
            finally:
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
                process.wait(timeout=10)


if __name__=='__main__':main()
