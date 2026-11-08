import type {Project} from '../../domain/projects';import {ProjectCard} from './ProjectCard';import styles from './ProjectWorkspace.module.css';
export function ProjectGrid({projects}:{projects:Project[]}){return <div className={styles.grid} id="project-grid">{projects.map(project=><ProjectCard key={project.id} project={project}/>)}{projects.length===0&&<p>No matching projects.</p>}</div>;}
