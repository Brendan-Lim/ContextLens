import type {ReactNode} from 'react';import styles from './ActionCluster.module.css';
export function ActionCluster({children,align='end'}:{children:ReactNode;align?:'start'|'end'}){return <div className={`${styles.root} ${align==='start'?styles.start:''}`} data-action-cluster="true">{children}</div>;}
