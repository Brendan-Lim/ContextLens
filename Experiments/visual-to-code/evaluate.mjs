import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {performance} from 'node:perf_hooks';
import {OwnedBrowser} from './src/browser-adapter/owned-browser.mjs';
import {mapAnnotation} from './src/browser-adapter/map.mjs';
import {normalizedRectangle} from './src/geometry/coordinates.mjs';
import {sha} from './src/source-mapping/project.mjs';
const base=path.dirname(fileURLToPath(import.meta.url)),repo=path.resolve(base,'../..');
const args=process.argv.slice(2),split=args[args.indexOf('--split')+1]||'development',output=path.resolve(args[args.indexOf('--output')+1]||path.join(base,'reports',split));
if(!['development','held-out'].includes(split))throw Error('Use --split development or held-out');
await fs.mkdir(output,{recursive:false});
const freeze=JSON.parse(await fs.readFile(path.join(base,'reports/ground-truth-freeze.json'),'utf8'));
for(const [file,hash] of Object.entries(freeze.files))if(sha(await fs.readFile(path.join(base,file)))!==hash)throw Error('Frozen ground truth/fixture drift');
const manifest=JSON.parse(await fs.readFile(path.join(base,'fixtures/cases.json'),'utf8'));
const cases=manifest.cases.filter(c=>c.split===split),rows=[];
async function matches(owner,candidate,selectors){
  if(!candidate)return false;
  const frame=owner.page.frames()[candidate.frameIndex];
  try{return await frame.locator(candidate.selector).evaluate((e,selectors)=>selectors.some(s=>e.matches(s)),selectors);}catch{return false;}
}
for(const c of cases){
  let owner;const caseStart=performance.now(),wallStart=Date.now();
  const record={id:c.id,split,expected:c};
  try {
    owner=await OwnedBrowser.create({projectRoot:c.fixture==='existing'?path.join(repo,'Benchmarks/tasks'):path.join(base,'fixtures/components'),
      width:c.width||1100,height:800,dpr:c.dpr||1,route:c.fixture==='existing'?`/?task=${c.task}`:`/${c.query||''}`,
      developmentRegistry:c.fixture==='components'?'src/dev-source.js':null});
    for(const action of c.actions||[]){if(action==='open-dropdown')await owner.page.click('#toggle');if(action==='focus-button')await owner.page.keyboard.press('Tab');}
    if(c.cssZoom)await owner.page.evaluate(z=>document.documentElement.style.zoom=String(z),c.cssZoom);
    if(c.pageScale){const session=await owner.context.newCDPSession(owner.page);await session.send('Emulation.setPageScaleFactor',{pageScaleFactor:c.pageScale});}
    if(c.scrollTarget)await owner.page.locator(c.target).scrollIntoViewIfNeeded();
    const captureStart=performance.now();
    const snapshot=await owner.capture({id:c.id,path:path.join(output,`${c.id}.png`)});
    record.captureMS=performance.now()-captureStart;record.snapshot=snapshot;
    let region=c.rectangle;
    if(!region){const locator=c.innerTarget?owner.page.frameLocator(c.target).locator(c.innerTarget):owner.page.locator(c.target);
      let box=await locator.boundingBox();if(!box)throw Error('Label target has no visible box');
      if(c.fraction){const f=c.fraction;box={x:box.x+f.x*box.width,y:box.y+f.y*box.height,width:box.width*f.width,height:box.height*f.height};}
      region=normalizedRectangle(box,snapshot);
    }
    record.annotation={frameID:c.id,issueID:'CL-001',region,category:c.category};
    if(c.afterCapture==='resize')await owner.page.setViewportSize({width:(c.width||1100)+100,height:800});
    if(c.afterCapture==='mutate')await owner.page.locator('#save').evaluate(e=>e.setAttribute('data-changed','true'));
    record.mapping=await mapAnnotation(owner,snapshot,record.annotation);
    const mapping=record.mapping,all=[...(c.expectedDOM||[]),...(c.acceptableAncestor||[])];
    record.domStrictTop1=mapping.status==='mapped'&&await matches(owner,mapping.element,c.expectedDOM||[]);
    record.domTop1=mapping.status==='mapped'&&await matches(owner,mapping.element,all);
    record.domTop3=false;
    if(mapping.status==='mapped')for(const candidate of mapping.candidates)if(await matches(owner,candidate,all))record.domTop3=true;
    record.sourceTop1=Boolean(c.expectedSources?.includes(mapping.sourceCandidates[0]?.file));
    record.sourceTop3=mapping.sourceCandidates.some(s=>c.expectedSources?.includes(s.file));
    record.highConfidenceSources=mapping.sourceCandidates.filter(s=>s.confidence==='high').map(s=>({file:s.file,kind:s.kind,
      relevantFile:c.expectedSources.includes(s.file),expectedRule:!c.expectedRules.length||c.expectedRules.includes(s.selector),line:s.line??null}));
    record.correctDOMAbstention=Boolean(c.expectAbstain&&mapping.status==='unavailable');
    record.correctSourceAbstention=Boolean((c.expectAbstain||c.expectSourceAbstain)&&mapping.sourceCandidates.length===0);
    record.payloadBytes=Buffer.byteLength(JSON.stringify(mapping));
    record.status='evaluated';
  }catch(error){record.status='infrastructure-error';record.error=error.stack;}
  finally{if(owner)await owner.close();record.totalCaseMonotonicMS=performance.now()-caseStart;record.totalCaseUTCMS=Date.now()-wallStart;rows.push(record);}
}
const evaluated=rows.filter(r=>r.status==='evaluated'),domPositive=evaluated.filter(r=>!r.expected.expectAbstain),sourcePositive=evaluated.filter(r=>r.expected.expectedSources.length),high=evaluated.flatMap(r=>r.highConfidenceSources);
const rate=(n,d)=>({correct:n,total:d,rate:d?n/d:null});
const values=key=>evaluated.map(r=>key==='runtimeMS'?r.mapping.runtimeMS:r[key]).sort((a,b)=>a-b);
const distribution=key=>{const v=values(key);return {n:v.length,mean:v.reduce((a,b)=>a+b,0)/v.length,median:v[Math.floor(v.length/2)],min:v[0],max:v.at(-1)};};
const result={kind:'actual-local-mapping-evaluation-not-agent-trials',split,measuredAt:new Date().toISOString(),groundTruthSHA256:freeze.files['fixtures/cases.json'],
  labelledCases:cases.length,evaluatedCases:evaluated.length,infrastructureErrors:rows.filter(r=>r.status!=='evaluated').map(r=>({id:r.id,error:r.error})),
  metrics:{elementStrictTop1:rate(domPositive.filter(r=>r.domStrictTop1).length,domPositive.length),elementSemanticTop1:rate(domPositive.filter(r=>r.domTop1).length,domPositive.length),elementSemanticTop3:rate(domPositive.filter(r=>r.domTop3).length,domPositive.length),
    sourceFileTop1:rate(sourcePositive.filter(r=>r.sourceTop1).length,sourcePositive.length),sourceFileTop3:rate(sourcePositive.filter(r=>r.sourceTop3).length,sourcePositive.length),
    DOMCoverage:rate(evaluated.filter(r=>r.mapping.status==='mapped').length,evaluated.length),sourceCoverage:rate(evaluated.filter(r=>r.mapping.sourceCandidates.length).length,evaluated.length),
    highConfidenceFilePrecision:rate(high.filter(r=>r.relevantFile).length,high.length),incorrectHighConfidenceFiles:high.filter(r=>!r.relevantFile).length,
    highConfidenceRulePrecision:rate(high.filter(r=>r.relevantFile&&r.expectedRule).length,high.length),
    correctDOMAbstentions:rate(evaluated.filter(r=>r.correctDOMAbstention).length,evaluated.filter(r=>r.expected.expectAbstain).length),
    correctSourceAbstentions:rate(evaluated.filter(r=>r.correctSourceAbstention).length,evaluated.filter(r=>r.expected.expectAbstain||r.expected.expectSourceAbstain).length),
    runtimeMS:distribution('runtimeMS'),captureMS:distribution('captureMS'),metadataBytes:distribution('payloadBytes')},
  groundTruthPolicy:'DOM rates exclude cases labelled for DOM abstention; source accuracy excludes unavailable-source labels. Coverage includes all evaluated cases. Candidate precision counts all supplied high-confidence source references. Top-3 is bounded, not arbitrary candidate recall.',
  newModelCalls:0,rows};
await fs.writeFile(path.join(output,'results.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({split,cases:cases.length,infrastructureErrors:result.infrastructureErrors,metrics:result.metrics},null,2));
