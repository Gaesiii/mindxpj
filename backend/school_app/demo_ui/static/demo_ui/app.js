/* Local staff UI. Authorization and all business decisions remain in Django. */
'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const state = {user:null, classes:[], students:[], sessions:[], roster:[], session:null,
    classId:'', epoch:0, reportEpoch:0, stream:null, frame:null, previewUrl:null,
    scan:null, analysis:null, analyzing:false, view:'dashboard', sampleCounts:new Map(),
    writes:new Map(), reportFilters:null, manual:null, uniform:null, enroll:null, authEpoch:0};
  const labels = {MORNING:'Buổi sáng',AFTERNOON:'Buổi chiều',PLANNED:'Chưa mở',OPEN:'Đang điểm danh',CLOSED:'Đã chốt',
    PRESENT:'Có mặt',ABSENT:'Vắng',UNMARKED:'Chưa ghi nhận',COMPLIANT:'Đạt',NON_COMPLIANT:'Không đạt',
    NOT_CHECKED:'Chưa kiểm tra',NOT_APPLICABLE:'—',SHIRT:'Sơ mi',SPORTS:'Thể dục',OTHER:'Loại khác',UNKNOWN:'Chưa rõ',
    VISION:'Nhận diện',MANUAL:'Thủ công',QR:'QR lịch sử',ON_TIME:'Đúng giờ',LATE:'Đi muộn'};
  const headings = {
    dashboard:['Tổng quan','Một ngày học mới, bắt đầu từ đây.','Cùng theo dõi sự hiện diện và nề nếp của lớp.'],
    attendance:['Điểm danh','Ghi nhận từng học sinh đến lớp.','Chọn buổi học, đối chiếu và xác nhận sự có mặt.'],
    students:['Học sinh','Những gương mặt của lớp học.','Đăng ký mẫu rõ mặt để hỗ trợ nhận diện chính xác hơn.'],
    reports:['Báo cáo','Một góc nhìn rõ ràng về mỗi buổi học.','Xem điểm danh, đồng phục và xuất dữ liệu theo phạm vi lớp.']};
  const messages = {
    INVALID_CREDENTIALS:'Tên đăng nhập hoặc mật khẩu chưa đúng.',UNAUTHENTICATED:'Phiên đăng nhập đã hết. Vui lòng đăng nhập lại.',
    NO_FACE:'Chưa tìm thấy khuôn mặt. Chụp rõ mặt hơn hoặc ghi nhận thủ công.',MULTIPLE_FACES:'Có nhiều khuôn mặt. Chỉ để một người trong ảnh.',
    BLURRY_FACE:'Ảnh khuôn mặt bị mờ. Giữ máy ổn định và chụp lại.',FACE_TOO_SMALL:'Khuôn mặt còn nhỏ. Hãy đứng gần camera hơn.',
    INVALID_IMAGE:'Ảnh chưa hợp lệ. Dùng JPEG, PNG hoặc WebP, tối đa 2 MiB và 4 triệu pixel.',
    SESSION_TIME:'Đang ngoài khung giờ điểm danh. Kiểm tra giờ buổi học hoặc dùng ghi nhận thủ công.',
    SESSION_DATE:'Buổi học không thuộc ngày hôm nay. Hãy chọn buổi hôm nay hoặc ghi nhận thủ công.',
    SESSION_CLOSED:'Buổi học chưa mở hoặc đã chốt. Hãy chọn buổi đang mở.',
    SCAN_NOT_PENDING:'Kết quả đã hết hạn hoặc được xử lý. Hãy chụp và phân tích lại.',
    VERSION_CONFLICT:'Dữ liệu vừa thay đổi. Làm mới danh sách trước khi thử lại.',
    ATTENDANCE_CHANGED:'Điểm danh đã thay đổi. Làm mới danh sách để kiểm tra.',
    ENROLLMENT_CHANGED:'Mẫu nhận diện đã thay đổi. Hãy quét lại.',ROSTER_CHANGED:'Học sinh không còn thuộc lớp đang điểm danh.',
    RATE_LIMITED:'Thao tác quá nhanh. Vui lòng đợi rồi thử lại.',FORBIDDEN:'Tài khoản không có quyền thực hiện thao tác này.',
    NOT_FOUND:'Không tìm thấy dữ liệu hoặc dữ liệu nằm ngoài lớp bạn quản lý.',
    IDEMPOTENCY_CONFLICT:'Yêu cầu trước có nội dung khác. Làm mới rồi thao tác lại.',
    DATABASE_BUSY:'Dữ liệu đang được xử lý. Thử lại để kiểm tra cùng yêu cầu.',
    NO_ENROLLMENT:'Lớp chưa có mẫu nhận diện phù hợp. Đăng ký mẫu ở mục Học sinh.',
    REENROLLMENT_REQUIRED:'Mẫu nhận diện cũ cần đăng ký lại. Vào Học sinh → Quản lý mẫu, chọn lại 3–10 ảnh rồi lưu.',
    VISION_UNAVAILABLE:'Chưa sẵn sàng bộ nhận diện. Liên hệ người quản lý demo để kiểm tra model.',
    VISION_DATA_ERROR:'Mẫu nhận diện không còn hợp lệ. Đăng ký lại mẫu ở mục Học sinh.',
    UNKNOWN_FACE:'Chưa nhận diện được học sinh. Chụp lại hoặc ghi nhận thủ công.',
    AMBIGUOUS_FACE:'Kết quả gần giống nhiều học sinh. Chụp lại hoặc đối chiếu thủ công.'};
  function text(tag, value, cls='') { const node=document.createElement(tag); node.textContent=value ?? ''; if(cls) node.className=cls; return node; }
  function localParts(value=new Date()) { return Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(value).filter(p=>p.type!=='literal').map(p=>[p.type,p.value])); }
  function localDate(value=new Date()) {const p=localParts(value);return `${p.year}-${p.month}-${p.day}`;}
  function localInput(value=new Date()) {const p=localParts(value);return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}:${p.second}`;}
  function displayDate(value) {if(!value)return '—';return value.split('-').reverse().join('/');}
  function displayTime(value) {return value ? new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit'}).format(new Date(value)) : '—';}
  const csrf = () => decodeURIComponent(document.cookie.split('; ').find(c=>c.startsWith('csrftoken='))?.slice(10) || '');
  function notify(message, error=false) { $('notice').textContent=message; $('notice').classList.toggle('error',error);$('notice').hidden=!message; }
  function errorText(error) {return messages[error.code] || error.message || 'Không thể thực hiện. Vui lòng thử lại.';}
  function formError(node,error) {node.textContent=errorText(error);node.hidden=false;}
  function setLoginError(message) {$('login-error').textContent=message;$('login-error').hidden=!message;}

  async function api(path,{method='GET',body,key,blob=false}={}) {
    const authEpoch=state.authEpoch;
    const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),45000);
    const headers={};if(method!=='GET')headers['X-CSRFToken']=csrf();
    if(key)headers['Idempotency-Key']=key;
    if(body!==undefined && !(body instanceof FormData)) {headers['Content-Type']='application/json';body=JSON.stringify(body);}
    try {
      const response=await fetch('/api/v1'+path,{method,body,headers,credentials:'same-origin',signal:controller.signal});
      // Await body consumption inside the same timeout and uncertainty boundary.
      if(response.ok) return await (blob ? response.blob() : response.json());
      const data=await response.json();
      const error=Object.assign(new Error(data.message),data,{status:response.status,uncertain:response.status>=500||data.code==='DATABASE_BUSY'});
      if(response.status===401 && authEpoch===state.authEpoch && !['/auth/login','/auth/me'].includes(path)) {resetClient();setLoginError(messages.UNAUTHENTICATED);}
      throw error;
    } catch(error) {
      if(error.status)throw error;
      throw Object.assign(new Error('Chưa nhận được phản hồi đầy đủ. Kiểm tra kết nối và thử lại cùng yêu cầu.'),{uncertain:true});
    } finally {clearTimeout(timer);}
  }
  async function write(path,method,body) {
    const signature=method+path+JSON.stringify(body);let key=state.writes.get(signature);
    if(!key){key=crypto.randomUUID();state.writes.set(signature,key);}
    try {const result=await api(path,{method,body,key});if(state.writes.get(signature)===key)state.writes.delete(signature);return result;}
    catch(error){if(!error.uncertain&&state.writes.get(signature)===key)state.writes.delete(signature);throw error;}
  }
  async function run(button,operation,errorNode=null) {
    const authEpoch=state.authEpoch;
    const context=contextStamp();
    if(button?.dataset.busy)return;
    if(button){button.dataset.busy='true';button.disabled=true;button.setAttribute('aria-busy','true');}
    if(errorNode)errorNode.hidden=true;
    try {await operation();}catch(error){
      const login=button?.closest('form')?.id==='login-form';
      if(!login && (authEpoch!==state.authEpoch || (errorNode&&!sameContext(context))))return;
      if(errorNode)formError(errorNode,error);else notify(errorText(error),true);
    }
    finally {if(button){delete button.dataset.busy;button.disabled=false;button.removeAttribute('aria-busy');}renderControls();}
  }
  function stopCamera() {
    state.stream?.getTracks().forEach(track=>track.stop());state.stream=null;
    $('camera-video').srcObject=null;$('camera-video').hidden=true;$('camera-guide').hidden=true;
    $('camera-status').textContent='Camera tắt';$('camera-empty').hidden=!!state.frame;$('camera-button').textContent='Bật camera';
    renderControls();
  }
  function clearCapture() {
    if(state.previewUrl)URL.revokeObjectURL(state.previewUrl);
    state.previewUrl=null;state.frame=null;state.analysis=null;
    $('capture-preview').removeAttribute('src');$('capture-preview').hidden=true;$('scan-upload').value='';
    $('camera-empty').hidden=!!state.stream;$('analyze-button').textContent='Phân tích ảnh';$('retry-analysis-button').hidden=true;
  }
  function clearProposal() {state.scan=null;$('confirm-scan-form').hidden=true;$('identity-confirmed').checked=false;$('candidate-reason').value='';for(const id of ['candidate-name','candidate-code','candidate-expiry','uniform-hint'])$(id).textContent='';$('candidate-uniform').value='';}
  function closeDialogs() {document.querySelectorAll('dialog[open]').forEach(d=>d.close());}
  function resetClient() {
    state.epoch++;state.authEpoch++;state.reportEpoch++;stopCamera();clearCapture();clearProposal();closeDialogs();
    Object.assign(state,{user:null,classes:[],students:[],sessions:[],roster:[],session:null,classId:'',enroll:null,manual:null,uniform:null});
    state.writes.clear();state.sampleCounts.clear();clearReports();renderData();
    $('class-select').replaceChildren();$('session-select').replaceChildren();$('identity-name').textContent='';$('identity-role').textContent='';
    for(const id of ['enroll-student-name','enroll-metadata','manual-student-name','uniform-student-name','uniform-required'])$(id).textContent='';
    for(const id of ['enroll-files','manual-reason','manual-arrival','uniform-reason'])$(id).value='';
    $('workspace').hidden=true;$('login-screen').hidden=false;$('login-password').value='';notify('');
  }
  function setView(view) {
    if(!headings[view])return;
    if(view!=='attendance')stopCamera();state.view=view;
    document.querySelectorAll('.view').forEach(node=>node.hidden=node.id!=='view-'+view);
    document.querySelectorAll('[data-view]').forEach(node=>{node.classList.toggle('active',node.dataset.view===view);node.setAttribute('aria-current',node.dataset.view===view?'page':'false');});
    const [title,heading,description]=headings[view];$('page-title').textContent=title;$('view-heading').textContent=heading;$('view-description').textContent=description;
    if(view==='reports' && state.classId && !state.reportFilters)run(null,loadReports);
  }
  function options(select,items,getText,value,empty) {
    select.replaceChildren();if(!items.length){const opt=text('option',empty);opt.value='';select.append(opt);return;}
    for(const item of items){const opt=text('option',getText(item));opt.value=item.id;select.append(opt);}select.value=value||items[0].id;
  }
  async function enterWorkspace(user) {
    if(!['HOMEROOM_TEACHER','SUPERVISOR'].includes(user.role)) {
      await api('/auth/logout',{method:'POST',body:{}});resetClient();setLoginError('Giao diện dành cho GVCN và giám thị. Vui lòng dùng tài khoản nhân sự.');return;
    }
    state.authEpoch++;state.user=user;$('login-screen').hidden=true;$('workspace').hidden=false;$('login-password').value='';
    $('identity-name').textContent=user.username;$('identity-role').textContent=user.role==='SUPERVISOR'?'Giám thị':'Giáo viên chủ nhiệm';
    $('identity-avatar').textContent=user.role==='SUPERVISOR'?'GT':'GV';setLoginError('');
    const token=++state.epoch;const result=await api('/classes');if(token!==state.epoch)return;
    state.classes=result.items;options($('class-select'),result.items,c=>c.name,result.items[0]?.id,'Chưa có lớp được giao');
    setView('dashboard');await loadClass($('class-select').value);
  }
  async function loadClass(classId,preferredSession) {
    const token=++state.epoch;stopCamera();clearCapture();clearProposal();closeDialogs();clearReports();
    state.classId=classId;state.students=[];state.sessions=[];state.roster=[];state.session=null;renderData();
    options($('session-select'),[],()=>'',null,'Đang tải buổi học…');renderControls();
    if(!classId){options($('session-select'),[],()=>'',null,'Chưa có buổi học');return;}
    const query=new URLSearchParams({class_id:classId});
    const [students,sessions]=await Promise.all([api('/students?'+query),api('/sessions?'+query)]);
    if(token!==state.epoch)return;
    state.students=students.items;state.sessions=sessions.items.sort((a,b)=>b.school_date.localeCompare(a.school_date)||a.slot.localeCompare(b.slot));
    let selected=state.sessions.find(s=>s.id===preferredSession) || state.sessions.find(s=>s.school_date===localDate()&&s.status==='OPEN') || state.sessions.find(s=>s.school_date===localDate()) || state.sessions[0];
    options($('session-select'),state.sessions,s=>`${displayDate(s.school_date)} · ${labels[s.slot]} · ${labels[s.status]}`,selected?.id,'Chưa có buổi học');
    renderStudents();await loadSession(selected?.id||'');
  }
  async function loadSession(sessionId) {
    const token=++state.epoch;stopCamera();clearCapture();clearProposal();closeDialogs();state.roster=[];
    state.session=state.sessions.find(s=>s.id===sessionId)||null;renderData();
    if(!state.session)return;
    const [session,roster,queue]=await Promise.all([api('/sessions/'+sessionId),api(`/sessions/${sessionId}/roster`),api(`/sessions/${sessionId}/vision-scans`)]);
    if(token!==state.epoch)return;
    state.session=session;state.sessions=state.sessions.map(s=>s.id===sessionId?session:s);state.roster=roster.items;renderData();
    if(queue.items.length)showProposal(queue.items[0]);
  }
  async function refreshContext() {await loadClass(state.classId,state.session?.id);}
  function contextStamp() {return {epoch:state.epoch,authEpoch:state.authEpoch,classId:state.classId,sessionId:state.session?.id,view:state.view};}
  function sameScope(context) {return context.authEpoch===state.authEpoch&&context.classId===state.classId&&context.sessionId===state.session?.id&&context.view===state.view;}
  function sameContext(context) {return context.epoch===state.epoch&&sameScope(context);}
  async function mutateThenRefresh(operation,message) {
    const context=contextStamp();await operation();if(!sameContext(context))return;
    await refreshContext();if(sameScope(context))notify(message);
  }
  function inWindow() {const s=state.session;const now=Date.now();return s?.status==='OPEN' && s.school_date===localDate() && now>=Date.parse(s.start_at)&&now<=Date.parse(s.close_at);}
  function renderControls() {
    const s=state.session;const staff=!!state.user;const available=inWindow();
    const update=(id,disabled)=>{const node=$(id);if(!node.dataset.busy)node.disabled=disabled;};
    update('rule-button',!staff||!state.classId);update('create-session-button',!staff||!state.classId);
    update('open-session-button',s?.status!=='PLANNED');update('close-session-button',s?.status!=='OPEN');
    update('camera-button',!available||state.analyzing);update('capture-button',!available||!state.stream||state.analyzing);
    update('analyze-button',!available||!state.frame||state.analyzing);
    $('scan-upload').disabled=!available||state.analyzing;
    update('retry-analysis-button',!available||state.analyzing);
    $('export-xlsx').disabled=!state.reportFilters;$('export-csv').disabled=!state.reportFilters;
    const submit=$('confirm-scan-form').querySelector('[type=submit]');
    if(!submit.dataset.busy)submit.disabled=!available||!state.scan||Date.parse(state.scan.expires_at)<=Date.now();
    update('reject-scan-button',!available||!state.scan||Date.parse(state.scan.expires_at)<=Date.now());
    if(state.scan) {
      const left=Math.ceil((Date.parse(state.scan.expires_at)-Date.now())/1000);
      $('candidate-expiry').textContent=left>0?`Chờ xác minh · còn ${left} giây`:'Kết quả đã hết hạn. Hãy chụp và phân tích lại.';
    }
  }
  function badge(value,type) {const tones={PRESENT:'green',ABSENT:'red',UNMARKED:'neutral',COMPLIANT:'green',NON_COMPLIANT:'orange',NOT_CHECKED:'neutral',NOT_APPLICABLE:'neutral',OPEN:'green',CLOSED:'blue',PLANNED:'neutral'};return text('span',labels[value]||value||'—','badge '+(type||tones[value]||'neutral'));}
  function emptyRows(target,columns,message) {const cell=text('td',message,'empty-cell');cell.colSpan=columns;const row=document.createElement('tr');row.append(cell);$(target).replaceChildren(row);}
  function studentCell(name,code) {const cell=document.createElement('td');const wrap=text('div','','student-cell');const initials=String(name).trim().split(/\s+/).slice(-2).map(p=>p[0]||'').join('').toUpperCase();wrap.append(text('span',initials||'HS','avatar'));const body=document.createElement('div');body.append(text('strong',name),text('small',code));wrap.append(body);cell.append(wrap);return cell;}
  function valueCell(value) {const td=document.createElement('td');td.append(value instanceof Node?value:document.createTextNode(value??'—'));return td;}
  function renderOverview() {
    const roster=state.roster,s=state.session;const marked=s&&s.status!=='PLANNED';
    const count=status=>roster.filter(r=>r.attendance.status===status).length;
    const present=count('PRESENT'),absent=count('ABSENT'),unmarked=count('UNMARKED'),late=roster.filter(r=>r.attendance.arrival_status==='LATE').length;
    for(const [id,value] of [['expected',roster.length],['present',present],['late',late],['unmarked',unmarked+absent]])$('stat-'+id).textContent=marked?value:'—';
    $('stat-present-note').textContent=marked?`${roster.length?Math.round(present/roster.length*100):0}% sĩ số buổi học`:'Chờ mở buổi học';
    $('stat-unmarked-note').textContent=marked?`${unmarked} chưa ghi nhận · ${absent} vắng`:'Chốt buổi để xác định vắng';
    $('progress-label').textContent=marked?`${present}/${roster.length} học sinh đã có mặt`:'Chưa có dữ liệu';
    $('progress-bar').style.width=roster.length?`${present/roster.length*100}%`:'0%';
    const overview=$('session-overview');overview.replaceChildren();
    if(!s){overview.append(text('p','Chọn hoặc tạo một buổi học để bắt đầu.','muted'));return;}
    overview.append(text('h3',`${labels[s.slot]} · ${displayDate(s.school_date)}`));
    const classroom=state.classes.find(c=>c.id===state.classId);overview.append(text('p',classroom?.name||''));
    overview.append(text('p',s.start_at?`${displayTime(s.start_at)} – ${displayTime(s.close_at)} · ${labels[s.required_uniform_snapshot]}`:'Chưa mở buổi · Chờ tạo danh sách'));overview.append(badge(s.status));
  }
  function renderRoster() {
    const search=$('roster-search').value.trim().toLocaleLowerCase('vi');
    const rows=state.roster.filter(r=>(r.full_name_snapshot+' '+r.student_code_snapshot).toLocaleLowerCase('vi').includes(search));
    $('roster-count').textContent=state.roster.length;
    if(!rows.length)emptyRows('attendance-roster',4,state.session?.status==='PLANNED'?'Mở buổi để tạo danh sách học sinh.':'Chưa có học sinh trong danh sách này.');
    else {
      $('attendance-roster').replaceChildren();
      for(const row of rows) {
        const tr=document.createElement('tr'),attendance=row.attendance;
        tr.append(studentCell(row.full_name_snapshot,row.student_code_snapshot),valueCell(badge(attendance.status)),valueCell(badge(attendance.uniform_status)));
        const actions=text('div','','row-actions');const manual=text('button','Ghi nhận','text-button');manual.type='button';
        manual.disabled=state.session.status!=='OPEN'&&!(state.session.status==='CLOSED'&&state.user?.role==='SUPERVISOR');
        manual.addEventListener('click',()=>openManual(row));actions.append(manual);
        if(attendance.status==='PRESENT') {const uniform=text('button','Đồng phục','text-button');uniform.type='button';uniform.disabled=manual.disabled;uniform.addEventListener('click',()=>openUniform(row));actions.append(uniform);}
        tr.append(valueCell(actions));$('attendance-roster').append(tr);
      }
    }
    const recent=state.roster.filter(r=>r.attendance.status==='PRESENT').slice(0,5);
    if(!recent.length)emptyRows('dashboard-roster',5,'Chưa có học sinh được xác nhận có mặt trong buổi.');
    else {$('dashboard-roster').replaceChildren();for(const row of recent){const tr=document.createElement('tr');tr.append(studentCell(row.full_name_snapshot,row.student_code_snapshot),valueCell(row.student_code_snapshot),valueCell(badge(row.attendance.status)),valueCell(badge(row.attendance.uniform_status)),valueCell(displayTime(row.attendance.arrived_at)));$('dashboard-roster').append(tr);}}
  }
  function renderStudents() {
    $('student-count').textContent=state.students.length;const search=$('student-search').value.trim().toLocaleLowerCase('vi');
    const rows=state.students.filter(s=>(s.full_name+' '+s.student_code).toLocaleLowerCase('vi').includes(search));
    if(!rows.length){emptyRows('students-table',5,'Chưa có học sinh phù hợp trong lớp.');return;}
    $('students-table').replaceChildren();
    for(const student of rows) {const tr=document.createElement('tr');const count=state.sampleCounts.get(student.id);const button=text('button','Quản lý mẫu ↗','text-button');button.type='button';button.addEventListener('click',()=>run(button,()=>openEnrollment(student)));tr.append(studentCell(student.full_name,student.student_code),valueCell(student.student_code),valueCell(badge(student.active?'Đang học':'Ngừng hoạt động',student.active?'green':'neutral')),valueCell(count===undefined?'Xem để kiểm tra':`${count} mẫu`),valueCell(button));$('students-table').append(tr);}
  }
  function renderData() {
    const s=state.session;$('context-status').replaceWith(Object.assign(badge(s?.status||'Chưa chọn buổi'),{id:'context-status'}));
    $('session-time-note').textContent=s?.start_at?`${displayDate(s.school_date)} · ${displayTime(s.start_at)} – ${displayTime(s.close_at)} · Yêu cầu ${labels[s.required_uniform_snapshot]}${inWindow()?'':' · Ngoài giờ hoặc buổi chưa mở'}`:'Chọn và mở buổi học để bắt đầu.';
    renderOverview();renderRoster();renderStudents();renderControls();
  }
  function clearReports() {state.reportEpoch++;state.reportFilters=null;$('report-summary').replaceChildren();emptyRows('report-table',6,'Chọn khoảng ngày và xem báo cáo của lớp.');$('report-caption').textContent='Chọn khoảng ngày để xem dữ liệu của lớp.';renderControls();}
  async function loadReports() {
    if(!state.classId)throw new Error('Chọn lớp trước khi xem báo cáo.');
    const from=$('report-from').value,to=$('report-to').value;if(!from||!to||from>to)throw new Error('Chọn khoảng ngày hợp lệ.');
    const token=++state.reportEpoch;const filters={date_from:from,date_to:to,class_id:state.classId};const query=new URLSearchParams(filters);
    const [details,summary]=await Promise.all([api('/reports/attendance?'+query),api('/reports/summary?'+query)]);
    if(token!==state.reportEpoch)return;state.reportFilters=filters;
    $('report-summary').replaceChildren();for(const [key,label] of [['expected','Tổng lượt học sinh'],['present','Có mặt'],['absent','Vắng'],['non_compliant','Đồng phục không đạt']]){const box=text('div',label);box.append(text('strong',summary[key]));$('report-summary').append(box);}
    if(!details.items.length)emptyRows('report-table',6,'Chưa có dữ liệu trong khoảng ngày này.');
    else {$('report-table').replaceChildren();for(const row of details.items){const tr=document.createElement('tr');tr.append(valueCell(`${displayDate(row.school_date)} · ${labels[row.slot]}`),studentCell(row.full_name_snapshot,row.student_code_snapshot),valueCell(badge(row.status)),valueCell(displayTime(row.arrived_at)),valueCell(badge(row.uniform_status)),valueCell(labels[row.source]||'—'));$('report-table').append(tr);}}
    $('report-caption').textContent=`${details.items.length} lượt học sinh · ${displayDate(from)} – ${displayDate(to)}`;renderControls();
  }
  async function download(kind) {
    if(!state.reportFilters)return;const token=state.reportEpoch;const filters={...state.reportFilters,format:kind};
    const blob=await api('/reports/export?'+new URLSearchParams(filters),{blob:true});if(token!==state.reportEpoch)return;
    const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=`diem-danh-${filters.date_from}-${filters.date_to}.${kind}`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),5000);
  }
  function showProposal(scan) {
    state.scan=scan;$('candidate-name').textContent=scan.full_name_snapshot;$('candidate-code').textContent=scan.student_code_snapshot;
    // A heuristic must not silently become a completed staff uniform check.
    $('candidate-uniform').value='';
    $('uniform-hint').textContent=`Gợi ý màu áo: ${labels[scan.observed_uniform]}. Hãy tự kiểm tra trang phục trước khi chọn.`;
    $('identity-confirmed').checked=false;$('candidate-reason').value='';$('confirm-scan-form').hidden=false;renderControls();
  }
  function uniformPayload(observed,reason) {
    if(!observed)return null;
    const compliant=observed===state.session.required_uniform_snapshot;
    if((!compliant||observed==='OTHER')&&!reason.trim())throw new Error('Nhập lý do khi đồng phục không đạt hoặc chọn loại khác.');
    return {observed_uniform:observed,uniform_status:compliant?'COMPLIANT':'NON_COMPLIANT',
      ...(!compliant?{reason:reason.trim()}:{}),...(observed==='OTHER'?{note:reason.trim()}: {})};
  }
  function validateFiles(files,min,max,total) {
    if(files.length<min||files.length>max)throw new Error(`Chọn ${min===max?min:`${min}–${max}`} ảnh.`);
    if(files.some(f=>f.size>2*1024*1024)||files.reduce((n,f)=>n+f.size,0)>total)throw new Error(`Mỗi ảnh tối đa 2 MiB; tổng bộ mẫu tối đa ${total/(1024*1024)} MiB.`);
    if(files.some(f=>!['image/png','image/jpeg','image/webp'].includes(f.type)))throw new Error('Chọn ảnh JPEG, PNG hoặc WebP.');
  }
  function useFrame(file) {
    validateFiles([file],1,1,2*1024*1024);clearCapture();clearProposal();state.frame=file;state.analysis={file,key:crypto.randomUUID()};
    state.previewUrl=URL.createObjectURL(file);$('capture-preview').src=state.previewUrl;$('capture-preview').hidden=false;$('camera-video').hidden=true;$('camera-guide').hidden=true;$('camera-empty').hidden=true;
    $('scan-feedback').textContent='Ảnh đã sẵn sàng. Phân tích để xem gợi ý nhận diện.';renderControls();
  }
  async function toggleCamera() {
    if(state.stream){stopCamera();return;}
    if(!navigator.mediaDevices?.getUserMedia)throw new Error('Trình duyệt chưa hỗ trợ camera. Dùng localhost hoặc tải ảnh từ thiết bị.');
    const token=state.epoch;let stream;
    try {stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:{ideal:640},height:{ideal:480}},audio:false});}
    catch {throw new Error('Không mở được camera. Cho phép truy cập camera trong trình duyệt hoặc tải ảnh từ thiết bị.');}
    if(token!==state.epoch||state.view!=='attendance'||!state.user){stream.getTracks().forEach(t=>t.stop());return;}
    clearCapture();clearProposal();state.stream=stream;$('camera-video').srcObject=stream;
    try {await $('camera-video').play();} catch {stopCamera();throw new Error('Không phát được hình từ camera. Hãy tải ảnh hoặc mở camera lại.');}
    $('camera-video').hidden=false;$('camera-empty').hidden=true;$('camera-guide').hidden=false;$('camera-status').textContent='Camera đang bật';$('camera-button').textContent='Tắt camera';
    stream.getVideoTracks()[0].addEventListener('ended',()=>{if(state.stream===stream)stopCamera();});renderControls();
  }
  async function capture() {
    const token=state.epoch,stream=state.stream;
    const video=$('camera-video');if(!video.videoWidth)throw new Error('Camera chưa sẵn sàng. Đợi một chút rồi chụp lại.');
    const canvas=document.createElement('canvas');const ratio=Math.min(960/video.videoWidth,960/video.videoHeight,1);canvas.width=Math.round(video.videoWidth*ratio);canvas.height=Math.round(video.videoHeight*ratio);canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);
    const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.9));if(!blob)throw new Error('Chưa chụp được ảnh. Thử lại.');
    if(token!==state.epoch||state.stream!==stream||!state.user)return;
    useFrame(new File([blob],'camera.jpg',{type:'image/jpeg'}));
  }
  async function analyze() {
    if(!state.frame||!state.session)return;
    const token=state.epoch;const request=state.analysis||{file:state.frame,key:crypto.randomUUID()};state.analysis=request;state.analyzing=true;renderControls();
    const form=new FormData();form.append('image',request.file);$('scan-feedback').textContent='Đang phân tích ảnh…';clearProposal();
    try {
      const result=await api(`/sessions/${state.session.id}/vision-scans`,{method:'POST',body:form,key:request.key});if(token!==state.epoch)return;
      $('retry-analysis-button').hidden=true;
      if(result.recognition==='CANDIDATE') {showProposal(result.scan);$('scan-feedback').textContent='Đã có ứng viên. Điểm danh chưa được lưu cho đến khi bạn xác nhận.';}
      else if(result.recognition==='ALREADY_MARKED') {$('scan-feedback').textContent='Học sinh đã được ghi nhận. Làm mới danh sách để xem kết quả.';}
      else {$('scan-feedback').textContent=messages[result.reason]||'Chưa nhận diện được học sinh. Chụp lại hoặc dùng ghi nhận thủ công.';}
      state.analysis=null;
    } catch(error) {
      if(token!==state.epoch)return;
      $('scan-feedback').textContent=errorText(error);$('retry-analysis-button').hidden=!error.uncertain;
      if(!error.uncertain)state.analysis=null;
      throw error;
    } finally {state.analyzing=false;renderControls();}
  }
  async function openEnrollment(student) {
    const token=state.epoch;const result=await api(`/students/${student.id}/face-samples`);if(token!==state.epoch)return;
    state.enroll=student;state.sampleCounts.set(student.id,result.usable_sample_count??result.sample_count);renderStudents();
    $('enroll-student-name').textContent=`${student.full_name} · ${student.student_code}`;
    $('enroll-metadata').textContent=result.requires_reenrollment
      ? `Đang lưu ${result.sample_count} mẫu cũ; cần đăng ký lại 3–10 ảnh để dùng bộ nhận diện mới. Chưa có đủ mẫu dùng được.`
      : `Đã đăng ký ${result.usable_sample_count??result.sample_count} mẫu dùng được. Bộ ảnh mới sẽ thay toàn bộ mẫu cũ.`;
    $('enroll-files').value='';$('enroll-dialog').querySelector('.dialog-error').hidden=true;$('enroll-dialog').showModal();
  }
  function openManual(row) {
    state.manual=structuredClone(row);$('manual-student-name').textContent=`${row.full_name_snapshot} · ${row.student_code_snapshot}`;
    $('manual-status').value=row.attendance.status==='ABSENT'?'ABSENT':'PRESENT';
    $('manual-arrival').value=row.attendance.arrived_at?localInput(new Date(row.attendance.arrived_at)):`${state.session.school_date}T${localInput().split('T')[1]}`;
    $('manual-arrival-label').hidden=$('manual-status').value==='ABSENT';$('manual-reason').value='';$('manual-dialog').querySelector('.dialog-error').hidden=true;$('manual-dialog').showModal();
  }
  function openUniform(row) {
    state.uniform=structuredClone(row);$('uniform-student-name').textContent=`${row.full_name_snapshot} · ${row.student_code_snapshot}`;
    $('uniform-required').textContent='Yêu cầu buổi học: '+labels[state.session.required_uniform_snapshot];$('uniform-observed').value=row.attendance.observed_uniform&&row.attendance.observed_uniform!=='UNKNOWN'?row.attendance.observed_uniform:state.session.required_uniform_snapshot;
    $('uniform-reason').value=row.attendance.uniform_reason||'';$('uniform-dialog').querySelector('.dialog-error').hidden=true;$('uniform-dialog').showModal();
  }
  const onClick=(id,fn)=>$(id).addEventListener('click',()=>run($(id),fn));
  const onSubmit=(id,fn)=>$(id).addEventListener('submit',event=>{event.preventDefault();run($(id).querySelector('[type=submit]'),fn,$(id).querySelector('.dialog-error')|| (id==='login-form'?$('login-error'):null));});

  document.querySelectorAll('[data-view],[data-goto]').forEach(button=>button.addEventListener('click',()=>setView(button.dataset.view||button.dataset.goto)));
  document.querySelectorAll('.dialog-close').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
  onSubmit('login-form',async()=>{const user=await api('/auth/login',{method:'POST',body:{username:$('login-username').value.trim(),password:$('login-password').value}});await enterWorkspace(user);});
  onClick('logout-button',async()=>{const authEpoch=state.authEpoch;await api('/auth/logout',{method:'POST',body:{}});if(authEpoch===state.authEpoch)resetClient();});
  onClick('refresh-button',async()=>{notify('');await refreshContext();if(state.view==='reports')await loadReports();});
  $('class-select').addEventListener('change',()=>run(null,()=>loadClass($('class-select').value)));
  $('session-select').addEventListener('change',()=>run(null,()=>loadSession($('session-select').value)));
  $('roster-search').addEventListener('input',renderRoster);$('student-search').addEventListener('input',renderStudents);
  onClick('create-session-button',async()=>{$('session-date').value=localDate();$('session-dialog').querySelector('.dialog-error').hidden=true;$('session-dialog').showModal();});
  onSubmit('session-form',async()=>{const context=contextStamp();const result=await api('/sessions',{method:'POST',body:{class_id:context.classId,school_date:$('session-date').value,slot:$('session-slot').value}});if(!sameContext(context))return;$('session-dialog').close();await loadClass(context.classId,result.id);if(context.authEpoch===state.authEpoch&&context.classId===state.classId)notify('Đã tạo buổi học. Mở buổi để bắt đầu điểm danh.');});
  onClick('rule-button',async()=>{const day=new Date(localDate()+'T12:00:00+07:00').getUTCDay();$('rule-weekday').value=(day+6)%7;$('rule-dialog').querySelector('.dialog-error').hidden=true;$('rule-dialog').showModal();});
  onSubmit('rule-form',async()=>{const context=contextStamp();const payload={weekday:Number($('rule-weekday').value),slot:$('rule-slot').value,start_time:$('rule-start').value+':00',close_time:$('rule-close').value+':00',grace_minutes:Number($('rule-grace').value),required_uniform:$('rule-uniform').value};const id=context.classId;const rules=await api(`/classes/${id}/schedule-rules`);const existing=rules.items.find(r=>r.weekday===payload.weekday&&r.slot===payload.slot);await api(existing?`/schedule-rules/${existing.id}`:`/classes/${id}/schedule-rules`,{method:existing?'PATCH':'POST',body:payload});if(!sameContext(context))return;$('rule-dialog').close();notify('Đã lưu lịch học. Buổi đã mở giữ nguyên quy định.');});
  onClick('open-session-button',async()=>{const s=state.session;await mutateThenRefresh(()=>api(`/sessions/${s.id}/open`,{method:'POST',body:{expected_version:s.version}}),'Buổi học đã mở. Danh sách học sinh đã sẵn sàng.');});
  onClick('close-session-button',async()=>{if(!confirm('Chốt buổi học? Học sinh chưa ghi nhận sẽ được tính là vắng.'))return;const s=state.session;await mutateThenRefresh(()=>api(`/sessions/${s.id}/close`,{method:'POST',body:{expected_version:s.version}}),'Đã chốt buổi học và cập nhật các học sinh vắng.');});
  onClick('camera-button',toggleCamera);onClick('capture-button',capture);onClick('analyze-button',analyze);onClick('retry-analysis-button',analyze);
  $('scan-upload').addEventListener('change',()=>run(null,async()=>{const file=$('scan-upload').files[0];if(file)useFrame(file);}));
  onSubmit('confirm-scan-form',async()=>{const scan=state.scan;if(!scan||!$('identity-confirmed').checked)throw new Error('Vui lòng xác nhận đúng học sinh.');const uniform=uniformPayload($('candidate-uniform').value,$('candidate-reason').value);await mutateThenRefresh(()=>write(`/vision-scans/${scan.id}/confirm`,'POST',{expected_scan_version:scan.version,expected_attendance_version:scan.expected_attendance_version,identity_confirmed:true,...(uniform?{uniform}:{})}),'Đã xác nhận có mặt và lưu kết quả điểm danh.');});
  onClick('reject-scan-button',async()=>{const scan=state.scan;if(!scan)return;const reason=prompt('Lý do từ chối kết quả nhận diện:');if(reason===null)return;if(!reason.trim())throw new Error('Nhập lý do từ chối.');await mutateThenRefresh(()=>write(`/vision-scans/${scan.id}/reject`,'POST',{expected_scan_version:scan.version,reason:reason.trim()}),'Đã từ chối kết quả. Có thể chụp lại hoặc ghi nhận thủ công.');});
  onSubmit('enroll-form',async()=>{const context=contextStamp(),student=state.enroll;if(!student)return;const files=[...$('enroll-files').files];validateFiles(files,3,10,Number(document.body.dataset.enrollmentLimit)||15*1024*1024);const form=new FormData();files.forEach(file=>form.append('images',file));const result=await api(`/students/${student.id}/face-samples`,{method:'POST',body:form});if(!sameContext(context)||state.enroll?.id!==student.id)return;state.sampleCounts.set(student.id,result.usable_sample_count??result.sample_count);$('enroll-dialog').close();$('enroll-files').value='';renderStudents();notify('Đã lưu bộ mẫu nhận diện riêng tư cho học sinh.');});
  onClick('delete-samples',async()=>{const context=contextStamp(),student=state.enroll;if(!student||!confirm('Xóa toàn bộ mẫu mặt của học sinh này? Kết quả quét chờ sẽ bị vô hiệu.'))return;await api(`/students/${student.id}/face-samples`,{method:'DELETE'});if(!sameContext(context)||state.enroll?.id!==student.id)return;state.sampleCounts.set(student.id,0);$('enroll-dialog').close();$('enroll-files').value='';renderStudents();clearProposal();notify('Đã xóa toàn bộ mẫu nhận diện.');});
  $('manual-status').addEventListener('change',()=>{$('manual-arrival-label').hidden=$('manual-status').value==='ABSENT';});
  onSubmit('manual-form',async()=>{const row=state.manual;if(!row)return;const status=$('manual-status').value;const reason=$('manual-reason').value.trim();const input=$('manual-arrival').value;if(status==='PRESENT'&&!input)throw new Error('Nhập thời gian đến.');await mutateThenRefresh(()=>write(`/attendance/${row.attendance.id}`,'PATCH',{expected_version:row.attendance.version,status,reason,...(status==='PRESENT'?{arrived_at:input+'+07:00'}:{absence_reason:reason})}),'Đã lưu điểm danh thủ công.');});
  onSubmit('uniform-form',async()=>{const row=state.uniform;if(!row)return;const payload=uniformPayload($('uniform-observed').value,$('uniform-reason').value);const body={expected_version:row.attendance.version,...payload,...(state.session.status==='CLOSED'?{reason:$('uniform-reason').value.trim()}:{})};await mutateThenRefresh(()=>write(`/attendance/${row.attendance.id}/uniform`,'PATCH',body),'Đã lưu kết quả kiểm tra đồng phục.');});
  onSubmit('report-form',loadReports);onClick('export-xlsx',()=>download('xlsx'));onClick('export-csv',()=>download('csv'));
  $('report-from').addEventListener('change',clearReports);$('report-to').addEventListener('change',clearReports);
  window.addEventListener('pagehide',stopCamera);document.addEventListener('visibilitychange',()=>{if(document.hidden)stopCamera();});
  $('today-label').textContent=new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',weekday:'long',day:'2-digit',month:'2-digit',year:'numeric'}).format(new Date());
  $('report-from').value=localDate();$('report-to').value=localDate();renderData();clearReports();
  setInterval(renderControls,1000);
  api('/auth/me').then(enterWorkspace).catch(error=>{if(error.status!==401)setLoginError(errorText(error));});
})();
