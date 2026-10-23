import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from './api';
import type { Branch, List } from './types';
import { Empty, ErrorNotice, Field, label, Loading, Modal, Pager, SaveForm, useResource } from './ui';

interface Assignment {branch:string;role:string}
interface Staff {id:number;username:string;name:string;account_active:boolean;status:'active'|'suspended';version:number;assignments:Assignment[]}
type StaffForm={kind:'create'}|{kind:'edit'|'status';staff:Staff};
const roles=['master_admin','reception','doctor','pharmacist','accounts','nurse','therapist'];
const roleLabel=(role:string)=>`${label(role)}${['pharmacist','accounts','therapist'].includes(role)?' (workflow planned)':''}`;
const branchLabel=(branch:Branch)=>`${branch.name} (${branch.code})`;

function useBranchNames(base:string,staff?:List<Staff>){
  const [state,setState]=useState<{names:Record<string,Branch>;error?:ApiError}>({names:{}});
  useEffect(()=>{
    const controller=new AbortController();let active=true;
    const needed=new Set(staff?.results.flatMap(person=>person.assignments.map(assignment=>assignment.branch))||[]);
    setState({names:{}});
    async function resolve(){
      const names:Record<string,Branch>={};let offset=0;
      try{
        while(needed.size){
          const page=await api<List<Branch>>(`${base}branches/?limit=100&offset=${offset}`,{signal:controller.signal});
          if(!active)return;
          for(const branch of page.results)if(needed.delete(branch.id))names[branch.id]=branch;
          setState({names:{...names}});offset+=page.results.length;
          if(!page.results.length||offset>=page.count)break;
        }
      }catch(error){if(active)setState({names,error:error instanceof ApiError?error:new ApiError('Branch names could not be loaded. Reload staff to try again.',0)});}
    }
    void resolve();return()=>{active=false;controller.abort();};
  },[base,staff]);
  return state;
}

function AssignmentBranch({base,index,value,onChange,known}:{base:string;index:number;value:string;onChange:(branch:string)=>void;known?:Branch}){
  const [offset,setOffset]=useState(0);const [refresh,setRefresh]=useState(0);
  const [selected,setSelected]=useState<Branch>();
  const state=useResource<List<Branch>>(`${base}branches/?limit=25&offset=${offset}`,refresh);
  const id=`assignment-branch-${index}`;
  const selectedName=selected?.id===value?selected:known;
  return <div><label className="field" htmlFor={id}><span>Branch {index+1}</span><select id={id} required value={value} disabled={state.loading||!!state.error} onChange={event=>{setSelected(state.data?.results.find(branch=>branch.id===event.target.value));onChange(event.target.value);}}>
    <option value="">Select a branch</option>{value&&!state.data?.results.some(branch=>branch.id===value)&&<option value={value}>{selectedName?branchLabel(selectedName):'Assigned branch (name unavailable)'}</option>}{state.data?.results.map(branch=><option key={branch.id} value={branch.id}>{branchLabel(branch)}</option>)}
  </select></label>{state.error&&<ErrorNotice error={state.error} retry={()=>setRefresh(n=>n+1)}/>}{state.data?.count===0&&<p className="form-hint">No branches available. Contact your administrator.</p>}
    <nav className="pager" aria-label={`Branch choices ${index+1}`}><span>{state.loading?'Loading branches…':`${state.data?.count||0} branches`}</span><div><button type="button" className="button secondary small" aria-label={`Previous branches ${index+1}`} disabled={state.loading||offset===0} onClick={()=>setOffset(n=>Math.max(0,n-25))}>Previous branches</button><button type="button" className="button secondary small" aria-label={`Next branches ${index+1}`} disabled={state.loading||!state.data||offset+25>=state.data.count} onClick={()=>setOffset(n=>n+25)}>Next branches</button></div></nav>
  </div>;
}

function StaffAccessForm({base,form,names,onClose,onSaved}:{base:string;form:StaffForm;names:Record<string,Branch>;onClose:()=>void;onSaved:(created:boolean)=>void}){
  const staff=form.kind==='create'?undefined:form.staff;
  const [assignments,setAssignments]=useState<(Assignment&{key:number})[]>(staff?.assignments.map((assignment,key)=>({...assignment,key}))||[{branch:'',role:'reception',key:0}]);
  const [nextKey,setNextKey]=useState(assignments.length);
  const [pending,setPending]=useState(false);
  function update(index:number,change:Partial<Assignment>){setAssignments(rows=>rows.map((row,i)=>i===index?{...row,...change}:row));}
  async function save(data:FormData){
    const status=form.kind==='status'?(staff?.status==='active'?'suspended':'active'):undefined;
    if(form.kind!=='status'){
      if(assignments.length<1||assignments.length>100)throw new ApiError('Choose between 1 and 100 branch and role assignments.',400,{assignments:['Choose between 1 and 100 assignments.']});
      if(assignments.some(row=>!row.branch))throw new ApiError('Select a branch for every assignment.',400,{assignments:['Every assignment needs a branch.']});
      if(new Set(assignments.map(row=>`${row.branch}:${row.role}`)).size!==assignments.length)throw new ApiError('Duplicate branch and role assignments are not allowed. Remove or change the duplicate.',400,{assignments:['Each branch and role pair must be unique.']});
    }
    const pairs=assignments.map(({branch,role})=>({branch,role}));
    const body=form.kind==='create'?{username:String(data.get('username')||'').trim(),name:String(data.get('name')||'').trim(),password:String(data.get('password')||''),assignments:pairs}:{expected_version:staff!.version,...(status?{status}:{assignments:pairs})};
    setPending(true);
    try{await api(`${base}${staff?`${staff.id}/`:''}`,{method:staff?'PATCH':'POST',body:JSON.stringify(body)});onSaved(!staff);}
    catch(error){
      if(error instanceof ApiError){
        if(!staff&&(error.status===409||error.status===0||error.status>=500||(error.status>=200&&error.status<300)))throw new ApiError(`${error.message} Your entries have been kept. Cancel, refresh staff and search for the username before attempting another creation. An existing account will never be attached automatically.`,error.status,error.fields);
        if(staff&&error.status===409)throw new ApiError(`${error.message} Your entries have been kept. Cancel, reload staff, then reopen this person to review the latest access.`,409,error.fields);
      }
      throw error;
    }finally{setPending(false);}
  }
  const close=useCallback(()=>{if(!pending)onClose();},[pending,onClose]);
  return <Modal title={form.kind==='create'?'Add staff':form.kind==='edit'?'Edit staff access':staff?.status==='active'?'Suspend staff access':'Restore staff access'} onClose={close}>
    {staff&&<p className="modal-description">{staff.name} · {staff.username}</p>}
    <SaveForm onSave={save} onCancel={close} submit={form.kind==='create'?'Create staff':form.kind==='edit'?'Save access':staff?.status==='active'?'Suspend organisation access':'Restore organisation access'}>{errors=><>
      {form.kind==='create'?<><Field name="username" title="Username" required maxLength={150} autoComplete="off" errors={errors}/><Field name="name" title="Full name" required maxLength={150} autoComplete="off" errors={errors}/><Field name="password" title="Initial password" type="password" required minLength={12} maxLength={128} autoComplete="new-password" errors={errors}/><p className="form-hint">Use 12–128 characters. Avoid common passwords, only numbers or words similar to the staff name.</p></>:form.kind==='edit'?<p className="form-hint">Username and full name cannot be changed here. Version {staff?.version}.</p>:<p className="form-hint">{staff?.status==='active'?'This removes access to this organisation until restored. Access to other organisations is unchanged.':'This restores the current branch and role assignments for this organisation. A globally disabled account still cannot sign in.'}</p>}
      {form.kind!=='status'&&<fieldset disabled={pending} className="staff-assignments"><legend>Branch and role assignments</legend>{errors.assignments&&<p className="field-error" id="assignments-error">{errors.assignments.join(' ')}</p>}{assignments.map((assignment,index)=><div className="staff-assignment" key={assignment.key}><AssignmentBranch base={base} index={index} value={assignment.branch} known={names[assignment.branch]} onChange={branch=>update(index,{branch})}/><label className="field" htmlFor={`assignment-role-${index}`}><span>Role {index+1}</span><select id={`assignment-role-${index}`} value={assignment.role} onChange={event=>update(index,{role:event.target.value})}>{roles.map(role=><option key={role} value={role}>{roleLabel(role)}</option>)}</select></label><button type="button" className="text-button danger" aria-label={`Remove assignment ${index+1}`} disabled={assignments.length<=1} onClick={()=>setAssignments(rows=>rows.filter((_,i)=>i!==index))}>Remove assignment</button></div>)}<button type="button" className="button secondary" disabled={assignments.length>=100} onClick={()=>{setAssignments(rows=>[...rows,{branch:'',role:'reception',key:nextKey}]);setNextKey(n=>n+1);}}>Add assignment</button><p className="form-hint">Choose 1–100 unique branch and role pairs per save. Roles do not grant clinical signing outside their authorised workflows.</p></fieldset>}
    </>}</SaveForm>
  </Modal>;
}

export function StaffAdministration({organisation,currentUserId,onChanged}:{organisation:string;currentUserId:number;onChanged:()=>void}){
  const base=`platform/organisations/${encodeURIComponent(organisation)}/staff/`;
  const [refresh,setRefresh]=useState(0);const [offset,setOffset]=useState(0);const [search,setSearch]=useState('');const [query,setQuery]=useState('');const [form,setForm]=useState<StaffForm>();const [notice,setNotice]=useState('');
  const close=useCallback(()=>setForm(undefined),[]);
  const state=useResource<List<Staff>>(`${base}?${new URLSearchParams({limit:'25',offset:String(offset),q:query})}`,refresh);
  const branches=useBranchNames(base,state.data);
  function reload(){setRefresh(n=>n+1);}
  function saved(created:boolean){close();setNotice(created?'Staff account created.':'Staff access updated.');reload();onChanged();}
  return <section className="panel staff-administration" aria-labelledby="staff-access-title"><div className="panel-title"><div><span className="eyebrow">PEOPLE AND PERMISSIONS</span><h2 id="staff-access-title">Staff access</h2></div><div className="resource-actions"><button className="button secondary" onClick={reload}>Reload staff</button><button className="button primary" onClick={()=>setForm({kind:'create'})}>Add staff</button></div></div>
    <p className="modal-description">Manage staff access for the organisation shown above. Staff can manage their authenticator and password in Account security. Administrator password reset is not available.</p>{notice&&<div className="notice success" role="status">{notice}</div>}
    <form className="list-toolbar" onSubmit={event=>{event.preventDefault();setOffset(0);setQuery(search.trim());}}><label className="field" htmlFor="staff-search"><span>Search staff</span><input type="search" id="staff-search" maxLength={200} value={search} onChange={event=>setSearch(event.target.value)} placeholder="Name or username"/></label><button className="button secondary">Search staff</button></form>
    {state.loading?<Loading/>:state.error?<ErrorNotice error={state.error} retry={reload}/>:!state.data?.count?<Empty title="No staff found">Search another name or username, or add a new staff account.</Empty>:<div className="table-scroll"><table><thead><tr><th>Staff member</th><th>Organisation access</th><th>Branch and role</th><th>Next action</th></tr></thead><tbody>{state.data.results.map(person=><tr key={person.id}><td><strong>{person.name}</strong><p>{person.username}</p><small>{person.account_active?'Global account enabled':'Global account disabled'}</small></td><td>{person.status==='active'?'Active organisation access':'Suspended organisation access'}<p className="subtle">Version {person.version}</p></td><td>{person.assignments.map(assignment=><div key={`${assignment.branch}:${assignment.role}`}><span>{branches.names[assignment.branch]?branchLabel(branches.names[assignment.branch]):'Branch name unavailable'}</span><p className="subtle">{roleLabel(assignment.role)}</p></div>)}</td><td>{person.id===currentUserId?<span className="subtle">Your access must be managed by another administrator.</span>:<div className="row-actions"><button className="button secondary small" aria-label={`Edit access for ${person.name}`} onClick={()=>setForm({kind:'edit',staff:person})}>Edit access</button><button className={`text-button ${person.status==='active'?'danger':''}`} aria-label={`${person.status==='active'?'Suspend':'Restore'} access for ${person.name}`} onClick={()=>setForm({kind:'status',staff:person})}>{person.status==='active'?'Suspend access':'Restore access'}</button></div>}</td></tr>)}</tbody></table></div>}
    {branches.error&&<ErrorNotice error={branches.error} retry={reload}/>} {state.data&&<Pager count={state.data.count} offset={offset} onChange={setOffset}/>}
    {form&&<StaffAccessForm base={base} form={form} names={branches.names} onClose={close} onSaved={saved}/>}
  </section>;
}
