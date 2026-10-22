(() => {
  'use strict';
  const $=id=>document.getElementById(id);
  const names={KV_UNIFORM:'Đồng phục KV',NON_UNIFORM:'Trang phục khác',UNKNOWN:'Chưa đủ tin cậy'};
  let stream=null, epoch=0, busy=false, ready=false, previewURL=null, activeRequest=null;
  const error=message=>{$('lab-error').textContent=message;$('lab-error').hidden=!message;};
  async function api(path,options={}){
    const response=await fetch('/api/v1/demo/uniform'+path,{credentials:'same-origin',...options});
    const data=await response.json();
    if(!response.ok) throw new Error(response.status===401?'Hãy đăng nhập ở trang điểm danh chính rồi quay lại đây.':response.status===403?'Tài khoản không có quyền xem demo.':data.message||'Chưa xử lý được. Thử lại sau.');
    return data;
  }
  function stop(){epoch++;if(activeRequest)activeRequest.abort();if(stream)stream.getTracks().forEach(t=>t.stop());stream=null;$('lab-video').srcObject=null;$('camera-box').hidden=true;$('lab-stop').disabled=true;$('lab-camera').disabled=!ready;}
  async function idle(){while(busy)await new Promise(resolve=>setTimeout(resolve,25));}
  function preview(blob){if(previewURL)URL.revokeObjectURL(previewURL);previewURL=URL.createObjectURL(blob);$('lab-preview').src=previewURL;$('lab-preview').hidden=false;}
  async function classify(blob,source,expected,token=epoch){
    if(busy)return;busy=true;error('');
    try{
      if(blob.size>2*1024*1024)throw new Error('Ảnh phải ≤2 MiB.');
      preview(blob);$('lab-decision').textContent='Đang nhận diện…';
      const form=new FormData();form.append('image',blob,'garment.png');
      activeRequest=new AbortController();
      const data=await api('/predict',{method:'POST',signal:activeRequest.signal,headers:{'X-CSRFToken':document.querySelector('[name=csrfmiddlewaretoken]').value},body:form});
      if(token!==epoch)return;
      $('lab-decision').textContent=names[data.decision];
      $('lab-result').className='result '+(data.decision==='KV_UNIFORM'?'good':data.decision==='NON_UNIFORM'?'other':'unknown');
      $('lab-confidence').textContent=data.confidence===null?'Cần ảnh vùng áo rõ hơn.':`Confidence model: ${(data.confidence*100).toFixed(1)}% · ngưỡng 95%`;
      $('lab-timing').textContent=data.inference_ms===null?'':`Xử lý model và chuẩn bị đầu vào: ${data.inference_ms} ms`;
      $('lab-source').textContent=source+(expected?` · Kỳ vọng: ${names[expected]}`:'')+' · Không ghi điểm danh';
    }catch(e){if(token===epoch){error(e.message);$('lab-decision').textContent='Chưa xử lý được ảnh';}}
    finally{busy=false;activeRequest=null;}
  }
  $('lab-upload').addEventListener('change',async e=>{stop();const token=epoch;const file=e.target.files[0];e.target.value='';await idle();if(file&&token===epoch)classify(file,'Ảnh vùng áo tải lên');});
  $('lab-stop').addEventListener('click',stop);
  $('lab-camera').addEventListener('click',async()=>{
    if(!ready)return;stop();error('');const token=epoch;
    try{
      if(!navigator.mediaDevices?.getUserMedia)throw new Error('Trình duyệt chưa hỗ trợ camera; dùng localhost hoặc tải ảnh.');
      const acquired=await navigator.mediaDevices.getUserMedia({video:{width:640,height:480},audio:false});
      if(token!==epoch){acquired.getTracks().forEach(t=>t.stop());return;}
      stream=acquired;$('lab-video').srcObject=stream;$('camera-box').hidden=false;await $('lab-video').play();
      if(token!==epoch)return;
      acquired.getVideoTracks().forEach(track=>track.addEventListener('ended',stop,{once:true}));
      $('lab-stop').disabled=false;$('lab-camera').disabled=true;
      async function tick(){
        if(token!==epoch||!stream)return;
        const v=$('lab-video');
        if(!busy&&v.videoWidth){const c=document.createElement('canvas');c.width=Math.round(v.videoWidth*.6);c.height=Math.round(v.videoHeight*.65);c.getContext('2d').drawImage(v,v.videoWidth*.2,v.videoHeight*.25,c.width,c.height,0,0,c.width,c.height);const b=await new Promise(resolve=>c.toBlob(resolve,'image/jpeg',.9));if(b&&token===epoch)await classify(b,'Camera · vùng áo trong khung',null,token);}
        if(token===epoch&&stream)setTimeout(tick,1500);
      }
      tick();
    }catch(e){if(token===epoch){stop();error('Không bật được camera: '+e.message);}}
  });
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
  window.addEventListener('pagehide',()=>{stop();if(previewURL)URL.revokeObjectURL(previewURL);});
  api('').then(data=>{
    ready=true;
    for(const sample of data.samples){const b=document.createElement('button');b.type='button';b.className='sample';b.dataset.sample=sample.id;
      const img=document.createElement('img');img.src='/api/v1/demo/uniform/samples/'+encodeURIComponent(sample.id);img.alt=sample.title;
      const title=document.createElement('span');title.textContent=sample.title;const label=document.createElement('small');label.textContent='Nhãn: '+names[sample.expected];b.append(img,title,label);
      b.addEventListener('click',async()=>{stop();const token=epoch;try{await idle();if(token!==epoch)return;const response=await fetch(img.src,{credentials:'same-origin'});if(!response.ok)throw new Error('Không đọc được mẫu.');const image=await response.blob();if(token===epoch)await classify(image,sample.title,sample.expected,token);}catch(e){if(token===epoch)error(e.message);}});$('lab-gallery').append(b);
    }
  }).catch(e=>{error(e.message);$('lab-camera').disabled=true;$('lab-upload').disabled=true;});
})();
