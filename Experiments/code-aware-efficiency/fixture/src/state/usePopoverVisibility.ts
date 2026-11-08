import {useCallback,useState} from 'react';
export function usePopoverVisibility(){const [open,setOpen]=useState(false);const close=useCallback(()=>setOpen(false),[]);const toggle=useCallback(()=>setOpen(v=>!v),[]);return {open,close,toggle};}
