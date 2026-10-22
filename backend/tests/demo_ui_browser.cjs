// Local demo browser smoke test. Run a Django development server first.
// API responses are fixtures; camera is Chromium fake media. No recognition accuracy claim.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright-core');
const assert=require('node:assert/strict');
let browser;
(async()=>{
 browser=await chromium.launch({executablePath:process.env.BROWSER_EXECUTABLE||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
 const context=await browser.newContext({permissions:['camera']});const page=await context.newPage();let errors=[],scans=[],writes=[],role='SUPERVISOR',uniformRejectReason=null;page.on('pageerror',e=>errors.push(e.message));
 const now=new Date(),today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Ho_Chi_Minh'}).format(now);
 const classroom={id:'c1',code:'10A',name:'Lớp 10A',grade_id:'g1',teacher_id:'t1',capacity:50,active:true,version:1,active_student_count:1};
 const student={id:'s1',student_code:'HS01',full_name:'Nguyễn An',class_id:'c1',active:true,version:1};
 const session={id:'q1',class_id:'c1',school_date:today,slot:'MORNING',status:'OPEN',version:1,required_uniform_snapshot:'SHIRT',start_at:new Date(+now-3600000).toISOString(),close_at:new Date(+now+3600000).toISOString()};
 const historical={...session,id:'q0',school_date:'2026-01-01',status:'CLOSED'};
 const attendance={id:'a1',version:1,status:'PRESENT',uniform_status:'REVIEW_REQUIRED',observed_uniform:'SPORTS',arrived_at:now.toISOString(),arrival_status:'ON_TIME'};
 attendance.uniform_source='AUTO';
 const row={student_id:'s1',full_name_snapshot:'Nguyễn An',student_code_snapshot:'HS01',attendance};
 await page.route('**/api/v1/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname.replace('/api/v1','');let body={};
  if(req.method()!=='GET')writes.push({path,body:req.postData(),method:req.method()});
  if(path==='/students/s1'){if(req.method()==='DELETE'){student.active=false;student.version++;classroom.active_student_count=0;}else if(req.method()==='PATCH'){Object.assign(student,req.postDataJSON(),{version:student.version+1});classroom.active_student_count=student.active?1:0;}body=student;}
  else if(path==='/auth/me'||path==='/auth/login')body={username:'demo',role};
  else if(path==='/classes')body=req.method()==='GET'?{items:[classroom]}:{...classroom,...req.postDataJSON()};
  else if(path==='/students')body=req.method()==='GET'?{items:[student]}:{...student,...req.postDataJSON()};
  else if(path==='/sessions')body={items:[session,historical]};
  else if(path==='/sessions/q1')body=session;else if(path==='/sessions/q0')body=historical;
  else if(['/sessions/q1/roster','/sessions/q0/roster'].includes(path))body={items:[row]};
  else if(['/sessions/q1/vision-scans','/sessions/q0/vision-scans'].includes(path))body={items:[]};
  else if(path==='/classes/c1/uniform-profile')body={profile:null,versions:[]};
  else if(path==='/classes/c1/uniform-samples'){
   if(req.method()==='POST'&&uniformRejectReason){await route.fulfill({status:422,json:{code:'INVALID_IMAGE',message:'Image rejected',details:{reason:uniformRejectReason}}});return;}
   body={items:[]};
  }
  else if(path==='/grades')body={items:[{id:'g1',name:'Khối 10'}]};
  else if(path==='/teachers')body={items:[{id:'t1',username:'teacher'}]};
  else if(path==='/sessions/q1/auto-attendance-scans'){
   const raw=req.postDataBuffer().toString('latin1');assert.equal((raw.match(/name="images"/g)||[]).length,2);assert(raw.includes('AUTO_ATTENDANCE')||raw.includes('UNIFORM_ONLY'));assert(req.headers()['idempotency-key']);
   scans.push({time:Date.now(),mode:raw.includes('UNIFORM_ONLY')?'UNIFORM_ONLY':'AUTO_ATTENDANCE'});body=scans.length===2?{outcome:'UNKNOWN',reason:'BLURRY_FACE'}:{outcome:scans.length>2?'ALREADY_RECORDED':'RECORDED',student_id:'s1',full_name_snapshot:'Nguyễn An',attendance:{...attendance,uniform_status:'NOT_CHECKED'}};
  }else if(path==='/attendance/a1/uniform'){body={...attendance,...req.postDataJSON(),uniform_source:'MANUAL'};Object.assign(attendance,body);}
  await route.fulfill({json:body});
 });
 await page.goto(process.env.UI_BASE_URL||'http://127.0.0.1:8766/');await page.locator('#identity-name').waitFor();await page.waitForFunction(()=>document.querySelector('#class-select').value==='c1');
 await page.locator('[data-view="attendance"]').click();await page.locator('#camera-button').click();await page.waitForTimeout(8500);
 assert((await page.locator('#scan-feedback').textContent()).includes('Đã lưu. Chờ 5 giây'),'blur after success retains committed receipt');
 assert(scans.length>=2,'camera must scan automatically');assert(scans[1].time-scans[0].time>=5000,'5 second pause after successful commit');
 await page.locator('[data-view="students"]').click();const stopped=scans.length;await page.waitForTimeout(4300);assert.equal(scans.length,stopped,'navigation stops camera');assert(await page.locator('#camera-video').evaluate(v=>!v.srcObject));
 await page.locator('#student-create-button').click();await page.locator('#student-code').fill('HS02');await page.locator('#student-name').fill('Trần Bình');await page.locator('#student-editor-form button[type="submit"]').click();await page.waitForTimeout(200);assert(writes.some(w=>w.path==='/students'&&w.body.includes('HS02')));
 await page.locator('[data-view="classes"]').click();await page.locator('#class-create-button').click();await page.locator('#class-code').fill('10B');await page.locator('#class-name').fill('Lớp 10B');await page.locator('#class-editor-form button[type="submit"]').click();await page.waitForTimeout(200);assert(writes.some(w=>w.path==='/classes'&&JSON.parse(w.body).capacity===50));
 await page.locator('[data-view="uniform"]').click();await page.locator('#uniform-review-table button').click();assert.equal(await page.locator('#uniform-final-status').inputValue(),'NON_COMPLIANT','pending review starts with explicit violation choice');const uniformWritesBefore=writes.filter(w=>w.path==='/attendance/a1/uniform').length;await page.locator('#uniform-form button[type="submit"]').click();await page.waitForTimeout(100);assert((await page.locator('#uniform-dialog .dialog-error').textContent()).includes('lý do'));assert.equal(writes.filter(w=>w.path==='/attendance/a1/uniform').length,uniformWritesBefore,'missing violation reason must prevent write');await page.locator('#uniform-observed').selectOption('SHIRT');await page.locator('#uniform-final-status').selectOption('COMPLIANT');await page.locator('#uniform-form button[type="submit"]').click();await page.waitForTimeout(300);assert(writes.some(w=>w.path==='/attendance/a1/uniform'&&JSON.parse(w.body).uniform_status==='COMPLIANT'));
 await page.locator('#camera-button').click();await page.waitForTimeout(1200);assert(scans.some(s=>s.mode==='UNIFORM_ONLY'));
 await page.locator('[data-view="uniform-samples"]').click();await page.waitForTimeout(200);assert.equal(await page.locator('#uniform-profile-select option').count(),1);

 const png=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=1920;c.height=1080;c.getContext('2d').fillRect(0,0,1920,1080);return c.toDataURL('image/png').split(',')[1];});
 await page.locator('#uniform-sample-file').setInputFiles({name:'portrait1920.png',mimeType:'image/png',buffer:Buffer.from(png,'base64')});
 await page.waitForFunction(()=>document.querySelector('#uniform-crop-canvas').width===600&&document.querySelector('#uniform-crop-canvas').height===338);
 await page.locator('#uniform-crop-canvas').scrollIntoViewIfNeeded();const box=await page.locator('#uniform-crop-canvas').boundingBox();
 await page.mouse.move(box.x+box.width*.25,box.y+box.height*.4);await page.mouse.down();await page.mouse.move(box.x+box.width*.75,box.y+box.height*.9);await page.mouse.up();
 await page.locator('#uniform-capture-group').fill('group-01');uniformRejectReason='UNIFORM_NO_FACE';
 await page.locator('#uniform-sample-form button[type="submit"]').click();await page.waitForTimeout(200);
 const cropError=await page.locator('#uniform-sample-form .dialog-error').textContent();
 assert(cropError.includes('khuôn mặt')&&!cropError.includes('2 MiB'),'face context rejection must not be shown as a size limit: '+cropError);
 uniformRejectReason=null;await page.locator('#uniform-sample-form button[type="submit"]').click();await page.waitForTimeout(200);
 const cropWrite=writes.find(w=>w.path==='/classes/c1/uniform-samples'&&w.method==='POST');assert(cropWrite,'crop upload submitted');
 const match=cropWrite.body.match(/name="roi"\r\n\r\n([^\r]+)/);assert(match);const roi=JSON.parse(match[1]);assert(Math.abs(roi[0]-240)<=1&&Math.abs(roi[1]-216)<=1&&Math.abs(roi[2]-480)<=1&&Math.abs(roi[3]-270)<=1,'1920 source maps to 960 decoder ROI: '+roi);
 const large=await page.evaluate(()=>{
  const tile=document.createElement('canvas');tile.width=640;tile.height=480;const t=tile.getContext('2d');
  const pixels=t.createImageData(640,480);let seed=19;
  for(let i=0;i<pixels.data.length;i+=4){seed=(1664525*seed+1013904223)>>>0;pixels.data[i]=seed&255;pixels.data[i+1]=(seed>>>8)&255;pixels.data[i+2]=(seed>>>16)&255;pixels.data[i+3]=255;}
  t.putImageData(pixels,0,0);const c=document.createElement('canvas');c.width=8000;c.height=6000;
  const ctx=c.getContext('2d');for(let y=0;y<6000;y+=480)for(let x=0;x<8000;x+=640)ctx.drawImage(tile,x,y);
  return c.toDataURL('image/jpeg',.65).split(',')[1];
 });
 const original=Buffer.from(large,'base64');assert(original.length>2*1048576&&original.length<=32*1048576);
 await page.locator('#uniform-sample-file').setInputFiles({name:'camera48mp.jpg',mimeType:'image/jpeg',buffer:original});
 await page.waitForFunction(()=>document.querySelector('#uniform-crop-status').textContent.includes('Đã tối ưu'),{},{timeout:30000});
 await page.locator('#uniform-crop-canvas').scrollIntoViewIfNeeded();const largeBox=await page.locator('#uniform-crop-canvas').boundingBox();
 await page.mouse.move(largeBox.x+largeBox.width*.25,largeBox.y+largeBox.height*.4);await page.mouse.down();await page.mouse.move(largeBox.x+largeBox.width*.75,largeBox.y+largeBox.height*.9);await page.mouse.up();
 await page.locator('#uniform-capture-group').fill('camera-48mp');await page.locator('#uniform-sample-form button[type="submit"]').click();await page.waitForTimeout(250);
 const largeWrite=writes.filter(w=>w.path==='/classes/c1/uniform-samples'&&w.method==='POST').at(-1);
 assert(largeWrite.body.includes('camera-48mp'));assert(Buffer.byteLength(largeWrite.body,'latin1')<2*1048576,'optimized uniform multipart fits server budget');
 const largeRoi=JSON.parse(largeWrite.body.match(/name="roi"\r\n\r\n([^\r]+)/)[1]);
 assert.deepEqual(largeRoi,[240,288,480,360],'48 MP optimized source preserves decoder ROI coordinates');
 console.log(JSON.stringify({uniform48mpOriginalBytes:original.length,optimizedMultipartBytes:Buffer.byteLength(largeWrite.body,'latin1'),roi:largeRoi}));
 role='HOMEROOM_TEACHER';await page.reload();await page.waitForTimeout(400);assert(await page.locator('[data-view="uniform-samples"]').isHidden());await page.locator('[data-view="students"]').click();assert(await page.locator('#student-create-button').isVisible());await page.locator('#student-create-button').click();assert(await page.locator('#student-class').isDisabled());await page.locator('#student-code').fill('HS03');await page.locator('#student-name').fill('Lê Cường');await page.locator('#student-editor-form button[type="submit"]').click();await page.waitForTimeout(200);assert(writes.some(w=>w.path==='/students'&&w.body.includes('HS03')));assert(await page.locator('#students-table').getByText('Lưu trữ',{exact:true}).isVisible());await page.locator('#session-select').selectOption('q0');await page.waitForTimeout(150);page.once('dialog',d=>d.accept());await page.locator('#students-table').getByText('Lưu trữ',{exact:true}).click();await page.waitForTimeout(200);assert(writes.some(w=>w.path==='/students/s1'&&w.method==='DELETE'&&JSON.parse(w.body).expected_version===1));assert.equal(await page.locator('#session-select').inputValue(),'q0','archive refresh preserves selected historical session');await page.locator('[data-view="classes"]').click();assert((await page.locator('#classes-table').textContent()).includes('0 / 50'),'archive updates live class count');await page.locator('[data-view="students"]').click();page.once('dialog',d=>d.accept());await page.locator('#students-table').getByText('Khôi phục',{exact:true}).click();await page.waitForTimeout(200);assert(writes.some(w=>w.path==='/students/s1'&&w.method==='PATCH'&&JSON.parse(w.body).active===true));assert.equal(await page.locator('#session-select').inputValue(),'q0','restore refresh preserves historical session');await page.locator('[data-view="classes"]').click();assert((await page.locator('#classes-table').textContent()).includes('1 / 50'),'restore updates live class count');
 assert.deepEqual(errors,[]);console.log(JSON.stringify({passed:true,automaticRequests:scans.length,checks:['camera pair multipart/idempotency','5s success hold and blur receipt preservation','navigation stop','student create','class capacity','uniform correction','uniform-only camera','role controls and own-class create/archive','1920x1080 garment ROI','no page errors']}));
 await browser.close();
})().catch(async e=>{console.error(e);await browser?.close();process.exitCode=1});
