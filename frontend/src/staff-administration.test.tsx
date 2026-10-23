import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { Administration } from './pages';
import type { User } from './types';

const user:User={id:1,username:'admin',name:'Synthetic Admin',roles:['master_admin'],branches:[],permissions:['platform.read','platform.staff.manage']};
const summary={organisation:{id:'org-1',name:'Synthetic Hospital'},branches_count:126,staff_count:2,active_staff_count:2,security:{ip_mode:'standard'},modules:[]};
const branches=Array.from({length:126},(_,i)=>({id:`b${i+1}`,name:`Branch ${i+1}`,code:`B${i+1}`}));
const staff={id:2,username:'staff.test',name:'Synthetic Staff',account_active:false,status:'active',version:0,assignments:[{branch:'b126',role:'reception'}]};
afterEach(()=>vi.unstubAllGlobals());
function serve(handler?:(url:string,options:RequestInit)=>Response|undefined){
 const writes:{url:string;method:string;body:unknown}[]=[];const reads:string[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string,options:RequestInit)=>{
  if(options.method)writes.push({url,method:options.method,body:JSON.parse(String(options.body))});else reads.push(url);
  const result=handler?.(url,options);if(result)return result;
  if(url.endsWith('platform/summary/'))return Response.json(summary);
  const params=new URL(url,'https://test.invalid').searchParams;const offset=Number(params.get('offset')||0);
  if(url.includes('/branches/'))return Response.json({count:126,results:branches.slice(offset,offset+Number(params.get('limit')||25))});
  return Response.json({count:1,results:[staff]});
 }));return {writes,reads};
}
async function openCreate(){await userEvent.click(await screen.findByRole('button',{name:'Add staff'}));return within(screen.getByRole('dialog'));}
async function fillCreate(){const dialog=await openCreate();await userEvent.type(dialog.getByRole('textbox',{name:'Username'}),'new.staff');await userEvent.type(dialog.getByRole('textbox',{name:'Full name'}),'Synthetic New');await userEvent.type(dialog.getByLabelText(/Initial password/),'SyntheticSecret!27');await userEvent.selectOptions(await dialog.findByRole('combobox',{name:'Branch 1'}),'b1');return dialog;}

it('makes no staff reads or controls without the explicit staff permission',async()=>{
 const {reads}=serve();render(<Administration user={{...user,permissions:['platform.read']}}/>);await screen.findByText('Synthetic Hospital');expect(screen.queryByRole('button',{name:'Add staff'})).not.toBeInTheDocument();expect(reads.some(path=>path.includes('/staff/'))).toBe(false);
});
it('resolves assignment names beyond 100 and scopes staff search to the current organisation',async()=>{
 const {reads}=serve();render(<Administration user={user}/>);await screen.findByText('Branch 126 (B126)');expect(screen.queryByText('b126')).not.toBeInTheDocument();
 await userEvent.type(screen.getByRole('searchbox',{name:'Search staff'}),'staff.test');await userEvent.click(screen.getByRole('button',{name:'Search staff'}));
 await waitFor(()=>expect(reads.some(path=>path.includes('/organisations/org-1/staff/?')&&new URL(path,'https://test.invalid').searchParams.get('q')==='staff.test')).toBe(true));
 expect(screen.getByText('Global account disabled')).toBeInTheDocument();expect(screen.getByText('Active organisation access')).toBeInTheDocument();
});
it('creates with a masked write-only secret and repeatable branch role choices beyond 100 then refreshes',async()=>{
 const {writes,reads}=serve((_url,options)=>options.method==='POST'?Response.json({...staff,id:3},{status:201}):undefined);render(<Administration user={user}/>);const dialog=await fillCreate();
 expect(dialog.getByLabelText(/Initial password/)).toHaveAttribute('type','password');
 await userEvent.click(dialog.getByRole('button',{name:'Add assignment'}));
 for(let i=0;i<4;i++){await waitFor(()=>expect(dialog.getByRole('button',{name:'Next branches 2'})).toBeEnabled());await userEvent.click(dialog.getByRole('button',{name:'Next branches 2'}));}
 await userEvent.selectOptions(await dialog.findByRole('combobox',{name:'Branch 2'}),'b101');await userEvent.selectOptions(dialog.getByRole('combobox',{name:'Role 2'}),'nurse');
 await userEvent.click(dialog.getByRole('button',{name:'Create staff'}));await screen.findByText('Staff account created.');expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 expect(writes).toEqual([{url:'/api/v1/platform/organisations/org-1/staff/',method:'POST',body:{username:'new.staff',name:'Synthetic New',password:'SyntheticSecret!27',assignments:[{branch:'b1',role:'reception'},{branch:'b101',role:'nurse'}]}}]);await waitFor(()=>expect(reads.filter(path=>path.endsWith('platform/summary/')).length).toBeGreaterThan(1));
 await openCreate();expect(screen.getByLabelText(/Initial password/)).toHaveValue('');
});
it('rejects duplicate branch role pairs before any write',async()=>{
 const {writes}=serve();render(<Administration user={user}/>);const dialog=await fillCreate();await userEvent.click(dialog.getByRole('button',{name:'Add assignment'}));await userEvent.selectOptions(dialog.getByRole('combobox',{name:'Branch 2'}),'b1');await userEvent.click(dialog.getByRole('button',{name:'Create staff'}));expect(await dialog.findByRole('alert')).toHaveTextContent(/duplicate/i);expect(writes).toHaveLength(0);
});
it('edits assignments using legacy expected version zero without identity or password fields',async()=>{
 const {writes}=serve((_url,options)=>options.method==='PATCH'?Response.json({...staff,version:1}):undefined);render(<Administration user={user}/>);await userEvent.click(await screen.findByRole('button',{name:'Edit access for Synthetic Staff'}));const dialog=within(screen.getByRole('dialog'));
 expect(dialog.queryByRole('textbox',{name:'Username'})).not.toBeInTheDocument();expect(dialog.queryByLabelText(/Initial password/)).not.toBeInTheDocument();await userEvent.selectOptions(dialog.getByRole('combobox',{name:'Role 1'}),'nurse');await userEvent.click(dialog.getByRole('button',{name:'Save access'}));await screen.findByText('Staff access updated.');expect(writes[0]).toEqual({url:'/api/v1/platform/organisations/org-1/staff/2/',method:'PATCH',body:{expected_version:0,assignments:[{branch:'b126',role:'nurse'}]}});
});
it.each(['active','suspended'])('explicitly confirms organisation status changes from %s',async(status)=>{
 const {writes}=serve((url,options)=>options.method==='PATCH'?Response.json({...staff,status:status==='active'?'suspended':'active',version:1}):url.includes('/staff/?')?Response.json({count:1,results:[{...staff,status}]}):undefined);render(<Administration user={user}/>);await userEvent.click(await screen.findByRole('button',{name:`${status==='active'?'Suspend':'Restore'} access for Synthetic Staff`}));const dialog=within(screen.getByRole('dialog'));expect(dialog.getByText(/Synthetic Staff/)).toBeInTheDocument();expect(writes).toHaveLength(0);await userEvent.click(dialog.getByRole('button',{name:status==='active'?'Suspend organisation access':'Restore organisation access'}));await screen.findByText('Staff access updated.');expect(writes[0].body).toEqual({expected_version:0,status:status==='active'?'suspended':'active'});
});
it('never offers self edits or self suspension',async()=>{
 serve(url=>url.includes('/staff/?')?Response.json({count:1,results:[{...staff,id:1}]}):undefined);render(<Administration user={user}/>);await screen.findByText('Synthetic Staff');expect(screen.queryByRole('button',{name:'Edit access for Synthetic Staff'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Suspend access for Synthetic Staff'})).not.toBeInTheDocument();
});
it('paginates staff without imposing a 100-person limit',async()=>{
 const {reads}=serve(url=>url.includes('/staff/?')?Response.json({count:126,results:[staff]}):undefined);render(<Administration user={user}/>);const region=within((await screen.findByRole('heading',{name:'Staff access'})).closest('section')!);await userEvent.click(await region.findByRole('button',{name:'Next'}));await waitFor(()=>expect(reads.some(path=>path.includes('/staff/?')&&path.includes('offset=25'))).toBe(true));
});
it.each([409,403,0])('keeps failed create fields and avoids automatic retry or foreign-user attachment (%s)',async(status)=>{
 const {writes}=serve((_url,options)=>{if(options.method==='POST'){if(!status)throw new TypeError('Network failed');return Response.json({message:'Cannot create account.',field_errors:{username:['Review username.']}},{status});}return undefined;});render(<Administration user={user}/>);const dialog=await fillCreate();await userEvent.click(dialog.getByRole('button',{name:'Create staff'}));expect(await dialog.findByRole('alert')).toHaveTextContent(status===403?/Cannot create/:/refresh.*search/i);expect(dialog.getByRole('textbox',{name:'Username'})).toHaveValue('new.staff');expect(dialog.getByLabelText(/Initial password/)).toHaveValue('SyntheticSecret!27');expect(writes).toHaveLength(1);
});
it('retains stale access edits with field errors and reload guidance',async()=>{
 const {writes}=serve((_url,options)=>options.method==='PATCH'?Response.json({message:'Access changed.',field_errors:{assignments:['Review assignments.']}},{status:409}):undefined);render(<Administration user={user}/>);await userEvent.click(await screen.findByRole('button',{name:'Edit access for Synthetic Staff'}));const dialog=within(screen.getByRole('dialog'));await userEvent.selectOptions(dialog.getByRole('combobox',{name:'Role 1'}),'nurse');await userEvent.click(dialog.getByRole('button',{name:'Save access'}));expect(await dialog.findByRole('alert')).toHaveTextContent(/reload/i);expect(dialog.getByRole('combobox',{name:'Role 1'})).toHaveValue('nurse');expect(dialog.getByText('Review assignments.')).toBeInTheDocument();expect(writes).toHaveLength(1);
});
it('treats an unreadable successful create response as ambiguous and retains the form',async()=>{
 const {writes}=serve((_url,options)=>options.method==='POST'?new Response('unreadable',{status:201}):undefined);render(<Administration user={user}/>);const dialog=await fillCreate();await userEvent.click(dialog.getByRole('button',{name:'Create staff'}));expect(await dialog.findByRole('alert')).toHaveTextContent(/refresh.*search/i);expect(dialog.getByRole('textbox',{name:'Username'})).toHaveValue('new.staff');expect(writes).toHaveLength(1);
});
it('clears a cancelled secret without storing form details and reports password validation inline',async()=>{
 const storage=vi.spyOn(Storage.prototype,'setItem');serve((_url,options)=>options.method==='POST'?Response.json({message:'Check the highlighted details.',field_errors:{password:['Choose a stronger password.']}},{status:400}):undefined);render(<Administration user={user}/>);const dialog=await fillCreate();await userEvent.click(dialog.getByRole('button',{name:'Create staff'}));expect(await dialog.findByText('Choose a stronger password.')).toBeInTheDocument();expect(dialog.getByLabelText(/Initial password/)).toHaveAttribute('aria-invalid','true');await userEvent.click(dialog.getByRole('button',{name:'Cancel'}));await openCreate();expect(screen.getByLabelText(/Initial password/)).toHaveValue('');expect(storage).not.toHaveBeenCalled();storage.mockRestore();
});
it('allows two distinct roles at one branch and removes an unwanted assignment before save',async()=>{
 const {writes}=serve((_url,options)=>options.method==='POST'?Response.json({...staff,id:3},{status:201}):undefined);render(<Administration user={user}/>);const dialog=await fillCreate();await userEvent.click(dialog.getByRole('button',{name:'Add assignment'}));await userEvent.selectOptions(dialog.getByRole('combobox',{name:'Branch 2'}),'b1');await userEvent.selectOptions(dialog.getByRole('combobox',{name:'Role 2'}),'nurse');await userEvent.click(dialog.getByRole('button',{name:'Add assignment'}));await userEvent.click(dialog.getByRole('button',{name:'Remove assignment 3'}));await userEvent.click(dialog.getByRole('button',{name:'Create staff'}));await screen.findByText('Staff account created.');expect(writes[0].body).toMatchObject({assignments:[{branch:'b1',role:'reception'},{branch:'b1',role:'nurse'}]});
});
it('retries failed branch choices without inventing a selected branch',async()=>{
 let fail=true;serve(url=>url.includes('/staff/branches/')&&new URL(url,'https://test.invalid').searchParams.get('limit')==='25'&&fail?Response.json({message:'Branch choices unavailable.'},{status:503}):undefined);render(<Administration user={user}/>);const dialog=await openCreate();expect(await dialog.findByRole('alert')).toHaveTextContent('Branch choices unavailable.');expect(dialog.getByRole('combobox',{name:'Branch 1'})).toBeDisabled();fail=false;await userEvent.click(dialog.getByRole('button',{name:'Try again'}));await dialog.findByRole('option',{name:'Branch 1 (B1)'});expect(dialog.getByRole('combobox',{name:'Branch 1'})).toHaveValue('');
});
it('keeps a selected branch name visible when paging assignment choices',async()=>{
 serve();render(<Administration user={user}/>);const dialog=await fillCreate();await userEvent.click(dialog.getByRole('button',{name:'Next branches 1'}));await dialog.findByRole('option',{name:'Branch 26 (B26)'});expect(dialog.getByRole('combobox',{name:'Branch 1'})).toHaveDisplayValue('Branch 1 (B1)');
});
