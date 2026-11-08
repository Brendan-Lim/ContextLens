import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {exportVariant} from '../src/export/sidecar.mjs';
const base=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),repo=path.resolve(base,'../..');
const fixture=path.join(base,'reports/offline-handoffs/01');
const original=path.join(fixture,'production-export');
const mapping=JSON.parse(await fs.readFile(path.join(fixture,'mapping.json'),'utf8'));
const raw=await fs.readFile(path.join(fixture,'owned-capture.png'));
const projectRoot=path.join(repo,'Benchmarks/tasks');
const options={basePackage:original,mapping,rawScreenshot:raw,projectRoot};
async function sandbox(fn){const temp=await fs.mkdtemp(path.join(os.tmpdir(),'contextlens-code-export-'));try{return await fn(temp);}finally{await fs.rm(temp,{recursive:true,force:true});}}

test('normal manifest and image references survive optional code-aware extension',()=>sandbox(async temp=>{
  const result=await exportVariant({...options,destination:path.join(temp,'out')});assert.equal(result.status,'code-aware');
  assert.equal(await fs.readFile(path.join(temp,'out/manifest.json'),'utf8'),await fs.readFile(path.join(original,'manifest.json'),'utf8'));
  const sidecar=JSON.parse(await fs.readFile(path.join(temp,'out/code-context/CL-001.json'),'utf8'));
  assert.equal(sidecar.captureBinding.method,'exact_RGBA_pixel_identity');assert.equal(sidecar.issueID,'CL-001');
  assert.ok(!JSON.stringify(sidecar).includes('contextLensCandidateNodes'));
}));
test('wrong raw screenshot falls back to byte-identical normal brief',()=>sandbox(async temp=>{
  const result=await exportVariant({...options,destination:path.join(temp,'out'),rawScreenshot:Buffer.from('wrong capture')});
  assert.equal(result.reason,'wrong_raw_capture');
  assert.equal(await fs.readFile(path.join(temp,'out/context.md'),'utf8'),await fs.readFile(path.join(original,'context.md'),'utf8'));
}));
test('correct source capture cannot be associated with different exported pixels',()=>sandbox(async temp=>{
  const wrong=path.join(temp,'wrong');await fs.cp(original,wrong,{recursive:true});
  await fs.copyFile(path.join(base,'reports/offline-handoffs/04/owned-capture.png'),path.join(wrong,'frames',mapping.frameID+'.png'));
  const result=await exportVariant({...options,basePackage:wrong,destination:path.join(temp,'out')});
  assert.equal(result.reason,'export_pixels_do_not_match_owned_capture');
}));
test('escaping or changed source references are not attached',()=>sandbox(async temp=>{
  const bad=structuredClone(mapping);bad.sourceCandidates[0].file='../outside.js';
  assert.equal((await exportVariant({...options,mapping:bad,destination:path.join(temp,'escape')})).reason,'escaping_or_missing_source');
  bad.sourceCandidates[0].file='styles.css';bad.sourceCandidates[0].sourceSHA256='0'.repeat(64);
  assert.equal((await exportVariant({...options,mapping:bad,destination:path.join(temp,'stale')})).reason,'source_changed_before_export');
}));
test('redacted frame metadata produces visual-only fallback',()=>sandbox(async temp=>{
  const redacted=path.join(temp,'redacted');await fs.cp(original,redacted,{recursive:true});
  const file=path.join(redacted,'metadata/session.json'),session=JSON.parse(await fs.readFile(file,'utf8'));
  session.annotations.push({...session.annotations[0],id:'CL-002',kind:'redaction'});await fs.writeFile(file,JSON.stringify(session));
  const result=await exportVariant({...options,basePackage:redacted,destination:path.join(temp,'out')});
  assert.equal(result.reason,'redacted_frame_metadata_omitted');
  assert.equal(await fs.readFile(path.join(temp,'out/context.md'),'utf8'),await fs.readFile(path.join(original,'context.md'),'utf8'));
}));
test('unknown mapping retains visual brief and existing destinations are never overwritten',()=>sandbox(async temp=>{
  const destination=path.join(temp,'out');
  const result=await exportVariant({...options,mapping:{status:'unavailable',reason:'stale'},destination});assert.equal(result.status,'visual-only');
  await assert.rejects(exportVariant({...options,destination}),/destination_exists/);
}));
test('minimal entrypoint preserves a distinct explicit overall task',()=>sandbox(async temp=>{
  const source=path.join(temp,'source');await fs.cp(original,source,{recursive:true});
  const file=path.join(source,'manifest.json'),manifest=JSON.parse(await fs.readFile(file,'utf8'));manifest.task='Preserve the team publish flow.';await fs.writeFile(file,JSON.stringify(manifest));
  const destination=path.join(temp,'out');await exportVariant({...options,basePackage:source,destination,condition:'minimal-code-aware'});
  assert.ok((await fs.readFile(path.join(destination,'context.md'),'utf8')).includes(manifest.task));
}));
