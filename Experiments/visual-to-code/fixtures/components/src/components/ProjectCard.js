import {register} from '../dev-source.js';
export function ProjectCard(id,title) {
  const card=document.createElement('article');card.id=id;card.className='project-card';
  const heading=document.createElement('h2');heading.textContent=title;card.append(heading);
  return register(card,import.meta.url,'ProjectCard');
}
