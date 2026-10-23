from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import Membership, Branch

READ = {'patients.read', 'appointments.read', 'beds.read', 'admissions.read', 'dashboard.read'}
ROLE_PERMISSIONS = {'reception': READ | {'patients.write', 'appointments.write', 'admissions.write'}, 'doctor': READ, 'nurse': READ, 'master_admin': {'platform.read', 'platform.configure', 'platform.staff.manage'}, 'pharmacist': set(), 'accounts': set(), 'therapist': set()}

def branch_ids(user, action):
    if not user.is_authenticated or not user.is_active:
        return set()
    roles = [role for role, permissions in ROLE_PERMISSIONS.items() if action in permissions]
    return set(Membership.objects.filter(user=user, is_active=True, role__in=roles).values_list('branch_id', flat=True))

def permitted_branches(user, action, selected=None):
    ids = branch_ids(user, action)
    if not ids:
        raise PermissionDenied('You do not have access to this action.')
    if selected:
        from uuid import UUID
        try:
            selected = UUID(str(selected))
        except ValueError:
            raise ValidationError({'branch': 'Select a valid branch.'})
        if selected not in ids:
            raise PermissionDenied('You do not have access to this branch.')
        return {selected}
    return ids

def current_user(user):
    memberships = list(Membership.objects.filter(user=user, is_active=True).select_related('branch')) if user.is_authenticated and user.is_active else []
    roles = sorted({m.role for m in memberships})
    branches = {str(m.branch_id): {'id': str(m.branch_id), 'name': m.branch.name, 'code': m.branch.code} for m in memberships}
    permissions = sorted(set().union(*(ROLE_PERMISSIONS.get(role, set()) for role in roles)))
    branch_permissions = {branch: set() for branch in branches}
    for membership in memberships:
        branch_permissions[str(membership.branch_id)].update(ROLE_PERMISSIONS.get(membership.role, set()))
    return {'id': user.pk, 'username': user.username, 'name': user.get_full_name() or user.username, 'roles': roles, 'branches': list(branches.values()), 'permissions': permissions, 'branch_permissions': {branch: sorted(grants) for branch, grants in branch_permissions.items()}}
