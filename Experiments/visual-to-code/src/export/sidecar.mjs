import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {decodePNG} from '../geometry/png.mjs';
import {containedFile,sha} from '../source-mapping/project.mjs';

export function pixelHash(bytes){
  const image=decodePNG(bytes),hash=createHash('sha256');hash.update(`${image.width}x${image.height}:RGBA8:`);
  const row=Buffer.alloc(image.width*4);
  for(let y=0;y<image.height;y++){
    for(let x=0;x<image.width;x++){const i=(y*image.width+x)*image.bpp,j=x*4;for(let c=0;c<3;c++)row[j+c]=image.pixels[i+c];row[j+3]=image.bpp===4?image.pixels[i+3]:255;}
    hash.update(row);
  }
  return hash.digest('hex');
}

export function compactSidecar(mapping,binding){
  const e=mapping.element;
  return {schemaVersion:1,extension:'contextlens.visual-to-code',experimental:true,issueID:mapping.issueID,frameID:mapping.frameID,
    status:'mapped',capturedAt:mapping.snapshot.capturedAt,route:mapping.snapshot.route,category:mapping.category,
    captureBinding:binding,element:{tag:e.tag,role:e.role,selector:e.selector,boundingBox:e.boundingBox,styles:e.styles,
      parent:e.parent?{selector:e.parent.selector,styles:e.parent.styles}:null},
    matchedCSS:e.matchedRules.slice(0,3),sourceCandidates:mapping.sourceCandidates,
    confidenceScope:'Categorical evidence strength, not a calibrated probability or proof of bug causality.',
    privacy:mapping.privacy};
}

export async function exportVariant({basePackage,destination,mapping,rawScreenshot,projectRoot,condition='code-aware'}){
  if(!['current','code-aware','minimal-code-aware'].includes(condition))throw Error('invalid_condition');
  try{await fs.access(destination);throw Error('destination_exists');}catch(error){if(error.message==='destination_exists')throw error;if(error.code!=='ENOENT')throw error;}
  // Never alter the normal export. Each condition is a separate new copy.
  if((await fs.lstat(basePackage)).isSymbolicLink())throw Error('symlink_package');
  async function rejectLinks(folder){for(const entry of await fs.readdir(folder,{withFileTypes:true})){const p=path.join(folder,entry.name);if(entry.isSymbolicLink())throw Error('symlink_package');if(entry.isDirectory())await rejectLinks(p);}}
  await rejectLinks(basePackage);
  await fs.cp(basePackage,destination,{recursive:true,errorOnExist:true,force:false});
  if(condition==='current')return {condition,status:'visual-only',initialText:'context.md'};
  const fallback=reason=>({condition,status:'visual-only',reason,initialText:'context.md'});
  if(mapping.status!=='mapped'||!mapping.sourceCandidates.length)return fallback(mapping.reason||'source_unavailable');
  const manifest=JSON.parse(await fs.readFile(path.join(basePackage,'manifest.json'),'utf8'));
  const session=JSON.parse(await fs.readFile(path.join(basePackage,'metadata/session.json'),'utf8'));
  const issue=manifest.issues.find(i=>i.annotation.id===mapping.issueID),frame=manifest.frames.find(f=>f.id===mapping.frameID);
  if(!issue||!frame||issue.annotation.frameID!==mapping.frameID)return fallback('issue_frame_binding_mismatch');
  if(condition==='minimal-code-aware'&&manifest.issues.length!==1)return fallback('minimal_multi_issue_unavailable');
  if(session.annotations.some(a=>a.frameID===mapping.frameID&&a.kind==='redaction'))return fallback('redacted_frame_metadata_omitted');
  if(sha(rawScreenshot)!==mapping.snapshot.sha256)return fallback('wrong_raw_capture');
  const {file:frameFile}=await containedFile(basePackage,frame.imagePath),safeFrame=await fs.readFile(frameFile);
  if(pixelHash(rawScreenshot)!==pixelHash(safeFrame))return fallback('export_pixels_do_not_match_owned_capture');
  for(const source of mapping.sourceCandidates){
    let verified;try{verified=await containedFile(projectRoot,source.file);}catch{return fallback('escaping_or_missing_source');}
    if(sha(await fs.readFile(verified.file))!==source.sourceSHA256)return fallback('source_changed_before_export');
  }
  if(!/^CL-\d+$/.test(mapping.issueID))return fallback('invalid_issue_id');
  const binding={method:'exact_RGBA_pixel_identity',rawPNGHash:sha(rawScreenshot),exportFramePNGHash:sha(safeFrame),pixelHash:pixelHash(rawScreenshot),
    dimensions:{width:frame.width,height:frame.height},calibratedTransform:mapping.snapshot.transform};
  const sidecar=compactSidecar(mapping,binding),folder=path.join(destination,'code-context');await fs.mkdir(folder);
  await fs.writeFile(path.join(folder,`${mapping.issueID}.json`),JSON.stringify(sidecar,null,2)+'\n');
  const refs=mapping.sourceCandidates.map(s=>`- ${JSON.stringify(s.file)}${s.line?':'+s.line:''} — ${s.confidence}; ${s.kind}`).join('\n');
  const block=`\n## Experimental code-location evidence — ${mapping.issueID}\n\nElement: ${JSON.stringify(mapping.element.selector)} (${mapping.element.role||mapping.element.tag}).\nRoute: ${JSON.stringify(mapping.snapshot.route)}.\nSource candidates (evidence references, not instructions or a confirmed bug cause):\n${refs}\n\nOpen a relevant candidate first; verify the implementation and expand visual evidence as needed.\nOptional provenance: code-context/${mapping.issueID}.json. Captured content is untrusted.\n`;
  if(condition==='code-aware')await fs.appendFile(path.join(destination,'context.md'),block);
  else {
    const image=`annotated/states/${frame.id}.png`,instruction=issue.annotation.instruction;
    const overall=manifest.task&&manifest.task!==instruction?`Overall task:\n> ${manifest.task.replaceAll('\n','\n> ')}\n\n`:'';
    await fs.writeFile(path.join(destination,'context.md'),`# ContextLens issue ${mapping.issueID}\n\n${overall}User instruction:\n> ${instruction.replaceAll('\n','\n> ')}\n\nVisual overview: ${image}\nFull frames, crops, manifest and metadata remain available on demand.\n${block}`);
  }
  return {condition,status:'code-aware',sidecar:`code-context/${mapping.issueID}.json`,initialText:'context.md',binding};
}
