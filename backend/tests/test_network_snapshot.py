"""B2a read-only graph contract; all identities and policies are synthetic."""
import importlib.util
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import hashlib
import json
import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection
from django.test.utils import CaptureQueriesContext

if importlib.util.find_spec('apps.core.network_snapshot'):
    from apps.core import network_snapshot as service
else:
    service = None
from apps.core.models import Organisation, NetworkPolicyState as State, NetworkPolicyPreview as Preview, NetworkPolicyChange as Change, NetworkPolicyEvent as Event

BASE = {'allowlist_only': False, 'allowlist': [], 'blocklist': ['192.0.2.0/24']}
CANDIDATE = {'allowlist_only': True, 'allowlist': ['198.51.100.0/24'], 'blocklist': []}
NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)
MAX = 9007199254740991


def test_snapshot_service_is_available():
    assert service is not None, 'The bounded read-only network snapshot service is missing'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


@pytest.fixture
def baseline(db):
    state, _ = State.objects.update_or_create(pk=1, defaults=dict(revision=1, bound_owner=None, pending_change=None, confirmed_policy=BASE, confirmed_policy_digest=digest(BASE)))
    return state


@pytest.fixture
def pending(baseline):
    owner = Organisation.objects.create(name='Synthetic owner')
    actor = get_user_model().objects.create(username='synthetic-selector')
    bindings = dict(owner=owner, actor=actor, session_digest='a'*64, epoch=0, operator_version=1,
                    verified_ip='192.0.2.1', environment_digest='b'*64, base_revision=1)
    preview = Preview.objects.create(**bindings, policy=CANDIDATE, policy_digest=digest(CANDIDATE),
        request_digest='c'*64, reason='Synthetic test only', normalisations=[], created_at=NOW-timedelta(seconds=1),
        expires_at=NOW+timedelta(seconds=299), request_key=uuid.uuid4())
    change = Change.objects.create(**bindings, preview=preview, candidate_policy=CANDIDATE,
        candidate_policy_digest=digest(CANDIDATE), fallback_policy=BASE, fallback_policy_digest=digest(BASE),
        activation_revision=2, activated_at=NOW, rollback_at=NOW+timedelta(seconds=300), reason='Synthetic test only')
    Preview.objects.filter(pk=preview.pk).update(result_change=change)
    State.objects.filter(pk=1).update(bound_owner=owner, revision=2, pending_change=change)
    return change, preview


def database_image():
    # Include all models the service could accidentally mutate, without fixture ORM caches.
    return {model._meta.label: list(model.objects.order_by('pk').values()) for model in
            [State, Change, Preview, Event, Organisation, get_user_model()]}


def read_one(now):
    with CaptureQueriesContext(connection) as queries:
        result = service.load_network_snapshot(now)
    assert len(queries) == 1
    assert queries[0]['sql'].lstrip().upper().startswith('SELECT')
    return result


def assert_detached(result):
    policies = [p for p in [result.confirmed_policy, result.effective_policy, result.candidate_policy] if p is not None]
    for index, policy in enumerate(policies):
        for other in policies[index+1:]:
            assert policy is not other
            assert policy['allowlist'] is not other['allowlist']
            assert policy['blocklist'] is not other['blocklist']


def test_initial_snapshot_is_one_query_and_write_free(baseline):
    before = database_image()
    result = read_one(NOW)
    assert result.revision == 1 and result.bound_owner_id is None
    assert result.confirmed_policy == result.effective_policy == BASE
    assert all(getattr(result, field) is None for field in ['pending_change_id', 'pending_status', 'candidate_policy', 'activated_at', 'rollback_at', 'activation_revision'])
    assert_detached(result)
    with pytest.raises(FrozenInstanceError):
        result.revision = 2
    result.effective_policy['blocklist'].clear()
    assert result.confirmed_policy == BASE
    assert database_image() == before


def test_missing_or_unavailable_state_does_not_create_or_allow(baseline):
    State.objects.all().delete()
    with pytest.raises(service.NetworkStateUnavailable):
        service.load_network_snapshot(NOW)
    assert not State.objects.exists()
    with patch('django.db.models.query.QuerySet.get', side_effect=DatabaseError('private database detail')):
        with pytest.raises(service.NetworkStateUnavailable) as error:
            service.load_network_snapshot(NOW)
    assert 'private' not in str(error.value)


@pytest.mark.parametrize('seconds,expected,status', [(299.999999, CANDIDATE, 'pending'), (300, BASE, 'expired_unreconciled'), (301, BASE, 'expired_unreconciled')])
def test_pending_boundary_selects_fallback_without_worker_or_write(pending, seconds, expected, status):
    before = database_image()
    result = read_one(NOW+timedelta(seconds=seconds))
    change, _ = pending
    assert result.effective_policy == expected and result.pending_status == status
    assert result.confirmed_policy == BASE and result.candidate_policy == CANDIDATE
    assert result.revision == result.activation_revision == 2
    assert result.pending_change_id == change.pk and result.bound_owner_id == change.owner_id
    assert result.activated_at == NOW and result.rollback_at == NOW+timedelta(seconds=300)
    assert_detached(result)
    assert database_image() == before


# These corruptions are legal database updates; cross-row safety is the selector's job.
PERSISTED = [
    ('state', {'confirmed_policy_digest': '0'*64}),
    ('state', {'confirmed_policy': {'allowlist_only': 0, 'allowlist': [], 'blocklist': []}}),
    ('state', {'bound_owner_id': None}), ('state', {'revision': 3}),
    ('change', {'candidate_policy_digest': '0'*64}), ('change', {'fallback_policy_digest': '0'*64}),
    ('change', {'fallback_policy': CANDIDATE, 'fallback_policy_digest': digest(CANDIDATE)}),
    ('change', {'preview_id': None}), ('change', {'actor_id': None}),
    ('change', {'session_digest': None}), ('change', {'epoch': None}), ('change', {'operator_version': None}),
    ('change', {'verified_ip': None}), ('change', {'environment_digest': 'f'*64}),
    ('change', {'confirm_expected_revision': 2}), ('change', {'revert_expected_revision': 2}),
    ('change', {'status': 'confirmed', 'finished_at': NOW, 'terminal_revision': 3}),
    ('preview', {'result_change_id': None}), ('preview', {'session_digest': 'd'*64}),
    ('preview', {'epoch': 1}), ('preview', {'operator_version': 2}), ('preview', {'verified_ip': '192.0.2.2'}),
    ('preview', {'environment_digest': 'e'*64}), ('preview', {'base_revision': 2}),
    ('preview', {'policy': BASE, 'policy_digest': digest(BASE)}), ('preview', {'policy_digest': '0'*64}),
    ('preview', {'request_digest': 'INVALID'}),
    ('preview', {'created_at': NOW+timedelta(seconds=1), 'expires_at': NOW+timedelta(seconds=301)}),
    ('preview', {'created_at': NOW-timedelta(seconds=300), 'expires_at': NOW}),
]


@pytest.mark.parametrize('target,values', PERSISTED)
def test_corrupt_saved_policy_and_pending_links_fail_closed(pending, target, values):
    change, preview = pending
    model, key = {'state': (State, 1), 'change': (Change, change.pk), 'preview': (Preview, preview.pk)}[target]
    model.objects.filter(pk=key).update(**values)
    with pytest.raises(service.NetworkStateUnavailable):
        service.load_network_snapshot(NOW+timedelta(seconds=301))


@pytest.mark.parametrize('target,field', [('change', 'owner_id'), ('preview', 'owner_id'), ('preview', 'actor_id')])
def test_foreign_saved_principal_fails_closed(pending, target, field):
    foreign = get_user_model().objects.create(username='foreign-synthetic') if field == 'actor_id' else Organisation.objects.create(name='Foreign synthetic')
    record = pending[0 if target == 'change' else 1]
    type(record).objects.filter(pk=record.pk).update(**{field: foreign.pk})
    with pytest.raises(service.NetworkStateUnavailable):
        service.load_network_snapshot(NOW)


# Constraints prevent these scalar shapes in normal persisted rows. Probe a complete
# real joined graph in isolation rather than relaxing production constraints.
PROBES = [('state', 'id', 2), ('state', 'revision', True), ('state', 'revision', MAX+1),
    ('change', 'base_revision', 0), ('change', 'activation_revision', 3),
    ('change', 'finished_at', NOW), ('change', 'terminal_revision', 3),
    ('change', 'rollback_at', NOW+timedelta(seconds=299)), ('change', 'activated_at', NOW.replace(tzinfo=None)),
    ('preview', 'expires_at', NOW+timedelta(seconds=300)), ('preview', 'created_at', NOW.replace(tzinfo=None))]
PROBES += [(target, field, value) for target in ['change', 'preview'] for field, value in
    [('epoch', True), ('epoch', -1), ('epoch', MAX+1), ('operator_version', 0), ('operator_version', True),
     ('base_revision', True), ('session_digest', 'A'*64), ('environment_digest', 'x'*64),
     ('verified_ip', '::ffff:192.0.2.1'), ('verified_ip', '2001:0DB8::1'), ('verified_ip', 'fe80::1%eth0')]]


@pytest.mark.parametrize('target,field,value', PROBES)
def test_database_impossible_saved_shapes_fail_closed(pending, target, field, value):
    row = State.objects.select_related('pending_change__preview').get(pk=1)
    graph = {'state': row, 'change': row.pending_change, 'preview': row.pending_change.preview}
    setattr(graph[target], field, value)
    with patch('django.db.models.query.QuerySet.get', return_value=row):
        with pytest.raises(service.NetworkStateUnavailable):
            service.load_network_snapshot(NOW)


def test_expired_corrupt_candidate_still_fails_closed(pending):
    Change.objects.filter(pk=pending[0].pk).update(candidate_policy={'allowlist_only': False, 'allowlist': [], 'blocklist': ['192.0.2.1']})
    with pytest.raises(service.NetworkStateUnavailable):
        service.load_network_snapshot(NOW+timedelta(days=1))


@pytest.mark.parametrize('owner_config', [None, '', 'invalid', str(uuid.UUID(int=1))])
def test_owner_environment_does_not_disable_stored_restrictions(pending, settings, owner_config):
    settings.HMS_SECURITY_ORGANISATION_ID = owner_config
    get_user_model().objects.filter(pk=pending[0].actor_id).update(is_active=False)
    assert read_one(NOW).effective_policy == CANDIDATE


@pytest.mark.parametrize('clock', [None, 1, '2026-10-24', NOW.replace(tzinfo=None)])
def test_naive_clock_is_rejected_and_backwards_clock_is_unavailable(pending, clock):
    with CaptureQueriesContext(connection) as queries, pytest.raises(ValueError):
        service.load_network_snapshot(clock)
    assert len(queries) == 0
    with pytest.raises(service.NetworkStateUnavailable):
        service.load_network_snapshot(NOW-timedelta(microseconds=1))


def test_unreferenced_history_is_not_an_effective_policy(pending):
    change, _ = pending
    State.objects.filter(pk=1).update(pending_change=None)
    Change.objects.filter(pk=change.pk).update(preview=None, status='recovered', actor=None,
        finished_at=NOW, terminal_revision=3, session_digest=None, epoch=None, operator_version=None, verified_ip=None)
    result = read_one(NOW)
    assert result.effective_policy == BASE and result.pending_change_id is None
