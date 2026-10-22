(function(root){
  'use strict';
  const MiB=1048576;
  async function optimize(file,budget,index,edges=[1920,1600,1280,1024,800]){
    const image=new Image(),url=URL.createObjectURL(file);
    try{
      image.src=url;await image.decode();
      if(!image.naturalWidth||image.naturalWidth*image.naturalHeight>120000000)throw new Error('Ảnh gốc tối đa 120 triệu pixel.');
      for(const edge of edges){
        const ratio=Math.min(1,edge/image.naturalWidth,edge/image.naturalHeight);
        const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(image.naturalWidth*ratio));canvas.height=Math.max(1,Math.round(image.naturalHeight*ratio));
        const ctx=canvas.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(image,0,0,canvas.width,canvas.height);
        for(const quality of [.92,.84,.74,.64]){
          const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',quality));
          if(blob&&blob.size<=budget)return new File([blob],`face-${index+1}.jpg`,{type:'image/jpeg'});
        }
      }
      throw new Error('Ảnh còn quá lớn sau tối ưu; chọn ảnh rõ và ít chi tiết nền hơn.');
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
  async function prepareUniform(file,encoder=optimize,isCurrent=()=>true){
    if(!file||file.size>32*MiB)throw new Error('Ảnh gốc đồng phục tối đa 32 MiB.');
    if(!['image/jpeg','image/png','image/webp'].includes(file.type))throw new Error('Chọn ảnh JPEG, PNG hoặc WebP; chuyển HEIC/RAW sang JPEG trước.');
    if(!isCurrent())return null;
    // Match the server decoder dimensions so ROI coordinates need no second resize.
    const budget=Math.floor(1.9*MiB),prepared=await encoder(file,budget,0,[960,800,640]);
    if(!isCurrent())return null;
    if(!prepared||prepared.size>budget)throw new Error('Ảnh đồng phục vượt dung lượng sau tối ưu.');
    return prepared;
  }
  function uniformRoi(start,end,displayWidth,displayHeight,imageWidth,imageHeight){
    const axis=(a,b,display,size)=>[a,b].map(v=>Math.max(0,Math.min(size,Math.round(v*size/display)))).sort((a,b)=>a-b);
    const [x1,x2]=axis(start[0],end[0],displayWidth,imageWidth),[y1,y2]=axis(start[1],end[1],displayHeight,imageHeight);
    return [x1,y1,x2-x1,y2-y1];
  }
  const api={prepare,prepareUniform,uniformRoi};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MindXEnrollment=api;
})(typeof window!=='undefined'?window:globalThis);
