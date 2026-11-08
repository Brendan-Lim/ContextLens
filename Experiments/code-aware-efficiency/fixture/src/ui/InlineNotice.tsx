export function InlineNotice({kind,children}:{kind:'error'|'success'|'info';children:string}){return <p className={`notice notice-${kind}`} role={kind==='error'?'alert':'status'}>{children}</p>;}
