import os
import subprocess
import sys
import pytest
from django.core.management import call_command
from django.contrib.auth import get_user_model
from apps.core.models import Patient, Bed

@pytest.mark.django_db
def test_seed_demo_is_synthetic_and_requires_private_password(monkeypatch):
    monkeypatch.setenv('HMS_DEMO_PASSWORD', 'Synthetic-tests-only-passphrase')
    call_command('seed_demo', username='synthetic-local-user')
    assert get_user_model().objects.get(username='synthetic-local-user').check_password('Synthetic-tests-only-passphrase')
    assert Patient.objects.count() > 0
    assert Bed.objects.count() > 0
    assert set(get_user_model().objects.get(username='synthetic-local-user').memberships.values_list('role', flat=True)) == {'master_admin', 'reception'}

def test_invalid_network_boolean_cannot_silently_open_access():
    env = {**os.environ, 'HMS_IP_ALLOWLIST_ONLY': 'truue'}
    result = subprocess.run([sys.executable, '-c', 'import hms.settings'], env=env, capture_output=True, text=True)
    assert result.returncode != 0
