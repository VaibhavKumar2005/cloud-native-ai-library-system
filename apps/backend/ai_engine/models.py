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

    # ========================================================================
    # UNIFIED DOCUMENT SUPPORT: Handle both uploads and external papers
    # ========================================================================
    class Source(models.TextChoices):
        UPLOAD = 'upload', 'User Upload'
        SEMANTIC_SCHOLAR = 'semantic_scholar', 'Semantic Scholar'
        ARXIV = 'arxiv', 'arXiv'
        CROSSREF = 'crossref', 'CrossRef'

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.UPLOAD,
        help_text="Where this document came from"
    )
    
    # For external papers, store the text content (abstract, full text, etc.)
    content = models.TextField(
        blank=True,
        default='',
        help_text="Text content for external papers (abstract, summary, etc.)"
    )
    
    # Metadata for external papers and source tracking
    source_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="External metadata: {paper_id, external_url, original_url, authors, year, venue, doi}"
    )

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


# ============================================================================
# RESEARCH-GRADE RAG: Citation-Aware Document & Chunk Models
# ============================================================================

class DocumentMetadata(models.Model):
    """
    Minimal academic metadata. Extracted during ingestion.
    Keep only what impacts retrieval and citation accuracy.
    """
    document = models.OneToOneField(
        Document, 
        on_delete=models.CASCADE, 
        related_name='metadata'
    )
    
    # Citation tracking (CRITICAL for $97 budget)
    # Format: {"smith2020": {"authors": "Smith et al.", "year": 2020, "page": 5}, ...}
    bibtex_entries = models.JSONField(
        default=dict, 
        help_text="BibTeX entries indexed by citation key"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Metadata: {self.document.title}"


class ChunkIndex(models.Model):
    """
    Minimal chunk storage: content + embedding + citations.
    Cost-optimized: No fancy metadata, no dual indexing, no versioning.
    """
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chunks'
    )
    
    # Core: Text and embedding
    content = models.TextField()
    embedding = models.BinaryField(null=True, blank=True)  # pgvector stores as binary
    
    # Minimal structural metadata
    page_number = models.IntegerField(default=0)
    
    # CRITICAL: Can we return this directly without LLM?
    is_qa = models.BooleanField(
        default=False,
        help_text="True if this chunk looks like Q&A pair - can return directly"
    )
    
    # CRITICAL: Pre-computed citations (format: ["smith2020", "jones2019"])
    citation_keys = models.JSONField(
        default=list,
        help_text="List of BibTeX keys cited in this chunk"
    )
    
    # Multi-tenant isolation
    user_id = models.IntegerField(db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user_id', 'document']),
            models.Index(fields=['user_id', 'is_qa']),
        ]
    
    def __str__(self):
        return f"Chunk(doc={self.document.id}, page={self.page_number}, qa={self.is_qa})"


class QueryLog(models.Model):
    """
    Minimal query logging for cost tracking and debugging.
    Usage: Monitor LLM spend and latency.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='query_logs')
    
    # What happened
    query_text = models.TextField()
    method = models.CharField(
        max_length=50,
        choices=[
            ('direct_retrieval', 'Direct Retrieval'),
            ('llm_synthesis', 'LLM Synthesis'),
            ('rejected', 'Rejected'),
        ]
    )
    
    # Cost tracking (minimal)
    tokens_used = models.IntegerField(default=0)  # Sum of in + out
    cost_usd = models.DecimalField(max_digits=8, decimal_places=6, default=0)
    
    # Performance
    latency_ms = models.IntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.method}: {self.query_text[:50]}"


# ============================================================================
# ACADEMIC PAPER MODELS - For PhD Student Research Discovery
# ============================================================================

class AcademicPaper(models.Model):
    """
    Represents an academic paper ingested from external sources
    (Semantic Scholar, arXiv, CrossRef, Google Scholar)
    """
    class Source(models.TextChoices):
        SEMANTIC_SCHOLAR = 'semantic-scholar', 'Semantic Scholar'
        ARXIV = 'arxiv', 'arXiv'
        CROSSREF = 'crossref', 'CrossRef'
        GOOGLE_SCHOLAR = 'google-scholar', 'Google Scholar'
        MANUAL_UPLOAD = 'manual', 'Manual Upload'
    
    # Multi-tenant
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='academic_papers')
    
    # Core metadata
    external_id = models.CharField(max_length=255, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    abstract = models.TextField(blank=True)
    source = models.CharField(max_length=20, choices=Source.choices)
    
    # Academic metadata
    authors = models.JSONField(default=list)  # List of author names
    publication_year = models.IntegerField(null=True, blank=True)
    venue = models.CharField(max_length=255, blank=True)  # Conference/Journal name
    doi = models.CharField(max_length=255, blank=True, db_index=True)
    
    # Academic impact
    citation_count = models.IntegerField(default=0)
    h_index_contribution = models.IntegerField(default=0)
    
    # URLs and links
    url = models.URLField(blank=True)
    pdf_url = models.URLField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-publication_year', '-citation_count']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'source']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.publication_year})"


class PaperLibrary(models.Model):
    """
    User's collection of papers for a research project
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paper_libraries')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    papers = models.ManyToManyField(AcademicPaper, related_name='libraries', blank=True)
    
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_favorite', '-updated_at']
    
    def __str__(self):
        return f"{self.user.username}'s {self.name}"


class ResearchTopic(models.Model):
    """
    AI engineering research topic recommendations for PhD students
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='research_topics')
    
    # Topic info
    title = models.CharField(max_length=255)
    description = models.TextField()
    relevance_score = models.FloatField(default=0.0)  # 0-100
    relevance_reason = models.TextField()
    
    # Research guidance
    key_challenges = models.JSONField(default=list)  # List of challenge descriptions
    skills_needed = models.JSONField(default=list)  # List of required skills
    related_fields = models.JSONField(default=list)  # Interdisciplinary connections
    
    # Trending info
    papers_count = models.IntegerField(default=0)
    growth_percentage = models.FloatField(default=0.0)  # Growth in last 12 months
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} ({self.relevance_score}% match)"


class ResearchGap(models.Model):
    """
    Identified research gaps for a given topic
    """
    topic = models.ForeignKey(ResearchTopic, on_delete=models.CASCADE, related_name='gaps')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='research_gaps')
    
    # Gap info
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Potential directions
    potential_research_directions = models.JSONField(default=list)
    
    # Supporting papers
    supporting_papers = models.ManyToManyField(AcademicPaper, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Gap: {self.title}"


class PaperQnA(models.Model):
    """
    Questions and answers about specific papers using RAG
    """
    paper = models.ForeignKey(AcademicPaper, on_delete=models.CASCADE, related_name='qna')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paper_qna')
    
    question = models.TextField()
    answer = models.TextField()
    
    # Source info
    sources_cited = models.JSONField(default=list)  # List of quote/page pairs
    faithfulness_score = models.FloatField(default=0.0)  # 0-1 confidence
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Q: {self.question[:50]}..." 
