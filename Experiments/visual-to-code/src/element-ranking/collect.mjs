// Executed inside one authorized same-origin frame. No form values or general DOM text.
export function collectCandidates({rectangle:r,properties,allowSafeNames=false,allowDevelopmentMetadata=false}){
  const area=b=>Math.max(0,b.width)*Math.max(0,b.height);
  const intersect=(a,b)=>{const x=Math.max(a.x,b.x),y=Math.max(a.y,b.y);return {x,y,width:Math.max(0,Math.min(a.x+a.width,b.x+b.width)-x),height:Math.max(0,Math.min(a.y+a.height,b.y+b.height)-y)};};
  const roles=new Set(['button','link','textbox','combobox','form','navigation','article','alert','dialog','region','checkbox','radio','menu','menuitem','tab','tablist']);
  const role=e=>(roles.has(e.getAttribute('role'))?e.getAttribute('role'):null)||({BUTTON:'button',A:e.hasAttribute('href')?'link':null,INPUT:'textbox',TEXTAREA:'textbox',SELECT:'combobox',FORM:'form',NAV:'navigation',ARTICLE:'article'}[e.tagName]??null);
  const safe=s=>typeof s==='string'&&/^[A-Za-z_][A-Za-z0-9_-]{0,47}$/.test(s);
  function selector(e){
    if(e.id&&safe(e.id)&&document.querySelectorAll('#'+CSS.escape(e.id)).length===1)return '#'+e.id;
    const classes=[...e.classList].filter(safe).slice(0,2),simple=classes.length?'.'+classes.map(CSS.escape).join('.'):e.localName;
    if(document.querySelectorAll(simple).length===1)return simple;
    if(!e.parentElement)return e.localName;
    const siblings=[...e.parentElement.children].filter(s=>s.localName===e.localName),index=siblings.indexOf(e)+1;
    return selector(e.parentElement)+' > '+e.localName+`:nth-of-type(${index})`;
  }
  const box=e=>{const b=e.getBoundingClientRect();return {x:b.x,y:b.y,width:b.width,height:b.height};};
  function styles(e){const c=getComputedStyle(e);return Object.fromEntries(properties.map(p=>[p,c.getPropertyValue(p)]));}
  function rules(e){
    const result=[];
    function visit(sheet,list,indexPath=[]){for(let i=0;i<list.length;i++){
      const rule=list[i],path=[...indexPath,i];
      if(rule.selectorText&&rule.style){
        let matches=false;try{matches=e.matches(rule.selectorText);}catch{}
        if(!matches)continue;
        const declarations=Object.fromEntries(properties.map(p=>[p,rule.style.getPropertyValue(p)]).filter(([,v])=>v));
        if(!Object.keys(declarations).length)continue;
        const node=sheet.ownerNode;
        result.push({selector:rule.selectorText,declarations,stylesheetURL:sheet.href,
          inlineText:!sheet.href&&node?.localName==='style'?(node.textContent.length<16000?node.textContent:null):null,
          documentURL:location.href,indexPath:path,winningCascadeVerified:false});
      }else if(rule.cssRules){
        if(rule.conditionText&&rule.constructor.name==='CSSMediaRule'&&!matchMedia(rule.conditionText).matches)continue;
        if(rule.conditionText&&rule.constructor.name==='CSSSupportsRule'&&!CSS.supports(rule.conditionText))continue;
        visit(sheet,rule.cssRules,path);
      }
    }}
    for(const sheet of document.styleSheets){try{visit(sheet,sheet.cssRules);}catch{}}
    return result.slice(-10);
  }
  const nodes=[...document.querySelectorAll('*')];
  if(nodes.length>1500)return {unavailable:'dom_budget_exceeded',candidates:[]};
  const dedup=new Set(),candidates=[];
  for(let e of nodes){
    if(['HTML','BODY','SCRIPT','STYLE','META','LINK','IFRAME'].includes(e.tagName))continue;
    if(['SPAN','SVG','PATH','I'].includes(e.tagName)&&!role(e))e=e.closest('button,a[href],[role="button"]')||e;
    if(dedup.has(e))continue;dedup.add(e);
    const c=getComputedStyle(e),b=box(e);
    if(c.display==='none'||c.visibility!=='visible'||Number(c.opacity)===0||!area(b))continue;
    const visible=intersect(b,{x:0,y:0,width:innerWidth,height:innerHeight}),overlap=intersect(visible,r),a=area(overlap);
    if(!a)continue;
    const samples=[[.5,.5],[.12,.12],[.88,.12],[.12,.88],[.88,.88]];
    const hit=samples.filter(([x,y])=>{
      const top=document.elementsFromPoint(overlap.x+x*overlap.width,overlap.y+y*overlap.height)[0];return top&&(top===e||e.contains(top));
    }).length/samples.length;
    if(!hit)continue;
    const semantic=['button','link','textbox','combobox','form','navigation','article','alert','dialog','region'].includes(role(e));
    const iou=a/(area(r)+area(visible)-a),annotationCoverage=a/area(r),elementCoverage=a/area(visible);
    if(!semantic&&annotationCoverage>.98&&elementCoverage<.15)continue;
    const rankScore=.55*iou+.25*annotationCoverage+.15*elementCoverage+(semantic?.05:0);
    candidates.push({e,b,iou,rankScore,hit,semantic});
  }
  candidates.sort((a,b)=>b.rankScore-a.rankScore||b.hit-a.hit);
  const best=candidates[0],second=candidates[1];
  const ambiguous=best&&second&&Math.abs(best.rankScore-second.rankScore)<.025&&!best.e.contains(second.e)&&!second.e.contains(best.e);
  window.contextLensCandidateNodes=[];
  const output=candidates.slice(0,3).map(({e,b,iou,rankScore,hit,semantic},i)=>{
    window.contextLensCandidateNodes.push(e);
    let developmentSource=null,owner=e;
    for(let depth=0;owner&&depth<3;depth++,owner=owner.parentElement){
      const observed=allowDevelopmentMetadata&&window.contextLensDevelopmentSources?.version===1?window.contextLensDevelopmentSources.get(owner):null;
      if(observed){developmentSource={...observed,inheritedFromAncestor:depth>0};break;}
    }
    const p=e.parentElement;
    return {token:i,tag:e.localName,role:role(e),selector:selector(e),selectorUnique:document.querySelectorAll(selector(e)).length===1,
      classes:[...e.classList].filter(safe).slice(0,4),boundingBox:b,styles:styles(e),matchedRules:rules(e),
      parent:p&&p!==document.body?{tag:p.localName,selector:selector(p),boundingBox:box(p),styles:styles(p),matchedRules:rules(p)}:null,
      state:{disabled:e.hasAttribute('disabled'),expanded:e.getAttribute('aria-expanded')==='true'},
      ...(allowSafeNames&&['button','link'].includes(role(e))&&e.getAttribute('aria-label')?{accessibleName:e.getAttribute('aria-label').slice(0,80)}:{}),
      developmentSource,geometricRankScore:Number(rankScore.toFixed(6)),rankScoreIsProbability:false,
      confidence:iou>.6&&hit===1?'high':'medium',semanticTarget:semantic};
  });
  return {unavailable:!best||best.rankScore<.28?'no_reliable_element':ambiguous?'ambiguous_elements':null,candidates:output};
}
