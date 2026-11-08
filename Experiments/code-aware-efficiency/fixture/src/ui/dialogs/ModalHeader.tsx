import {IconButton} from '../IconButton';
export function ModalHeader({title,onClose}:{title:string;onClose:()=>void}){return <header className="modal-header"><h2>{title}</h2><IconButton label="Close dialog" onClick={onClose}/></header>;}
