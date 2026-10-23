from datetime import timedelta
from uuid import uuid4
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from apps.core.models import Organisation, Branch, Membership, AuditEvent, IdentitySecurity

pytestmark = pytest.mark.django_db
SELF = '/api/v1/auth/security/activity/'

@pytest.fixture
def history():
    org = Organisation.objects.create(name='Synthetic history')
    branch = Branch.objects.create(organisation=org, name='Main', code='MAIN')
    other = Branch.objects.create(organisation=Organisation.objects.create(name='Foreign'), name='Foreign', code='F')
    actor = get_user_model().objects.create_user(username='audit-admin')
    target = get_user_model().objects.create_user(username='audit-target')
    Membership.objects.create(user=actor, branch=branch, role='master_admin')
    Membership.objects.create(user=target, branch=branch, role='reception')
    client = APIClient(); client.force_login(actor)
    return client, actor, target, org, branch, other, f'/api/v1/platform/organisations/{org.pk}/audit-events/'

def event(actor, branch, action='bed.changed', **kwargs):
    return AuditEvent.objects.create(actor=actor, branch=branch, action=action, object_id=str(uuid4()), **kwargs)

def test_scoped_history_and_no_get_writes(history):
    c,a,t,o,b,f,url=history
    wanted=event(a,b)
    for branch,action in [(f,'bed.changed'),(None,'bed.changed'),(b,'patient.created'),(b,'unknown')]: event(a,branch,action)
    count=AuditEvent.objects.count()
    response=c.get(url)
    assert response.status_code==200
    page=response.json(); assert page['count']==1 and page['results'][0]['id']==str(wanted.pk)
    assert set(page)=={'count','results','window'} and 'details' not in page['results'][0]
    assert c.get(url+str(wanted.pk)+'/').status_code==200
    assert AuditEvent.objects.count()==count and not IdentitySecurity.objects.exists()

def test_self_activity_is_caller_only_branchless_and_membership_independent(history):
    c,a,t,o,b,f,url=history
    wanted=event(a,None,'security.step_up',details={'method':'backup_code','secret':'hidden'})
    event(t,None,'security.step_up'); event(a,b,'security.step_up'); event(a,None,'security.unknown')
    Membership.objects.filter(user=a).update(is_active=False)
    response=c.get(SELF); assert response.status_code==200
    assert response.json()['count']==1 and response.json()['results'][0]['id']==str(wanted.pk)
    assert response.json()['results'][0]['method']=='backup_code'
    assert c.get(url).status_code==403

@pytest.mark.parametrize('query',['?actor=1','?branch=bad','?limit=0','?offset=-1','?offset=10001','?limit=1&limit=2','?action=patient.created','?before=2026-01-01','?before=0001-01-01T00:00:00Z','?after=0001-01-01T00:00:00%2B23:59','?after=2026-01-01T00:00:00Z&before=2026-05-01T00:00:00Z'])
def test_strict_queries_are_400(history,query):
    assert history[0].get(history[-1]+query).status_code==400

def test_malformed_route_and_concealed_detail(history):
    c,a,t,o,b,f,url=history
    assert c.get(url.replace(str(o.pk),'bad')).status_code==400
    assert c.get(url+'bad/').status_code==400
    for row in [event(a,f),event(a,b,'patient.created'),event(a,None)]:
        assert c.get(url+str(row.pk)+'/').status_code==404
    row=event(a,b)
    assert c.get(url+str(row.pk)+'/?limit=1').status_code==400
    assert c.get(url,{'branch':str(f.pk)}).status_code==404

def test_read_permission_and_mfa(history,settings):
    c,a,t,o,b,f,url=history
    assert 'platform.audit.read' in c.get('/api/v1/auth/me/').json()['permissions']
    settings.HMS_REQUIRE_ADMIN_MFA=True
    denied=c.get(url); assert denied.status_code==403 and denied.json()['code']=='mfa_enrollment_required'
    assert not IdentitySecurity.objects.exists()
    settings.HMS_REQUIRE_ADMIN_MFA=False
    Membership.objects.filter(user=a).update(role='doctor')
    assert c.get(url).status_code==403

def test_staff_projection_redacts_foreign_unknown_and_bounds(history):
    c,a,t,o,b,f,url=history
    assignments=[{'branch':str(b.pk),'role':'reception','secret':'hidden'},{'branch':str(f.pk),'role':'doctor'}]
    row=event(a,b,'staff.changed',details={'target_user_id':t.pk,'organisation_id':str(o.pk),'password':'hidden','before':{'status':'active','version':True},'after':{'version':2**64,'assignments':assignments*501}})
    data=c.get(url+str(row.pk)+'/').json()
    assert data['target']=={'id':t.pk,'username':t.username}
    assert data['details']['before']=={'status':'active'}
    assert 'version' not in data['details']['after']
    assert len(data['details']['after']['assignments'])==500 and data['details_truncated'] is True
    assert set(data['branch_labels'])=={str(b.pk)} and 'hidden' not in str(data)
    Membership.objects.filter(user=t).delete()
    assert c.get(url+str(row.pk)+'/').json()['target'] is None

def test_bed_branch_and_malformed_scalar_projection(history):
    c,a,t,o,b,f,url=history
    row=event(a,b,details={'before':{'number':'<script>','room_number':'x'*33,'category':'invalid','status':'active','version':True},'after':{'number':'102','status':'available','version':1,'name':'wrong-action'}})
    data=c.get(url+str(row.pk)+'/').json()
    assert data['details']=={'before':{'number':'<script>'},'after':{'number':'102','status':'available','version':1}}
    row.details=['bad']; row.object_id='not-a-uuid'; row.save()
    data=c.get(url+str(row.pk)+'/').json(); assert data['details']=={} and data['object_id']==''

def test_paging_filters_counts_and_pinned_window_beyond_100(history):
    c,a,t,o,b,f,url=history
    rows=[event(a,b) for _ in range(125)]
    now=timezone.now(); same=now-timedelta(minutes=1)
    AuditEvent.objects.filter(pk__in=[r.pk for r in rows]).update(created_at=same)
    first=c.get(url,{'limit':1000}).json(); assert len(first['results'])==100 and first['count']==125
    second=c.get(url,{'limit':100,'offset':100,**first['window']}).json()
    assert second['count']==125 and len(second['results'])==25
    ids=[r['id'] for r in first['results']+second['results']]
    assert ids==sorted(ids,reverse=True) and len(set(ids))==125
    assert c.get(url,{'action':'branch.created'}).json()['count']==0
    exact=c.get(url,{'after':same.isoformat(),'before':now.isoformat()}).json(); assert exact['count']==125
    assert c.get(url,{'before':same.isoformat()}).json()['count']==0

def test_postgres_audit_indexes_and_query_explain(history):
    from django.db import connection
    if connection.vendor!='postgresql': pytest.skip('Actual PostgreSQL index/explain evidence only.')
    c,a,t,o,b,f,url=history
    event(a,b)
    with connection.cursor() as cursor:
        indexes=connection.introspection.get_constraints(cursor,AuditEvent._meta.db_table)
    assert {'audit_branch_time_id','audit_actor_time_id'} <= set(indexes)
    plan=AuditEvent.objects.filter(branch=b,action='bed.changed').order_by('-created_at','-id').explain()
    assert 'core_auditevent' in plan

@pytest.mark.parametrize('bad',[{},[],True,1,None,'x'*200])
def test_hostile_stored_scalars_never_crash_or_escape(history,bad):
    c,a,t,o,b,f,url=history
    row=event(a,b,details={'before':{'number':bad,'category':bad,'status':bad,'version':bad},'after':bad})
    response=c.get(url+str(row.pk)+'/'); assert response.status_code==200
    assert response.json()['details']['before']==({'version':1} if bad is not True and type(bad) is int else {})

@pytest.mark.parametrize('query',['?branch=1','?actor=1','?action=bed.changed','?action=security.password&action=security.password','?offset=1.2'])
def test_self_rejects_overrides_and_invalid_queries(history,query):
    assert history[0].get(SELF+query).status_code==400

def test_mfa_freshness_full_identity_and_stale_epoch(history,settings):
    c,a,t,o,b,f,url=history
    state=IdentitySecurity.objects.create(user=a,active_ciphertext='synthetic-enabled')
    settings.HMS_REQUIRE_ADMIN_MFA=True
    assert c.get(url).json()['code']=='mfa_step_up_required'
    session=c.session; session['factor_verified_at']=timezone.now().timestamp(); session.save()
    assert c.get(url).status_code==200
    assert c.get(SELF).status_code==200
    state.auth_epoch=1; state.save()
    assert c.get(url).status_code in (401,403) and c.get(SELF).status_code in (401,403)
    assert APIClient().get(SELF).status_code in (401,403)

def test_projection_target_and_references_are_validated(history):
    c,a,t,o,b,f,url=history
    row=event(a,b,'staff.changed',details={'target_user_id':True,'organisation_id':str(f.organisation_id),'before':{'status':'active','version':2**63},'after':{'assignments':[{'branch':str(b.pk),'role':[]}]}})
    data=c.get(url+str(row.pk)+'/').json()
    assert data['target'] is None and data['object_id']==''
    assert data['details']=={'before':{'status':'active'},'after':{'assignments':[]}}
    row.object_id=str(t.pk); row.actor=None; row.save()
    assert c.get(url+str(row.pk)+'/').json()['actor'] is None

def test_future_window_clips_and_large_branch_labels_stay_bounded(history):
    from apps.core.audit_history import summary
    c,a,t,o,b,f,url=history
    now=timezone.now()
    data=c.get(url,{'before':(now+timedelta(days=30)).isoformat()}).json()
    assert timezone.datetime.fromisoformat(data['window']['before'])<now+timedelta(seconds=5)
    row=event(a,b,'branch.created',details={'after':{'name':'x'*161,'code':'x'*33,'number':'wrong'}})
    data=c.get(url+str(row.pk)+'/').json()
    assert data['details']=={'after':{}}
    # Corrupt in-memory labels exercise projection bounds without bypassing
    # PostgreSQL's varchar constraints merely to construct a test fixture.
    b.name='x'*161; a.username='x'*151
    row.branch=b; row.actor=a
    projected=summary(row)
    assert projected['branch'] is None and projected['actor'] is None

def test_exact_action_allowlists_and_read_only_methods(history):
    c,a,t,o,b,f,url=history
    admin=['branch.created','bed.created','bed.changed','staff.created','staff.changed']
    own=['security.'+s for s in ['enrolled','enrollment_started','login_verified','step_up','password','rotate','revoke','disable']]
    for action in admin: event(a,b,action)
    for action in own: event(a,None,action,details={'method':{'invalid':'object'},'password':'hidden'})
    assert {r['action'] for r in c.get(url).json()['results']}==set(admin)
    rows=c.get(SELF).json()['results']
    assert {r['action'] for r in rows}==set(own) and all(r['method'] is None for r in rows)
    count=AuditEvent.objects.count()
    for path in [url,SELF]:
        assert c.post(path,{},format='json').status_code==405
        assert c.get(path)['Cache-Control']=='no-store'
    assert AuditEvent.objects.count()==count

def test_partial_mfa_session_cannot_read_security_activity(history,settings):
    from cryptography.fernet import Fernet
    from apps.core.identity_security import encrypt
    settings.HMS_MFA_ENCRYPTION_KEYS=Fernet.generate_key().decode()
    c,a,t,o,b,f,url=history
    a.set_password('Synthetic-audit-identity-72!'); a.save()
    device=uuid4()
    IdentitySecurity.objects.create(user=a,device_id=device,active_ciphertext=encrypt('SYNTHETIC',a.pk,device,'active'))
    partial=APIClient()
    response=partial.post('/api/v1/auth/login/',{'username':a.username,'password':'Synthetic-audit-identity-72!'},format='json')
    assert response.status_code==202
    assert partial.get(SELF).status_code in (401,403)

@pytest.mark.parametrize('offset',['+01:60','+24:00','+99:00','-00:60'])
def test_invalid_iso_offsets_are_rejected(history,offset):
    assert history[0].get(history[-1],{'before':'2026-10-23T12:00:00'+offset}).status_code==400

@pytest.mark.parametrize('value',['2026-W43-5T12:00:00Z','20261023T120000Z','2026-10-23T12Z'])
def test_date_time_uses_rfc3339_calendar_shape(history,value):
    assert history[0].get(history[-1],{'before':value}).status_code==400
