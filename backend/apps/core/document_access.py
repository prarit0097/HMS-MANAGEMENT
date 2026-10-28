"""Private pure command preparation for future durable metadata admission.

Durable admission, allowance writes and admission tokens are not implemented.
"""
from dataclasses import dataclass, field

from .document_authority import DocumentServiceError
from .document_contracts import (
    DocumentContractError, canonical_uuid, command_fingerprint,
    parse_create, parse_list_query, parse_withdraw,
)


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
