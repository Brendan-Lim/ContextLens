import {useMemo,useState} from 'react';import {selectProjects} from '../domain/projects';
export function useProjectSearch(){const [query,setQuery]=useState('');const [status,setStatus]=useState('All');const results=useMemo(()=>selectProjects(query,status),[query,status]);return {query,setQuery,status,setStatus,results};}
