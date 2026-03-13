from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class Document(models.Model):
    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        INDEXING = 'indexing', 'Indexing'
        INDEXED = 'indexed', 'Indexed'
        FAILED = 'failed', 'Failed'

    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    progress_percent = models.PositiveSmallIntegerField(default=0)
    total_chunks = models.PositiveIntegerField(default=0)
    processed_chunks = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default='')
    
    # 🚨 THE MULTI-TENANT LINK: Associates the document with a specific user
    # null=True ensures older documents don't crash the database during migration
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents', null=True, blank=True)

    def __str__(self):
        return self.title


class ExternalAuthIdentity(models.Model):
    class Provider(models.TextChoices):
        GOOGLE = 'google', 'Google'
        GITHUB = 'github', 'GitHub'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='external_auth_identities',
    )
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_user_id = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    display_name = models.CharField(max_length=255, blank=True)
    avatar_url = models.URLField(blank=True)
    last_login_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'provider_user_id'],
                name='unique_external_auth_identity',
            )
        ]
        indexes = [
            models.Index(fields=['provider', 'provider_user_id']),
            models.Index(fields=['user', 'provider']),
        ]

    def __str__(self):
        return f'{self.get_provider_display()}:{self.provider_user_id}'


class OAuthExchangeCode(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='oauth_exchange_codes',
    )
    provider = models.CharField(
        max_length=20,
        choices=ExternalAuthIdentity.Provider.choices,
    )
    code_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['expires_at']),
            models.Index(fields=['user', 'provider']),
        ]

    def __str__(self):
        return f'{self.get_provider_display()} exchange for {self.user_id}'
