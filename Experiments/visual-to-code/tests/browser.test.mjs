import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {OwnedBrowser} from '../src/browser-adapter/owned-browser.mjs';
import {mapAnnotation} from '../src/browser-adapter/map.mjs';
import {normalizedRectangle} from '../src/geometry/coordinates.mjs';
const fixture=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../fixtures/components');

test('privacy, explicit dev-metadata trust, identity, redaction and stale source safeguards',async()=>{
  const temp=await fs.mkdtemp(path.join(os.tmpdir(),'contextlens-mapper-privacy-'));
  let owner;
  try{
    await fs.cp(fixture,temp,{recursive:true});owner=await OwnedBrowser.create({projectRoot:temp});
    await owner.page.fill('#project-name','NEVER_COLLECT_FORM_VALUE');
    let snap=await owner.capture({id:'privacy'}),box=await owner.page.locator('#project-name').boundingBox();
    let annotation={frameID:snap.id,region:normalizedRectangle(box,snap),category:'spacing'};
    let mapped=await mapAnnotation(owner,snap,annotation);
    assert.equal(mapped.status,'mapped');assert.ok(!JSON.stringify(mapped).includes('NEVER_COLLECT_FORM_VALUE'));
    const buttonBox=await owner.page.locator('#save').boundingBox();
    const noTrust=await mapAnnotation(owner,snap,{frameID:snap.id,region:normalizedRectangle(buttonBox,snap),category:'interaction'});
    assert.equal(noTrust.status,'mapped',JSON.stringify(noTrust));
    assert.equal(noTrust.sourceStatus,'unavailable','page-provided dev hooks are ignored without explicit local opt-in');
    assert.equal((await mapAnnotation(owner,snap,{...annotation,frameID:'wrong'})).reason,'screenshot_identity_mismatch');
    assert.equal((await mapAnnotation(owner,snap,{...annotation,redactedFrame:true})).reason,'redacted_frame_browser_metadata_omitted');
    assert.equal((await mapAnnotation(owner,{...snap},annotation)).reason,'unknown_page_or_screenshot');
    await fs.appendFile(path.join(temp,'styles/controls.css'),'\n/* changed source after snapshot */\n');
    assert.equal((await mapAnnotation(owner,snap,annotation)).reason,'stale_source_assets');
  }finally{await owner?.close();await fs.rm(temp,{recursive:true,force:true});}
});

test('hostile development paths cannot escape the selected project',async()=>{
  const owner=await OwnedBrowser.create({projectRoot:fixture,developmentRegistry:'src/dev-source.js'});
  try{
    await owner.page.evaluate(()=>window.contextLensDevelopmentSources={version:1,get:()=>({moduleURL:'file:///etc/passwd',exportName:'SaveButton'})});
    const snap=await owner.capture({id:'hostile'}),box=await owner.page.locator('#save').boundingBox();
    const mapped=await mapAnnotation(owner,snap,{frameID:snap.id,region:normalizedRectangle(box,snap),category:'interaction'});
    assert.equal(mapped.status,'mapped');assert.equal(mapped.sourceStatus,'unavailable');
    assert.ok(!JSON.stringify(mapped).includes('/etc/passwd'));
  }finally{await owner.close();}
});

test('resize recovery requires a new calibrated capture',async()=>{
  const owner=await OwnedBrowser.create({projectRoot:fixture});
  try{
    const old=await owner.capture({id:'before-resize'}),oldBox=await owner.page.locator('#save').boundingBox();
    await owner.page.setViewportSize({width:780,height:600});
    assert.equal((await mapAnnotation(owner,old,{frameID:old.id,region:normalizedRectangle(oldBox,old),category:'interaction'})).reason,'stale_dom_or_geometry');
    const fresh=await owner.capture({id:'after-resize'}),box=await owner.page.locator('#save').boundingBox();
    assert.equal((await mapAnnotation(owner,fresh,{frameID:fresh.id,region:normalizedRectangle(box,fresh),category:'interaction'})).status,'mapped');
  }finally{await owner.close();}
});
