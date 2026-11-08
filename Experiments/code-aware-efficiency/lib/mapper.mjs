import fs from 'node:fs/promises';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {TraceMap,originalPositionFor,sourceContentFor} from '../fixture/node_modules/@jridgewell/trace-mapping/dist/trace-mapping.mjs';
import {mapAnnotation} from '../../visual-to-code/src/browser-adapter/map.mjs';
import {containedFile,sha} from '../../visual-to-code/src/source-mapping/project.mjs';
import {openFixture} from './browser.mjs';
const builds=new WeakMap(),probes=new WeakMap();
const fields=['id','file','start','end','line','column','sourceSHA256','kind','name','effects','nativeEvents'];

export async function openMappedFixture(root,route,options={}){
  root=await fs.realpath(root);const owner=await openFixture(root,route,options),folder=options.plain?'dist-plain':'dist';
  const receipts={};
  for(const name of ['assets/app.js','assets/app.css','assets/app.css.map','assets/source-receipts.json']){
    try{const p=await containedFile(root,folder+'/'+name);receipts[name]=sha(await fs.readFile(p.file));}catch{}
  }
  const manifest=receipts['assets/source-receipts.json']?JSON.parse(await fs.readFile(path.join(root,folder,'assets/source-receipts.json'),'utf8')):null;
  builds.set(owner,{root,folder,receipts,manifest});return owner;
}
export async function observeProbe(owner,before,label,action){
  const invalid=await owner.validate(before);if(invalid)throw Error(invalid);
  const id=randomUUID(),url=owner.page.url();
  const supported=await owner.page.evaluate(()=>window.contextLensRuntime?.version===1);
  if(!supported){const proof=Object.freeze({id,available:false});probes.set(proof,{owner,before,label,entries:[],supported:false});return proof;}
  await owner.page.evaluate(label=>window.contextLensRuntime.beginProbe(label),label);
  let observed;
  try{await action();await owner.page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));}
  finally{observed=await owner.page.evaluate(()=>window.contextLensRuntime.endProbe());}
  if(owner.page.url()!==url)throw Error('probe_navigated');
  const afterSHA256=sha(await owner.screenshot()),proof=Object.freeze({id,available:true});
  probes.set(proof,{owner,before,label,entries:observed?.entries||[],supported:true,afterSHA256});return proof;
}
export function selectExecution(entries,mechanism){
  const eligible=entries.filter(e=>mechanism==='dismissal'?e.receipt.nativeEvents?.includes('pointerdown'):
    mechanism==='validation'?e.receipt.effects?.includes('string-boolean-predicate'):
    mechanism==='state-update'?e.receipt.effects?.includes('state-write'):false);
  const unique=[...new Map(eligible.map(e=>[e.receipt.id,e])).values()];if(!unique.length)return null;
  const depth=Math.max(...unique.map(e=>e.depth)),deepest=unique.filter(e=>e.depth===depth);
  return deepest.length===1?deepest[0].receipt:null;
}
export async function validateReceipt(receipt,build){
  const canonical=build.manifest?.receipts.find(r=>r.id===receipt?.id);
  if(!canonical||!fields.every(k=>JSON.stringify(canonical[k])===JSON.stringify(receipt[k])))return null;
  try{
    const source=await containedFile(build.root,canonical.file),bytes=await fs.readFile(source.file);
    if(sha(bytes)!==canonical.sourceSHA256||canonical.start<0||canonical.end>bytes.length)return null;
    return canonical;
  }catch{return null;}
}
async function validateBuild(owner,build){
  if(!build)return 'unregistered_project';
  for(const [relative,hash] of Object.entries(build.receipts)){
    try{const file=await containedFile(build.root,build.folder+'/'+relative);if(sha(await fs.readFile(file.file))!==hash)return 'stale_build_artifact';}catch{return 'stale_build_artifact';}
  }
  for(const name of ['assets/app.js','assets/app.css']){
    if(owner.assets.get(owner.project.origin+'/'+name)?.hash!==build.receipts[name])return 'unverified_browser_asset';
  }
  if(build.manifest){
    if(build.manifest.bundleSHA256!==build.receipts['assets/app.js']||build.manifest.cssSHA256!==build.receipts['assets/app.css'])return 'build_receipt_mismatch';
    for(const [file,expected] of [['tools/instrument.mjs',build.manifest.instrumenterSHA256],['tools/runtime.ts',build.manifest.runtimeSHA256]]){
      try{const p=await containedFile(build.root,file);if(sha(await fs.readFile(p.file))!==expected)return 'stale_instrumentation';}catch{return 'stale_instrumentation';}
    }
  }
  return null;
}
const escape=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
async function mappedDeclaration(element,build){
  const choices=[...(element.parent?.matchedRules||[]).map(r=>({...r,scope:'parent'})),...(element.matchedRules||[]).map(r=>({...r,scope:'element'}))];
  const rule=choices.find(r=>r.declarations['justify-content']);if(!rule)return null;
  const cssFile=await containedFile(build.root,build.folder+'/assets/app.css'),text=await fs.readFile(cssFile.file,'utf8');
  const rulePattern=new RegExp(escape(rule.selector)+'\\s*\\{([^}]+)\\}','g'),matches=[...text.matchAll(rulePattern)];if(matches.length!==1)return null;
  const body=matches[0][1],property=/justify-content\s*:\s*([^;]+);/.exec(body);if(!property)return null;
  const start=matches[0].index+matches[0][0].indexOf(body)+property.index;
  const prefix=text.slice(0,start),line=prefix.split('\n').length,column=start-(prefix.lastIndexOf('\n')+1);
  const mapFile=await containedFile(build.root,build.folder+'/assets/app.css.map');
  const map=new TraceMap(JSON.parse(await fs.readFile(mapFile.file,'utf8')),pathToFileURL(mapFile.file).href);
  const original=originalPositionFor(map,{line,column});if(!original.source||!original.line)return null;
  const absolute=original.source.startsWith('file:')?fileURLToPath(original.source):path.resolve(path.dirname(mapFile.file),original.source);
  const relative=path.relative(build.root,absolute).split(path.sep).join('/');
  const source=await containedFile(build.root,relative),raw=await fs.readFile(source.file,'utf8');
  if(sourceContentFor(map,original.source)!==raw)return null;
  const offset=raw.split('\n').slice(0,original.line-1).join('\n').length+(original.line>1?1:0)+original.column;
  const blocks=[...raw.matchAll(/([^{}]+)\{([^{}]*)\}/g)];
  const block=blocks.find(m=>m.index<=offset&&m.index+m[0].length>offset);if(!block)return null;
  const declaration=/justify-content\s*:\s*([^;]+);/.exec(block[2]);if(!declaration||declaration[1].trim()!==rule.declarations['justify-content'])return null;
  const sourceStart=block.index+block[0].indexOf(block[2])+declaration.index;
  return {file:source.relative,line:raw.slice(0,sourceStart).split('\n').length,column:sourceStart-raw.lastIndexOf('\n',sourceStart),start:sourceStart,end:sourceStart+declaration[0].length,
    symbol:block[1].trim(),kind:'css-module-declaration',confidence:'high',sourceSHA256:sha(raw),
    evidence:['browser_matched_property','linked_CSS_source_map','source_content_equals_selected_project'],scope:rule.scope,property:'justify-content',winningCascadeOrBugCauseClaimed:false};
}
export async function mapVerified(owner,snapshot,annotation,proof=null){
  const started=performance.now(),fail=reason=>({status:'unavailable',reason,sources:[],runtimeMS:performance.now()-started});
  const build=builds.get(owner),invalid=await validateBuild(owner,build);if(invalid)return fail(invalid);
  const dom=await mapAnnotation(owner,snapshot,{...annotation,category:annotation.mechanism==='alignment'?'alignment':'interaction'});
  if(dom.status!=='mapped')return fail(dom.reason);
  if(annotation.mechanism==='alignment'){
    try{const source=await mappedDeclaration(dom.element,build);if(!source)return fail('declaration_mapping_unavailable');return {status:'mapped',dom,sources:[source],runtimeMS:performance.now()-started};}
    catch(error){return fail('declaration_mapping_unavailable:'+error.message);}
  }
  const observation=probes.get(proof);
  if(!observation||observation.owner!==owner)return fail('unverified_execution_probe');
  if(!observation.supported||!build.manifest)return fail('runtime_unavailable');
  if(![observation.before.sha256,observation.afterSHA256].includes(snapshot.sha256))return fail('probe_snapshot_mismatch');
  const candidate=selectExecution(observation.entries,annotation.mechanism);if(!candidate)return fail('no_unique_responsible_execution');
  const receipt=await validateReceipt(candidate,build);if(!receipt)return fail('stale_or_invalid_source_receipt');
  return {status:'mapped',dom,sources:[{file:receipt.file,line:receipt.line,column:receipt.column,start:receipt.start,end:receipt.end,symbol:receipt.name,kind:'executed-'+annotation.mechanism,confidence:'high',sourceSHA256:receipt.sourceSHA256,
    evidence:['controlled_interaction_execution','build_instrumented_original_AST_span','observed_bundle_hash','selected_project_source_hash'],receiptID:receipt.id,
    bugCausalityScope:'Executed implementation candidate; responsibility is evaluated independently, not inferred from markup.'}],
    probe:{id:proof.id,label:observation.label,executionEntries:observation.entries.length,beforeImageSHA256:observation.before.sha256,afterImageSHA256:observation.afterSHA256},runtimeMS:performance.now()-started};
}
