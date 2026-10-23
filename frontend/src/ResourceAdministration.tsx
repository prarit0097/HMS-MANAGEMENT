import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from './api';
import type { Branch, List } from './types';
import { Badge, Empty, ErrorNotice, Field, label, Loading, Modal, Pager, SaveForm, useResource } from './ui';

interface ConfigurationBed { id:string; branch:string; number:string; room_number:string; category:string; status:string; version:number }
const categories=['general','semi_private','private','private_luxury','villa'];
const statuses=['available','cleaning','blocked'];
const value=(form:FormData,name:string)=>String(form.get(name)||'').trim();

function BranchChoices({base,errors}:{base:string;errors:Record<string,string[]>}) {
  const [offset,setOffset]=useState(0);
  const [selected,setSelected]=useState('');
  const [refresh,setRefresh]=useState(0);
  const state=useResource<List<Branch>>(`${base}branches/?limit=25&offset=${offset}`,refresh);
  return <div><Field name="branch" title="Branch" required errors={errors}><select id="branch" name="branch" required value={selected} onChange={event=>setSelected(event.target.value)} disabled={state.loading||!!state.error} aria-invalid={!!errors.branch} aria-describedby={errors.branch?'branch-error':undefined}><option value="">Select a branch</option>{state.data?.results.map(branch=><option key={branch.id} value={branch.id}>{branch.name} ({branch.code})</option>)}</select></Field>
    {state.loading?<Loading/>:state.error?<ErrorNotice error={state.error} retry={()=>setRefresh(n=>n+1)}/>:state.data?.count===0?<p>No branches available. Add a branch first.</p>:null}
    <nav className="pager" aria-label="Branch choices"><span>{state.data?`${state.data.count} branches`:'Loading branches…'}</span><div><button type="button" className="button secondary small" disabled={state.loading||offset===0} onClick={()=>{setSelected('');setOffset(n=>Math.max(0,n-25));}}>Previous branches</button><button type="button" className="button secondary small" disabled={state.loading||!state.data||offset+25>=state.data.count} onClick={()=>{setSelected('');setOffset(n=>n+25);}}>Next branches</button></div></nav>
  </div>;
}

export function ResourceAdministration({organisation,onChanged}:{organisation:string;onChanged:()=>void}) {
  const base=`platform/organisations/${encodeURIComponent(organisation)}/`;
  const [refresh,setRefresh]=useState(0);
  const [branchOffset,setBranchOffset]=useState(0);
  const [selectedBranch,setSelectedBranch]=useState<Branch>();
  const [form,setForm]=useState<'branch'|'bed'|ConfigurationBed>();
  const [notice,setNotice]=useState('');
  const close=useCallback(()=>setForm(undefined),[]);
  const branches=useResource<List<Branch>>(`${base}branches/?limit=25&offset=${branchOffset}`,refresh);
  useEffect(()=>{if(!selectedBranch&&branches.data?.results[0])setSelectedBranch(branches.data.results[0]);},[selectedBranch,branches.data]);
  const editing=typeof form==='object'?form:undefined;
  async function save(data:FormData) {
    if(form==='branch')await api(`${base}branches/`,{method:'POST',body:JSON.stringify({name:value(data,'name'),code:value(data,'code')})});
    else {
      const body={number:value(data,'number'),room_number:value(data,'room_number'),category:value(data,'category'),status:value(data,'status')};
      try { await api(`${base}beds/${editing?`${encodeURIComponent(editing.id)}/`:''}`,{method:editing?'PATCH':'POST',body:JSON.stringify(editing?{expected_version:editing.version,...body}:{branch:value(data,'branch'),...body})}); }
      catch(error) {if(error instanceof ApiError&&error.status===409)throw new ApiError(`${error.message} Your entries have been kept. Cancel, reload inventory, then reopen the bed to review the latest details.`,409,error.fields);throw error;}
    }
    setNotice(form==='branch'?'Branch added.':editing?'Bed updated.':'Bed added.');close();setRefresh(n=>n+1);onChanged();
  }
  return <div className="resource-administration">
    {notice&&<div className="notice success" role="status">{notice}</div>}
    <section className="panel" aria-labelledby="branches-title"><div className="panel-title"><div><span className="eyebrow">HOSPITAL CONFIGURATION</span><h2 id="branches-title">Branches</h2></div><button className="button primary" onClick={()=>setForm('branch')}>Add branch</button></div>
      {branches.loading?<Loading/>:branches.error?<ErrorNotice error={branches.error} retry={()=>setRefresh(n=>n+1)}/>:!branches.data?.count?<Empty title="No branches configured">Add the hospital branch before adding beds.</Empty>:<div className="admin-list">{branches.data.results.map(branch=><div key={branch.id}><span>{branch.name}</span><strong>{branch.code}</strong></div>)}</div>}
      {branches.data&&<Pager count={branches.data.count} offset={branchOffset} onChange={setBranchOffset}/>}
    </section>
    <section className="panel" aria-labelledby="inventory-title"><div className="panel-title"><div><span className="eyebrow">ROOMS AND CAPACITY</span><h2 id="inventory-title">Bed inventory</h2></div><div className="resource-actions"><button className="button secondary" onClick={()=>setRefresh(n=>n+1)}>Reload inventory</button><button className="button primary" onClick={()=>setForm('bed')}>Add bed</button></div></div>
      <div className="list-toolbar"><label className="field" htmlFor="inventory-branch"><span>Bed inventory branch</span><select id="inventory-branch" value={selectedBranch?.id||''} disabled={branches.loading||!branches.data?.count} onChange={event=>setSelectedBranch(branches.data?.results.find(branch=>branch.id===event.target.value))}>
        {!selectedBranch&&<option value="">Select a branch</option>}{selectedBranch&&!branches.data?.results.some(branch=>branch.id===selectedBranch.id)&&<option value={selectedBranch.id}>{selectedBranch.name} ({selectedBranch.code})</option>}{branches.data?.results.map(branch=><option key={branch.id} value={branch.id}>{branch.name} ({branch.code})</option>)}
      </select></label><p className="form-hint">Use the Branches page buttons above to find more branches.</p></div>
      {selectedBranch?<ConfiguredBeds key={selectedBranch.id} base={base} branch={selectedBranch} refresh={refresh} onEdit={setForm} onReload={()=>setRefresh(n=>n+1)}/>:branches.loading?<Loading/>:<p className="modal-description">Add a branch first to configure bed inventory.</p>}
    </section>
    {form&&<Modal title={form==='branch'?'Add branch':editing?`Edit bed ${editing.number}`:'Add bed'} onClose={close}>{editing&&<p className="modal-description">Bed allocation is checked again when you save. Occupied and reserved beds cannot be changed here.</p>}<SaveForm onSave={save} onCancel={close} submit={form==='branch'?'Save branch':'Save bed'}>{errors=>form==='branch'?<><Field name="name" title="Branch name" required errors={errors} maxLength={160}/><Field name="code" title="Branch code" required errors={errors} maxLength={32}/><p className="form-hint">Use letters, numbers or hyphens for the branch code.</p><p className="form-hint">New branches need staff access assignments before operational use. Ask a staff administrator to assign access after creating a branch.</p></>:<>
      {!editing&&<BranchChoices base={base} errors={errors}/>}
      <div className="form-row"><Field name="number" title="Bed number" required errors={errors} maxLength={32} defaultValue={editing?.number}/><Field name="room_number" title="Room number" required errors={errors} maxLength={32} defaultValue={editing?.room_number}/></div>
      <Field name="category" title="Accommodation" errors={errors}><select id="category" name="category" defaultValue={editing?.category||'general'} aria-invalid={!!errors.category} aria-describedby={errors.category?'category-error':undefined}>{categories.map(category=><option key={category} value={category}>{label(category)}</option>)}</select></Field>
      <Field name="status" title="Bed status" errors={errors}><select id="status" name="status" defaultValue={editing?.status||'available'} aria-invalid={!!errors.status} aria-describedby={errors.status?'status-error':undefined}>{statuses.map(status=><option key={status} value={status}>{label(status)}</option>)}</select></Field>
    </>}</SaveForm></Modal>}
  </div>;
}

function ConfiguredBeds({base,branch,refresh,onEdit,onReload}:{base:string;branch:Branch;refresh:number;onEdit:(bed:ConfigurationBed)=>void;onReload:()=>void}) {
  const [offset,setOffset]=useState(0);
  const beds=useResource<List<ConfigurationBed>>(`${base}beds/?limit=25&offset=${offset}&branch=${encodeURIComponent(branch.id)}`,refresh);
  return <>{beds.loading?<Loading/>:beds.error?<ErrorNotice error={beds.error} retry={onReload}/>:!beds.data?.count?<Empty title="No beds configured">Add beds for {branch.name}.</Empty>:<div className="bed-grid">{beds.data.results.map(bed=><article className={`bed-card ${bed.status}`} key={bed.id}><div className="bed-top"><h3>Bed {bed.number}</h3><Badge value={bed.status}/></div><p>Room {bed.room_number} · {label(bed.category)}</p><p>{branch.name} ({branch.code})</p>{statuses.includes(bed.status)?<button className="button secondary small" aria-label={`Edit bed ${bed.number}`} onClick={()=>onEdit(bed)}>Edit bed</button>:<p>Allocation must be resolved through inpatient care before editing.</p>}</article>)}</div>}{beds.data&&<Pager count={beds.data.count} offset={offset} onChange={setOffset}/>}</>;
}
