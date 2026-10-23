"""Run via manage.py shell with a root-only bootstrap environment; never print secrets."""
import os
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.core.models import Organisation, Branch, Membership, Bed

if os.environ.get('HMS_ENV') != 'production' or os.environ.get('HMS_PREVIEW_BOOTSTRAP') != '1':
    raise RuntimeError('Explicit production preview bootstrap flag required.')
username = os.environ['HMS_PREVIEW_USER']
password = os.environ['HMS_PREVIEW_PASSWORD']
with transaction.atomic():
    if get_user_model().objects.filter(username=username).exists():
        raise RuntimeError('Preview user already exists; refusing password reset.')
    organisation = Organisation.objects.create(name='The Circadian Rhythm Hospital — PREVIEW')
    branch = Branch.objects.create(organisation=organisation, code='PREVIEW', name='Faridabad — synthetic preview')
    user = get_user_model().objects.create_user(username=username, password=password, first_name='Preview owner')
    for role in ['master_admin', 'reception']:
        Membership.objects.create(user=user, branch=branch, role=role)
    for number in range(1, 121):
        Bed.objects.create(branch=branch, number=f'PREVIEW-{number:03}', room_number=f'P-{(number-1)//2+1:03}')
print('Created preview owner, scoped roles and120synthetic beds. No patients seeded.')
