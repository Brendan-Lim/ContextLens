import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createServer} from 'node:http';
export const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
export async function containedFile(root,relative){
  if(typeof relative!=='string'||relative.includes('\0')||relative.includes('\\')||path.isAbsolute(relative)||relative.split('/').includes('..'))throw Error('escaping_source_path');
  const canonical=await fs.realpath(root),file=await fs.realpath(path.resolve(canonical,relative));
  if(!file.startsWith(canonical+path.sep))throw Error('escaping_source_symlink');
  if(!(await fs.stat(file)).isFile())throw Error('not_source_file');
  return {file,relative:path.relative(canonical,file).split(path.sep).join('/')};
}
export async function serveProject(root){
  root=await fs.realpath(root);
  const types={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.map':'application/json','.png':'image/png'};
  const server=createServer(async(req,res)=>{try{
    const pathname=decodeURIComponent(new URL(req.url,'http://127.0.0.1').pathname);
    const {file}=await containedFile(root,pathname==='/'?'index.html':pathname.slice(1));
    const type=types[path.extname(file)];if(!type)throw Error('unsupported_asset');
    const bytes=await fs.readFile(file);res.writeHead(200,{'Content-Type':type,'Cache-Control':'no-store'});res.end(bytes);
  }catch{res.writeHead(404);res.end('Unavailable');}});
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  return {root,origin:`http://127.0.0.1:${server.address().port}`,close:()=>new Promise(resolve=>server.close(resolve))};
}
export async function verifiedAsset(url,assets,project){
  const parsed=new URL(url);if(parsed.origin!==project.origin||!assets.has(parsed.href))return null;
  try{
    const {file,relative}=await containedFile(project.root,decodeURIComponent(parsed.pathname).slice(1)||'index.html');
    const bytes=await fs.readFile(file),observed=assets.get(parsed.href);
    if(bytes.length>1000000||sha(bytes)!==observed.hash)return null;
    return {file:relative,text:bytes.toString('utf8'),sha256:observed.hash,url:parsed.pathname};
  }catch{return null;}
}
