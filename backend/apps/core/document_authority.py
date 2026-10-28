"""Read-only document authority samples; callers own transactions and locks.

These helpers do not admit an operation, inspect patients, or grant disclosure.
Samples describe observed state, rather than cancelling later logout/policy writes.
"""
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from hmac import compare_digest
import re
import time
from uuid import UUID
import weakref

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection
from django.http import HttpRequest
from django.utils import timezone
from django.utils.functional import SimpleLazyObject, empty

from apps.security.ip_policy import evaluate_ip, normalise_client_ip
from .authorization import ROLE_PERMISSIONS
from .models import IdentitySecurity, Membership
from .network_environment import environment_snapshot
from .network_snapshot import NetworkStateUnavailable, load_network_snapshot


_ERRORS = {
    'not_authenticated': (401, 'Your session ended. Sign in again.'),
    'permission_denied': (403, 'You do not have access to this action.'),
    'network_denied': (403, 'Access is not available from this network. Contact your administrator.'),
    'document_metadata_unavailable': (503, 'Document details are unavailable. Try again later.'),
}
_OPERATIONS = ('intent.list', 'intent.detail', 'intent.create', 'intent.withdraw')
_BACKEND = 'django.contrib.auth.backends.ModelBackend'
_MINT = object()
PolicyRules = tuple[bool, tuple[str, ...], tuple[str, ...]]


class DocumentServiceError(Exception):
    def __init__(self, code: str, status: int, message: str, retry_after: int | None = None):
        if (type(code) is not str or code not in _ERRORS or type(status) is not int
                or type(message) is not str or (status, message) != _ERRORS[code]
                or retry_after is not None):
            raise ValueError('Invalid document service error')
        self.code, self.status, self.message, self.retry_after = code, status, message, None
        super().__init__(message)


def _fail(code='document_metadata_unavailable'):
    raise DocumentServiceError(code, *_ERRORS[code]) from None


class _Proof:
    def __init__(self):
        self.mint = _MINT
        self.target = lambda: None


def _issue(cls, *args):
    proof = _Proof()
    value = cls(*args, proof)
    proof.target = weakref.ref(value)
    return value


def _issued(value, cls):
    return (type(value) is cls and type(value._mint) is _Proof
            and value._mint.mint is _MINT and value._mint.target() is value)


@dataclass(frozen=True)
class DocumentContext:
    actor_id: int
    captured_epoch: int | None
    operation: str
    session_digest: str = field(repr=False)
    remote_addr: str = field(repr=False)
    forwarded_for: str | None = field(repr=False)
    verified_ip: str = field(repr=False)
    environment_digest: str = field(repr=False)
    operation_started_at: datetime
    monotonic_started_at: float
    _request: HttpRequest = field(repr=False, compare=False)
    _mint: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class DocumentAuthoritySample:
    actor_id: int
    captured_epoch: int | None
    operation: str
    expires_at: datetime
    eligible_branches: frozenset[UUID]
    sampled_at: datetime
    _context: DocumentContext = field(repr=False, compare=False)
    _mint: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class DocumentNetworkSample:
    environment_digest: str = field(repr=False)
    verified_ip: str = field(repr=False)
    environment_policy: PolicyRules = field(repr=False)
    confirmed_policy: PolicyRules = field(repr=False)
    candidate_policy: PolicyRules | None = field(repr=False)
    pending_change_id: UUID | None = field(repr=False)
    activated_at: datetime | None = field(repr=False)
    rollback_at: datetime | None = field(repr=False)
    sampled_at: datetime
    _context: DocumentContext = field(repr=False, compare=False)
    _mint: object = field(repr=False, compare=False)


def _aware(value):
    return isinstance(value, datetime) and timezone.is_aware(value)


def _epoch(data):
    if 'auth_epoch' not in data:
        return None
    value = data['auth_epoch']
    if type(value) is not int or value < 0:
        _fail('not_authenticated')
    return value


def _live(request):
    if not isinstance(request, HttpRequest):
        _fail('not_authenticated')
    store = getattr(request, 'session', None)
    if type(store) is not SessionStore:
        _fail('not_authenticated')
    key = store.session_key
    if type(key) is not str or re.fullmatch('[a-z0-9]{32}', key) is None:
        _fail('not_authenticated')
    cache = store.__dict__.get('_session_cache')
    if type(cache) is not dict:
        _fail('not_authenticated')
    actor = getattr(request, 'user', None)
    if isinstance(actor, SimpleLazyObject):
        actor = actor.__dict__.get('_wrapped', empty)
        if actor is empty:
            _fail('not_authenticated')
    if not isinstance(actor, get_user_model()) or not actor.pk:
        _fail('not_authenticated')
    return store, key, actor.pk, _epoch(cache)


def _configuration():
    if (settings.SESSION_ENGINE != 'django.contrib.sessions.backends.db'
            or settings.AUTHENTICATION_BACKENDS != [_BACKEND]):
        _fail()


def _authentication(request, now, context=None):
    _configuration()
    store, key, actor_id, epoch = _live(request)
    digest = sha256(key.encode()).hexdigest()
    if context is not None and (actor_id != context.actor_id or epoch != context.captured_epoch
                               or not compare_digest(digest, context.session_digest)):
        _fail('not_authenticated')
    row = Session.objects.filter(session_key=key).first()
    if row is None or not _aware(row.expire_date) or row.expire_date <= now:
        _fail('not_authenticated')
    data = store.decode(row.session_data)
    if type(data) is not dict or data.get('_auth_user_backend') != _BACKEND:
        _fail('not_authenticated')
    try:
        persisted_id = get_user_model()._meta.pk.to_python(data['_auth_user_id'])
    except (KeyError, ValueError, TypeError, OverflowError, ValidationError):
        _fail('not_authenticated')
    if persisted_id != actor_id or _epoch(data) != epoch:
        _fail('not_authenticated')
    user = ModelBackend().get_user(persisted_id)
    supplied_hash = data.get('_auth_user_hash')
    if user is None or not user.is_active or type(supplied_hash) is not str or not supplied_hash:
        _fail('not_authenticated')
    # Compare all configured alternatives without rotating or rewriting the session.
    valid = False
    try:
        for expected in (user.get_session_auth_hash(), *user.get_session_auth_fallback_hash()):
            valid |= compare_digest(supplied_hash, expected)
    except TypeError:
        _fail('not_authenticated')
    if not valid:
        _fail('not_authenticated')
    current_epoch = IdentitySecurity.objects.filter(user_id=actor_id).values_list('auth_epoch', flat=True).first()
    current_epoch = 0 if current_epoch is None else current_epoch
    if type(current_epoch) is not int or current_epoch < 0 or (0 if epoch is None else epoch) != current_epoch:
        _fail('not_authenticated')
    return actor_id, epoch, digest, row.expire_date


def _branches(actor_id, operation):
    required = ['patients.read', 'documents.registration.read']
    if operation in ('intent.create', 'intent.withdraw'):
        required += ['patients.write', 'documents.registration.write']
    grants = {action: set() for action in required}
    for branch, role in Membership.objects.filter(user_id=actor_id, is_active=True).values_list('branch_id', 'role'):
        for action in required:
            if action in ROLE_PERMISSIONS.get(role, set()):
                grants[action].add(branch)
    branches = frozenset.intersection(*(frozenset(values) for values in grants.values()))
    if not branches:
        _fail('permission_denied')
    return branches


def _context(context, operation=None):
    if (not _issued(context, DocumentContext) or context.operation not in _OPERATIONS
            or (operation is not None and operation != context.operation)):
        _fail()


def _environment(remote, forwarded):
    try:
        environment = environment_snapshot()
        ip = normalise_client_ip(remote, forwarded, environment.trusted_proxies)
    except (NetworkStateUnavailable, ValueError, TypeError, AttributeError, OverflowError):
        _fail()
    return environment, ip


def capture_document_context(request: HttpRequest, operation: str) -> DocumentContext:
    if connection.in_atomic_block or not connection.get_autocommit() or operation not in _OPERATIONS:
        _fail()
    started, monotonic = timezone.now(), time.monotonic()
    if not _aware(started):
        _fail()
    try:
        actor, epoch, digest, _ = _authentication(request, started)
        _branches(actor, operation)
    except DatabaseError:
        _fail()
    remote = request.META.get('REMOTE_ADDR', '')
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if type(remote) is not str or (forwarded is not None and type(forwarded) is not str):
        _fail()
    environment, ip = _environment(remote, forwarded)
    if not environment.allows(ip):
        _fail('network_denied')
    return _issue(DocumentContext, actor, epoch, operation, digest, remote, forwarded,
                  ip, environment.digest, started, monotonic, request)


def sample_document_authority(context: DocumentContext, operation: str) -> DocumentAuthoritySample:
    _context(context, operation)
    if not connection.in_atomic_block and connection.get_autocommit():
        _fail()
    try:
        actor, epoch, _, expires = _authentication(context._request, timezone.now(), context)
        branches = _branches(actor, operation)
    except DatabaseError:
        _fail()
    sampled = timezone.now()
    if not _aware(sampled) or sampled < context.operation_started_at:
        _fail()
    return _issue(DocumentAuthoritySample, actor, epoch, operation, expires, branches, sampled, context)


def _rules(mode, allowed, blocked):
    rules = (mode, tuple(allowed), tuple(blocked))
    if not _rules_shape(rules):
        _fail()
    return rules


def _rules_shape(rules):
    return (type(rules) is tuple and len(rules) == 3 and type(rules[0]) is bool
            and all(type(part) is tuple and all(type(item) is str for item in part) for part in rules[1:]))


def sample_document_network(context: DocumentContext, now: datetime) -> DocumentNetworkSample:
    _context(context)
    if not _aware(now) or now < context.operation_started_at:
        _fail()
    _, key, actor, epoch = _live(context._request)
    if (actor != context.actor_id or epoch != context.captured_epoch
            or not compare_digest(sha256(key.encode()).hexdigest(), context.session_digest)):
        _fail('not_authenticated')
    environment, ip = _environment(context.remote_addr, context.forwarded_for)
    if ip != context.verified_ip or environment.digest != context.environment_digest:
        _fail()
    if not environment.allows(ip):
        _fail('network_denied')
    try:
        snapshot = load_network_snapshot(now)
        confirmed = _rules(
            snapshot.confirmed_policy['allowlist_only'], snapshot.confirmed_policy['allowlist'], snapshot.confirmed_policy['blocklist'])
        candidate = None if snapshot.candidate_policy is None else _rules(
            snapshot.candidate_policy['allowlist_only'], snapshot.candidate_policy['allowlist'], snapshot.candidate_policy['blocklist'])
    except (NetworkStateUnavailable, DatabaseError, KeyError, TypeError, ValueError, AttributeError):
        _fail()
    return _issue(DocumentNetworkSample, environment.digest, ip,
                  _rules(environment.allowlist_only, environment.allowlist, environment.blocklist),
                  confirmed, candidate, snapshot.pending_change_id, snapshot.activated_at,
                  snapshot.rollback_at, now, context)


def validate_document_selection(context: DocumentContext, authority_sample: DocumentAuthoritySample,
                                network_sample: DocumentNetworkSample, selected_at: datetime) -> None:
    _context(context)
    auth, network = authority_sample, network_sample
    if (not _issued(auth, DocumentAuthoritySample) or not _issued(network, DocumentNetworkSample)
            or auth._context is not context or network._context is not context
            or auth.actor_id != context.actor_id or auth.captured_epoch != context.captured_epoch
            or auth.operation != context.operation or network.environment_digest != context.environment_digest
            or network.verified_ip != context.verified_ip):
        _fail()
    if (not all(_aware(value) for value in (selected_at, context.operation_started_at,
                                          auth.sampled_at, network.sampled_at, auth.expires_at))
            or selected_at < max(context.operation_started_at, auth.sampled_at, network.sampled_at)
            or auth.sampled_at < context.operation_started_at or network.sampled_at < context.operation_started_at
            or type(auth.eligible_branches) is not frozenset or not auth.eligible_branches
            or any(type(branch) is not UUID for branch in auth.eligible_branches)
            or not _rules_shape(network.environment_policy) or not _rules_shape(network.confirmed_policy)):
        _fail()
    if selected_at >= auth.expires_at:
        _fail('not_authenticated')
    policy = network.confirmed_policy
    if network.pending_change_id is None:
        if any(value is not None for value in (network.candidate_policy, network.activated_at, network.rollback_at)):
            _fail()
    else:
        if (type(network.pending_change_id) is not UUID or not _rules_shape(network.candidate_policy)
                or not _aware(network.activated_at) or not _aware(network.rollback_at)
                or network.activated_at >= network.rollback_at or selected_at < network.activated_at):
            _fail()
        if selected_at < network.rollback_at:
            policy = network.candidate_policy
    for rules in (network.environment_policy, policy):
        if not evaluate_ip(network.verified_ip, rules[1], rules[2], rules[0]):
            _fail('network_denied')
