import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {selectExecution,validateReceipt} from '../lib/mapper.mjs';
const fixture=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../fixture');
test('execution evidence selects unique deepest semantic candidate and abstains on ambiguity',()=>{
  const state=(id,depth)=>({depth,receipt:{id,effects:['state-write']}}),a=state('a',1),b=state('b',2);
  assert.equal(selectExecution([a,b],'state-update'),b.receipt);
  assert.equal(selectExecution([b,state('c',2)],'state-update'),null);
  assert.equal(selectExecution([a],'validation'),null);
  assert.equal(selectExecution([a],'unknown'),null);
  const listener={depth:2,receipt:{id:'listener',nativeEvents:['pointerdown']}};
  assert.equal(selectExecution([listener,a],'dismissal'),listener.receipt);
});
test('plausible wrong file/symbol/line/span/hash hints are rejected against build receipts',async()=>{
  const manifest=JSON.parse(await fs.readFile(path.join(fixture,'dist/assets/source-receipts.json'),'utf8'));
  const original=manifest.receipts.find(r=>r.name==='acceptsContact');assert.ok(original);
  const build={root:fixture,manifest};assert.ok(await validateReceipt(original,build));
  for(const change of [{file:'src/domain/validation/reportPolicy.ts'},{name:'acceptsReport'},{line:original.line+1},{start:original.start+1},{sourceSHA256:'0'.repeat(64)},{file:'../../private.ts'}]){
    assert.equal(await validateReceipt({...original,...change},build),null);
  }
  assert.equal(await validateReceipt({...original,id:'invented'},build),null);
});
