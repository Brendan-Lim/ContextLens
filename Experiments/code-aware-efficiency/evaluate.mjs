// Frozen independent evaluator: never copied into agent workspaces.
import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {openFixture} from './lib/browser.mjs';
async function visit(page,origin,route){await page.goto(origin+'/'+route);await page.reload();await page.locator('h1').waitFor();}

export async function target(page,id,origin){
  if(id==='publish-actions')for(const width of [900,1200]){
    await page.setViewportSize({width,height:900});await visit(page,origin,'#/projects');await page.click('#review-update');
    const row=await page.locator('#publish-footer [data-action-cluster]').boundingBox(),button=await page.locator('#publish-confirm').boundingBox();
    assert.ok(Math.abs(row.x+row.width-button.x-button.width)<=2,'Publish aligns to the action row right edge');
    assert.ok(await page.getByText('The current project summary will be visible to your workspace.').isVisible());
    await page.getByText('Keep editing',{exact:true}).click();assert.equal(await page.getByRole('dialog').count(),0);
    await page.click('#review-update');await page.click('#publish-confirm');assert.ok(await page.getByText('Update published.',{exact:true}).isVisible());
    await page.click('#review-update');await page.getByLabel('Close dialog').click();assert.equal(await page.getByRole('dialog').count(),0);
  }
  if(id==='project-filter'){
    await visit(page,origin,'#/projects');await page.click('#project-filter-trigger');await page.click('#project-search');
    assert.ok(await page.locator('#project-filter-panel').isVisible(),'Inside click keeps filter open');
    await page.fill('#project-search','Atlas');assert.ok(await page.locator('#project-filter-panel').isVisible());
    assert.equal(await page.locator('#project-grid h2').allTextContents().then(a=>a.join(',')),'Atlas launch');
    await page.click('h1');assert.equal(await page.locator('#project-filter-panel').count(),0);
    await page.click('#project-filter-trigger');assert.equal(await page.inputValue('#project-search'),'Atlas');
    await page.click('#project-filter-trigger');assert.equal(await page.locator('#project-filter-panel').count(),0);
    await page.click('#project-filter-trigger');await page.click('#project-search');await page.fill('#project-search','');
    assert.equal(await page.locator('#project-grid h2').count(),4);
  }
  if(id==='seat-allocation'){
    await visit(page,origin,'#/team');assert.equal(await page.locator('#allocated-seats').innerText(),'12');
    await page.click('#allocate-seats');assert.equal(await page.locator('#allocated-seats').innerText(),'17','First allocation adds five');
    await page.click('#allocate-seats');assert.equal(await page.locator('#allocated-seats').innerText(),'22');
    await page.click('#release-seat');assert.equal(await page.locator('#allocated-seats').innerText(),'21');
    for(let i=0;i<23;i++)await page.click('#release-seat');assert.equal(await page.locator('#allocated-seats').innerText(),'0');
    await page.click('#allocate-seats');assert.equal(await page.locator('#allocated-seats').innerText(),'5');
    await page.click('#reserve-seat');assert.equal(await page.locator('#reserved-seats').innerText(),'4 draft invitations');
  }
  if(id==='contact-validation'){
    await visit(page,origin,'#/settings');const form=page.locator('#contact-form');
    assert.equal(await form.getByRole('alert').count(),0);
    const invalid=['','invalid','invalid@','@example.test','two@@example.test','bad address@example.test','name@example','name@.test','name@example..test','name@example.test '];
    const valid=['test@example.test','name+tag@example.test','first.last@sub.example.test'];
    for(const [i,bad] of invalid.entries())for(const [value,error] of [[bad,true],[valid[i%valid.length],false]]){
      await page.fill('#owner-email',value);await page.click('#save-contact');
      assert.equal(await form.getByRole('alert').count(),error?1:0,`Feedback for ${JSON.stringify(value)}`);
      assert.equal(await page.inputValue('#owner-email'),value);assert.equal(new URL(page.url()).hash,'#/settings');
    }
    const weekly=page.getByLabel('Weekly summary');await weekly.uncheck();assert.equal(await weekly.isChecked(),false);
  }
}
export async function regressions(page,origin){
  const results=[];
  async function check(name,fn){try{await fn();results.push({check:name,passed:true});}catch(e){results.push({check:name,passed:false,error:e.message});}}
  await check('all_routes_and_shared_layout',async()=>{
    for(const [route,title] of [['projects','Project workspace'],['team','Team capacity'],['settings','Workspace settings'],['reports','Delivery reports']]){
      await visit(page,origin,'#/'+route);assert.equal(await page.locator('h1').innerText(),title);assert.equal(await page.locator('.nav-rail a').count(),4);assert.ok(await page.locator('.workspace-footer').isVisible());
    }
  });
  await check('report_decoys_are_working_features',async()=>{
    await visit(page,origin,'#/reports');await page.selectOption('#report-period','Monthly');assert.equal(await page.getByText('Monthly performance snapshot',{exact:true}).count(),2);
    await page.click('#review-report');await page.getByText('Cancel digest',{exact:true}).click();assert.equal(await page.getByRole('dialog').count(),0);
  });
  await check('separate_team_reservation_and_filter',async()=>{
    await visit(page,origin,'#/team');await page.click('#reserve-seat');assert.equal(await page.locator('#reserved-seats').innerText(),'4 draft invitations');
    await page.click('#team-filter');assert.ok(await page.getByLabel('Team role').isVisible());await page.getByLabel('Team role').selectOption('Engineering');
    await page.click('#team-filter');assert.equal(await page.getByLabel('Team role').count(),0);
  });
  await check('notification_controls',async()=>{
    await visit(page,origin,'#/settings');await page.getByLabel('Mentions only').check();assert.equal(await page.getByLabel('Mentions only').isChecked(),true);
    await page.getByLabel('Weekly summary').uncheck();assert.equal(await page.getByLabel('Weekly summary').isChecked(),false);
  });
  return results;
}
export async function evaluate(root,only=null,{plain=false}={}){
  const owner=await openFixture(root,'/#/projects',{plain});const page=owner.page,errors=[];page.on('pageerror',e=>errors.push(e.message));
  const rows=[];
  try{
    for(const id of only?[only]:['publish-actions','project-filter','seat-allocation','contact-validation']){
      try{await target(page,id,owner.project.origin);rows.push({task:id,passed:true});}catch(e){rows.push({task:id,passed:false,error:e.message});}
    }
    const guards=await regressions(page,owner.project.origin);guards.push({check:'no_browser_exceptions',passed:errors.length===0,errors});
    return {targets:rows,regressions:guards};
  }finally{await owner.close();}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const result=await evaluate(path.resolve(process.argv[2]),process.argv[3]||null);
  console.log(JSON.stringify(result));process.exit([...result.targets,...result.regressions].every(r=>r.passed)?0:1);
}
