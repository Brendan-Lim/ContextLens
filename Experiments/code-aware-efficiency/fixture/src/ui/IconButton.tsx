import {Button} from './Button';import {Icon} from './Icon';
export function IconButton({label,onClick}:{label:string;onClick:()=>void}){return <Button tone="quiet" aria-label={label} onClick={onClick}><Icon name="close"/></Button>;}
