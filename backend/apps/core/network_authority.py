"""Server-created network authority. Reads never manufacture security/session rows."""
from dataclasses import dataclass, field
import hashlib
import math
from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.utils import timezone
from rest_framework.exceptions import APIException
from apps.security.ip_policy import normalise_client_ip
from .models import IdentitySecurity, Membership, Organisation, NetworkOperator, NetworkPolicyState
from .network_environment import configured_owner, environment_snapshot, overlay_allows
from .network_snapshot import load_network_snapshot, NetworkStateUnavailable

_MINT = object()


class NetworkError(APIException):
    def __init__(self, code, status=409, message=None):
        self.status_code = status
        self.default_code = code
        messages = {'not_authenticated': 'Your session ended. Sign in again.', 'permission_denied': 'You do not have access to this action.', 'mfa_enrollment_required': 'Set up an authenticator in Account security before continuing.', 'mfa_step_up_required': 'Verify your identity in Account security before continuing.', 'network_denied': 'Access is not available from this network.', 'network_owner_unavailable': 'Network management is unavailable. Contact your administrator.', 'network_policy_unavailable': 'Network settings are temporarily unavailable.', 'validation_error': 'Please check the supplied fields.', 'not_found': 'The requested change was not found.'}
        super().__init__(message or messages.get(code, 'Network settings changed or expired. Reload status and try again.'), code)


@dataclass(frozen=True)
class NetworkContext:
    actor_id: int
    session_digest: str
    epoch: int
    factor_verified_at: object
    verified_ip: str
    environment_digest: str
    remote_addr: str
    forwarded_for: str | None
    _request: object = field(repr=False, compare=False)
    _mint: object = field(repr=False, compare=False)


def _session_digest(request):
    key = request.session.session_key
    if not isinstance(key, str) or not key:
        raise NetworkError('not_authenticated', 401)
    return hashlib.sha256(key.encode()).hexdigest()


def capture_network_context(request):
    if not request.user.is_authenticated or not request.user.is_active:
        raise NetworkError('not_authenticated', 401)
    environment = environment_snapshot()
    try:
        ip = normalise_client_ip(request.META.get('REMOTE_ADDR', ''), request.META.get('HTTP_X_FORWARDED_FOR'), environment.trusted_proxies)
    except ValueError:
        raise NetworkError('network_denied', 403) from None
    return NetworkContext(request.user.pk, _session_digest(request), request.session.get('auth_epoch', 0), request.session.get('factor_verified_at'), ip, environment.digest, request.META.get('REMOTE_ADDR', ''), request.META.get('HTTP_X_FORWARDED_FOR'), request, _MINT)


def require_network_operator(context, now=None):
    if not isinstance(context, NetworkContext) or context._mint is not _MINT:
        raise NetworkError('not_authenticated', 401)
    now = now or timezone.now()
    user = get_user_model().objects.filter(pk=context.actor_id).first()
    if not user or not user.is_active or _session_digest(context._request) != context.session_digest:
        raise NetworkError('not_authenticated', 401)
    security = IdentitySecurity.objects.filter(user_id=user.pk).first()
    epoch = security.auth_epoch if security else 0
    if type(context.epoch) is not int or context.epoch != epoch or context._request.session.get('auth_epoch', 0) != context.epoch:
        raise NetworkError('not_authenticated', 401)
    # Basic current master authority precedes installation details.
    if not Membership.objects.filter(user_id=user.pk, is_active=True, role='master_admin').exists():
        raise NetworkError('permission_denied', 403)
    owner_id = configured_owner()
    snapshot = load_network_snapshot(now)
    if not owner_id or snapshot.bound_owner_id != owner_id:
        raise NetworkError('network_owner_unavailable', 503)
    if not Membership.objects.filter(user_id=user.pk, is_active=True, role='master_admin', branch__organisation_id=owner_id).exists():
        raise NetworkError('permission_denied', 403)
    operator = NetworkOperator.objects.filter(user_id=user.pk, organisation_id=owner_id, active=True).first()
    if not operator or type(operator.version) is not int or not 1 <= operator.version <= 9007199254740991:
        raise NetworkError('permission_denied', 403)
    if not security or not security.active_ciphertext:
        raise NetworkError('mfa_enrollment_required', 403)
    verified = context.factor_verified_at
    if type(verified) not in (int, float) or not math.isfinite(verified) or not 0 <= now.timestamp()-verified <= 900 or context._request.session.get('factor_verified_at') != verified:
        raise NetworkError('mfa_step_up_required', 403)
    environment = environment_snapshot()
    try:
        ip = normalise_client_ip(context.remote_addr, context.forwarded_for, environment.trusted_proxies)
    except ValueError:
        raise NetworkError('network_denied', 403) from None
    if ip != context.verified_ip or environment.digest != context.environment_digest:
        raise NetworkError('network_preview_invalidated')
    if not environment.allows(ip) or not overlay_allows(snapshot.effective_policy, ip):
        raise NetworkError('network_denied', 403)
    return user, security, owner_id, operator, snapshot


def lock_network_operator(context):
    # Authority before locks is preliminary only; repeat following the complete lock chain.
    _, _, owner_id, _, _ = require_network_operator(context)
    get_user_model().objects.select_for_update(no_key=True).get(pk=context.actor_id)
    IdentitySecurity.objects.select_for_update().get(user_id=context.actor_id)
    Organisation.objects.select_for_update(no_key=True).get(pk=owner_id)
    NetworkOperator.objects.select_for_update().get(user_id=context.actor_id, organisation_id=owner_id)
    state = NetworkPolicyState.objects.select_for_update().get(pk=1)
    require_network_operator(context)
    return state


def network_entitled(user):
    if not user.is_authenticated or not user.is_active:
        return False
    try:
        owner = configured_owner()
        state = load_network_snapshot(timezone.now())
        return bool(owner and state.bound_owner_id == owner and Membership.objects.filter(user_id=user.pk, role='master_admin', is_active=True, branch__organisation_id=owner).exists() and NetworkOperator.objects.filter(user_id=user.pk, organisation_id=owner, active=True).exists())
    except (DatabaseError, NetworkStateUnavailable):
        return False
