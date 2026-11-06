"""Portable original-budget boundaries using genuinely issued session contexts."""
import math

import pytest

from apps.core import document_access as access, document_authority as authority
from test_document_metadata_authority import signed


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('started', [0.0, 100.125, 1023.9999999999997, 1024.0, 65535.99999999998])
@pytest.mark.parametrize('position', ['before', 'at', 'after'])
def test_original_budget_representable_deadline(signed, monkeypatch, started, position):
    # Only context capture uses the controlled origin; worker/deadline clocks remain real.
    with monkeypatch.context() as capture_clock:
        capture_clock.setattr(authority.time, 'monotonic', lambda: started)
        context = authority.capture_document_context(signed.request, 'intent.list')
    authority._context(context, 'intent.list')
    deadline = started + 5
    current = {'before': math.nextafter(deadline, -math.inf),
               'at': deadline, 'after': math.nextafter(deadline, math.inf)}[position]
    monkeypatch.setattr(access, 'monotonic', lambda: current)
    if position == 'before':
        assert access._budget(context) >= context.operation_started_at
    else:
        with pytest.raises(authority.DocumentServiceError) as denied:
            access._budget(context)
        assert (denied.value.code, denied.value.status) == ('document_metadata_unavailable', 503)
