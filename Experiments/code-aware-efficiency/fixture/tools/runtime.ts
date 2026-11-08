type Receipt={id:string;file:string;line:number;column:number;start:number;end:number;sourceSHA256:string;kind:string;name:string;effects:string[];nativeEvents:string[]};
const functions=new WeakMap<Function,Receipt>();
const elements=new WeakMap<Element,{owner:Receipt;handlers:Record<string,Receipt>}>();
let probe:{label:string;entries:Array<{receipt:Receipt;depth:number}>}|null=null;
let depth=0;
export function markFunction<T extends Function>(fn:T,receipt:Receipt):T{functions.set(fn,receipt);return fn;}
export function enterFunction(receipt:Receipt){const previous=depth;depth++;if(probe)probe.entries.push({receipt,depth:previous});return previous;}
export function leaveFunction(previous:number){depth=previous;}
export function elementRef(previous:any,owner:Receipt,readProps:()=>Array<Record<string,unknown>>){
  let current:Element|null=null;
  return (element:Element|null)=>{
    current=element;
    if(element){const handlers:Record<string,Receipt>={};for(const props of readProps())for(const key of Object.keys(props))if(/^on[A-Z]/.test(key)){const value=props[key];if(typeof value==='function'){const receipt=functions.get(value);if(receipt)handlers[key]=receipt;}}elements.set(element,{owner,handlers});}
    const cleanup=typeof previous==='function'?previous(element):undefined;
    if(previous&&typeof previous==='object')previous.current=element;
    return()=>{if(current)elements.delete(current);if(typeof cleanup==='function')cleanup();else if(typeof previous==='function')previous(null);if(previous&&typeof previous==='object')previous.current=null;};
  };
}
Object.defineProperty(window,'contextLensRuntime',{configurable:false,writable:false,value:Object.freeze({version:1,
  getElement:(element:Element)=>elements.get(element)||null,
  beginProbe:(label:string)=>{if(probe)throw Error('probe already active');probe={label,entries:[]};},
  endProbe:()=>{const result=probe;probe=null;return result;}
})});
