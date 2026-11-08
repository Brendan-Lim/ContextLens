import {useEffect} from 'react';import type {RefObject} from 'react';
export function useLayerDismissal(open:boolean,anchor:RefObject<HTMLElement|null>,layer:RefObject<HTMLElement|null>,onDismiss:()=>void){
  useEffect(()=>{
    if(!open)return;
    const onPointerDown=(event:PointerEvent)=>{
      onDismiss();
    };
    document.addEventListener('pointerdown',onPointerDown);
    return()=>document.removeEventListener('pointerdown',onPointerDown);
  },[open,anchor,layer,onDismiss]);
}
