import {mkdtemp, cp, readFile, writeFile, rm, mkdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {evaluate} from './acceptance.mjs';
import {regressions} from './regressions.mjs';
const base = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const catalog = JSON.parse(await readFile(path.join(base,'task-catalog.json'))), ids = catalog.map(t=>t.id);
const guards = await regressions(path.join(base,'tasks'));
assert.ok(guards.every(r=>r.passed), 'Regression guards must pass the starting fixture');
const broken = await evaluate(path.join(base,'tasks'), ids);
const root = await mkdtemp(path.join(tmpdir(),'contextlens-acceptance-'));
try {
  await cp(path.join(base,'tasks'),root,{recursive:true});
  let css = await readFile(path.join(root,'styles.css'),'utf8');
  // Known-good controls are evaluator-only and never present in an agent workspace.
  css += '\n.actions { justify-content:flex-end; } .cards { gap:20px; } .content { margin-left:264px; } .mobile-nav { width:100%; flex-wrap:wrap; } .tab.active { background:#68dfbc; color:#10251e; } .focus-target:focus-visible { outline:3px solid #68dfbc; outline-offset:4px; } .scroll-dialog { overflow-y:auto; }';
  let js = await readFile(path.join(root,'app.js'),'utf8');
  js = js.replace("document.addEventListener('click', () => dropdown.hidden = true);", "document.addEventListener('click', e => { if(!dropdown.contains(e.target)) dropdown.hidden = true; });");
  js = js.replace("invalid ? 'none' : 'none'", "invalid ? 'block' : 'none'");
  js = js.replace('count += 1;', "count += 1; document.querySelector('#count').textContent = count;");
  await writeFile(path.join(root,'styles.css'),css); await writeFile(path.join(root,'app.js'),js);
  const fixed = await evaluate(root, ids);
  const data = {kind:'fixture-validation', measured_at:new Date().toISOString(), broken, fixed, regression_guards:guards, note:'Known-good controls validate acceptance tests; these are not agent trials.'};
  await mkdir(path.join(base,'reports'),{recursive:true});
  await writeFile(path.join(base,'reports/fixture-validation.json'),JSON.stringify(data,null,2)+'\n');
  assert.ok(broken.every(r=>!r.passed), 'Every deliberately broken task must fail its acceptance test');
  assert.ok(fixed.every(r=>r.passed), 'Every known-good control must pass');
  console.log(`${broken.length} defects reproduced; ${fixed.length} known-good controls pass.`);
} finally { await rm(root,{recursive:true,force:true}); }
