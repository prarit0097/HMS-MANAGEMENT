"""Bounded arithmetic: impossible deadlines fail closed before any write."""
from datetime import datetime, timedelta, timezone as dt_timezone
import uuid
import pytest
from django.test import RequestFactory
from apps.core import network_access
from apps.core.network_authority import capture_network_context, require_network_operator, NetworkError
from apps.core.models import NetworkPolicyState, NetworkPolicyPreview, NetworkPolicyEvent
from tests.test_network_access_api import manager, preview, OPEN

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('operation', ['preview', 'activate'])
def test_deadline_overflow_maps_unavailable_without_business_writes(manager, monkeypatch, operation):
    client, user, *_ = manager
    response = preview(client, policy=OPEN)
    assert response.status_code == 201
    saved = NetworkPolicyPreview.objects.get(pk=response.json()['preview_id'])
    request = RequestFactory().post('/api/v1/platform/network-policy/previews/', REMOTE_ADDR='127.0.0.1')
    request.user = user
    request.session = client.session
    context = capture_network_context(request)
    authority = require_network_operator(context)
    high = datetime.max.replace(tzinfo=dt_timezone.utc)
    NetworkPolicyPreview.objects.filter(pk=saved.pk).update(created_at=high-timedelta(seconds=300), expires_at=high)
    # Isolate arithmetic from real session expiry: all persistence below is real.
    monkeypatch.setattr(network_access, 'require_network_operator', lambda context: authority)
    monkeypatch.setattr(network_access, '_run', lambda context, callback, **kwargs: callback(NetworkPolicyState.objects.get(pk=1)))
    monkeypatch.setattr('django.utils.timezone.now', lambda: high-timedelta(seconds=1))
    with pytest.raises(NetworkError) as error:
        if operation == 'preview':
            network_access.preview_network_policy(context, 1, OPEN, 'Synthetic high clock', str(uuid.uuid4()))
        else:
            network_access.activate_network_preview(context, str(saved.pk), 1)
    assert error.value.status_code == 503
    assert NetworkPolicyState.objects.get(pk=1).revision == 1
    assert NetworkPolicyPreview.objects.count() == 1
    assert not NetworkPolicyEvent.objects.exists()
