import type {ReactNode} from 'react';
export function FormField({label,htmlFor,children}:{label:string;htmlFor:string;children:ReactNode}){return <div className="form-field"><label htmlFor={htmlFor}>{label}</label>{children}</div>;}
