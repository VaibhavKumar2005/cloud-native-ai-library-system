from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ai_engine', '0004_externalauthidentity'),
    ]

    operations = [
        migrations.CreateModel(
            name='OAuthExchangeCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('google', 'Google'), ('github', 'GitHub')], max_length=20)),
                ('code_hash', models.CharField(max_length=64, unique=True)),
                ('expires_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='oauth_exchange_codes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['expires_at'], name='ai_engine_o_expires_5edfe0_idx'),
                    models.Index(fields=['user', 'provider'], name='ai_engine_o_user_id_6c1f52_idx'),
                ],
            },
        ),
    ]