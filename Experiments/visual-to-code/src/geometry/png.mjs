// Minimal decoder for owned Chromium PNGs, not an arbitrary image import API.
import {inflateSync} from 'node:zlib';
export function decodePNG(bytes){
  if(bytes.subarray(0,8).toString('hex')!=='89504e470d0a1a0a')throw Error('not_png');
  let offset=8,width,height,bpp,idat=[];
  while(offset<bytes.length){const size=bytes.readUInt32BE(offset),type=bytes.toString('ascii',offset+4,offset+8),data=bytes.subarray(offset+8,offset+8+size);offset+=12+size;
    if(type==='IHDR'){width=data.readUInt32BE(0);height=data.readUInt32BE(4);if(data[8]!==8||![2,6].includes(data[9])||data[12]!==0||width*height>16000000)throw Error('unsupported_png');bpp=data[9]===2?3:4;}
    if(type==='IDAT')idat.push(data);if(type==='IEND')break;
  }
  if(!bpp)throw Error('missing_png_header');
  const raw=inflateSync(Buffer.concat(idat),{maxOutputLength:(width*bpp+1)*height}),stride=width*bpp,out=Buffer.alloc(stride*height);
  if(raw.length!==(stride+1)*height)throw Error('bad_png_size');
  const paeth=(a,b,c)=>{const p=a+b-c,x=Math.abs(p-a),y=Math.abs(p-b),z=Math.abs(p-c);return x<=y&&x<=z?a:y<=z?b:c;};
  for(let y=0;y<height;y++){const filter=raw[y*(stride+1)];if(filter>4)throw Error('unsupported_png_filter');
    for(let x=0;x<stride;x++){const a=x>=bpp?out[y*stride+x-bpp]:0,b=y?out[(y-1)*stride+x]:0,c=y&&x>=bpp?out[(y-1)*stride+x-bpp]:0;
      out[y*stride+x]=(raw[y*(stride+1)+1+x]+[0,a,b,Math.floor((a+b)/2),paeth(a,b,c)][filter])&255;}}
  return {width,height,bpp,pixels:out};
}
export function findColors(png,colors){
  const sums=colors.map(()=>({x:0,y:0,n:0}));
  for(let y=0;y<png.height;y++)for(let x=0;x<png.width;x++){
    const k=(y*png.width+x)*png.bpp;
    for(let i=0;i<colors.length;i++)if(colors[i].every((c,j)=>png.pixels[k+j]===c)){sums[i].x+=x+.5;sums[i].y+=y+.5;sums[i].n++;}
  }
  return sums.map(s=>{if(s.n<4)throw Error('calibration_color_missing');return {x:s.x/s.n,y:s.y/s.n};});
}
