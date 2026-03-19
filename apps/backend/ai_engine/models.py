from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
import hashlib
import os
from cryptography.fernet import Fernet
from base64 import b64encode, b64decode

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

    # 🚨 SECURITY: Field-level encryption for sensitive documents
    # Stores encrypted document content for at-rest protection
    # Used when document contains highly sensitive research data
    encrypted_content = models.BinaryField(null=True, blank=True, db_index=False)
    is_encrypted = models.BooleanField(default=False, help_text="Whether document content is encrypted at rest")
    encryption_version = models.PositiveSmallIntegerField(default=1, help_text="Encryption algorithm version")

    # 🚨 THE MULTI-TENANT LINK: Associates the document with a specific user
    # null=True ensures older documents don't crash the database during migration
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents', null=True, blank=True)

    def __str__(self):
        return self.title

    # ========================================================================
    # ENCRYPTION/DECRYPTION METHODS - Field-level security
    # ========================================================================

    @staticmethod
    def _derive_user_key(user_id: int, salt: str = "verirag:doc:encryption") -> bytes:
        """
        Derive a unique encryption key per user using PBKDF2.
        This ensures each user's documents are encrypted with their own key.

        Args:
            user_id: The user's database ID
            salt: Consistent salt across all derivations

        Returns:
            Fernet-compatible key (base64-encoded)
        """
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
        from cryptography.hazmat.backends import default_backend

        # Combine user ID with vault-stored secret for key derivation
        vault_secret = os.environ.get('DOCUMENT_ENCRYPTION_SECRET', 'dev-default-secret')
        combined = f"{vault_secret}:{user_id}:{salt}".encode('utf-8')

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode('utf-8'),
            iterations=480000,  # OWASP standard for PBKDF2
            backend=default_backend()
        )
        key_material = kdf.derive(combined)
        return b64encode(key_material)  # Fernet requires base64

    def encrypt_content(self, plaintext: bytes) -> None:
        """
        Encrypt document content at rest.
        Only the document owner can decrypt it.

        Args:
            plaintext: Raw document bytes (PDF content, etc.)
        """
        if not self.user:
            raise ValueError("Document must have an owner to be encrypted")

        key = self._derive_user_key(self.user.id)
        cipher = Fernet(key)
        self.encrypted_content = cipher.encrypt(plaintext)
        self.is_encrypted = True
        self.save(update_fields=['encrypted_content', 'is_encrypted'])

    def decrypt_content(self) -> bytes:
        """
        Decrypt document content.
        Only works if called by the document owner (views layer handles auth).

        Returns:
            Decrypted document bytes

        Raises:
            ValueError: If document is not encrypted or user not set
            cryptography.fernet.InvalidToken: If decryption fails (tampering detected)
        """
        if not self.is_encrypted or not self.encrypted_content:
            raise ValueError("Document is not encrypted")

        if not self.user:
            raise ValueError("Cannot decrypt: document has no owner")

        key = self._derive_user_key(self.user.id)
        cipher = Fernet(key)
        return cipher.decrypt(self.encrypted_content)

    def get_content_safe(self) -> bytes:
        """
        Get document content with error handling.
        Returns None if decryption fails (tamper detection).
        Log suspicious access attempts for audit trail.
        """
        try:
            if self.is_encrypted:
                return self.decrypt_content()
            else:
                # Document not encrypted, return from file
                if self.file:
                    self.file.open('rb')
                    content = self.file.read()
                    self.file.close()
                    return content
                return None
        except Exception as e:
            # Log tamper attempt
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"❌ SECURITY: Document decryption failed for doc_id={self.id}, user_id={self.user_id}. "
                f"Possible tampering detected. Error: {type(e).__name__}"
            )
            return None


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


class EmailLoginToken(models.Model):
    """
    Passwordless email authentication tokens.
    Supports magic link sign-in for enterprise security.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_login_tokens',
        null=True,
        blank=True,
    )
    email = models.EmailField()
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['expires_at']),
            models.Index(fields=['email', 'expires_at']),
        ]

    def __str__(self):
        return f'Email token for {self.email}'
