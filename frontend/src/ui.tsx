import { useEffect, useId, useRef, useState, type ReactNode, type FormEvent } from 'react';
import { api, ApiError } from './api';
export const label = (value: string) => value.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
export const localDate = () => new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
export function Icon({name, size=20}: {name:string;size?:number}) {
  const paths:Record<string,ReactNode>={
    dashboard:<><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="4" rx="1"/><rect x="14" y="11" width="7" height="10" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></>,
    patients:<><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m18 0v-2a4 4 0 0 0-3-3.87"/><circle cx="9" cy="7" r="4"/><path d="M16 3a4 4 0 0 1 0 8"/></>,
    appointments:<><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18m-13 5h2m4 0h2"/></>,
    beds:<><path d="M3 18v3m18-3v3M3 10v8h18v-5a3 3 0 0 0-3-3H9m-6 8V5"/><rect x="3" y="8" width="6" height="5" rx="1"/></>,
    admin:<><path d="m12 3 8 4v5c0 5-8 9-8 9s-8-4-8-9V7l8-4Z"/><path d="m8 12 3 3 5-6"/></>,
    plus:<path d="M12 5v14M5 12h14"/>,search:<><circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/></>,arrow:<path d="M5 12h14m-6-6 6 6-6 6"/>,close:<path d="m6 6 12 12M6 18 18 6"/>,logout:<><path d="M9 4H4v16h5m5-12 4 4-4 4m-6-4h13"/></>,clock:<><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,leaf:<><path d="M20 4C9 2 2 8 6 16s16 2 14-12Z"/><path d="M4 21 15 10"/></>,check:<path d="m5 12 4 4L19 6"/>,chevron:<path d="m9 5 7 7-7 7"/>,refresh:<><path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.dashboard}</svg>;
}
export function useResource<T>(path: string, refresh=0) {
  const [state,setState]=useState<{data?:T;error?:ApiError;loading:boolean}>({loading:true});
  useEffect(()=>{let active=true;const controller=new AbortController();setState({loading:true});api<T>(path,{signal:controller.signal}).then(data=>{if(active)setState({data,loading:false});}).catch(error=>{if(active)setState({error,loading:false});});return()=>{active=false;controller.abort();};},[path,refresh]);
  return state;
}
export function ErrorNotice({error,retry}:{error:Error;retry?:()=>void}) { return <div className="notice error" role="alert"><div><strong>{error instanceof ApiError && error.status===403?'Access restricted':error instanceof ApiError && error.status===409?'This record has changed':'Unable to complete request'}</strong><p>{error.message}</p>{error instanceof ApiError&&['mfa_enrollment_required','mfa_step_up_required'].includes(error.code)?<p>{error.code==='mfa_enrollment_required'?'Set up your authenticator before continuing.':'Verify your identity before continuing.'} <a href="#security">Open Account security</a>. Return to your intended action afterwards.</p>:error instanceof ApiError&&[401,403].includes(error.status)&&<p>Your session or permissions may have changed. Sign out and sign in again, or contact your administrator.</p>}</div>{retry&&<button className="button secondary" onClick={retry}>Try again</button>}</div>; }
export function Empty({title,children}:{title:string;children:ReactNode}) {return <div className="empty"><span className="empty-icon"><Icon name="search" size={26}/></span><h3>{title}</h3><p>{children}</p></div>;}
export function Loading(){return <div className="loading" role="status"><span className="spinner"/>Loading hospital records…</div>;}
export function Badge({value}:{value:string}){return <span className={`badge ${value}`}>{label(value)}</span>;}
export function Modal({title,onClose,children}:{title:string;onClose:()=>void;children:ReactNode}) {
  const ref=useRef<HTMLDivElement>(null);const id=useId();
  useEffect(()=>{const before=document.activeElement as HTMLElement;const element=ref.current;const focusable=()=>Array.from(element?.querySelectorAll<HTMLElement>('input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), [tabindex="0"]')||[]);const first=element?.querySelector<HTMLElement>('input, select, textarea')||focusable()[0];first?.focus();const key=(event:KeyboardEvent)=>{if(event.key==='Escape'){event.preventDefault();onClose();}if(event.key==='Tab'){const items=focusable();const index=items.indexOf(document.activeElement as HTMLElement);if(event.shiftKey&&index<=0){event.preventDefault();items.at(-1)?.focus();}else if(!event.shiftKey&&index===items.length-1){event.preventDefault();items[0]?.focus();}}};document.addEventListener('keydown',key);return()=>{document.removeEventListener('keydown',key);before?.focus();};},[onClose]);
  return <div className="modal-backdrop"><div className="modal" role="dialog" aria-modal="true" aria-labelledby={id} ref={ref}><div className="modal-header"><div><span className="eyebrow">HOSPITAL WORKSPACE</span><h2 id={id}>{title}</h2></div><button type="button" className="icon-button" aria-label="Close dialog" onClick={onClose}><Icon name="close"/></button></div>{children}</div></div>;
}
export function Field({name,title,type='text',required=false,children,errors,...props}:{name:string;title:string;type?:string;required?:boolean;children?:ReactNode;errors?:Record<string,string[]>;[key:string]:unknown}) {
  const error=errors?.[name];return <label className="field" htmlFor={name}><span id={`${name}-label`}>{title}{required&&<span className="required" aria-hidden="true"> *</span>}</span>{children||<input id={name} name={name} type={type} required={required} aria-labelledby={`${name}-label`} aria-invalid={!!error} aria-describedby={error?`${name}-error`:undefined} {...props}/ >}{error&&<small className="field-error" id={`${name}-error`}>{error.join(' ')}</small>}</label>;
}
export function SaveForm({children,onSave,submit='Save',onCancel}:{children:(fields:Record<string,string[]>)=>ReactNode;onSave:(data:FormData)=>Promise<void>;submit?:string;onCancel:()=>void}) {
  const [busy,setBusy]=useState(false);const [error,setError]=useState<ApiError>();const summary=useRef<HTMLDivElement>(null);
  async function save(event:FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setError(undefined);try{await onSave(new FormData(event.currentTarget));}catch(e){setError(e instanceof ApiError?e:new ApiError(e instanceof Error?e.message:'The request could not be completed. Try again.',0));}finally{setBusy(false);}}
  useEffect(()=>{if(error)summary.current?.focus();},[error]);
  return <form onSubmit={save} className="record-form">{error&&<div tabIndex={-1} ref={summary}><ErrorNotice error={error}/></div>}<div className="form-fields">{children(error?.fields||{})}</div><div className="form-footer"><span>* Required information</span><div><button type="button" className="button secondary" onClick={onCancel} disabled={busy}>Cancel</button><button className="button primary" disabled={busy}>{busy?'Saving…':submit}</button></div></div></form>;
}
export function Pager({count,offset,onChange}:{count:number;offset:number;onChange:(offset:number)=>void}){return <div className="pager"><span>{count===0?'0 records':`${offset+1}–${Math.min(offset+25,count)} of ${count} records`}</span><div><button className="button secondary small" disabled={offset===0} onClick={()=>onChange(Math.max(0,offset-25))}>Previous</button><button className="button secondary small" disabled={offset+25>=count} onClick={()=>onChange(offset+25)}>Next</button></div></div>;}
