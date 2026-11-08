// Explicit opt-in development metadata contract, independent of framework internals.
const enabled=new URL(location.href).searchParams.get('metadata')!=='off';
const registry=new WeakMap();
export function register(element,moduleURL,exportName){if(enabled)registry.set(element,{moduleURL,exportName});return element;}
if(enabled)window.contextLensDevelopmentSources=Object.freeze({version:1,get:element=>registry.get(element)??null});
