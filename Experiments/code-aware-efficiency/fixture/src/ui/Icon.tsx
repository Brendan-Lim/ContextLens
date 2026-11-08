export function Icon({name}:{name:'plus'|'filter'|'arrow'|'close'}){return <span className="icon" aria-hidden="true">{({plus:'+',filter:'≡',arrow:'→',close:'×'})[name]}</span>;}
