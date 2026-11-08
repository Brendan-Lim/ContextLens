// Post-study held-out quality audit. Does not replace the frozen primary evaluator or edit fixes.
import fs from 'node:fs/promises';
import path from 'node:path';
import {launchBrowser,serve} from './browser.mjs';
const root=path.resolve(process.argv[2] || 'Benchmarks/reports/lean-handoff/comparison');
const cases=[['invalid@',true],['@example.test',true],['two@@example.test',true],['bad address@example.test',true],['test@example.test',false],['name+tag@example.test',false]];
const browser=await launchBrowser(),rows=[];
try {
  for(const entry of (await fs.readdir(root,{withFileTypes:true})).filter(e=>e.isDirectory())) {
    const folder=path.join(root,entry.name);let result;
    try {result=JSON.parse(await fs.readFile(path.join(folder,'result.json'),'utf8'));}catch {continue;}
    if(result.task!=='08')continue;
    const server=await serve(path.join(folder,'project')),page=await browser.newPage();
    const checks=[];
    try {
      for(const [email,errorExpected] of cases) {
        await page.goto(`${server.url}/?task=08`);await page.fill('#email',email);await page.click('#submit');
        const errorVisible=await page.locator('.error').isVisible();
        checks.push({email,errorExpected,errorVisible,passed:errorVisible===errorExpected});
      }
    }finally {await page.close();await server.close();}
    rows.push({source:entry.name,condition:result.condition,trial:result.trial,checks,passed:checks.every(r=>r.passed)});
  }
}finally {await browser.close();}
const report={kind:'post-study-email-holdout-audit',pre_registered:false,
  scope:'Exploratory broader quality audit added after patch inspection. Original target/regression results and timings are retained unchanged. No fixes edited and no model calls.',
  cases,rows};
await fs.writeFile(path.join(root,'email-holdout-audit.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(rows.map(({condition,trial,passed})=>({condition,trial,passed}))));
