// Render completed fixture fixes only after timed trials finish. No external application capture.
import fs from 'node:fs/promises';
import path from 'node:path';
import {launchBrowser,serve} from './browser.mjs';

const root=path.resolve(process.argv[2] || 'Benchmarks/reports/lean-handoff/comparison');
const output=path.join(root,'visual-review');
await fs.mkdir(output,{recursive:true});
const browser=await launchBrowser(),rows=[];
try {
  for(const entry of (await fs.readdir(root,{withFileTypes:true})).filter(e=>e.isDirectory()).sort((a,b)=>a.name.localeCompare(b.name))) {
    const folder=path.join(root,entry.name);
    let result;try {result=JSON.parse(await fs.readFile(path.join(folder,'result.json'),'utf8'));}catch {continue;}
    if(!result.success)continue;
    const server=await serve(path.join(folder,'project'));
    const page=await browser.newPage({viewport:{width:result.task==='05'?390:1100,height:800}});
    const record={task:result.task,condition:result.condition,trial:result.trial,source:entry.name,images:[]};
    try {
      await page.goto(`${server.url}/?task=${result.task}`);
      if(result.task==='04') {await page.click('#toggle');await page.click('#search');await page.fill('#search','demo');}
      if(result.task==='08') {await page.fill('#email','invalid');await page.click('#submit');}
      if(result.task==='10') {await page.click('#increment');await page.click('#increment');}
      const snapshot=path.join(output,`${entry.name}.png`);
      await page.screenshot({path:snapshot});record.images.push(path.relative(root,snapshot));
      if(result.task==='04' || result.task==='08') {
        if(result.task==='04')await page.click('h1');
        else {await page.fill('#email','test@example.test');await page.click('#submit');}
        const next=path.join(output,`${entry.name}-next-state.png`);
        await page.screenshot({path:next});record.images.push(path.relative(root,next));
      }
      record.status='rendered';
    }catch(error) {record.status='failed-to-render';record.error=error.message;}
    finally {await page.close();await server.close();}
    rows.push(record);
  }
}finally {await browser.close();}
await fs.writeFile(path.join(output,'renders.json'),JSON.stringify({kind:'post-trial-fixture-renders',scope:'Generated fixture screenshots only; rendering is not itself an independent visual quality pass.',rows},null,2)+'\n');
console.log(`Rendered ${rows.length} completed fixture fixes to ${output}`);
