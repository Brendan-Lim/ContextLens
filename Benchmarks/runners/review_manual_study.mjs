// Post-trial render evidence; no model calls or fixture edits.
import fs from 'node:fs/promises';
import path from 'node:path';
import {launchBrowser,serve} from './browser.mjs';
const root=path.resolve(process.argv[2]),output=path.join(root,'visual-review');
await fs.mkdir(output,{recursive:true});
const browser=await launchBrowser(),rows=[],sidebar=[];
try {
  for(const entry of await fs.readdir(path.join(root,'trials'),{withFileTypes:true})) {
    if(!entry.isDirectory())continue;
    const folder=path.join(root,'trials',entry.name);
    const result=JSON.parse(await fs.readFile(path.join(folder,'result.json'),'utf8'));
    const page=await browser.newPage({viewport:{width:result.task==='05'?390:1100,height:800}});
    const server=await serve(path.join(folder,'project')),images=[];
    async function snap(state) {
      const image=path.join(output,`${entry.name}-${state}.png`);await page.screenshot({path:image});images.push(path.relative(root,image));
    }
    try {
      await page.goto(`${server.url}/?task=${result.task}`);
      if(result.task==='04'){await page.click('#toggle');await page.click('#search');await page.fill('#search','demo');}
      if(result.task==='08'){await page.fill('#email','invalid@');await page.click('#submit');}
      if(result.task==='10'){await page.click('#increment');await page.click('#increment');}
      if(result.task==='03') {
        const boxes=await page.evaluate(()=>{
          const box=s=>{const r=document.querySelector(s).getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};
          return {sidebar:box('.sidebar'),content:box('.content'),paragraph:box('.content p'),heading:box('header h1')};
        });
        sidebar.push({trial:entry.name,boxes,contentBoxGap:boxes.content.x-boxes.sidebar.x-boxes.sidebar.width,
          paragraphGap:boxes.paragraph.x-boxes.sidebar.x-boxes.sidebar.width,primaryAccepted:result.success});
      }
      await snap('primary');
      if(result.task==='04'){await page.click('h1');await snap('closed');}
      if(result.task==='08'){await page.fill('#email','name+tag@example.test');await page.click('#submit');await snap('valid');}
      rows.push({trial:entry.name,images,rendered:true,accepted:result.success,inspected:false});
    }catch(error){rows.push({trial:entry.name,images,rendered:false,error:error.message});}
    finally {await page.close();await server.close();}
  }
}finally{await browser.close();}
await fs.writeFile(path.join(output,'renders.json'),JSON.stringify({kind:'post-trial-fixture-renders-not-human-visual-acceptance',rows},null,2)+'\n');
await fs.writeFile(path.join(output,'sidebar-geometry.json'),JSON.stringify({kind:'exploratory-post-study-box-versus-text-audit',pre_registered:false,
  scope:'Added after inspecting the first sidebar failure. Measures geometry only; does not change the frozen border-box acceptance criterion or primary scores.',rows:sidebar},null,2)+'\n');
console.log(`Rendered ${rows.length} revised trial projects.`);
