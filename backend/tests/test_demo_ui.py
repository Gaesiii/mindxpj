from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import Client, TestCase, override_settings


class DemoUiTests(TestCase):
    @override_settings(VISION_ENROLLMENT_TOTAL_BYTES=3*1024*1024)
    def test_shell_advertises_runtime_upload_budget(self):
        response = self.client.get('/')
        self.assertContains(response, 'data-enrollment-limit="3145728"')
        self.assertContains(response, 'Tổng ≤3 MiB sau tối ưu.')
        self.assertContains(response, 'Ảnh gốc ≤32 MiB/ảnh')

    def test_public_shell_bootstraps_csrf_without_private_data(self):
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Điểm danh')
        self.assertContains(response,'csrfmiddlewaretoken')
        self.assertContains(response,'demo_ui/app.js')
        self.assertIn('csrftoken',response.cookies)
        self.assertIn('no-store',response.headers['Cache-Control'])
        self.assertNotContains(response,'Demo!')

    def test_script_and_styles_are_local_assets(self):
        for name in ('demo_ui/app.js','demo_ui/app.css'):
            path=finders.find(name)
            self.assertIsNotNone(path,name)
            self.assertGreater(Path(path).stat().st_size,100)

    def test_shell_does_not_grant_staff_api_or_bypass_csrf(self):
        secure=Client(enforce_csrf_checks=True)
        secure.get('/')
        self.assertEqual(secure.get('/api/v1/classes').status_code,401)
        self.assertEqual(secure.post('/api/v1/auth/login',{'username':'nobody','password':'no'}).status_code,403)
        user=get_user_model().objects.create_user(username='ui_student',role='STUDENT')
        secure.force_login(user)
        self.assertEqual(secure.get('/api/v1/classes').status_code,403)
        self.assertEqual(secure.get('/api/v1/reports/summary',{'date_from':'2026-10-18','date_to':'2026-10-18'}).status_code,403)

    def test_unknown_api_stays_json_and_ui_has_no_secret(self):
        self.assertEqual(self.client.get('/api/v1/ui-missing').json()['code'],'NOT_FOUND')
        response=self.client.get('/')
        self.assertNotContains(response,settings.SECRET_KEY)

class AutomaticCameraBehaviorTests(TestCase):
    def test_success_is_held_until_a_new_person_or_confirmed_empty_camera(self):
        import shutil
        import subprocess
        node = shutil.which('node')
        if not node:
            self.skipTest('Node required')
        script = Path(settings.BASE_DIR) / 'school_app/demo_ui/static/demo_ui/camera.js'
        program = r"""
const assert=require('node:assert/strict');
const {createAttendanceGate}=require(process.argv[1]);
const gate=createAttendanceGate();
const present={outcome:'RECORDED',student_id:'a',attendance:{status:'PRESENT'}};
assert.equal(gate.observe(present,0),'saved');
assert.equal(gate.remaining(4999),1);
assert.equal(gate.observe({outcome:'UNKNOWN',reason:'BLURRY_FACE'},5000),'waiting');
assert.equal(gate.observe({outcome:'UNKNOWN',reason:'NO_FACE'},6000),'waiting');
assert.equal(gate.observe({outcome:'UNKNOWN',reason:'BLURRY_FACE'},7000),'waiting');
assert.equal(gate.observe({outcome:'UNKNOWN',reason:'NO_FACE'},8000),'waiting');
assert.equal(gate.observe({outcome:'UNKNOWN',reason:'NO_FACE'},9000),'ready');
assert.equal(gate.observe(present,10000),'saved');
assert.equal(gate.observe({...present,outcome:'ALREADY_RECORDED'},15000),'waiting');
assert.equal(gate.observe({...present,student_id:'b'},16000),'saved');
assert.equal(gate.remaining(16000),5000);
assert.equal(gate.observe({...present,student_id:'b',attendance:{status:'ABSENT'}},21000),'ready');
gate.observe(present,22000);
assert.equal(gate.observe({...present,student_id:'b',attendance:{status:'ABSENT'}},28000),'ready');
gate.reset();assert.equal(gate.remaining(16000),0);
assert.equal(gate.observe({outcome:'UNKNOWN',reason:'BLURRY_FACE'},17000),'ready');
// Manual ABSENT must never be presented as a new successful PRESENT.
assert.equal(gate.observe({...present,attendance:{status:'ABSENT'}},18000),'ready');
"""
        result = subprocess.run([node, '-e', program, str(script)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pair_validation_and_serial_camera_loop(self):
        import shutil
        import subprocess
        node = shutil.which('node')
        if not node:
            self.skipTest('Node required for camera behavior test')
        script = Path(settings.BASE_DIR) / 'school_app/demo_ui/static/demo_ui/camera.js'
        program = r"""
const assert=require('node:assert/strict');
const {validatePair,createLoop,retryDelay}=require(process.argv[1]);
const good={size:500000,type:'image/jpeg'};
assert.throws(()=>validatePair([good]),/2/);
assert.throws(()=>validatePair([good,{...good,size:1048577}]),/1 MiB/);
validatePair([good,good]);
assert.equal(retryDelay('9',0),9000);
assert.equal(retryDelay('',2),16000);
(async()=>{
 let active=0,max=0,calls=0,release;
 const pending=new Promise(r=>release=r);
 const loop=createLoop(async()=>{calls++;active++;max=Math.max(max,active);await pending;active--;},()=>true,5);
 loop.start();
 await new Promise(r=>setTimeout(r,25));
 assert.equal(calls,1);assert.equal(max,1);
 loop.stop();release();
 await new Promise(r=>setTimeout(r,25));assert.equal(calls,1);
 console.log('pair limits, retry delay, no overlap, stop: passed');
})().catch(e=>{console.error(e);process.exitCode=1});
"""
        result = subprocess.run([node, '-e', program, str(script)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shell_exposes_automatic_and_separate_management_spaces(self):
        response = self.client.get('/')
        for element in ('view-uniform', 'view-uniform-samples', 'view-classes', 'scan-workspace', 'student-editor-dialog', 'class-editor-dialog', 'roster-add-button'):
            self.assertContains(response, 'id="' + element + '"')
        self.assertContains(response, 'demo_ui/camera.js')
