"""CurrentUser permission ceilings; these strings do not activate document routes."""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.core.authorization import current_user
from apps.core.models import Branch, Membership, Organisation


pytestmark = pytest.mark.django_db

PATIENT_READ = {
    'patients.read', 'appointments.read', 'beds.read',
    'admissions.read', 'dashboard.read',
}
RECEPTION = PATIENT_READ | {
    'patients.write', 'appointments.write', 'admissions.write',
    'documents.registration.read', 'documents.registration.write',
}
DOCUMENTS = {'documents.registration.read', 'documents.registration.write'}


@pytest.fixture
def staff():
    organisation = Organisation.objects.create(name='Synthetic document grants')
    branch_a = Branch.objects.create(organisation=organisation, name='A', code='A')
    branch_b = Branch.objects.create(organisation=organisation, name='B', code='B')
    actor = get_user_model().objects.create_user(username='synthetic-document-grants')
    return actor, branch_a, branch_b


def read_current_user(actor):
    # A CurrentUser read must neither manufacture security/network state nor
    # disclose feature readiness through extra top-level fields.
    with CaptureQueriesContext(connection) as queries:
        result = current_user(actor)
    assert all(query['sql'].lstrip().upper().startswith('SELECT') for query in queries)
    assert set(result) == {
        'id', 'username', 'name', 'roles', 'branches',
        'permissions', 'branch_permissions',
    }
    return result


@pytest.mark.parametrize('enabled', [False, True])
def test_reception_current_user_has_exact_grants_independent_of_readiness(staff, settings, enabled):
    actor, branch, _ = staff
    settings.HMS_DOCUMENT_METADATA_ENABLED = enabled
    Membership.objects.create(user=actor, branch=branch, role='reception')

    result = read_current_user(actor)

    assert set(result['permissions']) == RECEPTION
    assert result['branch_permissions'] == {str(branch.pk): sorted(RECEPTION)}
    assert result['roles'] == ['reception']


@pytest.mark.parametrize(('role', 'expected'), [
    ('master_admin', {'platform.read', 'platform.configure', 'platform.staff.manage', 'platform.audit.read'}),
    ('doctor', PATIENT_READ),
    ('nurse', PATIENT_READ),
    ('pharmacist', set()),
    ('accounts', set()),
    ('therapist', set()),
])
def test_other_roles_do_not_gain_document_or_other_permissions(staff, role, expected):
    actor, branch, _ = staff
    Membership.objects.create(user=actor, branch=branch, role=role)

    result = read_current_user(actor)

    assert result['permissions'] == sorted(expected)
    assert result['branch_permissions'] == {str(branch.pk): sorted(expected)}


def test_mixed_reception_b_doctor_a_keeps_document_grants_in_b(staff):
    actor, branch_a, branch_b = staff
    Membership.objects.create(user=actor, branch=branch_a, role='doctor')
    Membership.objects.create(user=actor, branch=branch_b, role='reception')

    result = read_current_user(actor)

    assert set(result['permissions']) == RECEPTION
    assert result['branch_permissions'] == {
        str(branch_a.pk): sorted(PATIENT_READ),
        str(branch_b.pk): sorted(RECEPTION),
    }


def test_inactive_reception_membership_cannot_add_documents_to_doctor(staff):
    actor, branch_a, branch_b = staff
    Membership.objects.create(user=actor, branch=branch_a, role='doctor')
    Membership.objects.create(user=actor, branch=branch_b, role='reception', is_active=False)

    result = read_current_user(actor)

    assert result['permissions'] == sorted(PATIENT_READ)
    assert result['branch_permissions'] == {str(branch_a.pk): sorted(PATIENT_READ)}


def test_reception_revocation_is_visible_without_reusing_cached_grants(staff):
    actor, branch, _ = staff
    membership = Membership.objects.create(user=actor, branch=branch, role='reception')
    read_current_user(actor)
    membership.is_active = False
    membership.save(update_fields=['is_active'])

    result = read_current_user(actor)

    assert result['permissions'] == []
    assert result['branch_permissions'] == {}
    assert result['roles'] == []


def test_inactive_account_has_no_document_grants_despite_active_reception(staff):
    actor, branch, _ = staff
    Membership.objects.create(user=actor, branch=branch, role='reception')
    actor.is_active = False
    actor.save(update_fields=['is_active'])

    result = read_current_user(actor)

    assert result['permissions'] == []
    assert result['branch_permissions'] == {}
    assert result['branches'] == []
