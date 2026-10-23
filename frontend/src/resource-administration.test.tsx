import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { Administration } from './pages';
import type { User } from './types';

const user:User={id:1,username:'synthetic',name:'Synthetic Admin',roles:['master_admin'],branches:[{id:'b1',name:'Main',code:'MAIN'}],permissions:['platform.read','platform.configure']};
const summary={organisation:{id:'org-1',name:'Synthetic Hospital'},branches_count:1,staff_count:2,active_staff_count:2,security:{ip_mode:'standard'},modules:[]};
const branches=Array.from({length:126},(_,i)=>({id:`b${i+1}`,name:`Branch ${i+1}`,code:`B${i+1}`}));
const bed={id:'bed-1',branch:'b1',number:'101',room_number:'A',category:'general',status:'available',version:7};
afterEach(()=>vi.unstubAllGlobals());
function serve(handler?:(url:string,options:RequestInit)=>Response|undefined){
 const writes:{url:string;body:unknown;method:string}[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string,options:RequestInit)=>{
  if(options.method)writes.push({url,body:JSON.parse(String(options.body)),method:options.method});
  const response=handler?.(url,options);if(response)return response;
  if(url.endsWith('platform/summary/'))return Response.json(summary);
  const offset=Number(new URL(url,'https://test.invalid').searchParams.get('offset')||0);
  return Response.json(url.includes('/branches/')?{count:126,results:branches.slice(offset,offset+25)}:{count:1,results:[bed]});
 }));return writes;
}
it('hides configuration controls and makes no configuration reads without the explicit permission',async()=>{
 const paths:string[]=[];serve(url=>{paths.push(url);return undefined;});
 render(<Administration user={{...user,permissions:['platform.read']}}/>);
 await screen.findByText('Synthetic Hospital');expect(screen.queryByRole('button',{name:'Add branch'})).not.toBeInTheDocument();
 expect(paths.some(path=>path.includes('/organisations/'))).toBe(false);
});
it('creates a scoped branch and refreshes the organisation overview',async()=>{
 let reads=0;const writes=serve((url,options)=>{if(url.endsWith('platform/summary/')){reads++;return Response.json(summary);}if(options.method==='POST')return Response.json(branches[0],{status:201});});
 render(<Administration user={user}/>);await userEvent.click(await screen.findByRole('button',{name:'Add branch'}));
 expect(screen.getByText(/New branches need staff access assignments/)).toBeInTheDocument();
 await userEvent.type(screen.getByRole('textbox',{name:'Branch name'}),'New Wing');await userEvent.type(screen.getByRole('textbox',{name:'Branch code'}),'NW');
 await userEvent.click(screen.getByRole('button',{name:'Save branch'}));await screen.findByText('Branch added.');
 expect(writes).toEqual([{url:'/api/v1/platform/organisations/org-1/branches/',method:'POST',body:{name:'New Wing',code:'NW'}}]);await waitFor(()=>expect(reads).toBeGreaterThan(1));
});
it('allows bed creation at a branch after the first hundred choices',async()=>{
 const writes=serve((_url,options)=>options.method==='POST'?Response.json(bed,{status:201}):undefined);
 render(<Administration user={user}/>);await userEvent.click(await screen.findByRole('button',{name:'Add bed'}));const dialog=within(screen.getByRole('dialog'));
 for(let i=0;i<4;i++)await userEvent.click(await dialog.findByRole('button',{name:'Next branches'}));
 await userEvent.selectOptions(await dialog.findByRole('combobox',{name:'Branch'}),'b101');
 await userEvent.type(dialog.getByRole('textbox',{name:'Bed number'}),'201');await userEvent.type(dialog.getByRole('textbox',{name:'Room number'}),'R2');
 expect(dialog.queryByRole('option',{name:'Occupied'})).not.toBeInTheDocument();expect(dialog.queryByRole('option',{name:'Reserved'})).not.toBeInTheDocument();
 await userEvent.click(dialog.getByRole('button',{name:'Save bed'}));await screen.findByText('Bed added.');
 expect(writes[0]).toEqual({url:'/api/v1/platform/organisations/org-1/beds/',method:'POST',body:{branch:'b101',number:'201',room_number:'R2',category:'general',status:'available'}});
});
it('retains a stale bed edit and sends the expected version without branch reassignment',async()=>{
 const writes=serve((_url,options)=>options.method==='PATCH'?Response.json({message:'Bed changed. Reload before saving.',field_errors:{number:['Review bed number.']}},{status:409}):undefined);
 render(<Administration user={user}/>);
 const inventory=within((await screen.findByRole('heading',{name:'Bed inventory'})).closest('section')!);
 await userEvent.click(await inventory.findByRole('button',{name:'Edit bed 101'}));
 const input=screen.getByRole('textbox',{name:'Bed number'});await userEvent.clear(input);await userEvent.type(input,'102');
 await userEvent.click(screen.getByRole('button',{name:'Save bed'}));expect(await screen.findByRole('alert')).toHaveTextContent(/reload/i);expect(input).toHaveValue('102');expect(screen.getByText('Review bed number.')).toBeInTheDocument();
 expect(writes[0]).toEqual({url:'/api/v1/platform/organisations/org-1/beds/bed-1/',method:'PATCH',body:{expected_version:7,number:'102',room_number:'A',category:'general',status:'available'}});
});
it.each(['occupied','reserved'])('does not offer editing for %s beds',async(status)=>{
 serve(url=>url.includes('/beds/')?Response.json({count:1,results:[{...bed,status}]}):undefined);render(<Administration user={user}/>);
 await screen.findByRole('heading',{name:'Bed inventory'});expect(screen.queryByRole('button',{name:'Edit bed 101'})).not.toBeInTheDocument();expect(await screen.findByText(/Allocation must be resolved/)).toBeInTheDocument();
});
it('keeps branch fields and reports forbidden writes clearly',async()=>{
 serve((_url,options)=>options.method==='POST'?Response.json({message:'Configuration permission was removed.'},{status:403}):undefined);render(<Administration user={user}/>);
 await userEvent.click(await screen.findByRole('button',{name:'Add branch'}));await userEvent.type(screen.getByRole('textbox',{name:'Branch name'}),'Wing');await userEvent.type(screen.getByRole('textbox',{name:'Branch code'}),'W');await userEvent.click(screen.getByRole('button',{name:'Save branch'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Configuration permission was removed.');expect(screen.getByRole('textbox',{name:'Branch name'})).toHaveValue('Wing');
});
it('retries a failed inventory read and presents the empty state',async()=>{
 let failed=true;serve(url=>url.includes('/beds/')?(failed?Response.json({message:'Inventory temporarily unavailable.'},{status:503}):Response.json({count:0,results:[]})):undefined);
 render(<Administration user={user}/>);expect(await screen.findByRole('alert')).toHaveTextContent('Inventory temporarily unavailable.');failed=false;
 await userEvent.click(screen.getByRole('button',{name:'Try again'}));expect(await screen.findByText('No beds configured')).toBeInTheDocument();
});
it('paginates branch inventory and refreshes a successful bed edit',async()=>{
 let updated=false;const writes=serve((url,options)=>{if(options.method==='PATCH'){updated=true;return Response.json({...bed,number:'102',version:8});}if(url.includes('/beds/'))return Response.json({count:1,results:[updated?{...bed,number:'102',version:8}:bed]});return undefined;});
 render(<Administration user={user}/>);const section=await screen.findByRole('heading',{name:'Branches'});const region=within(section.closest('section')!);
 await region.findByText('Branch 1');await userEvent.click(region.getByRole('button',{name:'Next'}));expect(await region.findByText('Branch 26')).toBeInTheDocument();
 await userEvent.click(await screen.findByRole('button',{name:'Edit bed 101'}));const input=screen.getByRole('textbox',{name:'Bed number'});await userEvent.clear(input);await userEvent.type(input,'102');await userEvent.click(screen.getByRole('button',{name:'Save bed'}));
 expect(await screen.findByRole('button',{name:'Edit bed 102'})).toBeInTheDocument();expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(writes).toHaveLength(1);
});
it('filters bed inventory by the named branch and resets the bed page when switching',async()=>{
 const paths:string[]=[];serve(url=>{paths.push(url);if(url.includes('/beds/'))return Response.json({count:60,results:[bed]});return undefined;});
 render(<Administration user={user}/>);const inventory=within((await screen.findByRole('heading',{name:'Bed inventory'})).closest('section')!);
 await inventory.findByRole('button',{name:'Edit bed 101'});expect(paths.some(path=>path.includes('/beds/?')&&path.includes('branch=b1'))).toBe(true);
 await userEvent.click(inventory.getByRole('button',{name:'Next'}));await waitFor(()=>expect(paths.some(path=>path.includes('/beds/?')&&path.includes('offset=25'))).toBe(true));
 await userEvent.selectOptions(screen.getByRole('combobox',{name:'Bed inventory branch'}),'b2');
 await waitFor(()=>expect(paths.some(path=>path.includes('/beds/?')&&path.includes('branch=b2')&&path.includes('offset=0'))).toBe(true));
 expect(inventory.getByRole('combobox',{name:'Bed inventory branch'})).toHaveDisplayValue('Branch 2 (B2)');
});
