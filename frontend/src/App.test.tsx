import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
const currentUser = {id:1,username:'synthetic',name:'Test Reception',roles:['reception'],branches:[{id:'b1',name:'Faridabad',code:'FBD'}],permissions:['dashboard.read','patients.read','patients.write','appointments.read','appointments.write','beds.read','admissions.write']};
afterEach(() => {vi.unstubAllGlobals(); window.location.hash='';});
function server(handler?: (url:string, options?: RequestInit)=>Response) {
  vi.stubGlobal('fetch', vi.fn(async (url: string, options?:RequestInit) => {
    if (handler) { const result = handler(url, options); if (result.status !== 599) return result; }
    if (url.endsWith('auth/csrf/')) return Response.json({detail:'CSRF cookie set'});
    if (url.endsWith('auth/me/')) return Response.json(currentUser);
    if (url.includes('dashboard/')) return Response.json({patients_total:12,opd_today:3,active_admissions:2,available_beds:8,appointments_today:5,therapy_pending:null});
    return Response.json({count:0,results:[]});
  }));
}
it('shows a real empty patient list and opens a labelled registration form by keyboard', async () => {
  server(); render(<App/>);
  await userEvent.click(await screen.findByRole('link',{name:'Patients'}));
  expect(await screen.findByText('No patients found')).toBeInTheDocument();
  const register = screen.getByRole('button',{name:'Register patient'}); register.focus();
  await userEvent.keyboard('{Enter}');
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  expect(screen.getByRole('textbox',{name:'Full name'})).toHaveFocus();
  await userEvent.keyboard('{Escape}');
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
it('submits registration to the API and keeps a rejected form open with field feedback', async () => {
  server((url, options) => url.endsWith('patients/') && options?.method === 'POST' ? Response.json({code:'validation_error',message:'Check the highlighted details',field_errors:{full_name:['Enter the full name']}},{status:400}) : new Response(null,{status:599}));
  render(<App/>); await userEvent.click(await screen.findByRole('link',{name:'Patients'}));
  await userEvent.click(await screen.findByRole('button',{name:'Register patient'}));
  await userEvent.type(screen.getByRole('textbox',{name:'Full name'}),'Synthetic Patient');
  await userEvent.click(screen.getByRole('button',{name:'Save patient'}));
  expect(await screen.findByText('Enter the full name')).toBeInTheDocument();
  expect(screen.getByRole('textbox',{name:'Full name'})).toHaveValue('Synthetic Patient');
});
it('does not offer operational charts to a platform-only administrator', async () => {
  server(url => url.endsWith('auth/me/') ? Response.json({...currentUser,roles:['master_admin'],permissions:['platform.read']}) : url.endsWith('platform/summary/') ? Response.json({organisation:{id:'o1',name:'Test hospital'},branches_count:1,staff_count:3,active_staff_count:2,security:{ip_mode:'standard'},modules:[]}) : new Response(null,{status:599}));
  render(<App/>);
  expect(await screen.findByRole('heading',{name:'Master administration'})).toBeInTheDocument();
  expect(screen.queryByRole('link',{name:'Patients'})).not.toBeInTheDocument();
});
it('shows login after an anonymous session and reports invalid credentials without losing username', async () => {
  server(url => url.endsWith('auth/me/') ? Response.json({code:'unauthenticated',message:'Sign in required'},{status:401}) : url.endsWith('auth/login/') ? Response.json({code:'invalid_credentials',message:'Username or password is incorrect'},{status:401}) : new Response(null,{status:599}));
  render(<App/>);
  await userEvent.type(await screen.findByRole('textbox',{name:'Username'}),'test.user');
  await userEvent.type(screen.getByLabelText('Password'),'wrong-password');
  await userEvent.click(screen.getByRole('button',{name:'Sign in'}));
  await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('Username or password is incorrect'));
  expect(screen.getByRole('textbox',{name:'Username'})).toHaveValue('test.user');
});
it('admits into an available bed beyond the first 100 records through paginated choices', async () => {
  let admission: Record<string,string> | undefined;
  const beds = Array.from({length:126}, (_,index)=>({id:`bed-${index+1}`,number:String(index+1),room_number:'A',category:'general',status:index>=100?'available':'occupied',patient_name:null,admission_id:null,branch:'b1'}));
  server((url,options)=>{
    if(url.includes('beds/?')) {
      const params=new URL(url,'http://localhost').searchParams;
      const offset=Number(params.get('offset')||0),limit=Number(params.get('limit')||25);
      const matches=params.get('status')?beds.filter(bed=>bed.status===params.get('status')):beds;
      return Response.json({count:matches.length,results:matches.slice(offset,offset+limit)});
    }
    if(url.includes('patients/?'))return Response.json({count:1,results:[{id:'patient-1',full_name:'Synthetic Admission',uhid:'TEST-1',phone:'',branch:'b1'}]});
    if(url.endsWith('admissions/')&&options?.method==='POST') {admission=JSON.parse(String(options.body));return Response.json({id:'admission-1'},{status:201});}
    return new Response(null,{status:599});
  });
  render(<App/>);
  await userEvent.click(await screen.findByRole('link',{name:'Bed board'}));
  await userEvent.click(screen.getByRole('button',{name:'New admission'}));
  const dialog=within(screen.getByRole('dialog'));
  await userEvent.click(await dialog.findByRole('button',{name:/Synthetic Admission/}));
  for(let page=0;page<1;page++){
    const navigation=within(dialog.getByRole('navigation',{name:'Bed choices'}));
    await waitFor(()=>expect(navigation.getByRole('button',{name:'Next beds'})).toBeEnabled());
    await userEvent.click(navigation.getByRole('button',{name:'Next beds'}));
  }
  await dialog.findByRole('option',{name:'Bed 126 · Room A · General'});
  await userEvent.selectOptions(dialog.getByRole('combobox',{name:/Available bed/}),'bed-126');
  await userEvent.click(dialog.getByRole('button',{name:'Previous beds'}));
  expect(dialog.getByRole('combobox',{name:/Available bed/})).toHaveValue('');
  await waitFor(()=>expect(dialog.getByRole('button',{name:'Next beds'})).toBeEnabled());
  await userEvent.click(dialog.getByRole('button',{name:'Next beds'}));
  await dialog.findByRole('option',{name:'Bed 126 · Room A · General'});
  expect(dialog.getByRole('combobox',{name:/Available bed/})).toHaveValue('');
  await userEvent.selectOptions(dialog.getByRole('combobox',{name:/Available bed/}),'bed-126');
  await userEvent.type(dialog.getByRole('textbox',{name:/Treating doctor/}),'Dr Synthetic');
  await userEvent.click(dialog.getByRole('button',{name:'Admit patient'}));
  await screen.findByText('Patient admitted and bed allocated.');
  expect(admission).toMatchObject({patient:'patient-1',bed:'bed-126',treating_doctor:'Dr Synthetic'});
});
it('lets staff retry failed admission bed choices without silently accepting a bed', async()=>{
  let fail=true;
  server(url=>url.includes('beds/?') ? (fail?Response.json({message:'Bed records are temporarily unavailable.'},{status:503}):Response.json({count:1,results:[{id:'bed-1',number:'1',room_number:'A',category:'general',status:'available',branch:'b1'}]})):new Response(null,{status:599}));
  render(<App/>);
  await userEvent.click(await screen.findByRole('link',{name:'Bed board'}));
  await userEvent.click(screen.getByRole('button',{name:'New admission'}));
  const dialog=within(screen.getByRole('dialog'));
  expect(await dialog.findByRole('alert')).toHaveTextContent('Bed records are temporarily unavailable.');
  expect(dialog.getByRole('combobox',{name:/Available bed/})).toBeDisabled();
  fail=false;
  await userEvent.click(dialog.getByRole('button',{name:'Try again'}));
  await dialog.findByRole('option',{name:'Bed 1 · Room A · General'});
  expect(dialog.getByRole('combobox',{name:/Available bed/})).toBeEnabled();
  expect(dialog.getByRole('combobox',{name:/Available bed/})).toHaveValue('');
});
it('clearly labels the unauthenticated deployed app as an initial preview for synthetic data', async()=>{
  server(url=>url.endsWith('auth/me/')?Response.json({message:'Sign in required'},{status:401}):new Response(null,{status:599}));
  render(<App/>);
  expect(await screen.findByText('INITIAL PREVIEW')).toBeInTheDocument();
  expect(screen.getByText(/Synthetic data only/)).toHaveTextContent('Not ready for real patient use');
});
it('uses selected branch permissions for doctor A and reception B while keeping union administration access',async()=>{
  const doctorPermissions=['dashboard.read','patients.read','appointments.read','beds.read'];
  server(url=>url.endsWith('auth/me/')?Response.json({...currentUser,roles:['doctor','reception','master_admin'],branches:[{id:'b1',name:'Doctor branch',code:'A'},{id:'b2',name:'Reception branch',code:'B'}],permissions:[...currentUser.permissions,'platform.read'],branch_permissions:{b1:doctorPermissions,b2:currentUser.permissions}}):url.endsWith('platform/summary/')?Response.json({organisation:{id:'o1',name:'Test hospital'},branches_count:2,staff_count:3,active_staff_count:2,security:{ip_mode:'standard'},modules:[]}):new Response(null,{status:599}));
  render(<App/>);
  await userEvent.click(await screen.findByRole('link',{name:'Patients'}));await screen.findByText('No patients found');
  expect(screen.queryByRole('button',{name:'Register patient'})).not.toBeInTheDocument();
  await userEvent.selectOptions(screen.getByRole('combobox',{name:'Branch'}),'b2');
  expect(await screen.findByRole('button',{name:'Register patient'})).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByRole('combobox',{name:'Branch'}),'b1');
  expect(screen.queryByRole('button',{name:'Register patient'})).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('link',{name:'Master administration'}));
  expect(await screen.findByRole('heading',{name:'Master administration'})).toBeInTheDocument();
});
