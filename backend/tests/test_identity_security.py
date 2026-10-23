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
