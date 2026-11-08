import type {ButtonHTMLAttributes} from 'react';
export function Button({tone='primary',className='',...props}:ButtonHTMLAttributes<HTMLButtonElement>&{tone?:'primary'|'quiet'}){
  return <button {...props} className={`button button-${tone} ${className}`}/>;
}
