import {mkdir, readFile, writeFile, copyFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {launchBrowser, serve} from './browser.mjs';
const base = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const cli = path.join(base,'../dist/contextlens-cli');
const output = path.resolve(process.argv[2] || path.join(base,'reports/browser-evidence'));
const catalog = JSON.parse(await readFile(path.join(base,'task-catalog.json')));
const selector = {'01':'#confirm','02':'.cards','03':'.content','04':'.dropdown','05':'.mobile-nav','06':'#overview','07':'#keyboard-action','08':'.error','09':'.scroll-dialog','10':'#count'};
const server = await serve(path.join(base,'tasks')); const browser = await launchBrowser();
const strategy = [];
await mkdir(output,{recursive:true});
await writeFile(path.join(base,'reports/capture-environment.json'),JSON.stringify({node:process.version,browser:browser.version(),platform:process.platform,arch:process.arch,playwright:'1.62.1',measured_at:new Date().toISOString()},null,2)+'\n');
try {
  for (const task of catalog) {
    const dir = path.join(output,task.id); await mkdir(path.join(dir,'raw'),{recursive:true});
    const page = await browser.newPage({viewport:{width:task.id==='05'?390:1100,height:800}});
    await page.goto(`${server.url}/?task=${task.id}`);
    const clock = performance.now(), events=[];
    async function snap(name,event) {
      const imagePath = `raw/${name}.png`; await page.screenshot({path:path.join(dir,imagePath)});
      events.push({timestampMS:Math.round(performance.now()-clock),imagePath,...(event?{event}: {})});
    }
    await snap('initial','fixture loaded');
    await page.waitForTimeout(250); await snap('unchanged');
    if(task.id==='04') await page.click('#toggle');
    if(task.id==='07') await page.keyboard.press('Tab');
    if(task.id==='08') {await page.fill('#email','invalid'); await page.click('#submit');}
    if(task.id==='10') await page.click('#increment');
    await snap('interaction', 'scripted benchmark interaction; typed characters are not event metadata');
    await page.waitForTimeout(500); await snap('settled');
    // Missing error element has no visible box; mark the containing form instead.
    let region = await page.locator(selector[task.id]).boundingBox();
    if(!region) region = await page.locator('form').boundingBox();
    const viewport = page.viewportSize();
    const x=Math.max(0,Math.min(0.99,region.x/viewport.width)),y=Math.max(0,Math.min(0.99,region.y/viewport.height));
    const normalized = {x,y,width:Math.min(1-x,Math.max(.01,region.width/viewport.width)),height:Math.min(1-y,Math.max(.01,region.height/viewport.height))};
    await writeFile(path.join(dir,'events.json'),JSON.stringify(events,null,2)+'\n');
    const source=path.join(dir,'source-session'), pkg=path.join(dir,'contextlens');
    function invoke(args) { const r=spawnSync(cli,args,{encoding:'utf8'}); if(r.status!==0) throw Error(r.stderr || r.stdout); }
    invoke(['replay',path.join(dir,'events.json'),source]);
    const s=JSON.parse(await readFile(path.join(source,'session.json')));
    const frame=s.frames.at(-1);
    s.annotations=[{id:'CL-001',frameID:frame.id,kind:'rectangle',region:normalized,points:[],instruction:task.instruction,severity:'normal'}]; s.nextIssueNumber=2;
    await writeFile(path.join(source,'session.json'),JSON.stringify(s,null,2)+'\n'); invoke(['export',source,pkg,'--all-frames','--keep-duplicates']);
    await writeFile(path.join(pkg,'task.md'),`Fix this issue in the fixture route ?task=${task.id}: ${task.instruction}\nRead manifest.json and context.md; open the relevant crop first, then expand to wider evidence as needed.\n`);
    const auto=path.join(dir,'auto-only'); await mkdir(path.join(auto,'frames'),{recursive:true});
    // Same selected capture states, with only simple captions and the identical task instruction.
    for(const f of s.frames) await copyFile(path.join(source,f.imagePath),path.join(auto,f.imagePath));
    await writeFile(path.join(auto,'task.md'),`Fix this issue in the fixture route ?task=${task.id}: ${task.instruction}\n\nOrdered screenshots:\n${s.frames.map(f=>`${f.timestampMS} ms: ${f.imagePath}${f.event?' — '+f.event:''}`).join('\n')}\n`);
    const manifest=JSON.parse(await readFile(path.join(pkg,'manifest.json')));
    const allPaths=events.map(e=>path.join(dir,e.imagePath));
    const dedupPaths=manifest.frames.map(f=>path.join(pkg,f.imagePath));
    const annotatedPaths=manifest.issues.map(i=>path.join(pkg,i.annotatedPath));
    const manifestPaths=['manifest.json','context.md'].map(p=>path.join(pkg,p));
    for(const [name,paths] of [['all-frames',allPaths],['deduplicated',dedupPaths],['annotated',annotatedPaths],['manifest-first',manifestPaths]]) {
      let bytes=0; for(const p of paths) bytes+=(await readFile(p)).length;
      strategy.push({kind:'measured-filesystem-payload',task:task.id,strategy:name,initial_image_count:name==='manifest-first'?0:paths.length,initial_payload_bytes:bytes,input_tokens:null,output_tokens:null,agent_runtime_seconds:null,task_success:null,note:'Automated fixture, not an operator timing or agent trial. Manifest-first excludes optional image reads; initial payload sizes do not predict token usage.'});
    }
    await page.close();
  }
  await writeFile(path.join(base,'reports/strategy-measurements.json'),JSON.stringify(strategy,null,2)+'\n');
  console.log(`Captured ${catalog.length} browser fixture sessions; measured initial filesystem payload for four strategies.`);
} finally { await browser.close(); await server.close(); }
