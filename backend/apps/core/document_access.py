"""Pure command preparation and separately committed metadata admission.

An admission is neither patient authority nor a disclosure/business result.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone as datetime_timezone
import math
from time import monotonic

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from . import document_authority as authority
from .document_authority import DocumentServiceError
from .document_contracts import (
    DocumentContractError, canonical_uuid, command_fingerprint,
    parse_create, parse_list_query, parse_withdraw,
)
from .models import DocumentMetadataRateWindow, IdentitySecurity


_ERRORS = {
    'validation_error': (400, 'Check the highlighted details.'),
    'not_found': (404, 'This record is unavailable.'),
    'request_too_large': (413, 'This request is too large.'),
    'document_metadata_unavailable': (503, 'Document details are unavailable. Try again later.'),
}


def _fail(code='validation_error'):
    raise DocumentServiceError(code, *_ERRORS[code]) from None


@dataclass(frozen=True)
class _PreparedDocumentCommand:
    operation: str
    patient_id: str = field(repr=False)
    document_id: str | None = field(repr=False)
    key: str | None = field(repr=False)
    payload: tuple | None = field(repr=False)
    query: tuple | None = field(repr=False)
    fingerprint: str | None = field(repr=False)


def _freeze(value):
    if type(value) is dict:
        return tuple((key, _freeze(item)) for key, item in sorted(value.items()))
    if type(value) not in (str, int, type(None)):
        _fail('document_metadata_unavailable')
    return value


def _path(value):
    try:
        return canonical_uuid(value)
    except DocumentContractError:
        _fail('not_found')


def _prepare_document_command(operation: str, patient_id: str, *, document_id: str | None = None,
                              key: str | None = None, body: bytes | None = None,
                              query_pairs: list | tuple = ()) -> _PreparedDocumentCommand:
    """Parse raw scalars only; this value carries no authority or admission proof."""
    if type(operation) is not str or operation not in ('intent.list', 'intent.detail', 'intent.create', 'intent.withdraw'):
        _fail()
    if type(query_pairs) not in (list, tuple) or (body is not None and type(body) is not bytes):
        _fail()
    if ((operation != 'intent.list' and query_pairs)
            or (operation in ('intent.list', 'intent.create') and document_id is not None)
            or (operation in ('intent.list', 'intent.detail') and key is not None)):
        _fail()
    patient = _path(patient_id)
    document = _path(document_id) if operation in ('intent.detail', 'intent.withdraw') else None
    try:
        command_key = canonical_uuid(key) if operation in ('intent.create', 'intent.withdraw') else None
        if body is not None and len(body) > 4096:
            _fail('request_too_large')
        payload, query, fingerprint = None, None, None
        if operation == 'intent.create':
            payload = parse_create(body)
        elif operation == 'intent.withdraw':
            payload = parse_withdraw(body)
        else:
            if body not in (None, b''):
                _fail()
            if operation == 'intent.list':
                query = parse_list_query(query_pairs, patient)
        if payload is not None:
            fingerprint = command_fingerprint(operation, patient, document, payload)
    except DocumentContractError as error:
        # Existing B1 failures are mapped only through this fixed vocabulary.
        if (type(error.code) is str and error.code in ('validation_error', 'request_too_large')
                and type(error.status) is int and type(error.message) is str
                and (error.status, error.message) == _ERRORS[error.code]):
            _fail(error.code)
        _fail('document_metadata_unavailable')
    return _PreparedDocumentCommand(operation, patient, document, command_key,
                                    _freeze(payload), _freeze(query), fingerprint)


@dataclass(frozen=True)
class DocumentAdmission:
    operation: str
    patient_id: str = field(repr=False)
    document_id: str | None = field(repr=False)
    key: str | None = field(repr=False)
    payload: tuple | None = field(repr=False)
    query: tuple | None = field(repr=False)
    fingerprint: str | None = field(repr=False)
    admitted_at: datetime
    operation_started_at: datetime
    monotonic_started_at: float
    _context: authority.DocumentContext = field(repr=False, compare=False)
    _mint: object = field(repr=False, compare=False)


def _validate_document_admission(admission: DocumentAdmission, context: authority.DocumentContext,
                                  operation: str) -> None:
    """Pure issuance/binding check only; future callers must reauthorise work."""
    authority._context(context, operation)
    if (not authority._issued(admission, DocumentAdmission) or admission._context is not context
            or admission.operation != operation
            or admission.operation_started_at != context.operation_started_at
            or admission.monotonic_started_at != context.monotonic_started_at):
        _fail('document_metadata_unavailable')


def _budget(context):
    started, current = context.monotonic_started_at, monotonic()
    now = timezone.now()
    if (type(started) not in (int, float) or type(current) not in (int, float)
            or not math.isfinite(started) or not math.isfinite(current)
            or current < started or current >= started + 5
            or not authority._aware(context.operation_started_at) or not authority._aware(now)
            or now < context.operation_started_at):
        _fail('document_metadata_unavailable')
    return now


def _enabled():
    value = settings.HMS_DOCUMENT_METADATA_ENABLED
    if type(value) is not bool:
        _fail('document_metadata_unavailable')
    return value


def _dependency_guard():
    # Configuration checks precede connection initialisation, let alone domain SQL.
    databases, routers = settings.DATABASES, settings.DATABASE_ROUTERS
    if (type(databases) is not dict or set(databases) != {'default'}
            or type(routers) not in (list, tuple) or routers):
        _fail('document_metadata_unavailable')
    if connection.in_atomic_block or not connection.get_autocommit():
        _fail('document_metadata_unavailable')
    if connection.vendor != 'postgresql' or connection.pg_version < 170000:
        _fail('document_metadata_unavailable')


def _rate_decision(actor_id, row, now):
    """Called only under actor -> existing identity -> rate locks."""
    minute = now.astimezone(datetime_timezone.utc).replace(second=0, microsecond=0)
    if row is None:
        DocumentMetadataRateWindow.objects.using('default').create(
            actor_id=actor_id, window_started_at=minute, admitted_count=1)
        return None
    start, count = row.window_started_at, row.admitted_count
    if (not authority._aware(start) or start.second != 0 or start.microsecond != 0
            or type(count) is not int or not 1 <= count <= 60 or now < start):
        _fail('document_metadata_unavailable')
    end = start + timedelta(minutes=1)
    if now >= end:
        row.window_started_at, row.admitted_count = minute, 1
    elif count < 60:
        row.admitted_count = count + 1
    else:
        return min(60, max(1, math.ceil((end - now).total_seconds())))
    row.save(using='default', update_fields=['window_started_at', 'admitted_count'])
    return None


def _idle_driver(driver):
    # No SQL or reconnect while deciding whether rollback was acknowledged.
    try:
        return (driver is not None and connection.connection is driver and not driver.closed
                and driver.info.transaction_status.name == 'IDLE'
                and not connection.in_atomic_block and not connection.needs_rollback)
    except (AttributeError, DatabaseError):
        return False


def admit_document_command(context: authority.DocumentContext, patient_id: str, *,
                           document_id: str | None = None, key: str | None = None,
                           body: bytes | None = None, query_pairs: list | tuple = ()) -> DocumentAdmission:
    """Commit one actor allowance; no patient/business lookup is performed."""
    try:
        _dependency_guard()
        authority._context(context)
        _budget(context)
        preliminary = authority.preflight_document_authority(context, context.operation)
        _budget(context)
        prepared = _prepare_document_command(context.operation, patient_id, document_id=document_id,
                                              key=key, body=body, query_pairs=query_pairs)
        _budget(context)
        entry_enabled = _enabled()
        network = authority.sample_document_network(context, _budget(context))
        authority.validate_document_selection(context, preliminary, network, _budget(context))
    except DatabaseError:
        _fail('document_metadata_unavailable')

    body_completed, commit_acknowledged, body_error = False, False, None
    driver = connection.connection
    try:
        with transaction.atomic(using='default', durable=True):
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout='2s'")
                    cursor.execute("SET LOCAL statement_timeout='3s'")
                    cursor.execute("SET LOCAL transaction_timeout='5s'")
                _budget(context)
                actor = get_user_model().objects.using('default').select_for_update(
                    no_key=True, of=('self',)).filter(pk=context.actor_id).first()
                _budget(context)
                if actor is None:
                    authority._fail('not_authenticated')
                IdentitySecurity.objects.using('default').select_for_update(
                    of=('self',)).filter(user_id=context.actor_id).first()
                _budget(context)
                row = DocumentMetadataRateWindow.objects.using('default').select_for_update(
                    of=('self',)).filter(actor_id=context.actor_id).first()
                _budget(context)
                authority.sample_document_authority(context, context.operation)
                retry_after = _rate_decision(context.actor_id, row, _budget(context))
                _budget(context)
                with connection.cursor() as cursor:
                    cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
                _budget(context)
                final_authority = authority.sample_document_authority(context, context.operation)
                _budget(context)
                final_network = authority.sample_document_network(context, _budget(context))
                selected_at = _budget(context)
                authority.validate_document_selection(context, final_authority, final_network, selected_at)
                precommit_enabled = _enabled()
                _budget(context)
                # A normal atomic exit may silently roll back a rollback-only
                # transaction; it must never be mistaken for an admitted commit.
                if connection.needs_rollback or connection.closed_in_transaction:
                    _fail('document_metadata_unavailable')
                body_completed = True
            except (DatabaseError, DocumentServiceError) as error:
                body_error = error
                raise
        commit_acknowledged = True
    except (DatabaseError, DocumentServiceError) as error:
        acknowledged_rollback = not body_completed and error is body_error and _idle_driver(driver)
        if not acknowledged_rollback:
            # COMMIT/rollback acknowledgement is uncertain: no token, refund or retry.
            connection.close()
        if acknowledged_rollback and isinstance(error, DocumentServiceError):
            raise
        _fail('document_metadata_unavailable')

    if not commit_acknowledged:
        # Defensive control-flow invariant; normal context exit sets the marker above.
        connection.close()
        _fail('document_metadata_unavailable')
    _budget(context)
    if retry_after is not None:
        raise DocumentServiceError('rate_limited', 429, 'Too many requests. Try again shortly.', retry_after)
    postcommit_enabled = _enabled()
    if not (entry_enabled and precommit_enabled and postcommit_enabled):
        _fail('document_metadata_unavailable')
    _budget(context)
    return authority._issue(DocumentAdmission, prepared.operation, prepared.patient_id, prepared.document_id,
                            prepared.key, prepared.payload, prepared.query, prepared.fingerprint,
                            selected_at, context.operation_started_at, context.monotonic_started_at, context)
