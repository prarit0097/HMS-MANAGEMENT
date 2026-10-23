import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
PASSWORD = 'Synthetic-long-identity-72!'

@pytest.fixture(autouse=True)
def fast_hashes(settings):
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

@pytest.fixture
def identity_client():
    user = get_user_model().objects.create_user(username='identity-synthetic', password=PASSWORD)
    client = APIClient(); client.force_login(user)
    return client, user

def test_security_status_has_no_read_side_effects(identity_client):
    client, user = identity_client
    response = client.get('/api/v1/auth/security/')
    assert response.status_code == 200
    assert response.json() == {'enabled': False, 'backup_codes_remaining': 0, 'version': 0, 'session_factor_verified_at': None, 'privileged_mfa_required': False}

def test_begin_enrollment_requires_password_and_dedicated_key(identity_client):
    client, user = identity_client
    response = client.post('/api/v1/auth/security/enrollment/', {'current_password': PASSWORD}, format='json')
    assert response.status_code == 503
    assert response.json()['code'] == 'security_unavailable'

def test_logout_anonymous_is_csrf_protected():
    client = APIClient(enforce_csrf_checks=True)
    assert client.post('/api/v1/auth/logout/').status_code == 403
    client.get('/api/v1/auth/csrf/')
    assert client.post('/api/v1/auth/logout/', HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value).status_code == 204

@pytest.fixture
def keyed(settings):
    from cryptography.fernet import Fernet
    settings.HMS_MFA_ENCRYPTION_KEYS = Fernet.generate_key().decode()

def enroll(client):
    import pyotp
    issued = client.post('/api/v1/auth/security/enrollment/', {'current_password': PASSWORD}, format='json')
    assert issued.status_code == 201
    setup = issued.json()
    result = client.post(f"/api/v1/auth/security/enrollment/{setup['enrollment_id']}/confirm/", {'code': pyotp.TOTP(setup['secret']).now()}, format='json')
    assert result.status_code == 200
    return setup, result.json()['backup_codes']

def test_full_enrollment_login_recovery_replay_and_epoch(identity_client, keyed):
    from apps.core.models import IdentitySecurity, IdentityBackupCode
    client, user = identity_client
    other = APIClient(); other.force_login(user)
    setup, codes = enroll(client)
    security = IdentitySecurity.objects.get(user=user)
    assert setup['secret'] not in security.active_ciphertext
    assert security.auth_epoch == 1 and len(codes) == 10
    assert all(code not in row.password_hash for row in IdentityBackupCode.objects.all() for code in codes)
    assert other.get('/api/v1/auth/me/').status_code in (401,403)
    anon = APIClient()
    pending = anon.post('/api/v1/auth/login/', {'username': user.username, 'password': PASSWORD}, format='json')
    assert pending.status_code == 202
    assert anon.get('/api/v1/auth/me/').status_code in (401,403)
    verified = anon.post('/api/v1/auth/mfa/verify/', {'method': 'backup_code', 'code': codes[0]}, format='json')
    assert verified.status_code == 200
    assert anon.get('/api/v1/auth/me/').status_code == 200
    replay = anon.post('/api/v1/auth/security/step-up/', {'current_password': PASSWORD, 'method': 'backup_code', 'code': codes[0]}, format='json')
    assert replay.status_code == 401
    assert client.get('/api/v1/auth/security/').json()['backup_codes_remaining'] == 9

def test_failure_budget_commits_and_missing_key_no_penalty(identity_client, keyed, settings):
    from apps.core.models import IdentitySecurity
    client,user = identity_client
    setup, codes = enroll(client)
    for _ in range(5):
        response = client.post('/api/v1/auth/security/step-up/', {'current_password': PASSWORD, 'method': 'totp', 'code': 'bad'}, format='json')
        assert response.status_code == 401
    state = IdentitySecurity.objects.get(user=user)
    assert state.failure_count == 5
    response = client.post('/api/v1/auth/security/step-up/', {'current_password': PASSWORD, 'method': 'backup_code', 'code': codes[0]}, format='json')
    assert response.status_code == 429 and int(response['Retry-After']) > 0

def test_security_mutations_revoke_others_and_password(identity_client, keyed):
    client,user = identity_client
    setup,codes = enroll(client)
    proof = {'current_password': PASSWORD, 'method':'backup_code', 'code':codes[0]}
    assert client.post('/api/v1/auth/security/sessions/revoke/', {**proof,'scope':'others'}, format='json').status_code == 204
    assert client.get('/api/v1/auth/me/').status_code == 200
    proof['code'] = codes[1]
    rotated = client.post('/api/v1/auth/security/backup-codes/rotate/', proof, format='json')
    assert rotated.status_code == 200
    proof['code'] = rotated.json()['backup_codes'][0]
    changed = client.post('/api/v1/auth/security/password/', {**proof,'new_password':'Different-synthetic-long-28!'}, format='json')
    assert changed.status_code == 204
    user.refresh_from_db(); assert user.check_password('Different-synthetic-long-28!')
    assert client.get('/api/v1/auth/me/').status_code == 200

@pytest.mark.parametrize('body', [[],None,{'unknown':True}])
def test_strict_security_bodies(identity_client, body):
    client,user=identity_client
    assert client.post('/api/v1/auth/security/enrollment/',body,format='json').status_code == 400

def test_status_post_is_405_without_state_writes(identity_client):
    client,user=identity_client
    response=client.post('/api/v1/auth/security/', {'current_password':PASSWORD},format='json')
    assert response.status_code==405
    from apps.core.models import IdentitySecurity, AuditEvent
    assert not IdentitySecurity.objects.exists() and not AuditEvent.objects.exists()

def test_wrong_key_swap_and_no_penalty(identity_client,keyed,settings):
    from cryptography.fernet import Fernet
    from apps.core.models import IdentitySecurity
    client,user=identity_client
    setup,codes=enroll(client)
    old=settings.HMS_MFA_ENCRYPTION_KEYS
    settings.HMS_MFA_ENCRYPTION_KEYS=Fernet.generate_key().decode()
    response=client.post('/api/v1/auth/security/step-up/',{'current_password':PASSWORD,'method':'backup_code','code':codes[0]},format='json')
    assert response.status_code==503
    assert IdentitySecurity.objects.get(user=user).failure_count==0
    settings.HMS_MFA_ENCRYPTION_KEYS=Fernet.generate_key().decode()+','+old
    assert client.post('/api/v1/auth/security/step-up/',{'current_password':PASSWORD,'method':'backup_code','code':codes[0]},format='json').status_code==200

def test_latest_challenge_and_session_binding(identity_client,keyed):
    client,user=identity_client
    setup,codes=enroll(client)
    first,second=APIClient(),APIClient()
    for c in [first,second]:
        assert c.post('/api/v1/auth/login/',{'username':user.username,'password':PASSWORD},format='json').status_code==202
    proof={'method':'backup_code','code':codes[0]}
    assert first.post('/api/v1/auth/mfa/verify/',proof,format='json').status_code==401
    assert APIClient().post('/api/v1/auth/mfa/verify/',proof,format='json').status_code==401
    assert second.post('/api/v1/auth/mfa/verify/',proof,format='json').status_code==200

def test_totp_cross_action_replay_and_replacement_proof(identity_client,keyed):
    import pyotp
    client,user=identity_client
    setup,codes=enroll(client)
    assert client.post('/api/v1/auth/security/step-up/',{'current_password':PASSWORD,'method':'totp','code':pyotp.TOTP(setup['secret']).now()},format='json').status_code==401
    assert client.post('/api/v1/auth/security/enrollment/',{'current_password':PASSWORD},format='json').status_code==401
    assert client.post('/api/v1/auth/security/disable/',{'current_password':PASSWORD,'method':'backup_code','code':codes[0]},format='json').status_code==200
    assert client.get('/api/v1/auth/security/').json()['enabled'] is False

def test_no_get_writes_and_no_secret_leak(identity_client,keyed):
    import json
    from apps.core.models import IdentitySecurity,AuditEvent
    client,user=identity_client
    client.get('/api/v1/auth/security/')
    assert not IdentitySecurity.objects.exists() and not AuditEvent.objects.exists()
    setup,codes=enroll(client)
    body=client.get('/api/v1/auth/security/')
    assert body['Cache-Control']=='no-store'
    evidence=json.dumps(list(AuditEvent.objects.values('details')))+json.dumps(body.json())
    assert all(secret not in evidence for secret in [setup['secret'],setup['otpauth_uri'],*codes])

def test_network_budget_shared_and_fixed_expiry(identity_client,settings):
    from apps.core.models import IdentityNetworkBudget
    from django.utils import timezone
    from datetime import timedelta
    client,user=identity_client
    for _ in range(10):
        assert APIClient().post('/api/v1/auth/login/',{'username':'missing','password':'wrong'},format='json').status_code==401
    assert APIClient().post('/api/v1/auth/login/',{'username':'missing','password':'wrong'},format='json').status_code==429
    IdentityNetworkBudget.objects.update(started_at=timezone.now()-timedelta(seconds=61))
    assert APIClient().post('/api/v1/auth/login/',{'username':'missing','password':'wrong'},format='json').status_code==401

def test_production_policy_applies_to_direct_services(identity_client,settings):
    from apps.core.resource_admin import create_branch
    from apps.core.models import Organisation,Branch,Membership
    from apps.core.identity_security import SecurityError
    client,user=identity_client
    org=Organisation.objects.create(name='Synthetic policy')
    branch=Branch.objects.create(organisation=org,name='Main',code='MAIN')
    Membership.objects.create(user=user,branch=branch,role='master_admin')
    settings.HMS_REQUIRE_ADMIN_MFA=True
    response=client.post(f'/api/v1/platform/organisations/{org.pk}/branches/',{'name':'New','code':'NEW'},format='json')
    assert response.status_code==403 and response.json()['code']=='mfa_enrollment_required'
    with pytest.raises(SecurityError) as exc:
        create_branch(user,org.pk,{'name':'New','code':'NEW'})
    assert exc.value.default_code=='mfa_enrollment_required'

def test_legacy_missing_epoch_never_adopts_current(identity_client,keyed):
    client,user=identity_client
    setup,codes=enroll(client)
    session=client.session;session.pop('auth_epoch');session.save()
    assert client.get('/api/v1/auth/me/').status_code==401

def test_fresh_deactivation_while_waiting_is_denied(identity_client,monkeypatch):
    from apps.core import identity_security as identity
    client,user=identity_client
    original=identity.lock_identity
    def deactivate(actor):
        fresh,state=original(actor)
        fresh.is_active=False;fresh.save(update_fields=['is_active'])
        return fresh,state
    monkeypatch.setattr(identity,'lock_identity',deactivate)
    assert client.post('/api/v1/auth/security/enrollment/',{'current_password':PASSWORD},format='json').status_code==401

@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('method',['totp','backup_code'])
def test_postgres_factor_race_one_winner(settings,method):
    from django.db import connection,close_old_connections,transaction
    if connection.vendor!='postgresql':pytest.skip('Requires PostgreSQL row locks.')
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from apps.core import identity_security as identity
    from cryptography.fernet import Fernet
    import pyotp,uuid
    settings.HMS_MFA_ENCRYPTION_KEYS=Fernet.generate_key().decode()
    user=get_user_model().objects.create_user(username='synthetic-factor-race')
    device=uuid.uuid4();secret=pyotp.random_base32()
    from apps.core.models import IdentitySecurity
    state=IdentitySecurity.objects.create(user=user,device_id=device,active_ciphertext=identity.encrypt(secret,user.pk,device,'active'))
    code=pyotp.TOTP(secret).now() if method=='totp' else identity.replace_codes(user)[0]
    barrier=Barrier(2)
    def redeem(_):
        close_old_connections()
        try:
            actor=get_user_model().objects.get(pk=user.pk)
            barrier.wait(timeout=10)
            with transaction.atomic():
                fresh,state=identity.lock_identity(actor)
                accepted=identity.factor(state,method,code)
                state.save()
                return accepted
        finally:close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(redeem,range(2)))==[False,True]

def test_successful_factor_transition_rotates_session(identity_client,keyed):
    client,user=identity_client
    before=client.session.session_key
    setup,codes=enroll(client)
    assert client.session.session_key!=before
    before=client.session.session_key
    assert client.post('/api/v1/auth/security/step-up/',{'current_password':PASSWORD,'method':'backup_code','code':codes[0]},format='json').status_code==200
    assert client.session.session_key!=before

def test_login_rechecks_password_after_identity_lock(identity_client,monkeypatch):
    from apps.core import identity_security as identity
    client,user=identity_client
    original=identity.lock_identity
    def changed(actor):
        fresh,state=original(actor)
        fresh.set_password('Changed-during-wait-79!');fresh.save(update_fields=['password'])
        return fresh,state
    monkeypatch.setattr(identity,'lock_identity',changed)
    response=APIClient().post('/api/v1/auth/login/',{'username':user.username,'password':PASSWORD},format='json')
    assert response.status_code==401

def test_login_password_maximum_1024_is_generic_credentials_failure(identity_client):
    client,user=identity_client
    response=APIClient().post('/api/v1/auth/login/',{'username':user.username,'password':'x'*1024},format='json')
    assert response.status_code==401

@pytest.mark.parametrize('service',['configuration','staff'])
def test_platform_proof_age_rechecked_after_organisation_wait(identity_client,keyed,settings,monkeypatch,service):
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models.query import QuerySet
    from apps.core.models import Organisation,Branch,Membership
    from apps.core.identity_security import SecurityError
    from apps.core.resource_admin import create_branch
    from apps.core.staff_access import create_staff
    client,user=identity_client
    setup,codes=enroll(client)
    org=Organisation.objects.create(name='Synthetic expiry')
    branch=Branch.objects.create(organisation=org,name='Main',code='MAIN')
    Membership.objects.create(user=user,branch=branch,role='master_admin')
    user._hms_auth_epoch=client.session['auth_epoch']
    user._hms_factor_verified_at=client.session['factor_verified_at']
    settings.HMS_REQUIRE_ADMIN_MFA=True
    started=timezone.now();clock=[started]
    monkeypatch.setattr(timezone,'now',lambda:clock[0])
    original=QuerySet.get
    def delayed(queryset,*args,**kwargs):
        result=original(queryset,*args,**kwargs)
        if queryset.model is Organisation and queryset.query.select_for_update:
            clock[0]=started+timedelta(seconds=901)
        return result
    monkeypatch.setattr(QuerySet,'get',delayed)
    with pytest.raises(SecurityError) as exc:
        if service=='configuration':
            create_branch(user,org.pk,{'name':'Should not exist','code':'EXPIRED'})
        else:
            create_staff(user,org.pk,{'username':'expired-staff','name':'Synthetic','password':PASSWORD,'assignments':[{'branch':branch.pk,'role':'reception'}]})
    assert exc.value.default_code=='mfa_step_up_required'
    assert not Branch.objects.filter(code='EXPIRED').exists()
    assert not get_user_model().objects.filter(username='expired-staff').exists()

@pytest.mark.parametrize('swap',['user','device','purpose'])
def test_ciphertext_binding_swap_fails_closed(identity_client,keyed,swap):
    import uuid
    from apps.core.models import IdentitySecurity,IdentityEnrollment
    from apps.core import identity_security as identity
    client,user=identity_client
    setup,codes=enroll(client)
    state=IdentitySecurity.objects.get(user=user)
    if swap=='user':
        state.active_ciphertext=identity.encrypt(setup['secret'],user.pk+100,state.device_id,'active')
    elif swap=='device':
        state.device_id=uuid.uuid4()
    else:
        state.active_ciphertext=identity.encrypt(setup['secret'],user.pk,state.device_id,'enrollment')
    state.save()
    response=client.post('/api/v1/auth/security/step-up/',{'current_password':PASSWORD,'method':'backup_code','code':codes[0]},format='json')
    assert response.status_code==503
    state.refresh_from_db();assert state.failure_count==0
    assert client.get('/api/v1/auth/security/').json()['backup_codes_remaining']==10

@pytest.mark.parametrize('failure',['expired','cross_session','replayed'])
def test_enrollment_confirmation_binding_expiry_and_consumption(identity_client,keyed,failure):
    import pyotp
    from datetime import timedelta
    from django.utils import timezone
    from apps.core.models import IdentityEnrollment,IdentitySecurity,IdentityBackupCode
    client,user=identity_client
    setup=client.post('/api/v1/auth/security/enrollment/',{'current_password':PASSWORD},format='json').json()
    path=f"/api/v1/auth/security/enrollment/{setup['enrollment_id']}/confirm/"
    body={'code':pyotp.TOTP(setup['secret']).now()}
    if failure=='expired':
        IdentityEnrollment.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
    elif failure=='cross_session':
        client=APIClient();client.force_login(user)
    else:
        assert client.post(path,body,format='json').status_code==200
    result=client.post(path,body,format='json')
    assert result.status_code==409 and result.json()['code']=='security_state_conflict'
    state=IdentitySecurity.objects.get(user=user)
    assert state.auth_epoch==(1 if failure=='replayed' else 0)
    assert IdentityBackupCode.objects.count()==(10 if failure=='replayed' else 0)
    assert 'secret' not in result.json() and 'backup_codes' not in result.json()


def test_anonymous_mfa_verification_requires_csrf(identity_client,keyed):
    client,user=identity_client
    setup,codes=enroll(client)
    anonymous=APIClient(enforce_csrf_checks=True)
    anonymous.get('/api/v1/auth/csrf/')
    csrf=anonymous.cookies['csrftoken'].value
    assert anonymous.post('/api/v1/auth/login/',{'username':user.username,'password':PASSWORD},format='json',HTTP_X_CSRFTOKEN=csrf).status_code==202
    body={'method':'backup_code','code':codes[0]}
    assert anonymous.post('/api/v1/auth/mfa/verify/',body,format='json').status_code==403
    assert anonymous.get('/api/v1/auth/me/').status_code in (401,403)
    assert anonymous.post('/api/v1/auth/mfa/verify/',body,format='json',HTTP_X_CSRFTOKEN=csrf).status_code==200


def test_fixed_account_window_survives_new_challenge_and_expires(identity_client,keyed,monkeypatch):
    from datetime import timedelta
    from django.utils import timezone
    from apps.core.models import IdentitySecurity,IdentityNetworkBudget
    client,user=identity_client
    setup,codes=enroll(client)
    start=timezone.now();clock=[start]
    monkeypatch.setattr(timezone,'now',lambda:clock[0])
    bad={'current_password':PASSWORD,'method':'totp','code':'bad'}
    for attempt in range(5):
        clock[0]=start+timedelta(seconds=attempt*10)
        assert client.post('/api/v1/auth/security/step-up/',bad,format='json').status_code==401
        state=IdentitySecurity.objects.get(user=user)
        assert state.failure_started==start and state.failure_count==attempt+1
    clock[0]=start+timedelta(seconds=61)
    other=APIClient()
    assert other.post('/api/v1/auth/login/',{'username':user.username,'password':PASSWORD},format='json').status_code==202
    assert IdentitySecurity.objects.get(user=user).failure_count==5
    blocked=other.post('/api/v1/auth/mfa/verify/',{'method':'backup_code','code':codes[0]},format='json')
    assert blocked.status_code==429 and int(blocked['Retry-After'])==239
    clock[0]=start+timedelta(seconds=301)
    assert other.post('/api/v1/auth/mfa/verify/',{'method':'backup_code','code':codes[0]},format='json').status_code==200
    state.refresh_from_db();assert state.failure_count==0 and state.failure_started is None


def test_challenge_lifetime_attempt_budget_independent_of_account_window(identity_client,keyed,monkeypatch):
    from datetime import timedelta
    from django.utils import timezone
    from apps.core.models import IdentityChallenge,IdentitySecurity,IdentityNetworkBudget
    client,user=identity_client
    setup,codes=enroll(client)
    anonymous=APIClient()
    anonymous.post('/api/v1/auth/login/',{'username':user.username,'password':PASSWORD},format='json')
    challenge=IdentityChallenge.objects.get(pk=anonymous.session['mfa_challenge'])
    start=timezone.now();clock=[start]
    monkeypatch.setattr(timezone,'now',lambda:clock[0])
    for attempt in range(5):
        result=anonymous.post('/api/v1/auth/mfa/verify/',{'method':'totp','code':'bad'},format='json')
        assert result.status_code==401
    challenge.refresh_from_db();assert challenge.attempts==5
    # Extend only expiry as a test fixture to isolate the lifetime ceiling from
    # its normal simultaneous five-minute deadline/account-window reset.
    IdentityChallenge.objects.filter(pk=challenge.pk).update(expires_at=start+timedelta(minutes=10))
    clock[0]=start+timedelta(seconds=301)
    result=anonymous.post('/api/v1/auth/mfa/verify/',{'method':'backup_code','code':codes[0]},format='json')
    assert result.status_code==429
    assert anonymous.get('/api/v1/auth/me/').status_code in (401,403)


def test_missing_key_during_challenge_preserves_factor_and_attempt_budgets(identity_client,keyed,settings):
    from apps.core.models import IdentityChallenge,IdentitySecurity
    client,user=identity_client
    setup,codes=enroll(client)
    anonymous=APIClient()
    anonymous.post('/api/v1/auth/login/',{'username':user.username,'password':PASSWORD},format='json')
    challenge=IdentityChallenge.objects.get(pk=anonymous.session['mfa_challenge'])
    settings.HMS_MFA_ENCRYPTION_KEYS=''
    response=anonymous.post('/api/v1/auth/mfa/verify/',{'method':'backup_code','code':codes[0]},format='json')
    assert response.status_code==503
    challenge.refresh_from_db();assert challenge.attempts==0 and not challenge.consumed
    state=IdentitySecurity.objects.get(user=user)
    assert state.failure_count==0 and state.failure_started is None

# PostgreSQL-only request races use real independent connections and explicit
# ordering at the canonical User/identity lock, not scheduler timing/sleeps.
def _ordered_identity_race(monkeypatch, operations, winner):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event,local
    from django.db import close_old_connections
    from apps.core import identity_security as identity
    winner_locked,loser_entered=Event(),Event()
    local_state=local();original=identity.lock_identity
    def ordered(actor):
        if local_state.name!=winner:
            assert winner_locked.wait(10),'Winning request never acquired identity lock.'
            loser_entered.set()
        result=original(actor)
        if local_state.name==winner:
            winner_locked.set()
            assert loser_entered.wait(10),'Losing request never attempted identity lock.'
        return result
    monkeypatch.setattr(identity,'lock_identity',ordered)
    def run(name):
        close_old_connections();local_state.name=name
        try:return operations[name]()
        finally:close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures={name:pool.submit(run,name) for name in operations}
        return {name:future.result(timeout=20) for name,future in futures.items()}


def _require_postgres():
    from django.db import connection
    if connection.vendor!='postgresql':pytest.skip('Requires PostgreSQL row locks and independent request connections.')


def _second_proven_client(client,user):
    other=APIClient();other.force_login(user)
    session=other.session
    session['auth_epoch']=client.session['auth_epoch']
    session['factor_verified_at']=client.session['factor_verified_at']
    session.save()
    return other


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('winner',['revoke','platform'])
def test_postgres_all_revoke_and_platform_write_have_defined_winner(identity_client,keyed,settings,monkeypatch,winner):
    _require_postgres()
    from apps.core.models import Organisation,Branch,Membership,IdentitySecurity,AuditEvent
    client,user=identity_client
    setup,codes=enroll(client)
    other=_second_proven_client(client,user)
    org=Organisation.objects.create(name='Synthetic revoke race')
    branch=Branch.objects.create(organisation=org,name='Main',code='MAIN')
    Membership.objects.create(user=user,branch=branch,role='master_admin')
    settings.HMS_REQUIRE_ADMIN_MFA=True
    results=_ordered_identity_race(monkeypatch,{
        'revoke':lambda:client.post('/api/v1/auth/security/sessions/revoke/',{'current_password':PASSWORD,'method':'backup_code','code':codes[0],'scope':'all'},format='json'),
        'platform':lambda:other.post(f'/api/v1/platform/organisations/{org.pk}/branches/',{'name':'Race branch','code':'RACE'},format='json'),
    },winner)
    assert results['revoke'].status_code==204
    assert results['platform'].status_code==(401 if winner=='revoke' else 201)
    assert Branch.objects.filter(organisation=org,code='RACE').exists()==(winner=='platform')
    assert IdentitySecurity.objects.get(user=user).auth_epoch==2
    assert not client.session.get('_auth_user_id')
    assert other.get('/api/v1/auth/me/').status_code==401
    assert AuditEvent.objects.filter(action='security.revoke').count()==1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('operation',['revoke','disable'])
@pytest.mark.parametrize('winner',['confirm','mutation'])
def test_postgres_enrollment_confirmation_vs_revoke_or_disable(identity_client,keyed,monkeypatch,operation,winner):
    _require_postgres()
    import pyotp
    from apps.core.models import IdentitySecurity,IdentityBackupCode,IdentityEnrollment
    client,user=identity_client
    setup,codes=enroll(client)
    replacement=client.post('/api/v1/auth/security/enrollment/',{'current_password':PASSWORD,'method':'backup_code','code':codes[0]},format='json').json()
    other=_second_proven_client(client,user)
    path='/api/v1/auth/security/'+('sessions/revoke/' if operation=='revoke' else 'disable/')
    body={'current_password':PASSWORD,'method':'backup_code','code':codes[1]}
    if operation=='revoke':body['scope']='all'
    results=_ordered_identity_race(monkeypatch,{
        'confirm':lambda:client.post(f"/api/v1/auth/security/enrollment/{replacement['enrollment_id']}/confirm/",{'code':pyotp.TOTP(replacement['secret']).now()},format='json'),
        'mutation':lambda:other.post(path,body,format='json'),
    },winner)
    assert results[winner].status_code==(200 if winner=='confirm' or operation=='disable' else 204)
    assert results['mutation' if winner=='confirm' else 'confirm'].status_code==401
    state=IdentitySecurity.objects.get(user=user)
    assert state.auth_epoch==2
    assert bool(state.active_ciphertext)==(winner=='confirm' or operation=='revoke')
    assert IdentityBackupCode.objects.filter(user=user).count()==(10 if winner=='confirm' else 0 if operation=='disable' else 8)
    assert not IdentityEnrollment.objects.filter(user=user,consumed=False).exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('enabled',[False,True])
def test_postgres_concurrent_logins_create_one_profile_and_authoritative_latest_challenge(identity_client,keyed,monkeypatch,enabled):
    _require_postgres()
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from django.db import close_old_connections
    from apps.core import identity_security as identity
    from apps.core.models import IdentitySecurity,IdentityChallenge
    client,user=identity_client
    codes=None
    if enabled:setup,codes=enroll(client)
    clients=[APIClient(),APIClient()]
    barrier=Barrier(2);original=identity.lock_identity
    def simultaneous(actor):
        barrier.wait(timeout=10)
        return original(actor)
    monkeypatch.setattr(identity,'lock_identity',simultaneous)
    def run(c):
        close_old_connections()
        try:return c.post('/api/v1/auth/login/',{'username':user.username,'password':PASSWORD},format='json')
        finally:close_old_connections()
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,clients))
    assert [r.status_code for r in results]==[202 if enabled else 200]*2
    assert IdentitySecurity.objects.filter(user=user).count()==1
    if enabled:
        state=IdentitySecurity.objects.get(user=user)
        assert IdentityChallenge.objects.filter(user=user).count()==2
        monkeypatch.setattr(identity,'lock_identity',original)
        for c in clients:
            latest=c.session['mfa_challenge']==str(state.latest_challenge)
            result=c.post('/api/v1/auth/mfa/verify/',{'method':'backup_code','code':codes[0]},format='json')
            assert result.status_code==(200 if latest else 401)

@pytest.mark.parametrize('service',['bed_create','bed_change','staff_change'])
def test_platform_proof_age_rechecked_after_final_resource_lock(identity_client,keyed,settings,monkeypatch,service):
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models.query import QuerySet
    from apps.core.models import Organisation,Branch,Membership,Bed,StaffAccessRevision,AuditEvent
    from apps.core.identity_security import SecurityError
    from apps.core.resource_admin import create_bed,change_bed
    from apps.core.staff_access import change_staff
    client,user=identity_client
    setup,codes=enroll(client)
    org=Organisation.objects.create(name='Synthetic final lock expiry')
    branch=Branch.objects.create(organisation=org,name='Main',code='MAIN')
    Membership.objects.create(user=user,branch=branch,role='master_admin')
    bed=Bed.objects.create(branch=branch,number='B1',room_number='R1')
    target=get_user_model().objects.create_user(username='expiry-target')
    Membership.objects.create(user=target,branch=branch,role='reception')
    StaffAccessRevision.objects.create(user=target,organisation=org,version=1)
    user._hms_auth_epoch=client.session['auth_epoch'];user._hms_factor_verified_at=client.session['factor_verified_at']
    settings.HMS_REQUIRE_ADMIN_MFA=True
    started=timezone.now();clock=[started]
    monkeypatch.setattr(timezone,'now',lambda:clock[0])
    original=QuerySet._fetch_all
    waited=Branch if service=='bed_create' else Bed if service=='bed_change' else StaffAccessRevision
    def delayed(queryset):
        original(queryset)
        if queryset.model is waited and queryset.query.select_for_update:
            clock[0]=started+timedelta(seconds=901)
    monkeypatch.setattr(QuerySet,'_fetch_all',delayed)
    with pytest.raises(SecurityError) as exc:
        if service=='bed_create':create_bed(user,org.pk,{'branch':branch,'number':'B2','room_number':'R2','category':'general','status':'available'})
        elif service=='bed_change':change_bed(user,org.pk,bed.pk,{'expected_version':1,'number':'CHANGED'})
        else:change_staff(user,org.pk,target.pk,{'expected_version':1,'status':'suspended'})
    assert exc.value.default_code=='mfa_step_up_required'
    bed.refresh_from_db();assert bed.number=='B1' and bed.version==1
    assert not Bed.objects.filter(number='B2').exists()
    assert Membership.objects.get(user=target).is_active
    assert not AuditEvent.objects.filter(action__in=['bed.created','bed.changed','staff.changed']).exists()
