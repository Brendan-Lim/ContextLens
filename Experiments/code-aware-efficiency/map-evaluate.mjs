import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {openMappedFixture,mapVerified} from './lib/mapper.mjs';
import {scenario} from './lib/scenario.mjs';
import {normalizedRectangle} from '../visual-to-code/src/geometry/coordinates.mjs';
import {sha} from '../visual-to-code/src/source-mapping/project.mjs';
const base=path.dirname(fileURLToPath(import.meta.url)),fixture=path.join(base,'fixture'),output=path.resolve(process.argv[2]||path.join(base,'reports/mapping'));
await fs.mkdir(output,{recursive:false});
const truth=JSON.parse(await fs.readFile(path.join(base,'reports/ground-truth.json'),'utf8'));
if(sha(await fs.readFile(path.join(base,'tasks.json')))!==truth.taskSpecSHA256)throw Error('ground_truth_drift');
for(const [file,hash] of Object.entries(truth.publicSourceFiles))if(sha(await fs.readFile(path.join(fixture,file)))!==hash)throw Error('source_drift');
const spec=JSON.parse(await fs.readFile(path.join(base,'tasks.json'),'utf8')),rows=[];
for(const c of spec.mapping_cases){
  const task=spec.tasks.find(t=>t.id===c.task);let owner,temp=null;
  const record={case:c.id,task:c.task,kind:c.kind};const start=performance.now(),wall=Date.now();
  try{
    let root=fixture;
    if(c.afterCapture==='source-change'){temp=await fs.mkdtemp(path.join(os.tmpdir(),'contextlens-source-stale-'));await fs.cp(fixture,temp,{recursive:true,filter:p=>!p.includes('/node_modules')});root=temp;}
    owner=await openMappedFixture(root,task.route,{dpr:c.dpr||1,plain:c.plain});
    const prepared=await scenario(owner,task,{id:c.id,path:path.join(output,c.id+'.png'),noProbe:c.noProbe});
    let box=await owner.page.locator(task.target).boundingBox();
    if(c.partial)box={x:box.x+box.width*.65,y:box.y+box.height*.1,width:box.width*.3,height:box.height*.7};
    const annotation={frameID:c.id,issueID:'CL-001',region:normalizedRectangle(box,prepared.snapshot),mechanism:task.mechanism};record.annotation=annotation;
    if(c.afterCapture==='resize')await owner.page.setViewportSize({width:1000,height:800});
    if(c.afterCapture==='source-change')await fs.appendFile(path.join(root,task.responsible.file),'\n// Source changed after capture.\n');
    const snapshot=c.wrongSnapshot?{...prepared.snapshot,pageIdentity:'other-owner'}:prepared.snapshot;
    const proof=c.forgedProbe?JSON.parse(JSON.stringify(prepared.proof)):prepared.proof;
    record.mapping=await mapVerified(owner,snapshot,annotation,proof);
    const expected=truth.responsibility.find(r=>r.task===c.task),source=record.mapping.sources[0];
    record.expected={file:expected.file,symbol:expected.symbol,blameStart:expected.blameStart,blameEnd:expected.blameEnd};
    record.sourceFileCorrect=source?.file===expected.file;
    record.responsibleSpanCorrect=record.sourceFileCorrect&&source.start<=expected.blameStart&&source.end>=expected.blameEnd&&source.symbol===expected.symbol;
    record.correctAbstention=c.kind==='abstain'&&record.mapping.status==='unavailable';
    record.incorrectHighConfidence=record.mapping.sources.some(s=>s.confidence==='high'&&!(s.file===expected.file&&s.start<=expected.blameStart&&s.end>=expected.blameEnd&&s.symbol===expected.symbol));
    record.status='evaluated';
  }catch(error){record.status='infrastructure-error';record.error=error.stack;}
  finally{await owner?.close();if(temp)await fs.rm(temp,{recursive:true,force:true});record.monotonicMS=performance.now()-start;record.utcWallMS=Date.now()-wall;rows.push(record);}
}
const evaluated=rows.filter(r=>r.status==='evaluated'),positive=evaluated.filter(r=>r.kind==='positive'),negative=evaluated.filter(r=>r.kind==='abstain');
const rate=(n,d)=>({correct:n,total:d,rate:d?n/d:null});
const result={kind:'actual-react-responsibility-mapping-not-agent-performance',newModelCalls:0,groundTruthSHA256:sha(await fs.readFile(path.join(base,'reports/ground-truth.json'))),
  cases:rows.length,infrastructureErrors:rows.filter(r=>r.status!=='evaluated'),
  metrics:{sourceFileTop1:rate(positive.filter(r=>r.sourceFileCorrect).length,positive.length),responsibleSpanTop1:rate(positive.filter(r=>r.responsibleSpanCorrect).length,positive.length),
    correctAbstentions:rate(negative.filter(r=>r.correctAbstention).length,negative.length),incorrectHighConfidenceHints:evaluated.filter(r=>r.incorrectHighConfidence).length,
    coverage:rate(evaluated.filter(r=>r.mapping.status==='mapped').length,evaluated.length)},rows};
await fs.writeFile(path.join(output,'results.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({metrics:result.metrics,infrastructureErrors:result.infrastructureErrors},null,2));
