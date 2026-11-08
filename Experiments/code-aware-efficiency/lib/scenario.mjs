import {observeProbe} from './mapper.mjs';
import {setup} from './browser.mjs';
export async function scenario(owner,task,{id='frame-001',path=null,noProbe=false}={}){
  await setup(owner,task);
  if(task.mechanism==='validation')await owner.page.fill('#owner-email','invalid@');
  let before=await owner.capture({id:id+'-before'}),proof=null;
  if(task.mechanism!=='alignment'&&!noProbe){
    proof=await observeProbe(owner,before,task.mechanism,async()=>{
      if(task.mechanism==='dismissal')await owner.page.locator('#project-search').evaluate(e=>e.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true})));
      if(task.mechanism==='state-update')await owner.page.click('#allocate-seats');
      if(task.mechanism==='validation')await owner.page.click('#save-contact');
    });
    if(task.mechanism==='dismissal'&&!await owner.page.locator('#project-search').count())await owner.page.click('#project-filter-trigger');
  }
  const snapshot=await owner.capture({id,path});return {snapshot,proof,before};
}
