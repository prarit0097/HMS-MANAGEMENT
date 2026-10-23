from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0005_identity_security')]
    operations = [
        migrations.AddIndex(model_name='auditevent', index=models.Index(fields=['branch', '-created_at', '-id'], name='audit_branch_time_id')),
        migrations.AddIndex(model_name='auditevent', index=models.Index(fields=['actor', '-created_at', '-id'], name='audit_actor_time_id')),
    ]
