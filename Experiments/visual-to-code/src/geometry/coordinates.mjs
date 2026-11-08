export function intersect(a,b){const x=Math.max(a.x,b.x),y=Math.max(a.y,b.y);return {x,y,width:Math.max(0,Math.min(a.x+a.width,b.x+b.width)-x),height:Math.max(0,Math.min(a.y+a.height,b.y+b.height)-y)};}
export const area=r=>r.width*r.height;
export function viewportRectangle(region,snapshot){
  const r=region,t=snapshot.transform;
  if(!r||![r.x,r.y,r.width,r.height].every(Number.isFinite)||r.width<=0||r.height<=0||r.x<0||r.y<0||r.x+r.width>1.000001||r.y+r.height>1.000001)throw Error('invalid_normalized_rectangle');
  if(!t?.verified||![t.scaleX,t.scaleY].every(n=>Number.isFinite(n)&&n>0))throw Error('unverified_transform');
  return {x:(r.x*snapshot.width-t.offsetX)/t.scaleX,y:(r.y*snapshot.height-t.offsetY)/t.scaleY,
    width:r.width*snapshot.width/t.scaleX,height:r.height*snapshot.height/t.scaleY};
}
export function normalizedRectangle(box,snapshot){
  const t=snapshot.transform;
  const px=intersect({x:box.x*t.scaleX+t.offsetX,y:box.y*t.scaleY+t.offsetY,width:box.width*t.scaleX,height:box.height*t.scaleY},{x:0,y:0,width:snapshot.width,height:snapshot.height});
  if(!area(px))throw Error('annotation_outside_screenshot');
  return {x:px.x/snapshot.width,y:px.y/snapshot.height,width:px.width/snapshot.width,height:px.height/snapshot.height};
}
export function calibrate(css,pixels){
  if(css.length!==4||pixels.length!==4)throw Error('missing_calibration_points');
  const scaleX=(pixels[1].x-pixels[0].x)/(css[1].x-css[0].x);
  const scaleY=(pixels[2].y-pixels[0].y)/(css[2].y-css[0].y);
  const offsetX=pixels[0].x-css[0].x*scaleX,offsetY=pixels[0].y-css[0].y*scaleY;
  const errors=css.map((p,i)=>Math.hypot(p.x*scaleX+offsetX-pixels[i].x,p.y*scaleY+offsetY-pixels[i].y));
  if(!Number.isFinite(scaleX)||!Number.isFinite(scaleY)||scaleX<=0||scaleY<=0||Math.max(...errors)>1.5)throw Error('calibration_failed');
  return {verified:true,scaleX,scaleY,offsetX,offsetY,maxResidualPixels:Math.max(...errors),method:'four_owned_fiducials_axis_aligned_affine'};
}
