// Evaluator lives outside each agent's isolated project. It is never copied to that project.
import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {launchBrowser, serve} from './browser.mjs';
export async function check(page, url, id) {
  await page.setViewportSize({width: id === '05' ? 390 : 1100, height: 800});
  await page.goto(`${url}/?task=${id}`);
  const box = selector => page.locator(selector).boundingBox();
  switch(id) {
    case '01': {
      const a = await box('.actions'), b = await box('#confirm'); assert.ok(Math.abs(a.x+a.width-b.x-b.width) <= 2, 'Confirm must align right'); break;
    }
    case '02': {
      const a = await box('.card:nth-child(1)'), b = await box('.card:nth-child(2)'); assert.ok(Math.abs(b.x-a.x-a.width-20) <= 1, 'Card gap must be 20px'); break;
    }
    case '03': { const a = await box('.sidebar'), b = await box('.content'); assert.ok(b.x >= a.x+a.width+24, 'Sidebar must not overlap content'); break; }
    case '04': {
      await page.click('#toggle'); await page.click('#search');
      assert.equal(await page.locator('.dropdown').isVisible(), true, 'Inside click must keep dropdown open');
      await page.fill('#search', 'demo'); await page.click('h1');
      assert.equal(await page.locator('.dropdown').isVisible(), false, 'Outside click must close dropdown'); break;
    }
    case '05': {
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No horizontal page overflow');
      for (const link of await page.locator('nav a').all()) { const b = await link.boundingBox(); assert.ok(b.x >= 0 && b.x+b.width <= 390, 'Links fit viewport'); } break;
    }
    case '06': {
      const style = s => page.locator(s).evaluate(e => { const c = getComputedStyle(e); return [c.backgroundColor,c.color,c.borderBottomColor,c.fontWeight].join('|'); });
      assert.notEqual(await style('#overview'), await style('#activity'), 'Active tab differs');
      await page.click('#activity'); assert.equal(await page.locator('#tab-content').innerText(), 'Activity panel');
      assert.notEqual(await style('#overview'), await style('#activity'), 'Active appearance follows selection'); break;
    }
    case '07': {
      await page.keyboard.press('Tab'); assert.equal(await page.locator('#keyboard-action').evaluate(e => e === document.activeElement), true);
      const focus = await page.locator('#keyboard-action').evaluate(e => { const s = getComputedStyle(e); return {outline: s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) >= 2, shadow: s.boxShadow !== 'none'}; });
      assert.ok(focus.outline || focus.shadow, 'Visible keyboard focus'); break;
    }
    case '08': {
      await page.fill('#email', 'invalid'); await page.click('#submit'); assert.equal(await page.locator('.error').isVisible(), true, 'Invalid email shows error');
      await page.fill('#email', 'test@example.test'); await page.click('#submit'); assert.equal(await page.locator('.error').isVisible(), false, 'Valid email clears error'); break;
    }
    case '09': {
      const scroll = await page.locator('.scroll-dialog').evaluate(e => { e.scrollTop = e.scrollHeight; return {top:e.scrollTop, overflow:getComputedStyle(e).overflowY}; });
      assert.ok(['auto','scroll'].includes(scroll.overflow) && scroll.top > 0, 'Dialog must scroll');
      const a = await box('.scroll-dialog'), b = await box('#accept'); assert.ok(b.y >= a.y && b.y+b.height <= a.y+a.height, 'Accept is reachable'); await page.click('#accept'); break;
    }
    case '10': await page.click('#increment'); await page.click('#increment'); assert.equal(await page.locator('#count').innerText(), '2', 'Counter reflects state'); break;
    default: throw Error('Unknown task');
  }
}
export async function evaluate(root, ids) {
  const server = await serve(root), browser = await launchBrowser();
  const page = await browser.newPage(); const results = [];
  try {
    for (const id of ids) {
      const start = performance.now();
      try { await check(page, server.url, id); results.push({task:id, passed:true, duration_ms:performance.now()-start}); }
      catch(error) { results.push({task:id, passed:false, error:error.message, duration_ms:performance.now()-start}); }
    }
  } finally { await browser.close(); await server.close(); }
  return results;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const rows = await evaluate(path.resolve(process.argv[2]), process.argv.slice(3));
  console.log(JSON.stringify(rows)); process.exit(rows.every(r=>r.passed) ? 0 : 1);
}
