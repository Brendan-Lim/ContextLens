import {register} from '../dev-source.js';
export function SaveButton(id='save') {
  const button=document.createElement('button');button.id=id;button.className='save-button';
  const icon=document.createElement('span');icon.id=id+'-icon';icon.className='button-icon';icon.setAttribute('aria-hidden','true');icon.textContent='+';
  button.append(icon,document.createTextNode(' Save project'));
  return register(button,import.meta.url,'SaveButton');
}
