export function StatTile({label,value,detail}:{label:string;value:string;detail:string}){return <div className="stat-tile"><small>{label}</small><strong>{value}</strong><span>{detail}</span></div>;}
