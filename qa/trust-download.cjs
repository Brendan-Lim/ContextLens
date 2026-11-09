const {chromium}=require('../Benchmarks/node_modules/playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto'),cp=require('child_process');
(async()=>{
  const out=process.env.RUNNER_TEMP+'/native-evidence',downloads=process.env.RUNNER_TEMP+'/genuine-browser-download';
  fs.mkdirSync(downloads,{recursive:true});
  const headers={Authorization:'Bearer '+process.env.GH_TOKEN,Accept:'application/vnd.github+json'};
  const listing=await fetch('https://api.github.com/repos/Brendan-Lim/ContextLens/actions/runs/42557369631/artifacts',{headers});
  if(!listing.ok)throw Error('Artifact listing HTTP '+listing.status);
  const artifact=(await listing.json()).artifacts.find(x=>x.name==='official-candidate-0.3.1'&&!x.expired);
  if(!artifact)throw Error('Exact candidate artifact unavailable');
  const redirect=await fetch('https://api.github.com/repos/Brendan-Lim/ContextLens/actions/artifacts/'+artifact.id+'/zip',{headers,redirect:'manual'});
  if(redirect.status!==302)throw Error('Artifact download HTTP '+redirect.status);
  const location=redirect.headers.get('location');
  if(!location||!location.startsWith('https://'))throw Error('Expected an HTTPS artifact redirect');
  const context=await chromium.launchPersistentContext(process.env.RUNNER_TEMP+'/trust-browser-profile',{headless:false,acceptDownloads:true,viewport:null,args:['--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-sync']});
  const page=context.pages()[0];
  const pending=page.waitForEvent('download',{timeout:30000});
  await page.goto(location).catch(()=>{});
  const download=await pending;const original=await download.path();
  const saved=downloads+'/official-candidate-browser.zip';await download.saveAs(saved);
  const attr=file=>{const r=cp.spawnSync('xattr',['-p','com.apple.quarantine',file],{encoding:'utf8'});return{present:r.status===0,value:r.status===0?r.stdout.trim():null}};
  const digest=crypto.createHash('sha256').update(fs.readFileSync(saved)).digest('hex');
  const report={artifactID:artifact.id,realHeadfulBrowser:true,browserVersion:context.browser().version(),downloadSource:'GitHub Actions authenticated API redirect followed by actual HTTPS browser download; no quarantine writes',originalQuarantine:attr(original),savedQuarantine:attr(saved),downloadedSHA256:digest,apiArtifactDigest:artifact.digest||null,localFile:saved,completedAt:new Date().toISOString()};
  if(artifact.digest)report.apiDigestMatched=artifact.digest==='sha256:'+digest;
  await context.close();
  if(!report.savedQuarantine.present){
    const safariFolder=process.env.HOME+'/Downloads';fs.mkdirSync(safariFolder,{recursive:true});
    const before=new Set(fs.readdirSync(safariFolder));
    const launch=cp.spawnSync('open',['-a','Safari',location],{encoding:'utf8'});
    report.safariAttempt={launchExitCode:launch.status,securityApprovalsAutomated:false};
    const deadline=Date.now()+35000;
    while(Date.now()<deadline){
      const files=fs.readdirSync(safariFolder).filter(n=>!before.has(n)&&n.endsWith('.zip')).map(n=>path.join(safariFolder,n));
      const file=files.find(f=>{try{return fs.statSync(f).isFile()&&fs.statSync(f).size>0}catch{return false}});
      if(file){
        const quarantine=attr(file),bytes=fs.readFileSync(file),actual=crypto.createHash('sha256').update(bytes).digest('hex');
        report.safariAttempt.downloadCompleted=true;report.safariAttempt.quarantine=quarantine;
        if(quarantine.present && (!artifact.digest||artifact.digest==='sha256:'+actual)){
          report.effectiveBrowser='Safari';report.localFile=file;report.savedQuarantine=quarantine;report.downloadedSHA256=actual;report.apiDigestMatched=!artifact.digest||artifact.digest==='sha256:'+actual;
        }
        break;
      }
      await new Promise(r=>setTimeout(r,200));
    }
    if(!report.safariAttempt.downloadCompleted)report.safariAttempt.downloadCompleted=false;
  }
  fs.writeFileSync(out+'/genuine-browser-download.json',JSON.stringify(report,null,2));
})().catch(error=>{const message=String(error).replace(/https:\/\/\S+/g,'[URL redacted]');fs.writeFileSync(process.env.RUNNER_TEMP+'/native-evidence/browser-download-error.txt',message);process.exit(1)});
