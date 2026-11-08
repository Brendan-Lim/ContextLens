import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {evaluate} from './evaluate.mjs';
const base=path.dirname(fileURLToPath(import.meta.url)),fixture=path.join(base,'fixture'),output=path.resolve(process.argv[2]||path.join(base,'reports/fixture-validation'));
await fs.mkdir(output,{recursive:false});
export const repairs={
  'publish-actions':['src/ui/dialogs/ActionCluster.module.css','justify-content: flex-start;','justify-content: flex-end;'],
  'project-filter':['src/interaction/useLayerDismissal.ts','      onDismiss();','      const target=event.target as Node;\n      if(!anchor.current?.contains(target)&&!layer.current?.contains(target))onDismiss();'],
  'seat-allocation':['src/state/useSeatAllocation.ts','setSeats(seats+1)','setSeats(value=>value+1)'],
  'contact-validation':['src/domain/validation/contactPolicy.ts',"return address.includes('@');","return /^[^\\s@]+@[^\\s@.]+(?:\\.[^\\s@.]+)+$/.test(address);"]
};
const baseline=await evaluate(fixture);assert.ok(baseline.targets.every(r=>!r.passed),'Every baseline issue must fail');assert.ok(baseline.regressions.every(r=>r.passed));
async function copy(){const dest=await fs.mkdtemp(path.join(os.tmpdir(),'contextlens-react-control-'));await fs.cp(fixture,dest,{recursive:true,filter:p=>!p.includes('/node_modules')&&!p.includes('/dist')});await fs.symlink(path.join(fixture,'node_modules'),path.join(dest,'node_modules'));return dest;}
function build(root,plain=false){const env={...process.env,...(plain?{LENSBOARD_OUT:'dist-plain'}:{})};const r=spawnSync(process.execPath,['tools/build.mjs',...(plain?['--plain']:[])],{cwd:root,env,encoding:'utf8'});assert.equal(r.status,0,r.stderr);}
const controls=[];
for(const task of Object.keys(repairs)){
  const temp=await copy();try{
    const [file,from,to]=repairs[task],p=path.join(temp,file),text=await fs.readFile(p,'utf8');assert.ok(text.includes(from));await fs.writeFile(p,text.replace(from,to));build(temp);
    const checks=await evaluate(temp);assert.equal(checks.targets.find(r=>r.task===task).passed,true,task);
    assert.ok(checks.targets.filter(r=>r.task!==task).every(r=>!r.passed),'Repair must not solve other independent issues');assert.ok(checks.regressions.every(r=>r.passed));
    controls.push({repair:task,changedFile:file,checks});
  }finally{await fs.rm(temp,{recursive:true,force:true});}
}
const temp=await copy();let combined,plainBaseline;
try{
  for(const [file,from,to] of Object.values(repairs)){const p=path.join(temp,file);await fs.writeFile(p,(await fs.readFile(p,'utf8')).replace(from,to));}
  build(temp);combined=await evaluate(temp);assert.ok([...combined.targets,...combined.regressions].every(r=>r.passed));
}finally{await fs.rm(temp,{recursive:true,force:true});}
// Plain React and instrumented builds must reproduce the same initial issues.
build(fixture,true);plainBaseline=await evaluate(fixture,null,{plain:true});assert.deepEqual(plainBaseline.targets.map(r=>r.passed),baseline.targets.map(r=>r.passed));assert.ok(plainBaseline.regressions.every(r=>r.passed));
await fs.writeFile(path.join(output,'results.json'),JSON.stringify({kind:'independent-fixture-controls-not-agent-results',baseline,controls,combined,plainBaseline,newModelCalls:0},null,2)+'\n');
console.log('All four initial defects reproduced; four isolated repairs and combined control pass; instrumentation parity verified.');
