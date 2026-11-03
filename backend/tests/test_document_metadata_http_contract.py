"""First literal HTTP RED batch: missing routes fail assertions, not imports.

These are initial rejection/dispatch cases, not the entire frozen B3 matrix.
"""
import pytest
from rest_framework.test import APIClient

from document_http_fixtures import (http_workspace, route, request, metadata_counts,
    local_headers, CREATE_BODY)

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize('shape,allow', [('collection', 'GET, POST'), ('detail', 'GET'), ('withdraw', 'POST')])
@pytest.mark.parametrize('method', ['HEAD', 'OPTIONS', 'PUT', 'PATCH', 'DELETE'])
def test_unsupported_methods_require_authority_then_fixed405_without_admission(http_workspace, shape, allow, method):
    before = metadata_counts()
    response = request(http_workspace, method, shape)
    assert response.status_code == 405
    local_headers(response, allow)
    if method == 'HEAD':
        assert response.content == b''
    else:
        assert response.json() == {'code': 'method_not_allowed', 'message': 'This action is unavailable.'}
    assert metadata_counts() == before


@pytest.mark.parametrize('shape', ['collection', 'detail', 'withdraw'])
@pytest.mark.parametrize('role', ['master_admin', 'doctor', 'nurse', None])
def test_global_action_denial_precedes_unsupported_method_without_object_disclosure(http_workspace, shape, role):
    if role is None:
        http_workspace.membership.delete()
    else:
        http_workspace.membership.role = role
        http_workspace.membership.save(update_fields=['role'])
    before = metadata_counts()
    response = request(http_workspace, 'OPTIONS', shape)
    assert response.status_code == 403
    assert response.json() == {'code': 'permission_denied', 'message': 'You do not have access to this action.'}
    local_headers(response)
    assert metadata_counts() == before


@pytest.mark.parametrize('shape,method', [('collection', 'GET'), ('collection', 'POST'), ('detail', 'GET'), ('withdraw', 'POST')])
def test_anonymous_local403_has_distinct_safe_message(http_workspace, shape, method):
    client = APIClient(enforce_csrf_checks=True)
    before = metadata_counts()
    response = client.generic(method, route(http_workspace, shape), data=CREATE_BODY if method == 'POST' else b'', content_type='application/json')
    assert response.status_code == 403
    assert response.json() == {'code': 'not_authenticated', 'message': 'Sign in to continue.'}
    local_headers(response)
    assert metadata_counts() == before


def test_registered_post_uses_real_csrf_before_admission(http_workspace):
    before = metadata_counts()
    response = request(http_workspace, 'POST', csrf=False)
    assert response.status_code == 403
    assert response.json() == {'code': 'csrf_failed', 'message': 'Refresh the page and try again.'}
    local_headers(response)
    assert metadata_counts() == before


def test_content_subpath_stays_unregistered(http_workspace):
    before = metadata_counts()
    response = http_workspace.client.get(route(http_workspace, 'detail') + 'content/')
    assert response.status_code == 404
    assert metadata_counts() == before
