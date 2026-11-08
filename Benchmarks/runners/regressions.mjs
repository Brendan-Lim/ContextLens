// Baseline-passing checks independent of the ten deliberately broken properties.
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {launchBrowser,serve} from './browser.mjs';
import assert from 'node:assert/strict';
export async function regressions(root) {
  const server=await serve(root), browser=await launchBrowser(), page=await browser.newPage({viewport:{width:1100,height:800}}), errors=[];
  page.on('pageerror',e=>errors.push(e.message));const checks=[];
  const selectors={'01':'#confirm','02':'.cards .card','03':'.sidebar','04':'#toggle','05':'nav a','06':'#activity','07':'#keyboard-action','08':'#email','09':'#accept','10':'#increment'};
  try {
    for(const [id,selector] of Object.entries(selectors)) {
      try { await page.goto(`${server.url}/?task=${id}`);assert.ok(await page.locator(selector).count()>0,'Task controls remain present');assert.equal(await page.locator('h1').innerText(),'Project overview');checks.push({check:`task-${id}-structure`,passed:true}); }
      catch(e) {checks.push({check:`task-${id}-structure`,passed:false,error:e.message});}
    }
    try {
      await page.goto(`${server.url}/?task=06`);await page.click('#activity');assert.equal(await page.locator('#tab-content').innerText(),'Activity panel');
      await page.goto(`${server.url}/?task=04`);await page.click('#toggle');assert.equal(await page.locator('.dropdown').isVisible(),true);await page.click('#toggle');assert.equal(await page.locator('.dropdown').isVisible(),false);
      checks.push({check:'shared-tab-and-menu-actions',passed:true});
    } catch(e) {checks.push({check:'shared-tab-and-menu-actions',passed:false,error:e.message});}
    checks.push({check:'no-javascript-exceptions',passed:errors.length===0,errors});
  } finally {await browser.close();await server.close();}
  return checks;
}
if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {const rows=await regressions(path.resolve(process.argv[2]));console.log(JSON.stringify(rows));process.exit(rows.every(r=>r.passed)?0:1);}
