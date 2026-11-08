import {register} from '../dev-source.js';
import {SaveButton} from './SaveButton.js';
import {ProjectCard} from './ProjectCard.js';
import {MemberCounter} from './MemberCounter.js';
export function Workspace() {
  const root=document.createElement('section');root.id='workspace';
  const heading=document.createElement('h1');heading.textContent='Project workspace';root.append(heading);
  const row=document.createElement('div');row.id='button-row';row.className='button-row';
  row.append(SaveButton(),SaveButton('publish'));register(row,import.meta.url,'Workspace');root.append(row);
  const label=document.createElement('label');label.textContent='Project name';
  const input=document.createElement('input');input.id='project-name';label.append(input);root.append(label);
  const grid=document.createElement('div');grid.id='projects';grid.className='projects';
  grid.append(ProjectCard('project-a','Alpha'),ProjectCard('project-b','Beta'));register(grid,import.meta.url,'Workspace');root.append(grid,MemberCounter());
  const overlap=document.createElement('div');overlap.id='overlap';
  const under=SaveButton('covered');const cover=document.createElement('div');cover.id='cover';cover.className='cover';cover.setAttribute('role','alert');cover.textContent='Overlay';
  register(cover,import.meta.url,'Workspace');overlap.append(under,cover);root.append(overlap);
  const frame=document.createElement('iframe');frame.id='local-frame';frame.src='frame.html';frame.title='Local frame';root.append(frame);
  const opaque=document.createElement('iframe');opaque.id='opaque-frame';opaque.sandbox='';opaque.srcdoc='<button>Opaque content</button>';opaque.title='Unsupported opaque frame';root.append(opaque);
  const bottom=document.createElement('div');bottom.id='scroll-target';bottom.append(SaveButton('scroll-save'));root.append(bottom);
  return register(root,import.meta.url,'Workspace');
}
