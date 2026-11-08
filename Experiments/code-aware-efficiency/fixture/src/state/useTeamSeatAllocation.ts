import {useState} from 'react';
export function useTeamSeatAllocation(){const [reserved,setReserved]=useState(3);const reserve=()=>setReserved(v=>v+1);return {reserved,reserve};}
