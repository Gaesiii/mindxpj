/* Camera cadence and limits, shared by attendance and uniform review. */
'use strict';
((root)=>{
  function validatePair(files) {
    if(files.length!==2)throw new Error('Chọn đúng 2 ảnh khác nhau, chụp cách nhau một chút.');
    if(files.some(f=>f.size>1048576)||files.reduce((n,f)=>n+f.size,0)>2097152)throw new Error('Mỗi ảnh tối đa 1 MiB, tổng tối đa 2 MiB.');
    if(files.some(f=>!['image/jpeg','image/png','image/webp'].includes(f.type)))throw new Error('Chọn ảnh JPEG, PNG hoặc WebP.');
  }
  function retryDelay(header,failures=0) {
    const seconds=Number(header);
    const date=Date.parse(header);
    return Math.max(4000,Number.isFinite(seconds)&&seconds>0?seconds*1000:Number.isFinite(date)?date-Date.now():Math.min(60000,4000*2**failures));
  }
  function createLoop(operation,allowed,interval=4000) {
    let generation=0,timer=null,running=false;
    const stop=()=>{generation++;clearTimeout(timer);timer=null;};
    const start=()=>{
      stop();const token=generation;
      async function tick(){
        if(token!==generation||!allowed())return;
        if(running){timer=setTimeout(tick,interval);return;}
        running=true;const started=Date.now();let delay=interval;
        try {delay=Math.max(interval,await operation()||interval);} catch {delay=interval*2;}
        finally {running=false;if(token===generation&&allowed())timer=setTimeout(tick,Math.max(0,delay-(Date.now()-started)));}
      }
      timer=setTimeout(tick,0);
    };
    return {start,stop};
  }
  function createAttendanceGate(hold=5000) {
    let student=null,until=0,emptyAt=null;
    return {
      remaining:(now=Date.now())=>Math.max(0,until-now),
      reset(){student=null;until=0;emptyAt=null;},
      observe(result,now=Date.now()) {
        if(result.student_id&&result.attendance&&result.attendance.status!=='PRESENT'){
          this.reset();return 'ready';
        }
        const success=['RECORDED','ALREADY_RECORDED'].includes(result.outcome)&&result.attendance?.status==='PRESENT'&&result.student_id;
        if(success&&result.student_id!==student){student=result.student_id;until=now+hold;emptyAt=null;return 'saved';}
        if(!student)return 'ready';
        // Unknown identity, blur and multiple faces are not evidence of departure.
        if(now>=until&&result.reason==='NO_FACE'){
          if(emptyAt!==null&&now-emptyAt>=1000){this.reset();return 'ready';}
          emptyAt=now;
        }else emptyAt=null;
        return 'waiting';
      }
    };
  }
  const api={validatePair,retryDelay,createLoop,createAttendanceGate};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MindXCamera=api;
})(typeof window==='undefined'?globalThis:window);
