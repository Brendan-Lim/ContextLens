import type {ReactNode} from 'react';
export function CardHeader({title,extra}:{title:string;extra?:ReactNode}){return <header className="card-header"><h2>{title}</h2>{extra}</header>;}
