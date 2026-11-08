import {useCallback,useState} from 'react';
export function useSeatAllocation(){
  const [seats,setSeats]=useState(12);
  const allocate=useCallback((amount:number)=>{
    for(let index=0;index<amount;index++)setSeats(seats+1);
  },[seats]);
  const release=useCallback(()=>setSeats(value=>Math.max(0,value-1)),[]);
  return {seats,allocate,release};
}
