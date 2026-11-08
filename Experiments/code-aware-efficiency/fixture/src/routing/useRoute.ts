import {useEffect,useState} from 'react';
export function useRoute(){
  const [route,setRoute]=useState(location.hash.slice(1)||'/projects');
  useEffect(()=>{const update=()=>setRoute(location.hash.slice(1)||'/projects');window.addEventListener('hashchange',update);return()=>window.removeEventListener('hashchange',update);},[]);
  return route;
}
