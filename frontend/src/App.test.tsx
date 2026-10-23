import { render, screen, waitFor } from '@testing-library/react';
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
