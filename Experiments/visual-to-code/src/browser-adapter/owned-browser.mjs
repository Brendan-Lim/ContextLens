import fs from 'node:fs/promises';
import {randomUUID} from 'node:crypto';
import {chromium} from '../../../../Benchmarks/node_modules/playwright/index.mjs';
import {serveProject,sha,containedFile,verifiedAsset} from '../source-mapping/project.mjs';
import {decodePNG,findColors} from '../geometry/png.mjs';
import {calibrate} from '../geometry/coordinates.mjs';

export class OwnedBrowser {
  static async create({projectRoot,width=1100,height=800,dpr=1,route='/',developmentRegistry=null}){
    const owner=new OwnedBrowser();owner.project=await serveProject(projectRoot);
    try{
      owner.developmentRegistry=developmentRegistry?(await containedFile(owner.project.root,developmentRegistry)).relative:null;
      owner.browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{})});
      owner.context=await owner.browser.newContext({viewport:{width,height},deviceScaleFactor:dpr,serviceWorkers:'block'});
      // Isolated temporary browser only. No attach-to-profile/debugging endpoint API exists.
      await owner.context.route('**/*',r=>new URL(r.request().url()).origin===owner.project.origin?r.continue():r.abort());
      owner.page=await owner.context.newPage();owner.identity=randomUUID();owner.assets=new Map();owner.pending=[];owner.snapshots=new Map();owner.sourceReceipts=new Map();
      owner.page.on('response',response=>{
        const request=response.request();if(!['stylesheet','script','document'].includes(request.resourceType()))return;
        if(new URL(response.url()).origin!==owner.project.origin)return;
        owner.pending.push((async()=>{try{const body=await response.body();if(body.length<=1000000)owner.assets.set(response.url(),{hash:sha(body),type:request.resourceType()});}catch{}})());
      });
      await owner.page.addInitScript(()=>{
        window.contextLensDOMRevision=0;
        new MutationObserver(()=>window.contextLensDOMRevision++).observe(document,{subtree:true,attributes:true,characterData:true,childList:true});
      });
      const target=new URL(route,owner.project.origin);if(target.origin!==owner.project.origin)throw Error('nonlocal_target');
      await owner.page.goto(target.href);await owner.page.waitForLoadState('networkidle');await Promise.all(owner.pending);
      return owner;
    }catch(error){await owner.close();throw error;}
  }
  async metrics(){return this.page.evaluate(async()=>{
    // Screenshot caret suppression can create temporary mutations. Compare the
    // resulting structure, not just a revision counter. Never read form values/text.
    const safe=s=>/^[A-Za-z_][A-Za-z0-9_-]{0,47}$/.test(s);
    const shape=[...document.querySelectorAll('*')].slice(0,1501).map(e=>[
      e.localName,safe(e.id)?e.id:null,[...e.classList].filter(safe),e.getAttributeNames().sort(),e.hasAttribute('hidden'),e.hasAttribute('disabled'),e.getAttribute('aria-expanded')==='true',e.getAttribute('role')?.slice(0,30)??null]);
    const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(shape)));
    return {width:innerWidth,height:innerHeight,dpr:devicePixelRatio,structuralDigest:[...new Uint8Array(digest)].map(n=>n.toString(16).padStart(2,'0')).join(''),
      scrollX,scrollY,visualViewport:{width:visualViewport.width,height:visualViewport.height,offsetLeft:visualViewport.offsetLeft,offsetTop:visualViewport.offsetTop,scale:visualViewport.scale},
      cssZoom:getComputedStyle(document.documentElement).zoom,revision:window.contextLensDOMRevision,route:location.pathname};
  });}
  async screenshot(){return this.page.screenshot({type:'png',fullPage:false,scale:'device',animations:'disabled',caret:'hide'});}
  async capture({id=randomUUID(),path=null}={}){
    const colors=[[251,1,217],[1,251,217],[217,1,251],[251,217,1]];
    let css;
    try{
      css=await this.page.evaluate(colors=>{
        const zoom=parseFloat(getComputedStyle(document.documentElement).zoom)||1;
        const v=visualViewport,positions=[[8,8],[v.width-20,8],[8,v.height-20],[v.width-20,v.height-20]];
        return positions.map(([x,y],i)=>{
          const e=document.createElement('div');e.dataset.contextlensCalibration='true';
          e.style.cssText=`position:fixed;left:${x}px;top:${y}px;width:7px;height:7px;background:rgb(${colors[i].join(',')});z-index:2147483647;pointer-events:none;zoom:${1/zoom};`;
          document.documentElement.append(e);const b=e.getBoundingClientRect();return {x:b.x+b.width/2,y:b.y+b.height/2};
        });
      },colors);
      const bytes=await this.screenshot(),png=decodePNG(bytes),pixels=findColors(png,colors);
      const transform=calibrate(css,pixels);
      await this.page.locator('[data-contextlens-calibration]').evaluateAll(elements=>elements.forEach(e=>e.remove()));
      await this.page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
      const clean=await this.screenshot(),header=decodePNG(clean);
      if(header.width!==png.width||header.height!==png.height)throw Error('resize_during_capture');
      const metrics=await this.metrics();
      const snapshot=Object.freeze({id,pageIdentity:this.identity,width:png.width,height:png.height,transform,
        metrics,capturedAt:new Date().toISOString(),capturedClock:performance.now(),sha256:sha(clean),kind:'owned_browser_viewport'});
      this.snapshots.set(id,snapshot);this.sourceReceipts.set(id,new Map(this.assets));if(path)await fs.writeFile(path,clean);
      return snapshot;
    }finally{await this.page.locator('[data-contextlens-calibration]').evaluateAll(es=>es.forEach(e=>e.remove())).catch(()=>{});}
  }
  async validate(snapshot){
    if(this.snapshots.get(snapshot?.id)!==snapshot||snapshot.pageIdentity!==this.identity)return 'unknown_page_or_screenshot';
    if(performance.now()-snapshot.capturedClock>60000)return 'stale_snapshot_age';
    const now=await this.metrics();
    const {revision:nowRevision,...nowState}=now,{revision:oldRevision,...oldState}=snapshot.metrics;
    if(JSON.stringify(nowState)!==JSON.stringify(oldState))return 'stale_dom_or_geometry';
    for(const [url,receipt] of this.sourceReceipts.get(snapshot.id))if(!await verifiedAsset(url,new Map([[url,receipt]]),this.project))return 'stale_source_assets';
    if(sha(await this.screenshot())!==snapshot.sha256)return 'stale_pixels';
    return null;
  }
  async close(){await this.browser?.close();await this.project?.close();}
}
