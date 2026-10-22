from io import BytesIO
from pathlib import Path
import subprocess
import shutil
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from school_app.accounts.services import AccountError
from school_app.vision import engine


class EnrollmentLargeImageTests(SimpleTestCase):
    def test_uniform_large_original_is_prepared_with_camera_payload_budget(self):
        node=shutil.which('node')
        if not node:self.skipTest('Node required')
        module=Path(__file__).resolve().parents[1]/'school_app/demo_ui/static/demo_ui/enrollment.js'
        code=r'''
const assert=require('node:assert/strict');
const {prepareUniform}=require(process.argv[1]);
(async()=>{
 const original={size:25*1048576,type:'image/jpeg'};
 const result=await prepareUniform(original,async(file,budget)=>{
  assert.equal(file,original);assert.ok(budget<2*1048576);
  return {size:1000000,type:'image/jpeg'};
 });
 assert.equal(result.size,1000000);
 await assert.rejects(()=>prepareUniform({...original,size:33*1048576}),/32/);
 await assert.rejects(()=>prepareUniform({...original,type:'image/heic'}),/JPEG/);
 await assert.rejects(()=>prepareUniform(original,async()=>({size:3*1048576})),/dung lượng/);
 let current=true;
 assert.equal(await prepareUniform(original,async()=>{current=false;return result;},()=>current),null);
})().catch(e=>{console.error(e);process.exit(1)});
'''
        result=subprocess.run([node,'-e',code,str(module)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_large_photo_allowed_only_with_explicit_enrollment_budget(self):
        buffer=BytesIO();Image.new('RGB',(5000,3000),(40,80,120)).save(buffer,format='JPEG')
        data=buffer.getvalue()
        with self.assertRaises(AccountError):
            engine.decode_upload(SimpleUploadedFile('camera.jpg',data))
        image=engine.decode_upload(SimpleUploadedFile('camera.jpg',data),max_bytes=16*1024*1024,max_pixels=64_000_000)
        self.assertEqual(image.shape[:2],(576,960))
        with self.assertRaises(AccountError):
            engine.decode_upload(SimpleUploadedFile('camera.jpg',data),max_bytes=100,max_pixels=64_000_000)

    def test_enrollment_preparation_is_serial_and_meets_vercel_budget(self):
        node=shutil.which('node')
        if not node:self.skipTest('Node required')
        module=Path(__file__).resolve().parents[1]/'school_app/demo_ui/static/demo_ui/enrollment.js'
        code=r'''
const assert=require('node:assert/strict');
const {prepare}=require(process.argv[1]);
(async()=>{
 let active=0,max=0;
 const originals=Array.from({length:10},()=>({size:20*1048576,type:'image/jpeg'}));
 const out=await prepare(originals,3*1048576,async(file,budget)=>{active++;max=Math.max(max,active);await new Promise(r=>setTimeout(r,1));active--;return {size:Math.floor(budget),type:'image/jpeg'};});
 assert.equal(out.length,10);assert.equal(max,1);assert.ok(out.reduce((n,f)=>n+f.size,0)<3*1048576);
 await assert.rejects(()=>prepare([{size:33*1048576,type:'image/jpeg'},...originals.slice(0,2)],3*1048576),/32/);
 await assert.rejects(()=>prepare(originals,3*1048576,async()=>({size:3*1048576})),/dung lượng|quá lớn/);
 let current=true,encodes=0;
 assert.equal(await prepare(originals,3*1048576,async()=>{encodes++;current=false;return {size:100}},()=>{},()=>current),null);
 assert.equal(encodes,1,'Cancel stops subsequent large decodes');
 console.log('serial preparation, large originals, payload budgets: passed');
})().catch(e=>{console.error(e);process.exit(1)});
'''
        result=subprocess.run([node,'-e',code,str(module)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
