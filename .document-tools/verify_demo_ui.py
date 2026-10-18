"""Real local browser QA. Camera denial is simulated only in this test context.

Starts a separate fresh QA server on8001; user demo on8000 is untouched.
Passwords are temporary and never printed. No face detector is mocked in server code.
"""
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import time
import urllib.request
import shutil
from datetime import datetime, timedelta, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.document-tools/browser-deps'))
from playwright.sync_api import sync_playwright, expect
from PIL import Image
from openpyxl import load_workbook

OUT=ROOT/'docs/project-management/evidence/ui-demo'
OUT.mkdir(parents=True,exist_ok=True)
LOG=[]


def note(message):
    LOG.append(message);print(message,flush=True)


def stop_server(process):
    # Windows venv python may launch a redirector child. Kill only this owned tree.
    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    process.wait(timeout=10)


def main(values):
    with sync_playwright() as driver:
        browser=driver.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1050},locale='vi-VN',timezone_id='Asia/Ho_Chi_Minh',accept_downloads=True)
        # This tests the permission failure path without opening a physical camera.
        context.add_init_script("navigator.mediaDevices.getUserMedia=()=>Promise.reject(new DOMException('Denied','NotAllowedError'));")
        page=context.new_page();errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(values['URL'],wait_until='networkidle')
        expect(page.locator('#login-screen')).to_be_visible()
        page.screenshot(path=str(OUT/'login-desktop.png'),full_page=True)
        page.locator('#login-username').fill(values['Username'])
        page.locator('#login-password').fill('incorrect-test-password')
        page.locator('#login-form button[type=submit]').click()
        expect(page.locator('#login-error')).to_contain_text('chưa đúng')
        page.locator('#login-password').fill(values['Password'])
        page.locator('#login-form button[type=submit]').click()
        expect(page.locator('#workspace')).to_be_visible()
        expect(page.locator('#stat-expected')).to_have_text('10')
        expect(page.locator('#stat-present')).to_have_text('0')
        expect(page.locator('#class-select option')).to_have_count(2)
        page.screenshot(path=str(OUT/'dashboard-desktop.png'),full_page=True)
        note('Browser login: invalid password feedback, real CSRF session, two scoped demo classes and ten-student roster: PASS')

        page.locator('.nav-item[data-view=attendance]').click()
        expect(page.locator('#attendance-roster tr')).to_have_count(10)
        # Create a second real session using the UI instead of relying on bootstrap.
        page.locator('#rule-button').click()
        page.locator('#rule-slot').select_option('AFTERNOON')
        page.locator('#rule-start').fill('00:00')
        page.locator('#rule-close').fill('23:59')
        page.locator('#rule-form button[type=submit]').click()
        expect(page.locator('#rule-dialog')).not_to_be_visible()
        page.locator('#create-session-button').click()
        page.locator('#session-slot').select_option('AFTERNOON')
        page.locator('#session-form button[type=submit]').click()
        expect(page.locator('#session-dialog')).not_to_be_visible()
        expect(page.locator('#context-status')).to_have_text('Chưa mở')
        page.locator('#open-session-button').click()
        expect(page.locator('#context-status')).to_have_text('Đang điểm danh')
        expect(page.locator('#attendance-roster tr')).to_have_count(10)
        note('Real UI schedule save -> session create(PLANNED) -> open -> ten-student snapshot roster: PASS')
        page.locator('#camera-button').click()
        expect(page.locator('#notice')).to_contain_text('Không mở được camera')
        expect(page.locator('#camera-status')).to_have_text('Camera tắt')
        image=io.BytesIO();Image.new('RGB',(640,480),'white').save(image,format='PNG')
        data=image.getvalue()
        page.locator('#scan-upload').set_input_files({'name':'blank.png','mimeType':'image/png','buffer':data})
        page.locator('#analyze-button').click()
        expect(page.locator('#scan-feedback')).to_contain_text('Chưa tìm thấy khuôn mặt')
        expect(page.locator('#confirm-scan-form')).to_be_hidden()
        note('Camera permission denial/upload fallback; real Haar rejects blank image, no candidate/attendance fabricated: PASS')

        # Isolated browser contract fixture ONLY. This does not alter the server's
        # detector or save recognition/attendance. The live user UI never receives it.
        session_id=page.locator('#session-select').input_value()
        roster=page.request.get(values['URL']+f'api/v1/sessions/{session_id}/roster').json()['items'][0]
        mock_id='11111111-1111-4111-8111-111111111111'
        mock_scan={'id':mock_id,'roster_id':roster['id'],'attendance_id':roster['attendance']['id'],
            'student_id':roster['student_id'],'student_code_snapshot':roster['student_code_snapshot'],
            'full_name_snapshot':roster['full_name_snapshot'],'version':0,'expected_attendance_version':0,
            'status':'PENDING','distance':12.0,'observed_uniform':'SHIRT','color_coverage':.9,
            'scanned_at':datetime.now(timezone.utc).isoformat(),'expires_at':(datetime.now(timezone.utc)+timedelta(seconds=120)).isoformat()}
        pattern='**/api/v1/sessions/*/vision-scans'
        def proposal(route):
            if route.request.method=='POST':route.fulfill(json={'recognition':'CANDIDATE','scan':mock_scan,'uniform':{'observed_uniform':'SHIRT','color_coverage':.9}})
            else:route.continue_()
        confirmations=[]
        def confirm_fixture(route):
            confirmations.append(route.request.post_data_json)
            route.fulfill(json={'scan':{**mock_scan,'status':'CONFIRMED'},'attendance':{'status':'PRESENT'}})
        page.route(pattern,proposal)
        page.route('**/api/v1/vision-scans/'+mock_id+'/confirm',confirm_fixture)
        page.locator('#analyze-button').click()
        expect(page.locator('#confirm-scan-form')).to_be_visible()
        expect(page.locator('#candidate-uniform')).to_have_value('')
        page.locator('#confirm-scan-form button[type=submit]').click()
        assert page.locator('#identity-confirmed').evaluate('(el)=>el.validity.valueMissing')
        assert confirmations==[]
        page.locator('#identity-confirmed').check()
        page.locator('#confirm-scan-form button[type=submit]').click()
        expect(page.locator('#confirm-scan-form')).to_be_hidden()
        assert confirmations==[{'expected_scan_version':0,'expected_attendance_version':0,'identity_confirmed':True}]
        expect(page.locator('#stat-present')).to_have_text('0')
        page.unroute(pattern,proposal)
        page.unroute('**/api/v1/vision-scans/'+mock_id+'/confirm',confirm_fixture)
        note('Mocked UI contract only: HSV never pre-checks uniform; identity checkbox required; confirm sends versions/identity, no student_id/uniform by default; actual DB stays unmarked: PASS')

        # A synthetic MediaStream exercises browser video lifecycle, not camera accuracy.
        page.evaluate("""() => {
          const canvas=document.createElement('canvas');canvas.width=640;canvas.height=480;
          canvas.getContext('2d').fillRect(0,0,640,480);
          window.__cameraTestStream=canvas.captureStream(5);
          navigator.mediaDevices.getUserMedia=async()=>window.__cameraTestStream;
        }""")
        page.locator('#camera-button').click()
        expect(page.locator('#camera-video')).to_be_visible()
        page.locator('#capture-button').click()
        expect(page.locator('#capture-preview')).to_be_visible()

        page.locator('.nav-item[data-view=students]').click()
        assert page.evaluate('window.__cameraTestStream.getTracks().every(track=>track.readyState==="ended")')
        note('Synthetic MediaStream preview/capture works; navigation stops every track: PASS')
        expect(page.locator('#students-table tr')).to_have_count(10)
        page.locator('#students-table tr').first.locator('button').click()
        expect(page.locator('#enroll-metadata')).to_contain_text('0 mẫu')
        page.locator('#enroll-files').set_input_files([{'name':f'blank{i}.png','mimeType':'image/png','buffer':data} for i in range(3)])
        page.locator('#enroll-form button[type=submit]').click()
        expect(page.locator('#enroll-dialog .dialog-error')).to_contain_text('Chưa tìm thấy khuôn mặt')
        # A delayed old-class error must not modify a new-class enrollment dialog.
        held=[]
        pattern_samples='**/api/v1/students/*/face-samples'
        def delayed_enrollment(route):
            if route.request.method=='POST':held.append((route,route.fetch()))
            else:route.continue_()
        page.route(pattern_samples,delayed_enrollment)
        page.locator('#enroll-form button[type=submit]').click()
        deadline=time.monotonic()+10
        while not held:
            if time.monotonic()>deadline:raise RuntimeError('Enrollment delay fixture did not receive request')
            page.wait_for_timeout(50)
        page.locator('#enroll-dialog .dialog-close').click()
        previous=page.locator('#students-table tr').first.inner_text()
        second_class=page.locator('#class-select option').nth(1).get_attribute('value')
        page.locator('#class-select').select_option(second_class)
        expect(page.locator('#students-table tr').first).not_to_have_text(previous)
        page.locator('#students-table tr').first.locator('button').click()
        expect(page.locator('#enroll-dialog')).to_be_visible()
        new_name=page.locator('#enroll-student-name').inner_text()
        expect(page.locator('#enroll-dialog .dialog-error')).to_be_hidden()
        old_route,old_response=held[0];old_route.fulfill(response=old_response)
        page.wait_for_function("!document.querySelector('#enroll-form [type=submit]').dataset.busy")
        expect(page.locator('#enroll-student-name')).to_have_text(new_name)
        expect(page.locator('#enroll-dialog .dialog-error')).to_be_hidden()
        page.unroute(pattern_samples,delayed_enrollment)
        page.locator('#enroll-dialog .dialog-close').click()
        note('Delayed old-class enrollment response cannot alter a new-class dialog: PASS')
        note('Student enrollment dialog uses private metadata and rejects invalid no-face samples without saving: PASS')

        page.locator('.nav-item[data-view=attendance]').click()
        first=page.locator('#attendance-roster tr').first
        first.get_by_role('button',name='Ghi nhận',exact=True).click()
        page.locator('#manual-reason').fill('Demo browser: camera unavailable, staff verified pupil')
        # Lose the first successful response body AFTER the real server commits.
        page.evaluate(r"""() => {
          const realFetch=window.fetch;window.__manualKeys=[];window.__dropBody=true;
          window.fetch=async (...args)=>{
            const [url,options]=args;
            const manual=options?.method==='PATCH' && /\/api\/v1\/attendance\/[^/]+$/.test(String(url));
            if(manual)window.__manualKeys.push(options.headers['Idempotency-Key']);
            const response=await realFetch(...args);
            if(manual && window.__dropBody && response.ok){
              window.__dropBody=false;
              Object.defineProperty(response,'json',{value:()=>Promise.reject(new SyntaxError('Simulated interrupted response body'))});
            }
            return response;
          };
        }""")
        page.locator('#manual-form button[type=submit]').click()
        expect(page.locator('#manual-dialog .dialog-error')).to_be_visible()
        page.locator('#manual-form button[type=submit]').click()
        expect(page.locator('#manual-dialog')).not_to_be_visible()
        keys=page.evaluate('window.__manualKeys')
        assert len(keys)==2 and keys[0]==keys[1],'Uncertain response must retain idempotency key'
        note('Real committed write with simulated lost response body: same-key retry succeeds without a duplicate write: PASS')
        expect(page.locator('#stat-present')).to_have_text('1')
        first=page.locator('#attendance-roster tr').first
        first.get_by_role('button',name='Đồng phục',exact=True).click()
        page.locator('#uniform-observed').select_option('SPORTS')
        page.locator('#uniform-reason').fill('Demo: shirt is required for this session')
        page.locator('#uniform-form button[type=submit]').click()
        expect(page.locator('#uniform-dialog')).not_to_be_visible()
        expect(page.locator('#attendance-roster tr').first).to_contain_text('Không đạt')
        page.screenshot(path=str(OUT/'attendance-desktop.png'),full_page=True)
        page.once('dialog',lambda dialog:dialog.accept())
        page.locator('#close-session-button').click()
        expect(page.locator('#context-status')).to_have_text('Đã chốt')
        expect(page.locator('#stat-unmarked-note')).to_contain_text('9 vắng')
        note('Real browser manual entry + uniform violation + versioned session close: one present/nine absent: PASS')

        page.locator('.nav-item[data-view=reports]').click()
        expect(page.locator('#report-table tr')).to_have_count(10)
        expect(page.locator('#report-summary')).to_contain_text('10')
        for kind in ('xlsx','csv'):
            with page.expect_download() as download:
                page.locator('#export-'+kind).click()
            path=OUT/('browser-attendance.'+kind);download.value.save_as(path)
            if kind=='xlsx':
                book=load_workbook(path);summary=dict(book['Tong_hop'].values)
                assert (summary['present'],summary['absent'],summary['non_compliant'])==(1,9,1)
            else:
                rows=list(csv.DictReader(io.StringIO(path.read_text(encoding='utf-8-sig'))))
                assert len(rows)==10 and sum(row['Trạng thái']=='PRESENT' for row in rows)==1
                assert sum(row['Kết quả đồng phục']=='NON_COMPLIANT' for row in rows)==1
        note('Actual protected XLSX/CSV downloads through UI reopened; ten records/one present/nine absent/one uniform violation: PASS')

        page.locator('.nav-item[data-view=dashboard]').click()
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),'Page overflows mobile viewport'
        page.screenshot(path=str(OUT/'dashboard-mobile.png'),full_page=True)
        page.locator('#logout-button').click()
        expect(page.locator('#login-screen')).to_be_visible()
        expect(page.locator('#workspace')).to_be_hidden()
        expect(page.locator('#enroll-student-name')).to_have_text('')
        assert page.locator('#enroll-files').evaluate('(input)=>input.files.length')==0
        page.locator('#login-username').fill('demo_student_01')
        page.locator('#login-password').fill(values['Password'])
        page.locator('#login-form button[type=submit]').click()
        expect(page.locator('#login-error')).to_contain_text('Giao diện dành cho GVCN')
        expect(page.locator('#workspace')).to_be_hidden()
        note('390px mobile layout has no page overflow; logout clears workspace; student login cannot enter staff UI: PASS')

        page.locator('#login-username').fill('demo_teacher_b')
        page.locator('#login-password').fill(values['Password'])
        page.locator('#login-form button[type=submit]').click()
        expect(page.locator('#workspace')).to_be_visible()
        expect(page.locator('#class-select option')).to_have_count(1)
        expect(page.locator('#class-select')).to_contain_text('10B')
        note('Homeroom teacher sees only assigned class through real scoped APIs: PASS')
        page.evaluate("""async()=>{const csrf=document.cookie.split('; ').find(c=>c.startsWith('csrftoken=')).slice(10);await fetch('/api/v1/auth/logout',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:'{}'});}""")
        page.locator('#refresh-button').click()
        expect(page.locator('#login-screen')).to_be_visible()
        expect(page.locator('#login-error')).to_contain_text('Phiên đăng nhập đã hết')
        expect(page.locator('#enroll-student-name')).to_have_text('')
        note('Server-side session logout followed by API401 clears private UI and returns to login: PASS')
        assert not errors,errors
        note('JavaScript uncaught errors: 0. Real camera/positive face recognition not tested. Permission denial, MediaStream, proposal/confirm contract and lost response body are simulated only in isolated QA browser.')
        context.close();browser.close()


if __name__=='__main__':
    process=None;runtime=None
    try:
        with tempfile.TemporaryDirectory(prefix='projectmindx-browser-qa-') as folder:
            ready=Path(folder)/'ready.json'
            with (OUT/'browser-server.txt').open('w',encoding='utf-8') as server_log:
                process=subprocess.Popen([sys.executable,str(ROOT/'.document-tools/run_demo.py'),'--port','8001','--ready-file',str(ready)],
                    cwd=ROOT,stdout=server_log,stderr=server_log,creationflags=subprocess.CREATE_NO_WINDOW)
                deadline=time.monotonic()+60
                while not ready.exists():
                    if process.poll() is not None:raise RuntimeError('QA server failed to start; inspect local temporary server log.')
                    if time.monotonic()>deadline:raise RuntimeError('QA server startup timeout.')
                    time.sleep(.25)
                info=json.loads(ready.read_text(encoding='utf-8'));runtime=Path(info['runtime']).resolve()
                values=dict(line.split(': ',1) for line in Path(info['credentials']).read_text(encoding='utf-8-sig').splitlines() if ': ' in line)
                while True:
                    try:
                        with urllib.request.urlopen(info['url'],timeout=2) as response:assert response.status==200
                        break
                    except OSError:
                        if time.monotonic()>deadline:raise
                        time.sleep(.25)
                try:main(values)
                finally:
                    stop_server(process);process=None
    finally:
        if process is not None:
            stop_server(process)
        if runtime is not None and runtime.is_relative_to(Path(tempfile.gettempdir()).resolve()) and runtime.name.startswith('projectmindx-demo-ui-'):
            shutil.rmtree(runtime)
        (OUT/'browser-validation.txt').write_text('\n'.join(LOG),encoding='utf-8')
