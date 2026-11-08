import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {randomUUID} from 'node:crypto';
import {OwnedBrowser} from './src/browser-adapter/owned-browser.mjs';
import {mapAnnotation} from './src/browser-adapter/map.mjs';
import {exportVariant} from './src/export/sidecar.mjs';
import {sha} from './src/source-mapping/project.mjs';
const base=path.dirname(fileURLToPath(import.meta.url)),repo=path.resolve(base,'../..');
const output=path.resolve(process.argv[2]||path.join(base,'reports/offline-handoffs'));
await fs.mkdir(output,{recursive:false});
const cli=path.join(repo,'.build/release/contextlens-cli'),rows=[];
const specs=JSON.parse(await fs.readFile(path.join(repo,'Benchmarks/manual-vs-contextlens-spec.json'),'utf8'));
async function inventory(folder){const files={};async function scan(dir){for(const e of await fs.readdir(dir,{withFileTypes:true})){const p=path.join(dir,e.name);if(e.isSymbolicLink())throw Error('symlink');if(e.isDirectory())await scan(p);else files[path.relative(folder,p)]={bytes:(await fs.stat(p)).size,sha256:sha(await fs.readFile(p))};}}await scan(folder);return files;}
for(const task of ['01','04','08','10']){
  const folder=path.join(output,task);await fs.mkdir(folder);let owner;
  try{
    const old=JSON.parse(await fs.readFile(path.join(repo,`Benchmarks/reports/manual-vs-contextlens/study-v2/packages/${task}/contextlens/metadata/session.json`),'utf8'));
    const annotation=old.annotations.find(a=>a.id==='CL-001'),frame=old.frames.find(f=>f.id===annotation.frameID);
    const instruction=specs.tasks.find(t=>t.id===task).instruction;
    if(annotation.instruction!==instruction)throw Error('historical_instruction_drift');
    owner=await OwnedBrowser.create({projectRoot:path.join(repo,'Benchmarks/tasks'),route:`/?task=${task}`});
    if(task==='04')await owner.page.click('#toggle');
    if(task==='08'){await owner.page.fill('#email','invalid');await owner.page.click('#submit');}
    if(task==='10')await owner.page.click('#increment');
    const snapshot=await owner.capture({id:frame.id,path:path.join(folder,'owned-capture.png')});
    const mapping=await mapAnnotation(owner,snapshot,{frameID:frame.id,issueID:annotation.id,region:annotation.region,category:task==='01'?'alignment':'interaction'});
    await fs.writeFile(path.join(folder,'mapping.json'),JSON.stringify(mapping,null,2)+'\n');
    const sessionDir=path.join(folder,'source-session');await fs.mkdir(path.join(sessionDir,'frames'),{recursive:true});
    await fs.copyFile(path.join(folder,'owned-capture.png'),path.join(sessionDir,frame.imagePath));
    const session={...old,id:'visual-code-'+randomUUID(),createdAt:new Date().toISOString(),task:instruction,
      frames:[{...frame,width:snapshot.width,height:snapshot.height,timestampMS:0,applicationName:'Owned local browser fixture'}],annotations:[annotation]};
    await fs.writeFile(path.join(sessionDir,'session.json'),JSON.stringify(session,null,2)+'\n');
    const current=path.join(folder,'production-export');
    const process=spawnSync(cli,['export',sessionDir,current],{encoding:'utf8'});if(process.status!==0)throw Error(process.stderr||process.stdout);
    const manifest=JSON.parse(await fs.readFile(path.join(current,'manifest.json'),'utf8'));
    const images=manifest.frames.map(f=>`annotated/states/${f.id}.png`);
    const rawScreenshot=await fs.readFile(path.join(folder,'owned-capture.png'));
    const expectedSource=task==='01'?'styles.css':'app.js';
    const baselineImages={};
    for(const condition of ['current','code-aware','minimal-code-aware']){
      const destination=path.join(folder,condition);
      const result=await exportVariant({basePackage:current,destination,mapping,rawScreenshot,projectRoot:path.join(repo,'Benchmarks/tasks'),condition});
      const files=await inventory(destination),text=await fs.readFile(path.join(destination,'context.md'),'utf8');
      if(!text.includes(instruction))throw Error('user_instruction_lost');
      const imageHashes=Object.fromEntries(Object.entries(files).filter(([p])=>p.endsWith('.png')).map(([p,v])=>[p,v.sha256]));
      if(condition==='current')Object.assign(baselineImages,imageHashes);
      else if(JSON.stringify(imageHashes)!==JSON.stringify(baselineImages))throw Error('image_evidence_changed');
      const sources=result.status==='code-aware'?mapping.sourceCandidates:[];
      rows.push({task,condition,kind:'measured-offline-filesystem-and-local-mapping-not-agent-usage',
        initialTextUTF8Bytes:Buffer.byteLength(text),initialTextCharacters:text.length,initialImageCount:images.length,
        initialImageSHA256:Object.fromEntries(images.map(p=>[p,files[p].sha256])),totalFilesystemBytes:Object.values(files).reduce((n,v)=>n+v.bytes,0),
        sourceCandidateCount:sources.length,confidence:sources.map(s=>s.confidence),correctSourcePointers:sources.filter(s=>s.file===expectedSource).length,
        incorrectSourcePointers:sources.filter(s=>s.file!==expectedSource).length,sourcePointers:sources.map(s=>s.file),
        mappingRuntimeMS:mapping.runtimeMS,mappingStatus:mapping.status,exportResult:result,package:path.relative(base,destination),
        files,inputTokens:null,agentExecutionSeconds:null,humanPreparationSeconds:null});
    }
  }finally{await owner?.close();}
}
await fs.writeFile(path.join(output,'comparison.json'),JSON.stringify({kind:'offline-context-payload-comparison',newModelCalls:0,
  instructionsAndImagesIdenticalAcrossArms:true,rows,note:'Text characters/bytes, images and filesystem size are actual offline measurements, not measured token savings. Each package is freshly compiled with the unchanged production exporter; annotation IDs/regions/instructions are reused, but native-window calibration is not claimed.'},null,2)+'\n');
const profile=JSON.parse(await fs.readFile(path.join(base,'reports/trace-profile-v2/profile.json'),'utf8'));
const counterfactual=profile.individual_trials.filter(t=>['01','04','08','10'].includes(t.task)).map(t=>{
  const pointers=rows.find(r=>r.task===t.task&&r.condition==='code-aware').sourcePointers;
  return {study:t.study,task:t.task,condition:t.condition,repeat:t.repeat,trace:t.trace,pointers,
    recognizedSourceFilesRead:Object.keys(t.source_files_read_recognized),pointersReachingEventuallyReadFile:pointers.filter(p=>Object.hasOwn(t.source_files_read_recognized,p)),
    sourceSearchCallsObserved:t.source_search_or_listing_calls,predictedAvoidedSearches:null,predictedTokenSaving:null,
    interpretation:'Counterfactual file-navigation overlap only. Does not establish that source hints would change an agent action, reduce search, or save tokens.'};
});
await fs.writeFile(path.join(output,'counterfactual.json'),JSON.stringify({kind:'counterfactual-historical-trace-analysis-not-agent-results',rows:counterfactual},null,2)+'\n');
console.log(`Prepared ${rows.length} A/B/C packages for four tasks with zero model calls.`);
