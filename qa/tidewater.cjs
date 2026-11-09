const {chromium}=require('../Benchmarks/node_modules/playwright');
const fs=require('fs'),http=require('http'),path=require('path');
const out=process.env.RUNNER_TEMP+'/native-evidence';
let context,page,other;
(async()=>{
  const html=fs.readFileSync('docs/screenshot-kit/demo-site/index.html');
  const server=http.createServer(async(req,res)=>{
    if(req.url==='/'){res.writeHead(200,{'Content-Type':'text/html'});res.end(html);return;}
    if(req.url!=='/control'){res.writeHead(404);res.end();return;}
    let raw='';for await(const chunk of req)raw+=chunk;
    try{
      const c=JSON.parse(raw),a=c.action;
      if(a==='share')await page.locator('#share').click();
      if(a==='link')await page.getByRole('button',{name:'Link',exact:true}).click();
      if(a==='invite')await page.getByRole('button',{name:'Invite',exact:true}).click();
      if(a==='fill')await page.locator('#email').fill('reviewer@tidewater.example');
      if(a==='cancel')await page.locator('#cancel').click();
      if(a==='reset'){
        if(!context.browser().isConnected())await launch();
        else if(page.isClosed()){page=await newWindow();await page.goto(origin+'/');}
        else await page.reload();
      }
      if(a==='other'){other=await newWindow();await other.setContent('<title>Never capture this other window</title><body style="background:#ff00ff"><h1>NOT THE SELECTED WINDOW</h1></body>');}
      if(a==='close')await page.close();
      if(a==='quit'){await context.close();res.end(JSON.stringify({closed:true}));return;}
      const state=page.isClosed()?{closed:true,otherAlive:other && !other.isClosed()}:await page.evaluate(()=>{
        const rect=s=>{const r=document.querySelector(s).getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height}};
        return{actions:rect('.actions'),cancel:rect('#cancel'),send:rect('.actions .primary'),avatar:rect('.row.drift .av'),innerWidth,innerHeight,outerWidth,outerHeight,title:document.title};
      });
      fs.appendFileSync(out+'/browser-actions.jsonl',JSON.stringify({at:new Date().toISOString(),action:a,state})+'\n');
      res.end(JSON.stringify(state));
    }catch(e){res.writeHead(500);res.end(JSON.stringify({error:String(e)}));}
  });
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const origin='http://127.0.0.1:'+server.address().port;
  async function newWindow(){
    const next=context.waitForEvent('page');
    const session=await context.browser().newBrowserCDPSession();
    await session.send('Target.createTarget',{url:'about:blank',newWindow:true});
    return await next;
  }
  async function launch(){
    context=await chromium.launchPersistentContext(process.env.RUNNER_TEMP+'/tidewater-profile',{headless:false,viewport:null,args:['--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-sync','--window-position=30,70','--window-size=1102,776']});
    await context.route('**/*',r=>r.request().url().startsWith(origin+'/')?r.continue():r.abort());
    page=context.pages()[0];await page.goto(origin+'/');
  }
  await launch();
  fs.writeFileSync(out+'/browser-ready.json',JSON.stringify({origin,browserVersion:context.browser().version(),temporaryProfile:true,realHeadfulBrowser:true}));
})().catch(e=>{fs.writeFileSync(out+'/browser-fatal.txt',String(e));process.exit(1)});
