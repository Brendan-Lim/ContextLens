export interface Project {id:string;name:string;owner:string;status:'Active'|'Review'|'Paused';progress:number;}
export const projects:Project[]=[
  {id:'atlas',name:'Atlas launch',owner:'Jordan',status:'Review',progress:72},
  {id:'beacon',name:'Beacon portal',owner:'Morgan',status:'Active',progress:46},
  {id:'cedar',name:'Cedar research',owner:'Casey',status:'Paused',progress:31},
  {id:'delta',name:'Delta migration',owner:'Alex',status:'Active',progress:83}
];
export function selectProjects(query:string,status:string){return projects.filter(p=>p.name.toLowerCase().includes(query.toLowerCase())&&(status==='All'||p.status===status));}
