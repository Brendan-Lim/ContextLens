import type {ReactNode} from 'react';
export function ModalFrame({label,children}:{label:string;children:ReactNode}){return <div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-label={label}>{children}</section></div>;}
