"""Portable B2b RED: pure projections confer no authority or persistence."""
from datetime import datetime, timedelta, timezone
from importlib import import_module

import pytest

from apps.core.document_authority import DocumentServiceError


NOW = datetime(2026, 11, 2, 12, 0, 0, 123456, tzinfo=timezone.utc)
PATIENT = 'a1111111-1111-4111-8111-111111111111'
DOCUMENT = 'b2222222-2222-4222-8222-222222222222'
BRANCH = 'c3333333-3333-4333-8333-333333333333'


def service():
    return import_module('apps.core.document_services')


@pytest.mark.parametrize('code,message', [
    ('idempotency_conflict', 'This request could not be repeated. Refresh before continuing.'),
    ('version_conflict', 'The record changed. Refresh before continuing.'),
    ('intent_state_conflict', 'This request can no longer be withdrawn.'),
])
def test_exact_conflict_vocabulary(code, message):
    error = DocumentServiceError(code, 409, message)
    assert (error.code, error.status, error.message, error.retry_after) == (code, 409, message, None)
    for status, text, retry in [(400, message, None), (409, 'private detail', None), (409, message, 1)]:
        with pytest.raises(ValueError):
            DocumentServiceError(code, status, text, retry)


@pytest.mark.parametrize('retry', [1, 60, 61, 3599, 3600])
def test_generic_quota_retry_range(retry):
    error = DocumentServiceError('rate_limited', 429, 'Too many requests. Try again shortly.', retry)
    assert error.retry_after == retry


@pytest.mark.parametrize('retry', [None, False, True, -1, 0, 3601, 1.0, '1'])
def test_generic_retry_rejects_noninteger_or_outside_range(retry):
    with pytest.raises(ValueError):
        DocumentServiceError('rate_limited', 429, 'Too many requests. Try again shortly.', retry)


@pytest.mark.parametrize('write', [False, True])
def test_closed_capabilities_are_fresh_detached_values(write):
    api = service()
    expected = dict(can_create_intent=write, can_upload=False, can_download=False,
                    upload_categories=[], allowed_media_types=['image/jpeg', 'image/png'],
                    max_size_bytes=10485760, max_filename_characters=120)
    first = api._capabilities(write)
    assert first == expected
    first['allowed_media_types'].clear()
    first['upload_categories'].append('forged')
    assert api._capabilities(write) == expected


@pytest.mark.parametrize('stored,offset,creator,write,version,status,withdraw', [
    ('pending', -1, True, True, 1, 'pending', True),
    ('pending', 0, True, True, 1, 'expired', False),
    ('pending', 1, True, True, 1, 'expired', False),
    ('pending', -1, False, True, 1, 'pending', False),
    ('pending', -1, True, False, 1, 'pending', False),
    ('pending', -1, True, True, 2147483647, 'pending', False),
    ('withdrawn', -1, True, True, 2, 'withdrawn', False),
    ('withdrawn', 1, True, True, 2, 'withdrawn', False),
])
def test_projection_closed_fields_exact_expiry_and_incrementability(stored, offset, creator, write, version, status, withdraw):
    record = dict(id=DOCUMENT, created_by_id=7, declared_filename='synthetic.png',
                  declared_media_type='image/png', declared_size_bytes=128,
                  status=stored, version=version, created_at=NOW-timedelta(minutes=30), expires_at=NOW)
    before = record.copy()
    result = service()._project_intent(record, PATIENT, BRANCH, 7 if creator else 8, write,
                                       NOW+timedelta(microseconds=offset))
    assert result == dict(id=DOCUMENT, patient_id=PATIENT, branch_id=BRANCH, category='registration',
                          filename='synthetic.png', media_type='image/png', size_bytes=128,
                          status=status, version=version, created_at='2026-11-02T11:30:00.123456Z',
                          expires_at='2026-11-02T12:00:00.123456Z', is_creator=creator,
                          can_withdraw=withdraw, can_upload=False, can_download=False)
    assert record == before


def test_projection_normalizes_non_utc_aware_timestamps():
    record = dict(id=DOCUMENT, created_by_id=7, declared_filename='synthetic.png',
                  declared_media_type='image/png', declared_size_bytes=128, status='pending', version=1,
                  created_at=NOW.astimezone(timezone(timedelta(hours=5, minutes=30))),
                  expires_at=(NOW+timedelta(minutes=30)).astimezone(timezone(timedelta(hours=5, minutes=30))))
    result = service()._project_intent(record, PATIENT, BRANCH, 7, True, NOW)
    assert result['created_at'] == '2026-11-02T12:00:00.123456Z'
    assert result['expires_at'] == '2026-11-02T12:30:00.123456Z'


@pytest.mark.parametrize('active_count,org_count,active_wait,org_wait,expected', [
    (0, 0, 0, 0, None), (19, 999, 10, 20, None), (20, 0, 0.1, 0, 1),
    (20, 999, 1.1, 20, 2), (0, 1000, 0, 30.1, 31),
    (20, 1000, 20, 40, 40), (20, 1000, 40, 20, 40),
    (20, 0, 5000, 0, 3600), (0, 1000, 0, 3600, 3600),
])
def test_quota_threshold_ceiling_maximum_and_clamp(active_count, org_count, active_wait, org_wait, expected):
    active = [NOW+timedelta(seconds=active_wait+i) for i in range(active_count)]
    created = [NOW-timedelta(hours=1)+timedelta(seconds=org_wait+i) for i in range(org_count)]
    active_before, created_before = active.copy(), created.copy()
    assert service()._quota_retry(active, created, NOW) == expected
    assert active == active_before and created == created_before
