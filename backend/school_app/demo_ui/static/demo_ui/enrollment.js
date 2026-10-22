(function(root){
  'use strict';
  const MiB=1048576;
  async function optimize(file,budget,index){
    const image=new Image(),url=URL.createObjectURL(file);
    try{
      image.src=url;await image.decode();
      if(!image.naturalWidth||image.naturalWidth*image.naturalHeight>120000000)throw new Error('Ảnh gốc tối đa 120 triệu pixel.');
      for(const edge of [1920,1600,1280,1024,800]){
        const ratio=Math.min(1,edge/image.naturalWidth,edge/image.naturalHeight);
        const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(image.naturalWidth*ratio));canvas.height=Math.max(1,Math.round(image.naturalHeight*ratio));
        const ctx=canvas.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(image,0,0,canvas.width,canvas.height);
        for(const quality of [.92,.84,.74,.64]){
          const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',quality));
          if(blob&&blob.size<=budget)return new File([blob],`face-${index+1}.jpg`,{type:'image/jpeg'});
        }
      }
      throw new Error('Ảnh còn quá lớn sau tối ưu; chọn ảnh rõ mặt và ít chi tiết nền hơn.');
    }finally{URL.revokeObjectURL(url);image.src='';}
  }
  async function prepare(files,total,encoder=optimize,progress=()=>{},isCurrent=()=>true){
    if(files.length<3||files.length>10)throw new Error('Chọn 3–10 ảnh của cùng học sinh.');
    if(files.some(f=>f.size>32*MiB))throw new Error('Mỗi ảnh gốc tối đa 32 MiB.');
    if(files.some(f=>!['image/jpeg','image/png','image/webp'].includes(f.type)))throw new Error('Chọn ảnh JPEG, PNG hoặc WebP; chuyển HEIC/RAW sang JPEG trước.');
    if(!Number.isFinite(total)||total<1024)throw new Error('Giới hạn gửi ảnh chưa hợp lệ.');
    const perImage=Math.min(1.9*MiB,Math.floor(total*.9/files.length)),out=[];
    for(let i=0;i<files.length;i++){
      if(!isCurrent())return null;
      progress(i+1,files.length);
      const file=await encoder(files[i],perImage,i);
      if(!isCurrent())return null;
      if(!file||file.size>perImage)throw new Error('Ảnh vượt dung lượng sau tối ưu.');
      out.push(file);
    }
    if(out.reduce((n,f)=>n+f.size,0)>total)throw new Error('Bộ mẫu vượt dung lượng sau tối ưu.');
    return out;
  }
  const api={prepare};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MindXEnrollment=api;
})(typeof window!=='undefined'?window:globalThis);
