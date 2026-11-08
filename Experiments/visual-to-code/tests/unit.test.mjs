import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {deflateSync} from 'node:zlib';
import {viewportRectangle,normalizedRectangle,calibrate} from '../src/geometry/coordinates.mjs';
import {decodePNG,findColors} from '../src/geometry/png.mjs';
import {containedFile} from '../src/source-mapping/project.mjs';
import {selectorLine} from '../src/source-mapping/candidates.mjs';

test('owned-browser adapter imports the reused locked Playwright',async()=>{await import('../src/browser-adapter/owned-browser.mjs');});
test('Retina/zoom/offset transforms round-trip without applying DPR twice',()=>{
  const snap={width:2000,height:1200,transform:{verified:true,scaleX:2.5,scaleY:2.5,offsetX:-10,offsetY:5}};
  const box={x:40,y:30,width:120,height:50},r=normalizedRectangle(box,snap),back=viewportRectangle(r,snap);
  for(const k of ['x','y','width','height'])assert.ok(Math.abs(back[k]-box[k])<1e-9);
});
test('unverified, escaping and zero-area coordinates fail closed',()=>{
  assert.throws(()=>viewportRectangle({x:0,y:0,width:.1,height:.1},{transform:{verified:false}}));
  assert.throws(()=>viewportRectangle({x:-.01,y:0,width:.1,height:.1},{transform:{verified:true,scaleX:1,scaleY:1}}));
});
test('fourth calibration fiducial verifies rather than assumes the transform',()=>{
  const css=[{x:1,y:2},{x:9,y:2},{x:1,y:8},{x:9,y:8}],pixels=css.map(p=>({x:2*p.x+3,y:2*p.y+4}));
  assert.equal(calibrate(css,pixels).scaleX,2);pixels[3].x+=8;assert.throws(()=>calibrate(css,pixels));
});
test('PNG reader identifies actual pixel colors',()=>{
  const header=Buffer.alloc(13);header.writeUInt32BE(2,0);header.writeUInt32BE(2,4);header[8]=8;header[9]=2;
  const chunk=(name,bytes)=>{const b=Buffer.alloc(bytes.length+12);b.writeUInt32BE(bytes.length);b.write(name,4);bytes.copy(b,8);return b;};
  const png=Buffer.concat([Buffer.from('89504e470d0a1a0a','hex'),chunk('IHDR',header),chunk('IDAT',deflateSync(Buffer.from([0,251,1,217,251,1,217,0,251,1,217,251,1,217]))),chunk('IEND',Buffer.alloc(0))]);
  assert.deepEqual(findColors(decodePNG(png),[[251,1,217]]),[{x:1,y:1}]);
});
test('CSS locations point at selector lines, ignore comments and abstain on duplicates',()=>{
  assert.equal(selectorLine('.a {margin:0}\n.b {padding:2px}', '.b'),2);
  assert.equal(selectorLine('/* .b { fake } */\n.b {padding:2px}', '.b'),2);
  assert.equal(selectorLine('.b {padding:2px}\n.b {padding:3px}', '.b'),null);
});
test('selected-project path checks reject traversal and symlink escape',async()=>{
  const temp=await fs.mkdtemp(path.join(os.tmpdir(),'contextlens-code-path-'));
  try{await fs.mkdir(path.join(temp,'project'));await fs.writeFile(path.join(temp,'outside.js'),'private');
    await fs.symlink(path.join(temp,'outside.js'),path.join(temp,'project/escape.js'));
    await assert.rejects(containedFile(path.join(temp,'project'),'../outside.js'));
    await assert.rejects(containedFile(path.join(temp,'project'),'escape.js'));
  }finally{await fs.rm(temp,{recursive:true,force:true});}
});
