import type {InputHTMLAttributes} from 'react';
export function TextField(props:InputHTMLAttributes<HTMLInputElement>){return <input {...props} className={`text-field ${props.className||''}`}/>;}
