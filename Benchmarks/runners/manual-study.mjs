// No model calls. Hidden evaluator, controls and browser evidence for the new study.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {launchBrowser,serve} from './browser.mjs';
import {regressions} from './regressions.mjs';
const base=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const spec=JSON.parse(await fs.readFile(path.join(base,'manual-vs-contextlens-spec.json'),'utf8'));
const tasks=spec.tasks;

export async function targeted(page,url,task) {
  const id=task.id, checks=[];
  async function test(name,action) {
    try {await action();checks.push({check:name,passed:true});}
    catch(error) {checks.push({check:name,passed:false,error:error.message});}
  }
  async function load(width=1100) {await page.setViewportSize({width,height:800});await page.goto(`${url}/?task=${id}`);}
  async function visible(selector) {assert.ok(await page.locator(selector).isVisible(),`${selector} visible`);}
  if(id==='01' || id==='03') for(const width of task.widths) {
    await load(width);
    await test(`geometry-and-content-${width}`,async()=>{
      if(id==='01') {
        const a=await page.locator('.actions').boundingBox(),b=await page.locator('#confirm').boundingBox();
        assert.ok(Math.abs(a.x+a.width-b.x-b.width)<=2,'Confirm right aligned');
        const d=await page.locator('.dialog').boundingBox();
        assert.ok(b.x>=d.x && b.y>=d.y && b.x+b.width<=d.x+d.width && b.y+b.height<=d.y+d.height,'Button inside dialog');
        await visible('.dialog h2');await visible('.dialog p');await page.click('#confirm');
        assert.equal(await page.locator('.dialog h2').innerText(),'Publish changes?');
      } else {
        const a=await page.locator('.sidebar').boundingBox(),b=await page.locator('.content').boundingBox();
        assert.ok(b.x>=a.x+a.width+24,'Content separated from sidebar');
        const text=await page.locator('.content p').boundingBox();
        assert.ok(text.width>100 && text.x+text.width<=width,'Content readable within viewport');
        assert.ok((await page.locator('.sidebar').innerText()).includes('Projects'));
        assert.equal(await page.locator('.sidebar').evaluate(e=>getComputedStyle(e).position),'fixed');
      }
    });
  }
  if(id==='04') {
    await load();
    await test('open-inside-type-outside-reopen-toggle',async()=>{
      assert.equal(await page.locator('.dropdown').isVisible(),false);
      await page.click('#toggle');await visible('.dropdown');await page.click('#search');await visible('.dropdown');
      await page.fill('#search','demo projects');await page.keyboard.press('ArrowLeft');await page.keyboard.type('X');await visible('.dropdown');
      const query=await page.inputValue('#search');assert.equal(query,'demo projectXs');
      await page.click('h1');assert.equal(await page.locator('.dropdown').isVisible(),false);
      await page.click('#toggle');await visible('.dropdown');assert.equal(await page.inputValue('#search'),query);
      await page.click('#toggle');assert.equal(await page.locator('.dropdown').isVisible(),false);
      await page.click('#toggle');await page.click('#search');await visible('.dropdown');
    });
  }
  if(id==='05') for(const width of [390,1100,390]) {
    await load(width);
    await test(`navigation-geometry-and-links-${width}`,async()=>{
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No page overflow');
      const links=page.locator('nav a');assert.equal(await links.count(),4);
      for(const [i,hash] of ['home','projects','members','settings'].entries()) {
        const link=links.nth(i),b=await link.boundingBox();await visible(`nav a:nth-child(${i+1})`);
        assert.ok(b.width>0 && b.height>0 && b.x>=0 && b.x+b.width<=width,'Link inside viewport');
        await link.click();assert.equal(new URL(page.url()).hash,`#${hash}`);
      }
    });
  }
  if(id==='08') {
    await load();
    await test('initial-error-hidden',async()=>assert.equal(await page.locator('.error').isVisible(),false));
    // Interleave valid/invalid values without resetting; stale-state fixes must fail.
    const cases=task.invalid.flatMap((email,i)=>[[email,true],[task.valid[i%task.valid.length],false]]);
    for(const [email,errorExpected] of cases) await test(`email-${JSON.stringify(email)}-${errorExpected}`,async()=>{
      await page.fill('#email',email);await page.click('#submit');
      assert.equal(await page.locator('.error').isVisible(),errorExpected);
      assert.equal(await page.inputValue('#email'),email,'Submission must preserve input');
      assert.equal(new URL(page.url()).search,`?task=${id}`,'No submission navigation');
    });
  }
  if(id==='10') {
    await load();
    await test('repeated-clicks-and-reload',async()=>{
      assert.equal(await page.locator('#count').innerText(),'0');
      for(let i=1;i<=10;i++){await page.click('#increment');assert.equal(await page.locator('#count').innerText(),String(i));}
      await page.reload();assert.equal(await page.locator('#count').innerText(),'0');
    });
  }
  return checks;
}

export async function evaluate(root,ids=tasks.map(t=>t.id),screenshots=null) {
  const server=await serve(root),browser=await launchBrowser(),rows=[];
  const page=await browser.newPage();page.setDefaultTimeout(2500);const errors=[];page.on('pageerror',e=>errors.push(e.message));
  try {
    for(const id of ids) {
      const start=performance.now();
      const checks=await targeted(page,server.url,tasks.find(t=>t.id===id));
      checks.push({check:'no-target-javascript-errors',passed:errors.length===0,errors:[...errors]});errors.length=0;
      if(screenshots){await fs.mkdir(screenshots,{recursive:true});await page.screenshot({path:path.join(screenshots,`${id}.png`)});}
      rows.push({task:id,passed:checks.every(c=>c.passed),checks,duration_ms:performance.now()-start});
    }
  } finally {await browser.close();await server.close();}
  return rows;
}

async function validate(output) {
  await fs.mkdir(output,{recursive:true});
  const broken=await evaluate(path.join(base,'tasks'),undefined,path.join(output,'broken'));
  const temp=await fs.mkdtemp(path.join(os.tmpdir(),'contextlens-manual-controls-'));
  let fixed,guards;
  try {
    await fs.cp(path.join(base,'tasks'),temp,{recursive:true});
    await fs.appendFile(path.join(temp,'styles.css'),'\n.actions {justify-content:flex-end} .content {margin-left:264px} .mobile-nav {width:100%;flex-wrap:wrap}');
    let js=await fs.readFile(path.join(temp,'app.js'),'utf8');
    js=js.replace("document.addEventListener('click', () => dropdown.hidden = true);","document.addEventListener('click', e => {if(!dropdown.contains(e.target)) dropdown.hidden=true;});");
    js=js.replace("!document.querySelector('#email').value.includes('@')","!/^[^\\s@]+@[^\\s@.]+(?:\\.[^\\s@.]+)+$/.test(document.querySelector('#email').value)");
    js=js.replace("invalid ? 'none' : 'none'","invalid ? 'block' : 'none'");
    js=js.replace('count += 1;','count += 1; document.querySelector("#count").textContent=count;');
    await fs.writeFile(path.join(temp,'app.js'),js);
    fixed=await evaluate(temp,undefined,path.join(output,'known-good'));guards=await regressions(temp);
  } finally {await fs.rm(temp,{recursive:true,force:true});}
  const baselineGuards=await regressions(path.join(base,'tasks'));
  const weak=[];
  const prior=path.join(base,'reports/lean-handoff/comparison');
  for(const entry of await fs.readdir(prior,{withFileTypes:true})) {
    if(!entry.isDirectory())continue;
    let row;try{row=JSON.parse(await fs.readFile(path.join(prior,entry.name,'result.json'),'utf8'));}catch{continue;}
    if(row.task!=='08')continue;
    weak.push({source:entry.name,results:await evaluate(path.join(prior,entry.name,'project'),['08'])});
  }
  const report={kind:'evaluator-validation-not-agent-trials',measured_at:new Date().toISOString(),broken,fixed,baselineGuards,guards,priorEmailRecheck:weak};
  await fs.writeFile(path.join(output,'fixture-validation.json'),JSON.stringify(report,null,2)+'\n');
  assert.ok(broken.every(r=>!r.passed),'All six originals must fail');
  assert.ok(fixed.every(r=>r.passed),'All six known-good controls must pass');
  assert.ok([...guards,...baselineGuards].every(r=>r.passed),'Shared regression guards pass both controls');
  assert.ok(weak.filter(r=>!r.results[0].passed).length>=2,'Both prior weak email fixes must be rejected');
  console.log('Six broken fixtures rejected; six known-good controls and shared guards passed; prior weak email fixes rejected.');
}

async function prepare(output,cli) {
  const server=await serve(path.join(base,'tasks')),browser=await launchBrowser(),audit=[];
  await fs.mkdir(output,{recursive:true});
  try {
    for(const task of tasks) {
      const dir=path.join(output,'preparations',task.id);await fs.mkdir(path.join(dir,'raw'),{recursive:true});
      const page=await browser.newPage({viewport:{width:task.id==='05'?390:1100,height:800}});
      await page.goto(`${server.url}/?task=${task.id}`);const start=performance.now(),events=[];
      async function snap(name,event) {
        const imagePath=`raw/${name}.png`;await page.screenshot({path:path.join(dir,imagePath)});
        events.push({timestampMS:Math.round(performance.now()-start),imagePath,...(event?{event}:{})});
      }
      await snap('initial','fixture loaded');await page.waitForTimeout(250);await snap('unchanged');
      if(task.id==='04')await page.click('#toggle');
      if(task.id==='08'){await page.fill('#email','invalid');await page.click('#submit');}
      if(task.id==='10')await page.click('#increment');
      await snap('interaction','scripted fixture interaction');await page.waitForTimeout(550);await snap('settled');
      await fs.writeFile(path.join(dir,'events.json'),JSON.stringify(events,null,2)+'\n');
      function invoke(args){const r=spawnSync(cli,args,{encoding:'utf8'});assert.equal(r.status,0,r.stderr||r.stdout);}
      invoke(['replay',path.join(dir,'events.json'),path.join(dir,'session')]);
      const sessionFile=path.join(dir,'session/session.json'),session=JSON.parse(await fs.readFile(sessionFile,'utf8'));
      const selectors={'01':'#confirm','03':'.content','04':'.dropdown','05':'nav','08':'form','10':'#count'};
      const box=await page.locator(selectors[task.id]).boundingBox(),viewport=page.viewportSize();
      const frame=session.frames.at(-1),x=box.x/viewport.width,y=box.y/viewport.height;
      session.task=task.instruction;
      session.annotations=[{id:'CL-001',frameID:frame.id,kind:'rectangle',region:{x,y,width:Math.min(1-x,box.width/viewport.width),height:Math.min(1-y,box.height/viewport.height)},points:[],instruction:task.instruction,severity:'normal'}];
      session.nextIssueNumber=2;await fs.writeFile(sessionFile,JSON.stringify(session,null,2)+'\n');
      const cl=path.join(output,'packages',task.id,'contextlens'),manual=path.join(output,'packages',task.id,'manual-equivalent');
      await fs.mkdir(path.dirname(cl),{recursive:true});invoke(['export',path.join(dir,'session'),cl]);
      await fs.mkdir(path.join(manual,'screenshots'),{recursive:true});
      const names=['04','08','10'].includes(task.id)?['initial','interaction']:['initial'];
      for(const name of names)await fs.copyFile(path.join(dir,'raw',`${name}.png`),path.join(manual,'screenshots',`${name}.png`));
      const captions={initial:'Before interaction; fixture as opened.',interaction:task.id==='04'?'After opening the project filter.':task.id==='08'?'After submitting invalid (the expected error is missing).':'After clicking Add member once (the visible count remains zero).'};
      await fs.writeFile(path.join(manual,'task.md'),`Please fix this issue on route ?task=${task.id}.\n\n${task.instruction}\n\nScreenshots:\n${names.map(n=>`- screenshots/${n}.png — ${captions[n]}`).join('\n')}\n`);
      audit.push({task:task.id,instruction:task.instruction,manualScreenshots:names.map(n=>`screenshots/${n}.png`),contextlensFrames:session.frames.map(f=>f.id),exportOptions:'Current production defaults: annotated only, exclude duplicates',humanPreparationSeconds:null,difference:'Manual uses clear prose and full unmarked screenshots; ContextLens uses one annotated retained state, crop, lean context report and optional metadata. Same raw source pixels and requested outcome; no evaluator or solution attached.'});
      await page.close();
    }
  } finally {await browser.close();await server.close();}
  await fs.writeFile(path.join(output,'evidence-audit.json'),JSON.stringify({kind:'automated-fixture-evidence-not-human-observations',rows:audit},null,2)+'\n');
}

if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const [mode,root,...args]=process.argv.slice(2);
  if(mode==='validate')await validate(path.resolve(root));
  else if(mode==='prepare')await prepare(path.resolve(root),path.resolve(args[0]));
  else if(mode==='evaluate') {
    const result={target:await evaluate(path.resolve(root),[args[0]]),regressions:await regressions(path.resolve(root))};
    console.log(JSON.stringify(result));process.exit([...result.target,...result.regressions].every(r=>r.passed)?0:1);
  } else throw Error('Use validate OUTPUT, prepare OUTPUT CLI, or evaluate PROJECT TASK');
}
