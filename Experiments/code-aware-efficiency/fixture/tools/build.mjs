import fs from 'node:fs/promises';
import path from 'node:path';
import {build} from 'esbuild';
import {instrument,hash} from './instrument.mjs';
const root=process.cwd(),plain=process.argv.includes('--plain'),output=process.env.LENSBOARD_OUT||'dist',receipts=[];
await fs.mkdir(output,{recursive:true});
const result=await build({absWorkingDir:root,entryPoints:['src/main.tsx'],bundle:true,format:'esm',target:'chrome120',jsx:'automatic',
  outfile:path.join(output,'assets/app.js'),sourcemap:'linked',sourcesContent:true,metafile:true,loader:{'.module.css':'local-css'},
  define:{'process.env.NODE_ENV':'"production"'},
  plugins:plain?[]:[{name:'local-source-evidence',setup(builder){builder.onLoad({filter:/\.(tsx|ts)$/},async args=>{
    if(!args.path.startsWith(path.join(root,'src')+path.sep)||args.path.endsWith('.d.ts'))return null;
    const source=await fs.readFile(args.path,'utf8'),transformed=instrument(source,args.path,root);receipts.push(...transformed.receipts);
    return {contents:transformed.contents,loader:args.path.endsWith('.tsx')?'tsx':'ts',resolveDir:path.dirname(args.path)};
  });}}]});
await fs.copyFile('index.html',path.join(output,'index.html'));
if(!plain)await fs.writeFile(path.join(output,'assets/source-receipts.json'),JSON.stringify({version:1,kind:'explicit-development-build-instrumentation',
  bundleSHA256:hash(await fs.readFile(path.join(output,'assets/app.js'))),cssSHA256:hash(await fs.readFile(path.join(output,'assets/app.css'))),
  instrumenterSHA256:hash(await fs.readFile('tools/instrument.mjs')),runtimeSHA256:hash(await fs.readFile('tools/runtime.ts')),receipts},null,2)+'\n');
await fs.writeFile(path.join(output,'metafile.json'),JSON.stringify(result.metafile,null,2)+'\n');
console.log(`Built ${plain?'plain':'instrumented'} local frontend.`);
