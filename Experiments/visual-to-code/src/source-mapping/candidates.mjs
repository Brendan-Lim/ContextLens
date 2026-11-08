import {verifiedAsset} from './project.mjs';

const escape=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
function uniqueLine(text,pattern){const matches=[...text.matchAll(new RegExp(pattern,'g'))];return matches.length===1?text.slice(0,matches[0].index).split('\n').length:null;}
export function selectorLine(text,selector){
  // Remove comments at equal length, retaining line offsets; do not guess duplicate rules.
  const clean=text.replace(/\/\*[\s\S]*?\*\//g,s=>s.replace(/[^\n]/g,' '));
  const normalized=selector.replace(/\s+/g,' ').trim(),matches=[];
  const rx=/(?:^|[{}])\s*([^{}]+)\{/g;let m;
  while((m=rx.exec(clean))){const header=m[1].trim().replace(/\s+/g,' ');if(header===normalized)matches.push(m.index+m[0].indexOf(m[1])+m[1].search(/\S/));rx.lastIndex--;}
  return matches.length===1?clean.slice(0,matches[0]).split('\n').length:null;
}

export async function sourceCandidates(element,owner,category){
  const candidates=[];
  async function addRules(rules,scope){for(const rule of rules??[]){
    const url=rule.stylesheetURL||rule.documentURL;
    const asset=await verifiedAsset(url,owner.assets,owner.project);if(!asset)continue;
    let line=null;
    if(rule.stylesheetURL)line=selectorLine(asset.text,rule.selector);
    else {
      // An injected style is not attributed to the HTML file merely because it is inline.
      if(!rule.inlineText)continue;
      const blocks=[...asset.text.matchAll(/<style(?:\s[^>]*)?>([\s\S]*?)<\/style>/gi)].filter(m=>m[1]===rule.inlineText);
      if(blocks.length!==1)continue;
      const inner=selectorLine(rule.inlineText,rule.selector);
      if(inner)line=asset.text.slice(0,blocks[0].index+blocks[0][0].indexOf(blocks[0][1])).split('\n').length+inner-1;
    }
    const specificity=rule.selector.includes('#')?4:rule.selector.includes('.')?2:rule.selector==='*'?0:1;
    candidates.push({file:asset.file,...(line?{line}:{}),confidence:line?'high':'medium',kind:'matched_stylesheet_rule',
      evidence:['browser_cssom_match','same_origin_asset','served_bytes_match_selected_project'],reason:`Observed matching ${scope} CSS rule; winning cascade/bug cause not established.`,
      selector:rule.selector,scope,exactRuleLocationVerified:Boolean(line),sourceSHA256:asset.sha256,
      priority:(category==='alignment'&&scope==='parent'?110:scope==='element'?100:85)+specificity+Object.keys(rule.declarations).length});
  }}
  if(category!=='interaction'){await addRules(element.matchedRules,'element');await addRules(element.parent?.matchedRules,'parent');}
  const dev=element.developmentSource;
  const registry=owner.developmentRegistry?await verifiedAsset(new URL('/'+owner.developmentRegistry,owner.project.origin).href,owner.assets,owner.project):null;
  if(registry&&dev&&typeof dev.exportName==='string'&&/^[A-Za-z_$][\w$]*$/.test(dev.exportName)){
    const asset=await verifiedAsset(dev.moduleURL,owner.assets,owner.project);
    if(asset){const line=uniqueLine(asset.text,`export\\s+function\\s+${escape(dev.exportName)}\\s*\\(`);
      if(line)candidates.push({file:asset.file,line,confidence:'high',kind:'opt_in_development_registration',
        evidence:['operator_opted_in_registry_file','browser_development_registry_v1','unique_export_declaration','served_bytes_match_selected_project'],
        reason:`Explicit development registration to ${dev.exportName}; declaration line, not a recovered JSX or event-handler location.`,
        inheritedFromAncestor:dev.inheritedFromAncestor,sourceSHA256:asset.sha256,priority:category==='interaction'?120:80});
    }
  }
  // Strong literal evidence is not equivalent to a framework/component source map.
  const id=element.selector.startsWith('#')?element.selector.slice(1):null;
  const cls=element.classes?.[0];
  const signature=id?`<${escape(element.tag)}\\b[^>]*\\bid=["']${escape(id)}["']`:
    cls?`<${escape(element.tag)}\\b[^>]*\\bclass=["'][^"']*\\b${escape(cls)}\\b[^"']*["']`:`<${escape(element.tag)}(?:\\s|>)`;
  for(const [url,observed] of owner.assets){
    if(!['document','script'].includes(observed.type))continue;
    const asset=await verifiedAsset(url,owner.assets,owner.project);if(!asset)continue;
    const line=uniqueLine(asset.text,signature);if(!line)continue;
    const direct=observed.type==='document'&&new URL(url).href===new URL(element.documentURL).href;
    candidates.push({file:asset.file,line,confidence:direct?'high':'medium',kind:direct?'static_html_literal':'unique_html_literal_in_script',
      evidence:[direct?'observed_document_literal':'unique_tag_identifier_literal','served_bytes_match_selected_project'],
      reason:direct?'Unique tag/identifier in the served HTML.':'Unique matching markup literal in a served script; not verified runtime component or handler attribution.',
      sourceSHA256:asset.sha256,priority:category==='interaction'?(direct?100:70):(direct?60:50)});
  }
  const relevant=category!=='interaction'&&candidates.some(c=>c.kind==='matched_stylesheet_rule')?
    candidates.filter(c=>c.kind==='matched_stylesheet_rule'):candidates;
  relevant.sort((a,b)=>b.priority-a.priority||a.file.localeCompare(b.file));
  // One strongest stylesheet pointer for styling; at most three attributable sources
  // for interaction. More candidate files is not automatically better context.
  const files=new Set();return relevant.filter(c=>!files.has(c.file)&&files.add(c.file)).slice(0,category==='interaction'?3:1).map(({priority,...c})=>c);
}
