"""Frozen HTTP behavior: changes fail these tests if authority, retries or deadlines break."""
import uuid
from datetime import timedelta
from unittest.mock import patch
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from apps.core.models import Organisation, Branch, Membership, IdentitySecurity, NetworkOperator, NetworkPolicyState, NetworkPolicyPreview, NetworkPolicyChange, NetworkPolicyEvent

pytestmark = pytest.mark.django_db
ROOT = '/api/v1/platform/network-policy/'
OPEN = {'allowlist_only': False, 'allowlist': [], 'blocklist': []}
CANDIDATE = {'allowlist_only': True, 'allowlist': ['127.0.0.1'], 'blocklist': []}


@pytest.fixture
def manager(settings):
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    settings.HMS_REQUIRE_ADMIN_MFA = False
    owner = Organisation.objects.create(name='Synthetic network owner')
    branch = Branch.objects.create(organisation=owner, name='Synthetic branch', code='NET')
    user = get_user_model().objects.create_user(username='network-synthetic', password='Synthetic-only-72!')
    Membership.objects.create(user=user, branch=branch, role='master_admin')
    IdentitySecurity.objects.create(user=user, active_ciphertext='synthetic-enrolled-marker', auth_epoch=0)
    operator = NetworkOperator.objects.create(user=user, organisation=owner)
    NetworkPolicyState.objects.filter(pk=1).update(bound_owner=owner)
    settings.HMS_SECURITY_ORGANISATION_ID = str(owner.pk)
    client = APIClient()
    client.force_login(user)
    session = client.session
    session['auth_epoch'] = 0
    session['factor_verified_at'] = timezone.now().timestamp()
    session.save()
    return client, user, owner, operator


def preview(client, policy=CANDIDATE, key=None, revision=1):
    return client.post(ROOT+'previews/', {'expected_revision': revision, 'policy': policy, 'reason': 'Synthetic policy change'}, format='json', HTTP_IDEMPOTENCY_KEY=str(key or uuid.uuid4()))


def test_state_is_pure_and_capability_is_deployment_only(manager):
    client, user, owner, operator = manager
    before = (NetworkPolicyState.objects.get(pk=1).revision, NetworkPolicyEvent.objects.count(), IdentitySecurity.objects.count())
    response = client.get(ROOT)
    assert response.status_code == 200
    data = response.json()
    assert data['scope'] == 'deployment'
    assert data['verified_client_ip'] == '127.0.0.1'
    assert data['owner_organisation'] == {'id': str(owner.pk), 'name': 'Synthetic network owner'}
    assert data['pending'] is None and data['revision'] == 1
    me = client.get('/api/v1/auth/me/').json()
    assert 'platform.security.manage' in me['permissions']
    assert all('platform.security.manage' not in permissions for permissions in me['branch_permissions'].values())
    assert before == (NetworkPolicyState.objects.get(pk=1).revision, NetworkPolicyEvent.objects.count(), IdentitySecurity.objects.count())


@pytest.mark.parametrize('revocation,code', [('operator','permission_denied'), ('membership','permission_denied'), ('enrollment','mfa_enrollment_required'), ('proof','mfa_step_up_required')])
def test_authority_is_unconditional_even_when_platform_mfa_disabled(manager, revocation, code):
    client, user, owner, operator = manager
    if revocation == 'operator':
        NetworkOperator.objects.filter(pk=operator.pk).update(active=False)
    elif revocation == 'membership':
        Membership.objects.filter(user=user).update(is_active=False)
    elif revocation == 'enrollment':
        IdentitySecurity.objects.filter(user=user).update(active_ciphertext='')
    else:
        session = client.session
        session['factor_verified_at'] = timezone.now().timestamp()-901
        session.save()
    response = client.get(ROOT)
    assert response.status_code == 403
    assert response.json()['code'] == code
    assert not NetworkPolicyPreview.objects.exists()


def test_preview_activate_confirm_exact_retries_do_not_extend_deadlines(manager):
    client, user, owner, operator = manager
    key = uuid.uuid4()
    first = preview(client, key=key)
    assert first.status_code == 201
    repeated = preview(client, key=key)
    assert repeated.status_code == 200
    assert repeated.json()['preview_id'] == first.json()['preview_id']
    assert repeated.json()['expires_at'] == first.json()['expires_at']
    preview_id = first.json()['preview_id']
    activation = client.post(ROOT+f'previews/{preview_id}/activate/', {'expected_revision': 1}, format='json')
    assert activation.status_code == 200
    assert activation.json()['outcome'] == 'pending' and activation.json()['revision'] == 2
    change_id = activation.json()['change_id']
    confirmed = client.post(ROOT+f'changes/{change_id}/confirm/', {'expected_revision': 2}, format='json')
    assert confirmed.status_code == 200
    assert confirmed.json()['outcome'] == 'confirmed' and confirmed.json()['revision'] == 3
    replay = client.post(ROOT+f'changes/{change_id}/confirm/', {'expected_revision': 2}, format='json')
    assert replay.status_code == 200
    assert replay.json()['revision'] == 3
    activation_replay = client.post(ROOT+f'previews/{preview_id}/activate/', {'expected_revision': 1}, format='json')
    assert activation_replay.json()['outcome'] == 'confirmed'
    assert activation_replay.json()['rollback_at'] == activation.json()['rollback_at']
    opposite = client.post(ROOT+f'changes/{change_id}/revert/', {'expected_revision': 2}, format='json')
    assert opposite.status_code == 409 and opposite.json()['code'] == 'network_change_finished'
    assert NetworkPolicyEvent.objects.count() == 2


def test_expiry_read_is_pure_and_conflicting_write_commits_expiry(manager):
    client, *_ = manager
    initial = preview(client)
    assert initial.status_code == 201
    activated = client.post(ROOT+f"previews/{initial.json()['preview_id']}/activate/", {'expected_revision': 1}, format='json')
    assert activated.status_code == 200
    change = NetworkPolicyChange.objects.get(pk=activated.json()['change_id'])
    with patch('django.utils.timezone.now', return_value=change.rollback_at):
        state = client.get(ROOT)
        assert state.status_code == 200
        assert state.json()['pending']['status'] == 'expired_unreconciled'
        assert state.json()['effective_policy'] == OPEN
        assert NetworkPolicyState.objects.get(pk=1).revision == 2
        conflict = preview(client, revision=2)
        assert conflict.status_code == 409
        assert conflict.json()['code'] == 'network_revision_conflict'
    state = NetworkPolicyState.objects.get(pk=1)
    assert state.revision == 3 and state.pending_change_id is None
    assert NetworkPolicyEvent.objects.filter(action='policy.expired').count() == 1


def test_candidate_lockout_and_changed_request_are_rejected(manager):
    client, *_ = manager
    key = uuid.uuid4()
    policy = {'allowlist_only': True, 'allowlist': ['198.51.100.1'], 'blocklist': []}
    first = preview(client, policy=policy, key=key)
    assert first.status_code == 201 and first.json()['can_activate'] is False
    conflict = preview(client, policy=CANDIDATE, key=key)
    assert conflict.status_code == 409 and conflict.json()['code'] == 'idempotency_conflict'
    denied = client.post(ROOT+f"previews/{first.json()['preview_id']}/activate/", {'expected_revision': 1}, format='json')
    assert denied.status_code == 400
    assert NetworkPolicyState.objects.get(pk=1).revision == 1


@pytest.mark.parametrize('body', ['{"expected_revision":1,"expected_revision":1}', '{"expected_revision":true}', '[]', '{"expected_revision":1,"unknown":0}'])
def test_strict_action_body_rejects_duplicate_coercion_and_extra_fields(manager, body):
    client, *_ = manager
    response = client.post(ROOT+f'changes/{uuid.uuid4()}/confirm/', body, content_type='application/json')
    assert response.status_code == 400 and response.json()['code'] == 'validation_error'


def test_unknown_repeated_query_and_oversized_body_are_bounded(manager):
    client, *_ = manager
    assert client.get(ROOT+'?unknown=1').status_code == 400
    assert client.get(ROOT+'history/?limit=1&limit=2').status_code == 400
    response = client.post(ROOT+'previews/', ' '*32769, content_type='application/json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    assert response.status_code == 413


def test_probe_is_empty_network_only_and_never_touches_session(manager, settings):
    client, user, *_ = manager
    settings.HMS_NETWORK_PROBE_PEERS = ('127.0.0.1',)
    settings.SESSION_SAVE_EVERY_REQUEST = True
    IdentitySecurity.objects.filter(user=user).update(auth_epoch=3)
    response = client.get('/api/v1/network-policy/edge-probe/', HTTP_X_HMS_NETWORK_PROBE='1', HTTP_AUTHORIZATION='ignored')
    assert response.status_code == 204 and response.content == b''
    assert not response.cookies and response['Cache-Control'] == 'no-store'
    assert client.session.get('_auth_user_id') == str(user.pk)
    invalid = client.get('/api/v1/network-policy/edge-probe/', HTTP_X_HMS_NETWORK_PROBE='1', REMOTE_ADDR='198.51.100.2')
    assert invalid.status_code == 404 and invalid.content == b'' and not invalid.cookies


@pytest.mark.parametrize('proof', [True, False, float('nan'), float('inf'), -1, None])
@pytest.mark.parametrize('route,method', [('', 'get'), ('history/', 'get'), ('previews/', 'post'), ('previews/00000000-0000-4000-8000-000000000001/activate/', 'post'), ('changes/00000000-0000-4000-8000-000000000001/confirm/', 'post'), ('changes/00000000-0000-4000-8000-000000000001/revert/', 'post')])
def test_all_six_routes_require_strict_finite_fresh_factor_before_id_lookup(manager, route, method, proof):
    client, *_ = manager
    session = client.session
    session['factor_verified_at'] = proof
    session.save()
    kwargs = {'data': {'expected_revision': 1}, 'format': 'json'} if method == 'post' else {}
    response = getattr(client, method)(ROOT+route, **kwargs)
    assert response.status_code == 403
    assert response.json()['code'] == 'mfa_step_up_required'


def test_history_never_exposes_private_operator_target_fields(manager):
    client, user, owner, operator = manager
    NetworkPolicyEvent.objects.create(owner=owner, actor=user, target_user=user, os_actor='Synthetic operator', action='operator.granted', outcome='granted', revision=1, reason='Synthetic entitlement event', before_policy=None, after_policy=None, created_at=timezone.now()-timedelta(seconds=1), entitlement_version_before=0, entitlement_version_after=1)
    response = client.get(ROOT+'history/')
    assert response.status_code == 200
    data = response.json()
    assert data['count'] == 1
    event = data['results'][0]
    assert set(event) == {'id', 'created_at', 'action', 'outcome', 'actor', 'os_actor', 'reason', 'change_id', 'revision', 'before', 'after'}
    assert event['before'] is None and event['after'] is None


def test_cross_session_preview_is_hidden_and_environment_drift_invalidates(manager, settings):
    client, user, *_ = manager
    issued = preview(client)
    assert issued.status_code == 201
    path = ROOT+f"previews/{issued.json()['preview_id']}/activate/"
    other = APIClient()
    other.force_login(user)
    session = other.session
    session['auth_epoch'] = 0
    session['factor_verified_at'] = timezone.now().timestamp()
    session.save()
    assert other.post(path, {'expected_revision': 1}, format='json').status_code == 404
    from apps.core.network_environment import environment_snapshot
    original_digest = environment_snapshot().digest
    settings.HMS_TRUSTED_PROXIES = () if settings.HMS_TRUSTED_PROXIES else ('127.0.0.1/32',)
    assert environment_snapshot().digest != original_digest
    response = client.post(path, {'expected_revision': 1}, format='json')
    assert response.status_code == 409 and response.json()['code'] == 'network_preview_invalidated'


def test_summary_reports_effective_pending_mode_and_expired_fallback(manager):
    client, *_ = manager
    issued = preview(client)
    assert issued.status_code == 201
    activation = client.post(ROOT+f"previews/{issued.json()['preview_id']}/activate/", {'expected_revision': 1}, format='json')
    assert activation.status_code == 200
    summary = client.get('/api/v1/platform/summary/')
    assert summary.status_code == 200
    assert summary.json()['security'] == {'ip_mode': 'allowlist_only', 'policy_scope': 'effective_deployment', 'blocked_addresses_apply': True}
    change = NetworkPolicyChange.objects.get(pk=activation.json()['change_id'])
    with patch('django.utils.timezone.now', return_value=change.rollback_at):
        summary = client.get('/api/v1/platform/summary/')
        assert summary.json()['security']['ip_mode'] == 'allow_authenticated'
    assert NetworkPolicyState.objects.get(pk=1).revision == 2


def test_original_reason_and_control_characters_are_not_fingerprint_aliases(manager):
    client, *_ = manager
    key = str(uuid.uuid4())
    data = {'expected_revision': 1, 'policy': OPEN, 'reason': '  Synthetic policy reason  '}
    assert client.post(ROOT+'previews/', data, format='json', HTTP_IDEMPOTENCY_KEY=key).status_code == 201
    data['reason'] = 'Synthetic policy reason'
    conflict = client.post(ROOT+'previews/', data, format='json', HTTP_IDEMPOTENCY_KEY=key)
    assert conflict.status_code == 409 and conflict.json()['code'] == 'idempotency_conflict'
    data['reason'] = 'Synthetic\u0085control reason'
    invalid = client.post(ROOT+'previews/', data, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
    assert invalid.status_code == 400


@pytest.mark.parametrize('field,value', [('normalisations', [{'list': 'allowlist', 'index': 0, 'input': 'x'*10000, 'canonical': '127.0.0.1/32'}]), ('reason', 'x'), ('request_digest', 'not-sha')])
def test_corrupt_saved_preview_cannot_be_projected_or_activated(manager, field, value):
    client, *_ = manager
    key = uuid.uuid4()
    issued = preview(client, key=key)
    assert issued.status_code == 201
    NetworkPolicyPreview.objects.filter(pk=issued.json()['preview_id']).update(**{field: value})
    response = preview(client, key=key)
    assert response.status_code == 503 and response.json()['code'] == 'network_policy_unavailable'


def test_terminal_replay_preserves_later_state_and_rejects_missing_terminal_revision(manager):
    client, *_ = manager
    issued = preview(client)
    activated = client.post(ROOT+f"previews/{issued.json()['preview_id']}/activate/", {'expected_revision': 1}, format='json')
    cid = activated.json()['change_id']
    assert client.post(ROOT+f'changes/{cid}/confirm/', {'expected_revision': 2}, format='json').status_code == 200
    issued2 = preview(client, policy=OPEN, revision=3)
    assert issued2.status_code == 201
    activation2 = client.post(ROOT+f"previews/{issued2.json()['preview_id']}/activate/", {'expected_revision': 3}, format='json')
    assert activation2.status_code == 200
    replay = client.post(ROOT+f'changes/{cid}/confirm/', {'expected_revision': 2}, format='json')
    assert replay.status_code == 200 and replay.json()['revision'] == 4
    assert NetworkPolicyState.objects.get(pk=1).pending_change_id == uuid.UUID(activation2.json()['change_id'])


def test_owner_transfer_after_state_authorization_cannot_disclose_new_policy(manager, monkeypatch):
    client, *_ = manager
    from apps.core import network_access
    authorize = network_access.require_network_operator
    other = Organisation.objects.create(name='Synthetic other owner')
    def transfer_after_authorization(context, *args, **kwargs):
        result = authorize(context, *args, **kwargs)
        NetworkPolicyState.objects.filter(pk=1).update(bound_owner=other)
        return result
    monkeypatch.setattr(network_access, 'require_network_operator', transfer_after_authorization)
    response = client.get(ROOT)
    assert response.status_code == 503
    assert response.json()['code'] == 'network_owner_unavailable'
    assert 'effective_policy' not in response.json()


def test_summary_revalidates_overlay_even_when_environment_requires_allowlist(manager, settings, monkeypatch):
    client, *_ = manager
    from apps.core import network_environment
    settings.HMS_IP_ALLOWLIST_ONLY = True
    settings.HMS_IP_ALLOWLIST = ['127.0.0.1']
    original = network_environment.environment_snapshot
    calls = []
    def remove_after_admission():
        result = original()
        calls.append(True)
        if len(calls) == 2:
            NetworkPolicyState.objects.all().delete()
        return result
    monkeypatch.setattr(network_environment, 'environment_snapshot', remove_after_admission)
    response = client.get('/api/v1/platform/summary/')
    assert response.status_code == 503


def test_unlisted_options_method_is_not_a_capability(manager):
    client, *_ = manager
    assert client.options(ROOT).status_code == 405


@pytest.mark.parametrize('method,status', [('head', 204), ('post', 405)])
def test_private_probe_supported_safe_head_and_unsupported_method(manager, settings, method, status):
    client, *_ = manager
    settings.HMS_NETWORK_PROBE_PEERS = ('127.0.0.1',)
    response = getattr(client, method)('/api/v1/network-policy/edge-probe/', HTTP_X_HMS_NETWORK_PROBE='1')
    assert response.status_code == status and response.content == b'' and not response.cookies
