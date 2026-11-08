import path from 'node:path';
import {OwnedBrowser} from '../../visual-to-code/src/browser-adapter/owned-browser.mjs';
export async function openFixture(root,route,{width=1200,dpr=1,plain=false}={}){
  const owner=await OwnedBrowser.create({projectRoot:path.join(root,plain?'dist-plain':'dist'),route,width,height:900,dpr});
  owner.page.setDefaultTimeout(2000);
  await owner.page.locator('h1').waitFor();
  return owner;
}
export async function setup(owner,task){
  if(task.setup==='publish-dialog')await owner.page.click('#review-update');
  if(task.setup==='project-filter')await owner.page.click('#project-filter-trigger');
}
