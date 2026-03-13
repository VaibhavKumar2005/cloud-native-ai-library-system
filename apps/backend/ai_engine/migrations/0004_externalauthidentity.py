from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ai_engine', '0003_document_status_progress'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalAuthIdentity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('google', 'Google'), ('github', 'GitHub')], max_length=20)),
                ('provider_user_id', models.CharField(max_length=255)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('display_name', models.CharField(blank=True, max_length=255)),
                ('avatar_url', models.URLField(blank=True)),
                ('last_login_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='external_auth_identities', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['provider', 'provider_user_id'], name='ai_engine_e_provider_6c98a3_idx'),
                    models.Index(fields=['user', 'provider'], name='ai_engine_e_user_id_369b17_idx'),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='externalauthidentity',
            constraint=models.UniqueConstraint(fields=('provider', 'provider_user_id'), name='unique_external_auth_identity'),
        ),
    ]