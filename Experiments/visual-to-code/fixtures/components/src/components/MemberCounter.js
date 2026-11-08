import {register} from '../dev-source.js';
export function MemberCounter() {
  let count=0;const box=document.createElement('section');box.id='counter';box.className='counter';
  const output=document.createElement('output');output.id='member-count';output.textContent='0';
  const button=document.createElement('button');button.id='add-member';button.textContent='Add member';
  button.onclick=()=>{count+=1;}; // Deliberately broken state-driven display, retained for a future pilot.
  register(button,import.meta.url,'MemberCounter');box.append(output,button);
  return register(box,import.meta.url,'MemberCounter');
}
