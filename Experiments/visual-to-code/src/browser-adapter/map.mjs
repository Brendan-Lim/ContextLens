import {performance} from 'node:perf_hooks';
import {viewportRectangle,intersect,area} from '../geometry/coordinates.mjs';
import {collectCandidates} from '../element-ranking/collect.mjs';
import {PROPERTY_SETS,category as normalizedCategory} from '../style-inspection/properties.mjs';
import {sourceCandidates} from '../source-mapping/candidates.mjs';

function safeRule(r){return {selector:r.selector,declarations:r.declarations,origin:r.stylesheetURL?'same-origin stylesheet':'inline stylesheet',winningCascadeVerified:false};}
function publicElement(e){
  const {matchedRules,developmentSource,parent,documentURL,...rest}=e;
  return {...rest,matchedRules:matchedRules.map(safeRule),parent:parent?{
    tag:parent.tag,selector:parent.selector,boundingBox:parent.boundingBox,styles:parent.styles,matchedRules:parent.matchedRules.map(safeRule)}:null};
}
export async function mapAnnotation(owner,snapshot,{frameID,issueID='CL-001',region,category='unknown',redactedFrame=false,allowSafeNames=false}){
  const started=performance.now(),unavailable=reason=>({schemaVersion:1,experimental:true,issueID,frameID,status:'unavailable',reason,sourceCandidates:[],candidates:[],runtimeMS:performance.now()-started});
  if(redactedFrame)return unavailable('redacted_frame_browser_metadata_omitted');
  if(frameID!==snapshot?.id)return unavailable('screenshot_identity_mismatch');
  try{
    const invalid=await owner.validate(snapshot);if(invalid)return unavailable(invalid);
    const rectangle=viewportRectangle(region,snapshot),kind=normalizedCategory(category),found=[];
    for(const [index,frame] of owner.page.frames().entries()){
      let offset={x:0,y:0},local=rectangle;
      if(frame!==owner.page.mainFrame()){
        if(!frame.url().startsWith(owner.project.origin+'/'))continue;
        const handle=await frame.frameElement(),b=await handle.boundingBox();if(!b)continue;
        const dims=await handle.evaluate(e=>({width:e.offsetWidth,height:e.offsetHeight,borderX:e.clientLeft,borderY:e.clientTop}));
        if(Math.abs(b.width-dims.width)>1||Math.abs(b.height-dims.height)>1)continue;
        offset={x:b.x+dims.borderX,y:b.y+dims.borderY};
        local={...rectangle,x:rectangle.x-offset.x,y:rectangle.y-offset.y};
        if(!area(intersect(rectangle,b)))continue;
      }
      const result=await frame.evaluate(collectCandidates,{rectangle:local,properties:PROPERTY_SETS[kind],allowSafeNames,allowDevelopmentMetadata:Boolean(owner.developmentRegistry)});
      for(const candidate of result.candidates){
        candidate.frameIndex=index;candidate.frameOffset=offset;candidate.documentURL=frame.url();
        candidate.mappingUnavailable=result.unavailable;found.push(candidate);
      }
    }
    found.sort((a,b)=>b.geometricRankScore-a.geometricRankScore);
    const primary=found[0];if(!primary||primary.mappingUnavailable)return unavailable(primary?.mappingUnavailable||'no_reliable_element');
    const sources=await sourceCandidates(primary,owner,kind);
    return {schemaVersion:1,experimental:true,issueID,frameID,status:'mapped',category:kind,
      snapshot:{id:snapshot.id,width:snapshot.width,height:snapshot.height,sha256:snapshot.sha256,pageIdentity:snapshot.pageIdentity,
        route:snapshot.metrics.route,capturedAt:snapshot.capturedAt,transform:snapshot.transform,viewport:snapshot.metrics},
      viewportAnnotation:rectangle,element:publicElement(primary),candidates:found.slice(0,3).map(publicElement),sourceCandidates:sources,
      sourceStatus:sources.length?'available':'unavailable',componentSourceStatus:sources.some(s=>s.kind==='opt_in_development_registration')?'explicit-development-registration':'unavailable',
      privacy:{formValuesCollected:false,generalDOMTextCollected:false,cookiesCollected:false,requestBodiesCollected:false},
      runtimeMS:performance.now()-started};
  }catch(error){return unavailable(error.message);}
}
