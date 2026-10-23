"""Explicit development-only synthetic fixtures; no default account/password."""
import os
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from apps.core.models import Organisation, Branch, Membership, Patient, Bed, Appointment

class Command(BaseCommand):
    help = 'Create synthetic local demo data using HMS_DEMO_PASSWORD from the environment.'
    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
    @transaction.atomic
    def handle(self, *args, **options):
        if settings.ENVIRONMENT != 'development':
            raise CommandError('Synthetic seeding is restricted to development.')
        password = os.getenv('HMS_DEMO_PASSWORD', '')
        if len(password) < 12:
            raise CommandError('Supply a private HMS_DEMO_PASSWORD of at least 12 characters.')
        if get_user_model().objects.filter(username=options['username']).exists():
            raise CommandError('This username already exists. Seeding never resets existing accounts.')
        user = get_user_model().objects.create_user(username=options['username'], password=password, first_name='Local', last_name='Demo')
        organisation, _ = Organisation.objects.get_or_create(name='Synthetic Hospital — Development')
        branch, _ = Branch.objects.get_or_create(organisation=organisation, code='DEMO', defaults={'name': 'Synthetic Main Branch'})
        for role in ('reception', 'master_admin'):
            Membership.objects.get_or_create(user=user, branch=branch, role=role)
        for index, name in enumerate(('Synthetic Patient One', 'Synthetic Patient Two', 'Synthetic Patient Three'), 1):
            patient, _ = Patient.objects.get_or_create(branch=branch, full_name=name, defaults={'phone': '0000000000', 'city': 'Synthetic City', 'age': 30 + index})
            Appointment.objects.get_or_create(patient=patient, branch=branch, doctor_name='Synthetic Doctor', defaults={'scheduled_at': timezone.now() + timedelta(hours=index), 'reason': 'Synthetic demonstration only'})
        for index in range(1, 13):
            Bed.objects.get_or_create(branch=branch, number=f'D-{index:02}', defaults={'room_number': str((index-1)//2+1), 'category': 'general' if index < 7 else 'private'})
        self.stdout.write(self.style.SUCCESS('Synthetic development workspace created. No credentials displayed.'))
