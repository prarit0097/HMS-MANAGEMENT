import json
from uuid import uuid4
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.test import APIClient
from apps.core.models import Organisation, Branch, Membership, AuditEvent, Patient, IdempotencyRecord

pytestmark = pytest.mark.django_db

@pytest.fixture
def staff():
    org = Organisation.objects.create(name='Synthetic staff')
    branch = Branch.objects.create(organisation=org, name='Main', code='MAIN')
    sibling = Branch.objects.create(organisation=org, name='Sibling', code='SIB')
    foreign = Branch.objects.create(organisation=Organisation.objects.create(name='Foreign'), name='Foreign', code='F')
    actor = get_user_model().objects.create_user(username='staff-admin')
    target = get_user_model().objects.create_user(username='staff-target', first_name='Synthetic Person')
    Membership.objects.create(user=actor, branch=branch, role='master_admin')
    Membership.objects.create(user=target, branch=branch, role='reception')
    Membership.objects.create(user=target, branch=foreign, role='doctor')
    client = APIClient(); client.force_login(actor)
    return client, actor, target, org, branch, sibling, foreign, f'/api/v1/platform/organisations/{org.pk}/staff/'

def payload(branch, **changes):
    return {'username': 'new-synthetic', 'name': 'New Synthetic', 'password': 'A9!unrelated-long-pass', 'assignments': [{'branch': str(branch.pk), 'role': 'reception'}], **changes}

def test_list_legacy_version_zero_scoped_no_read_writes(staff):
    c, a, target, org, b, s, f, url = staff
    response = c.get(url+'?q=Synthetic Person')
    assert response.status_code == 200
    assert response.json() == {'count': 1, 'results': [{'id': target.pk, 'username': 'staff-target', 'name': 'Synthetic Person', 'account_active': True, 'status': 'active', 'version': 0, 'assignments': [{'branch': str(b.pk), 'role': 'reception'}]}]}
    from apps.core.models import StaffAccessRevision
    assert StaffAccessRevision.objects.count() == 0 and AuditEvent.objects.count() == 0
    assert 'platform.staff.manage' in c.get('/api/v1/auth/me/').json()['permissions']

def test_create_password_hash_secrecy_and_audit(staff):
    c, a, target, org, b, s, f, url = staff
    response = c.post(url, payload(s), format='json')
    assert response.status_code == 201
    row = response.json(); user = get_user_model().objects.get(pk=row['id'])
    assert row['version'] == 1 and row['status'] == 'active'
    assert user.check_password('A9!unrelated-long-pass') and not user.is_staff and not user.is_superuser
    assert 'password' not in json.dumps(row)
    event = AuditEvent.objects.get(action='staff.created')
    assert event.actor == a and event.branch == s and event.details['after']['version'] == 1
    assert set(event.details) == {'target_user_id', 'organisation_id', 'before', 'after'}
    assert 'password' not in json.dumps(event.details) and 'New Synthetic' not in json.dumps(event.details)
    assert IdempotencyRecord.objects.count() == 0

@pytest.mark.parametrize('changes', [{'password':'123456789012'}, {'password':'password123456'}, {'password':'short'}, {'password':'x'*129}, {'password':'new-synthetic'}, {'username':'bad space'}, {'name':''}, {'assignments':[]}, {'assignments':[{'branch':'bad','role':'reception'}]}, {'assignments':[{'branch':str(uuid4()),'role':'reception','extra':True}]}, {'is_superuser':True}, {'account_active':False}])
def test_create_invalid_fields_are_400_with_array_errors(staff, changes):
    c, a, t, org, b, s, f, url = staff
    response = c.post(url, payload(b, **changes), format='json')
    assert response.status_code == 400
    assert all(isinstance(v, list) for v in response.json()['field_errors'].values())
    assert get_user_model().objects.count() == 2 and AuditEvent.objects.count() == 0

@pytest.mark.parametrize('body', [[], 'bad', None])
def test_nonobject_requests(staff, body):
    c, a, t, org, b, s, f, url = staff
    assert c.post(url, body, format='json').status_code == 400
    assert c.patch(url+f'{t.pk}/', body, format='json').status_code == 400

def test_username_duplicate_and_foreign_branch_concealed(staff):
    c, a, t, org, b, s, f, url = staff
    assert c.post(url, payload(b, username=t.username), format='json').status_code == 409
    assert c.post(url, payload(f), format='json').status_code == 404
    assert c.get(url.replace(str(org.pk), str(f.organisation_id))).status_code == 404
    stranger = get_user_model().objects.create_user(username='foreign-only')
    Membership.objects.create(user=stranger, branch=f, role='master_admin')
    assert c.patch(url+f'{stranger.pk}/', {'expected_version':0,'status':'suspended'}, format='json').status_code == 404

def test_duplicate_assignments_and_overlong_batch_rejected(staff):
    c, a, t, org, b, s, f, url = staff
    item = {'branch':str(b.pk),'role':'doctor'}
    for assignments in ([item,item], [item]*101):
        assert c.post(url,payload(b,assignments=assignments),format='json').status_code == 400

def test_suspend_revoke_replay_context_and_restore_preserve_other_org(staff):
    c, a, t, org, b, s, f, url = staff
    tc=APIClient();tc.force_login(t)
    key=str(uuid4()); data={'branch':str(b.pk),'full_name':'Synthetic retry'}
    assert tc.post('/api/v1/patients/',data,format='json',HTTP_IDEMPOTENCY_KEY=key).status_code == 201
    assert c.patch(url+f'{t.pk}/',{'expected_version':0,'status':'suspended'},format='json').status_code == 200
    assert tc.post('/api/v1/patients/',data,format='json',HTTP_IDEMPOTENCY_KEY=key).status_code == 403
    assert tc.get(f'/api/v1/patients/?branch={b.pk}').status_code == 403
    assert tc.get('/api/v1/auth/me/').json()['roles'] == ['doctor']
    assert tc.get('/api/v1/branches/').json()['results'][0]['id'] == str(f.pk)
    assert c.get('/api/v1/platform/summary/').json()['active_staff_count'] == 1
    response=c.patch(url+f'{t.pk}/',{'expected_version':1,'status':'active','assignments':[{'branch':str(s.pk),'role':'nurse'}]},format='json')
    assert response.status_code == 200 and response.json()['version'] == 2
    assert not Membership.objects.filter(user=t,branch=b).exists()
    assert Membership.objects.get(user=t,branch=f).role == 'doctor'
    assert tc.get('/api/v1/patients/').status_code == 200
    assert c.patch(url+f'{t.pk}/',{'expected_version':1,'status':'suspended'},format='json').status_code == 409

@pytest.mark.parametrize('changes',[{'username':'forged'},{'name':'forged'},{'password':'forged'},{'is_active':False},{'expected_version':True},{'expected_version':1.5},{'expected_version':-1},{}])
def test_patch_readonly_invalid_and_empty_edit(staff,changes):
    c,a,t,org,b,s,f,url=staff
    assert c.patch(url+f'{t.pk}/',{'expected_version':0, **({'status':'active'} if changes else {}), **changes},format='json').status_code == 400
    assert AuditEvent.objects.count() == 0

def test_self_edit_nonmaster_and_suspended_config_denied(staff):
    c,a,t,org,b,s,f,url=staff
    assert c.patch(url+f'{a.pk}/',{'expected_version':0,'status':'active'},format='json').status_code == 403
    Membership.objects.filter(user=a).update(role='reception')
    assert c.get(url).status_code == 403
    Membership.objects.filter(user=a).update(role='master_admin',is_active=False)
    assert c.get('/api/v1/platform/summary/').status_code == 403
    assert c.get(url.replace('staff/','branches/')).status_code == 403
    assert c.get('/api/v1/auth/me/').json()['permissions'] == []

@pytest.mark.parametrize('operation',['create','patch'])
def test_audit_failure_rolls_back_staff_everything(staff,monkeypatch,operation):
    c,a,t,org,b,s,f,url=staff
    def fail(*args,**kwargs):raise IntegrityError('synthetic audit failure')
    monkeypatch.setattr(AuditEvent.objects,'create',fail)
    with pytest.raises(IntegrityError):
        if operation=='create':c.post(url,payload(b),format='json')
        else:c.patch(url+f'{t.pk}/',{'expected_version':0,'status':'suspended'},format='json')
    from apps.core.models import StaffAccessRevision
    assert get_user_model().objects.count()==2 and StaffAccessRevision.objects.count()==0
    assert Membership.objects.get(user=t,branch=b).is_active

def test_search_paging_and_csrf(staff):
    c,a,t,org,b,s,f,url=staff
    for query in ['q='+'x'*201,'offset=-1','limit=bad']:
        assert c.get(url+'?'+query).status_code == 400
    assert len(c.get(url+'?limit=1').json()['results']) == 1
    assert c.get(url+'?limit=1&offset=1').json()['count'] == 2
    csrf=APIClient(enforce_csrf_checks=True);csrf.force_login(a)
    assert csrf.post(url,payload(b),format='json').status_code == 403

def test_inactive_direct_business_actor_has_no_ceiling(staff):
    c,a,t,org,b,s,f,url=staff
    from apps.core.authorization import branch_ids,current_user
    t.is_active=False;t.save()
    assert branch_ids(t,'patients.write') == set()
    assert current_user(t)['permissions'] == []

def test_staff_only_branch_picker_is_scoped_without_config_permission(staff,monkeypatch):
    c,a,t,org,b,s,f,url=staff
    from apps.core.authorization import ROLE_PERMISSIONS
    monkeypatch.setitem(ROLE_PERMISSIONS,'master_admin',{'platform.staff.manage'})
    response=c.get(url+'branches/?limit=1&offset=1')
    assert response.status_code == 200 and response.json()['count']==2
    assert set(response.json()['results'][0]) == {'id','name','code'}
    assert c.get(url.replace('staff/','branches/')).status_code == 403

def test_global_disabled_target_org_status_independent(staff):
    c,a,t,org,b,s,f,url=staff
    t.is_active=False;t.save()
    row=c.get(url+'?q=staff-target').json()['results'][0]
    assert row['status']=='active' and row['account_active'] is False
    assert c.patch(url+f'{t.pk}/',{'expected_version':0,'status':'active'},format='json').status_code==200
    t.refresh_from_db();assert t.is_active is False

def test_malformed_org_uuid_safe_400(staff):
    c,a,t,org,b,s,f,url=staff
    assert c.get(url.replace(str(org.pk),'bad')).status_code==400

def test_staff_picker_and_inventory_reach_after_hundred(staff):
    c,a,t,org,b,s,f,url=staff
    Branch.objects.bulk_create([Branch(organisation=org,name=f'Extra {i:03}',code=f'E{i}') for i in range(110)])
    users=get_user_model().objects.bulk_create([get_user_model()(username=f'synthetic-extra-{i:03}') for i in range(110)])
    Membership.objects.bulk_create([Membership(user=user,branch=b,role='nurse') for user in users])
    assert c.get(url+'branches/?limit=100&offset=100').json()['count']==112
    assert len(c.get(url+'branches/?limit=100&offset=100').json()['results'])==12
    assert len(c.get(url+'?limit=100&offset=100').json()['results'])==12

def test_search_matches_legacy_full_display_name(staff):
    c,a,t,org,b,s,f,url=staff
    t.first_name='Synthetic';t.last_name='Legacy';t.save()
    response=c.get(url+'?q=Synthetic Legacy')
    assert response.status_code==200 and response.json()['count']==1
