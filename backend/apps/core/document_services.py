"""Audited metadata services: admission first, detached disclosure after commit.

Private phase B owns its transaction. An admission alone grants no patient access.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone as datetime_timezone
from hashlib import sha256
import json
import math

from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection, transaction
from django.db.models import Q

from . import document_authority as authority
from . import document_access as access
from .authorization import ROLE_PERMISSIONS
from .document_access import admit_document_command
from .document_authority import DocumentContext, DocumentServiceError
from .document_contracts import encode_cursor
from .models import (DocumentAccessEvent, DocumentIntentReceipt, IdentitySecurity,
                     Membership, Organisation, Patient, PatientDocumentIntent)


@dataclass(frozen=True)
class DocumentServiceResult:
    status: int
    body: bytes = field(repr=False)


def _timestamp(value):
    return value.astimezone(datetime_timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _capabilities(can_write: bool) -> dict:
    return dict(can_create_intent=can_write, can_upload=False, can_download=False,
                upload_categories=[], allowed_media_types=['image/jpeg', 'image/png'],
                max_size_bytes=10485760, max_filename_characters=120)


def _project_intent(record: dict, patient_id: str, branch_id: str, actor_id: int,
                    can_write: bool, selected_at: datetime) -> dict:
    pending = record['status'] == 'pending'
    live = selected_at < record['expires_at']
    creator = record['created_by_id'] == actor_id
    return dict(id=str(record['id']), patient_id=patient_id, branch_id=branch_id,
                category='registration', filename=record['declared_filename'],
                media_type=record['declared_media_type'], size_bytes=record['declared_size_bytes'],
                status='expired' if pending and not live else record['status'],
                version=record['version'], created_at=_timestamp(record['created_at']),
                expires_at=_timestamp(record['expires_at']), is_creator=creator,
                can_withdraw=can_write and creator and pending and live and record['version'] < 2147483647,
                can_upload=False, can_download=False)


def _quota_retry(active_expiries: list, organisation_created: list, now: datetime) -> int | None:
    waits = []
    if len(active_expiries) >= 20:
        waits.append((min(active_expiries) - now).total_seconds())
    if len(organisation_created) >= 1000:
        waits.append((min(organisation_created) + timedelta(hours=1) - now).total_seconds())
    return min(3600, max(1, math.ceil(max(waits)))) if waits else None


def _encode_document_body(payload: dict) -> bytes:
    try:
        body = json.dumps(payload, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError):
        authority._fail()
    if len(body) > 262144:
        authority._fail()
    return body


def list_document_intents(context: DocumentContext, patient_id: str,
                          query_pairs: list | tuple = ()) -> DocumentServiceResult:
    authority._context(context, 'intent.list')
    return _execute(admit_document_command(context, patient_id, query_pairs=query_pairs), 'intent.list')


def get_document_intent(context: DocumentContext, patient_id: str, document_id: str) -> DocumentServiceResult:
    authority._context(context, 'intent.detail')
    return _execute(admit_document_command(context, patient_id, document_id=document_id), 'intent.detail')


def create_document_intent(context: DocumentContext, patient_id: str, key: str, body: bytes) -> DocumentServiceResult:
    authority._context(context, 'intent.create')
    return _execute(admit_document_command(context, patient_id, key=key, body=body), 'intent.create')


def withdraw_document_intent(context: DocumentContext, patient_id: str, document_id: str,
                             key: str, body: bytes) -> DocumentServiceResult:
    authority._context(context, 'intent.withdraw')
    return _execute(admit_document_command(context, patient_id, document_id=document_id, key=key, body=body), 'intent.withdraw')


def _scope(context, patient_id, branch_id, organisation_id, sample):
    """Fresh exact scope and separate write conjunction; no membership locks."""
    descriptor = Patient.objects.using('default').filter(pk=patient_id).values(
        'branch_id', 'branch__organisation_id').first()
    if (descriptor is None or descriptor['branch_id'] != branch_id
            or descriptor['branch__organisation_id'] != organisation_id
            or branch_id not in sample.eligible_branches):
        authority._fail('not_found')
    grants = set()
    for role in Membership.objects.using('default').filter(
            user_id=context.actor_id, branch_id=branch_id, is_active=True).values_list('role', flat=True):
        grants.update(ROLE_PERMISSIONS.get(role, set()))
    if not {'patients.read', 'documents.registration.read'} <= grants:
        authority._fail('not_found')
    return {'patients.read', 'documents.registration.read', 'patients.write', 'documents.registration.write'} <= grants


def _record(intent):
    return {key: getattr(intent, key) for key in (
        'id', 'created_by_id', 'declared_filename', 'declared_media_type', 'declared_size_bytes',
        'status', 'version', 'created_at', 'expires_at')}


def _withdrawable(intent, expected_version, selected_at):
    if intent.status != 'pending' or selected_at >= intent.expires_at:
        authority._fail('intent_state_conflict')
    if intent.version != expected_version or intent.version >= 2147483647:
        authority._fail('version_conflict')


def _business(admission, context):
    """Run under User/identity gates, before final statement snapshots."""
    operation = admission.operation
    sample = authority.sample_document_authority(context, operation)
    descriptor = Patient.objects.using('default').filter(
        pk=admission.patient_id, branch_id__in=sample.eligible_branches).values(
        'branch_id', 'branch__organisation_id').first()
    if descriptor is None:
        authority._fail('not_found')
    branch_id, org_id = descriptor['branch_id'], descriptor['branch__organisation_id']
    org = Organisation.objects.using('default').select_for_update(no_key=True, of=('self',)).filter(pk=org_id).first()
    access._budget(context)
    sample = authority.sample_document_authority(context, operation)
    if org is None:
        authority._fail('not_found')
    _scope(context, admission.patient_id, branch_id, org_id, sample)
    receipt = None
    if admission.key is not None:
        receipt = DocumentIntentReceipt.objects.using('default').select_for_update(no_key=True, of=('self',)).filter(
            actor_id=context.actor_id, operation=operation, key=admission.key).first()
    patient = Patient.objects.using('default').select_for_update(no_key=True, of=('self',)).filter(pk=admission.patient_id).first()
    access._budget(context)
    if patient is None or patient.branch_id != branch_id:
        authority._fail('not_found')
    _scope(context, patient.pk, branch_id, org_id, sample)
    if operation != 'intent.withdraw' and receipt is not None and receipt.fingerprint != admission.fingerprint:
        authority._fail('idempotency_conflict')
    intents = PatientDocumentIntent.objects.using('default')
    locked = intents.select_for_update(no_key=True, of=('self',))
    has_more, next_cursor, original_withdrawal = False, None, None
    if operation == 'intent.list':
        query = dict(admission.query)
        selection = intents.filter(patient_id=patient.pk)
        if query['cursor'] is not None:
            cursor = dict(query['cursor'])
            created = datetime.fromisoformat(cursor['created_at'].replace('Z', '+00:00'))
            selection = selection.filter(Q(created_at__lt=created) | Q(created_at=created, id__lt=cursor['id']))
        ids = list(selection.order_by('-created_at', '-id').values_list('id', flat=True)[:query['limit'] + 1])
        has_more = len(ids) > query['limit']
        ids = ids[:query['limit']]
        rows = list(locked.filter(patient_id=patient.pk, pk__in=ids).order_by('id'))
        by_id = {row.pk: row for row in rows}
        if len(by_id) != len(ids):
            authority._fail()
        rows = [by_id[value] for value in ids]
        if has_more:
            last = rows[-1]
            next_cursor = encode_cursor(str(patient.pk), _timestamp(last.created_at), str(last.pk))
    else:
        target = (admission.document_id if operation == 'intent.withdraw' else
                  receipt.result_id if receipt is not None else admission.document_id)
        intent = locked.filter(patient_id=patient.pk, pk=target).first() if target is not None else None
        if operation == 'intent.withdraw':
            if intent is None:
                authority._fail('not_found')
            if intent.created_by_id != context.actor_id:
                authority._fail('permission_denied')
            if receipt is not None and receipt.fingerprint != admission.fingerprint:
                authority._fail('idempotency_conflict')
        if receipt is not None:
            if (intent is None or intent.patient_id != patient.pk
                    or (operation == 'intent.create' and intent.created_by_id != context.actor_id)
                    or (operation == 'intent.withdraw' and receipt.result_id != intent.pk)):
                authority._fail()
        elif operation != 'intent.create' and (intent is None or intent.patient_id != patient.pk):
            authority._fail('not_found')
        payload = dict(admission.payload) if admission.payload is not None else None
        now = access._budget(context)
        if operation == 'intent.create' and receipt is None:
            active = list(intents.filter(patient_id=patient.pk, status='pending', expires_at__gt=now).order_by(
                'expires_at', 'id').values_list('expires_at', flat=True)[:20])
            rolling = list(intents.filter(patient__branch__organisation_id=org_id, created_at__gt=now-timedelta(hours=1)).order_by(
                'created_at', 'id').values_list('created_at', flat=True)[:1000])
            retry = _quota_retry(active, rolling, now)
            if retry is not None:
                raise DocumentServiceError('rate_limited', 429, 'Too many requests. Try again shortly.', retry)
            intent = intents.create(patient=patient, created_by_id=context.actor_id, category='registration',
                declared_filename=payload['filename'], declared_media_type=payload['media_type'],
                declared_size_bytes=payload['size_bytes'], declared_sha256=payload['sha256'],
                created_at=now, expires_at=now+timedelta(minutes=30))
        elif operation == 'intent.withdraw' and receipt is None:
            _withdrawable(intent, payload['expected_version'], now)
            original_withdrawal = _record(intent)
            intent.status, intent.version = 'withdrawn', intent.version + 1
            intent.withdrawn_at, intent.withdrawn_by_id = now, context.actor_id
            intent.withdrawal_reason = payload['reason']
            intent.save(using='default', update_fields=['status', 'version', 'withdrawn_at', 'withdrawn_by', 'withdrawal_reason'])
        if operation in ('intent.create', 'intent.withdraw') and receipt is None:
            DocumentIntentReceipt.objects.using('default').create(actor_id=context.actor_id, operation=operation,
                key=admission.key, fingerprint=admission.fingerprint, result=intent)
        rows = [intent]
    # Linkage is enforced explicitly before the required event write.
    if any(row.patient_id != patient.pk for row in rows):
        authority._fail()
    ids = sorted(str(row.pk) for row in rows)
    event_operation = operation + '_result' if operation in ('intent.create', 'intent.withdraw') else operation
    DocumentAccessEvent.objects.using('default').create(actor_id=context.actor_id, patient=patient,
        document=None if operation == 'intent.list' else rows[0], operation=event_operation,
        result_count=len(rows), projection_sha256=sha256(json.dumps(ids, separators=(',', ':')).encode('utf-8')).hexdigest())
    return patient, branch_id, org_id, rows, has_more, next_cursor, original_withdrawal


def _execute(admission, expected_operation):
    context = admission._context
    access._validate_document_admission(admission, context, expected_operation)
    access._dependency_guard()
    access._budget(context)
    if not access._enabled():
        authority._fail()
    body_completed, body_error = False, None
    driver = connection.connection
    try:
        with transaction.atomic(using='default', durable=True):
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout='2s'")
                    cursor.execute("SET LOCAL statement_timeout='3s'")
                    cursor.execute("SET LOCAL transaction_timeout='5s'")
                actor = get_user_model().objects.using('default').select_for_update(no_key=True, of=('self',)).filter(pk=context.actor_id).first()
                access._budget(context)
                if actor is None:
                    authority._fail('not_authenticated')
                IdentitySecurity.objects.using('default').select_for_update(of=('self',)).filter(user_id=context.actor_id).first()
                access._budget(context)
                patient, branch, org, rows, has_more, next_cursor, original = _business(admission, context)
                with connection.cursor() as cursor:
                    cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
                access._budget(context)
                sample = authority.sample_document_authority(context, expected_operation)
                can_write = _scope(context, patient.pk, branch, org, sample)
                network = authority.sample_document_network(context, access._budget(context))
                selected_at = access._budget(context)
                authority.validate_document_selection(context, sample, network, selected_at)
                if original is not None:
                    if selected_at >= original['expires_at']:
                        authority._fail('intent_state_conflict')
                    if original['version'] != dict(admission.payload)['expected_version'] or original['version'] >= 2147483647:
                        authority._fail('version_conflict')
                if expected_operation in ('intent.create', 'intent.withdraw') and not can_write:
                    authority._fail('not_found')
                if not access._enabled():
                    authority._fail()
                projected = [_project_intent(_record(row), str(patient.pk), str(branch), context.actor_id, can_write, selected_at) for row in rows]
                payload = dict(server_time=_timestamp(selected_at), capabilities=_capabilities(can_write))
                if expected_operation == 'intent.list':
                    payload.update(results=projected, has_more=has_more, next_cursor=next_cursor)
                else:
                    payload['document'] = projected[0]
                body = _encode_document_body(payload)
                access._budget(context)
                if connection.needs_rollback or connection.closed_in_transaction:
                    authority._fail()
                body_completed = True
            except (DatabaseError, DocumentServiceError) as error:
                body_error = error
                raise
    except (DatabaseError, DocumentServiceError) as error:
        acknowledged_rollback = not body_completed and error is body_error and access._idle_driver(driver)
        if not acknowledged_rollback:
            connection.close()
        if acknowledged_rollback and isinstance(error, DocumentServiceError):
            raise
        authority._fail()
    if not access._idle_driver(driver):
        connection.close()
        authority._fail()
    access._budget(context)
    if not access._enabled():
        authority._fail()
    access._budget(context)
    return DocumentServiceResult(201 if expected_operation == 'intent.create' else 200, body)
