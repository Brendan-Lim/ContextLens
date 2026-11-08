import {useState} from 'react';import type {FormEvent} from 'react';import {acceptsContact} from '../domain/validation/contactPolicy';
export function useContactSubmission(){
  const [email,setEmail]=useState('');const [status,setStatus]=useState<'idle'|'error'|'saved'>('idle');
  const submit=(event:FormEvent)=>{event.preventDefault();setStatus(acceptsContact(email)?'saved':'error');};
  return {email,setEmail,status,submit};
}
