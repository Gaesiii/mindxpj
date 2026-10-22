"""Real local model/UI check and private gallery recording; never prints login."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.document-tools/browser-deps'))
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--ready-file',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
ready=json.loads(args.ready_file.read_text())
credentials=dict(line.split(': ',1) for line in Path(ready['credentials']).read_text().splitlines() if ': ' in line)
args.output.mkdir(parents=True,exist_ok=True)
origin=ready['url'].rstrip('/')
with sync_playwright() as p:
    chrome=Path.home()/'AppData/Local/ms-playwright/chromium-1181/chrome-win/chrome.exe'
    browser=p.chromium.launch(executable_path=str(chrome),headless=True,
        args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream'])
    context=browser.new_context(viewport={'width':1440,'height':1080},record_video_dir=str(args.output),
                                record_video_size={'width':1440,'height':1080})
    context.request.get(origin+'/')
    token=next(c['value'] for c in context.cookies() if c['name']=='csrftoken')
    login=context.request.post(origin+'/api/v1/auth/login',data={'username':credentials['Username'],'password':credentials['Password']},
                               headers={'X-CSRFToken':token})
    assert login.ok,'Local login failed'
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(origin+'/uniform-demo/');page.wait_for_selector('.sample');assert page.locator('.sample').count()==8
    data=context.request.get(origin+'/api/v1/demo/uniform').json()
    results=[]
    for sample in data['samples']:
        page.locator('[data-sample="'+sample['id']+'"]').click()
        page.wait_for_function("!['Chọn một ảnh để bắt đầu','Đang nhận diện…'].includes(document.getElementById('lab-decision').textContent)")
        page.wait_for_function("title => document.getElementById('lab-source').textContent.startsWith(title)",arg=sample['title'])
        results.append({'sample':sample['id'],'expected':sample['expected'],'result_text':page.locator('#lab-decision').inner_text()})
        page.wait_for_timeout(1200)
    assert sum(r['result_text']=='Đồng phục KV' for r in results)==3
    assert sum(r['result_text']=='Trang phục khác' for r in results)==3
    assert sum(r['result_text']=='Chưa đủ tin cậy' for r in results)==2
    page.screenshot(path=str(args.output/'gallery.png'),full_page=True)
    # End this recording before testing synthetic camera input.
    video=page.video;page.close();context.close();video.save_as(str(args.output/'pm-demo.webm'))
    checks=browser.new_context(viewport={'width':1440,'height':1080})
    checks.request.get(origin+'/');token=next(c['value'] for c in checks.cookies() if c['name']=='csrftoken')
    assert checks.request.post(origin+'/api/v1/auth/login',data={'username':credentials['Username'],'password':credentials['Password']},headers={'X-CSRFToken':token}).ok
    page=checks.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(origin+'/uniform-demo/');page.wait_for_selector('.sample')
    # Change upload while the preceding inference is deliberately delayed.
    calls=[]
    def delayed(route):
        calls.append(1)
        if len(calls)==1:time.sleep(.3)
        try:route.continue_()
        except Exception:pass  # First request may have been aborted on purpose.
    page.route('**/api/v1/demo/uniform/predict',delayed)
    first=checks.request.get(origin+'/api/v1/demo/uniform/samples/s01').body()
    second=checks.request.get(origin+'/api/v1/demo/uniform/samples/s04').body()
    page.locator('#lab-upload').set_input_files({'name':'first.png','mimeType':'image/png','buffer':first})
    page.locator('#lab-upload').set_input_files({'name':'second.png','mimeType':'image/png','buffer':second})
    page.wait_for_function("document.getElementById('lab-decision').textContent === 'Đồng phục KV'")
    page.unroute('**/api/v1/demo/uniform/predict',delayed)
    page.locator('#lab-camera').click();page.wait_for_selector('#lab-video',state='visible')
    page.wait_for_function('document.getElementById("lab-video").videoWidth > 0')
    geometry=page.evaluate('''() => {const v=document.getElementById('lab-video');const rect=v.getBoundingClientRect();return {rendered:rect.width/rect.height,source:v.videoWidth/v.videoHeight};}''')
    assert abs(geometry['rendered']-geometry['source'])<.01,'Camera ROI aspect mismatch'
    page.locator('#lab-stop').click();assert page.locator('#camera-box').is_hidden()
    assert page.locator('#lab-camera').is_enabled()
    assert not errors,errors
    checks.close();browser.close()
    result={'gallery_count':8,'real_model_gallery_results':results,'rapid_upload_latest_image_processed':True,
            'camera_layout_geometry':geometry,'camera_stop_cleanup':True,'camera_test_input':'Chromium synthetic stream, not physical camera proof',
            'javascript_errors':errors,'private_recording':'pm-demo.webm','recording_contains_camera_simulation':False}
    (args.output/'browser-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True,indent=2))
