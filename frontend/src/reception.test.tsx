import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { Patients, Appointments, Beds } from './pages';
import type { User } from './types';
const user:User={id:1,username:'test',name:'Test',roles:['reception'],branches:[{id:'b1',name:'Test',code:'T'}],permissions:['patients.write','appointments.write','admissions.write']};
const patient={id:'p1',uhid:'TEST-1',full_name:'Synthetic Patient',phone:'123',date_of_birth:null,age:30,gender:'female',city:'Test City',branch:'b1',created_at:'2026-10-23T08:00:00Z'};
const appointment={id:'a1',patient:'p1',patient_name:patient.full_name,doctor_name:'Dr Test',scheduled_at:'2026-10-23T10:00:00Z',status:'scheduled',reason:'Review',branch:'b1',version:7};
afterEach(()=>vi.unstubAllGlobals());
function serve(handler:(url:string,options:RequestInit)=>Response){vi.stubGlobal('fetch',vi.fn(async(url:string,options:RequestInit)=>handler(url,options)));}
it('corrects demographics with only editable fields',async()=>{
 let body:unknown;
 serve((url,options)=>{if(options.method==='PATCH'){body=JSON.parse(String(options.body));return Response.json({...patient,full_name:'Corrected Patient'});}return Response.json(url.includes('patients/p1/')?patient:{count:1,results:[patient]});});
 render(<Patients branch="b1" user={user}/>);
 await userEvent.click(await screen.findByRole('button',{name:'View Synthetic Patient'}));
 await userEvent.click(await screen.findByRole('button',{name:'Correct demographics'}));
 const name=screen.getByRole('textbox',{name:'Full name'});await userEvent.clear(name);await userEvent.type(name,'Corrected Patient');
 await userEvent.click(screen.getByRole('button',{name:'Save corrections'}));
 await waitFor(()=>expect(body).toEqual({full_name:'Corrected Patient',phone:'123',date_of_birth:null,age:30,gender:'female',city:'Test City'}));
});
it('reschedules with the displayed version and keeps values after stale conflict',async()=>{
 let body:unknown;
 serve((_url,options)=>{if(options.method==='PATCH'){body=JSON.parse(String(options.body));return Response.json({message:'Stale appointment'},{status:409});}return Response.json({count:1,results:[appointment]});});
 render(<Appointments branch="b1" user={user}/>);
 await userEvent.click(await screen.findByRole('button',{name:'Reschedule'}));
 const doctor=screen.getByRole('textbox',{name:'Doctor name'});await userEvent.clear(doctor);await userEvent.type(doctor,'Dr Next');
 await userEvent.click(screen.getByRole('button',{name:'Save appointment'}));
 expect(await screen.findByRole('alert')).toHaveTextContent(/close.*reload/i);
 expect(doctor).toHaveValue('Dr Next');expect(body).toMatchObject({expected_version:7,doctor_name:'Dr Next',reason:'Review'});
});
it('selects a patient after the first 25 matches without submitting the form',async()=>{
 serve((url)=>{const offset=Number(new URL(url,'http://localhost').searchParams.get('offset')||0);return Response.json(url.includes('patients/')?{count:26,results:offset?[{...patient,id:'p26',full_name:'Patient Twenty Six'}]:Array.from({length:25},(_,i)=>({...patient,id:`p${i}`,full_name:`Patient ${i}`}))}:{count:0,results:[]});});
 render(<Appointments branch="b1" user={user}/>);await userEvent.click(screen.getByRole('button',{name:'Schedule appointment'}));
 const dialog=within(screen.getByRole('dialog'));await userEvent.click(await dialog.findByRole('button',{name:'Next patients'}));
 await userEvent.click(await dialog.findByRole('button',{name:/Patient Twenty Six/}));expect(dialog.getByText('Patient Twenty Six')).toBeInTheDocument();
});
it('requests available beds before pagination and resets bed board page on filtering',async()=>{
 const paths:string[]=[];serve((url)=>{paths.push(url);return Response.json({count:60,results:[{id:'bed1',number:'1',room_number:'A',category:'general',status:'available',branch:'b1'}]});});
 render(<Beds branch="b1" user={user}/>);await screen.findByText('Bed 1');await userEvent.click(screen.getByRole('button',{name:'Next'}));
 await userEvent.click(screen.getByRole('button',{name:'Available'}));await waitFor(()=>expect(paths.some(p=>p.includes('status=available')&&p.includes('offset=0'))).toBe(true));
 await userEvent.click(screen.getByRole('button',{name:'New admission'}));await waitFor(()=>expect(paths.filter(p=>p.includes('status=available')).length).toBeGreaterThan(1));
});
it('retains the create UUID across ambiguous retries and body changes, replacing it for a new form',async()=>{
 const keys:(string|null)[]=[];let succeed=false;
 serve((_url,options)=>{if(options.method==='POST'){keys.push(new Headers(options.headers).get('Idempotency-Key'));if(!succeed)throw new TypeError('connection lost');return Response.json(patient,{status:201});}return Response.json({count:0,results:[]});});
 render(<Patients branch="b1" user={user}/>);await userEvent.click(screen.getByRole('button',{name:'Register patient'}));await userEvent.type(screen.getByRole('textbox',{name:'Full name'}),'Test Patient');
 await userEvent.click(screen.getByRole('button',{name:'Save patient'}));await screen.findByRole('alert');await userEvent.click(screen.getByRole('button',{name:'Save patient'}));await screen.findByRole('alert');
 await userEvent.type(screen.getByRole('textbox',{name:'Full name'}),' Changed');succeed=true;await userEvent.click(screen.getByRole('button',{name:'Save patient'}));await screen.findByText(/registered. UHID/);
 expect(keys[0]).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);expect(keys[1]).toBe(keys[0]);expect(keys[2]).toBe(keys[0]);
 await userEvent.click(screen.getByRole('button',{name:'Register patient'}));await userEvent.type(screen.getByRole('textbox',{name:'Full name'}),'Next Patient');await userEvent.click(screen.getByRole('button',{name:'Save patient'}));await waitFor(()=>expect(keys).toHaveLength(4));expect(keys[3]).not.toBe(keys[0]);
});
it.each(['appointment','admission'])('keeps the %s request key and entered values after a lost response',async(kind)=>{
 const keys:(string|null)[]=[];
 serve((url,options)=>{
  if(options.method==='POST'){keys.push(new Headers(options.headers).get('Idempotency-Key'));throw new TypeError('lost response');}
  if(url.includes('patients/'))return Response.json({count:1,results:[patient]});
  if(url.includes('appointments/'))return Response.json({count:0,results:[]});
  return Response.json({count:1,results:[{id:'bed1',number:'1',room_number:'A',category:'general',status:'available',patient_name:null,admission_id:null,branch:'b1'}]});
 });
 render(kind==='appointment'?<Appointments branch="b1" user={user}/>:<Beds branch="b1" user={user}/>);
 await userEvent.click(screen.getByRole('button',{name:kind==='appointment'?'Schedule appointment':'New admission'}));
 const dialog=within(screen.getByRole('dialog'));await userEvent.click(await dialog.findByRole('button',{name:/Synthetic Patient/}));
 await userEvent.type(dialog.getByRole('textbox',{name:kind==='appointment'?'Doctor name':'Treating doctor'}),'Dr Synthetic');
 if(kind==='appointment')await userEvent.type(dialog.getByLabelText(/Appointment date and time/),'2026-10-24T12:00');
 else await userEvent.selectOptions(await dialog.findByRole('combobox',{name:'Available bed'}),'bed1');
 const submit=dialog.getByRole('button',{name:kind==='appointment'?'Schedule visit':'Admit patient'});
 await userEvent.click(submit);await dialog.findByRole('alert');await userEvent.click(submit);await dialog.findByRole('alert');
 expect(keys).toHaveLength(2);expect(keys[0]).toMatch(/^[0-9a-f-]{36}$/i);expect(keys[1]).toBe(keys[0]);
 expect(dialog.getByRole('textbox',{name:kind==='appointment'?'Doctor name':'Treating doctor'})).toHaveValue('Dr Synthetic');
});
it('explains how to verify a previous create when the key conflicts and preserves the changed form',async()=>{
 serve((_url,options)=>options.method==='POST'?Response.json({message:'Earlier request used different details.'},{status:409}):Response.json({count:0,results:[]}));
 render(<Patients branch="b1" user={user}/>);await userEvent.click(screen.getByRole('button',{name:'Register patient'}));
 await userEvent.type(screen.getByRole('textbox',{name:'Full name'}),'Changed Name');await userEvent.click(screen.getByRole('button',{name:'Save patient'}));
 expect(await screen.findByRole('alert')).toHaveTextContent(/verify whether the earlier save succeeded/);expect(screen.getByRole('textbox',{name:'Full name'})).toHaveValue('Changed Name');
});
it('keeps demographic correction unavailable without the write permission',async()=>{
 serve(url=>Response.json(url.includes('patients/p1/')?patient:{count:1,results:[patient]}));
 render(<Patients branch="b1" user={{...user,permissions:[]}}/>);await userEvent.click(await screen.findByRole('button',{name:'View Synthetic Patient'}));
 await screen.findByRole('heading',{name:'Synthetic Patient'});expect(screen.queryByRole('button',{name:'Correct demographics'})).not.toBeInTheDocument();
});
