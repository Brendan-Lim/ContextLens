export const PROPERTY_SETS=Object.freeze({
  spacing:['padding','margin','gap','width','height','box-sizing','display'],
  alignment:['display','flex-direction','justify-content','align-items','position','grid-template-columns','gap'],
  visibility:['display','visibility','opacity','overflow','z-index','position','outline','box-shadow'],
  interaction:[],
  unknown:['display','position','padding','margin','width','height']
});
export function category(value){return Object.hasOwn(PROPERTY_SETS,value)?value:'unknown';}
