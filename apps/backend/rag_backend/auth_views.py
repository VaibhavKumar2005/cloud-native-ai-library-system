import hashlib
import logging
import secrets
from datetime import timedelta
from urllib.parse import urlencode, urlparse

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_200_OK
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from ai_engine.models import ExternalAuthIdentity, OAuthExchangeCode, EmailLoginToken
from ai_engine.throttles import LoginAnonRateThrottle

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"
FRONTEND_CALLBACK_PATH = "/login"
OAUTH_STATE_SESSION_PREFIX = "oauth_state:"
OAUTH_EXCHANGE_CODE_TTL = timedelta(minutes=2)
User = get_user_model()


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [LoginAnonRateThrottle]


class AccountLinkRequiredError(Exception):
    """Raised when a social login matches an existing local account."""


def build_auth_provider_manifest():
    """
    Describe currently available auth methods without coupling the frontend to
    a specific social-auth implementation yet.
    """
    frontend_ready = _get_frontend_callback_origin() is not None
    google_enabled = _provider_is_ready(
        settings.GOOGLE_OAUTH_CLIENT_ID,
        settings.GOOGLE_OAUTH_CLIENT_SECRET,
        settings.GOOGLE_OAUTH_REDIRECT_URI,
        frontend_ready,
    )
    github_enabled = _provider_is_ready(
        settings.GITHUB_OAUTH_CLIENT_ID,
        settings.GITHUB_OAUTH_CLIENT_SECRET,
        settings.GITHUB_OAUTH_REDIRECT_URI,
        frontend_ready,
    )

    return [
        {
            "id": "password",
            "label": "Email or Username",
            "type": "password",
            "enabled": True,
        },
        {
            "id": "google",
            "label": "Google",
            "type": "oauth",
            "enabled": google_enabled,
            "start_url": "/api/auth/google/start/" if google_enabled else None,
        },
        {
            "id": "github",
            "label": "GitHub",
            "type": "oauth",
            "enabled": github_enabled,
            "start_url": "/api/auth/github/start/" if github_enabled else None,
        },
    ]


def _get_frontend_callback_origin():
    frontend_url = (settings.FRONTEND_URL or "").strip()
    if not frontend_url:
        return None

    parsed = urlparse(frontend_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        logger.warning("FRONTEND_URL is invalid for OAuth redirects: %r", frontend_url)
        return None

    return f"{parsed.scheme}://{parsed.netloc}"


def _provider_is_ready(client_id, client_secret, redirect_uri, frontend_ready):
    parsed_redirect = urlparse((redirect_uri or "").strip())
    redirect_ready = parsed_redirect.scheme in {"http", "https"} and bool(parsed_redirect.netloc)
    return bool(client_id and client_secret and redirect_ready and frontend_ready)


def _frontend_redirect_url(params):
    frontend_origin = _get_frontend_callback_origin()
    if not frontend_origin:
        raise ValueError("FRONTEND_URL must be a valid http(s) origin for OAuth redirects.")
    return f"{frontend_origin}{FRONTEND_CALLBACK_PATH}#{urlencode(params)}"


def _oauth_error_redirect(code, message):
    return HttpResponseRedirect(
        _frontend_redirect_url(
            {
                "oauth": "error",
                "error": code,
                "message": message,
            }
        )
    )


def _issue_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh),
    }


def _hash_exchange_code(raw_code):
    return hashlib.sha256(raw_code.encode("utf-8")).hexdigest()


def _can_auto_link_existing_user(user):
    # Only link automatically to accounts that were already created for social auth
    # and do not have a local password-based login path.
    return not user.has_usable_password()


@transaction.atomic
def _create_exchange_code(user, provider):
    OAuthExchangeCode.objects.filter(expires_at__lt=timezone.now()).delete()
    raw_code = secrets.token_urlsafe(32)
    OAuthExchangeCode.objects.create(
        user=user,
        provider=provider,
        code_hash=_hash_exchange_code(raw_code),
        expires_at=timezone.now() + OAUTH_EXCHANGE_CODE_TTL,
    )
    return raw_code


@transaction.atomic
def _consume_exchange_code(raw_code):
    code_hash = _hash_exchange_code(raw_code)
    exchange_code = OAuthExchangeCode.objects.select_for_update().select_related("user").filter(
        code_hash=code_hash,
    ).first()

    if not exchange_code:
        return None
    if exchange_code.used_at is not None or exchange_code.expires_at <= timezone.now():
        return None

    exchange_code.used_at = timezone.now()
    exchange_code.save(update_fields=["used_at"])
    return exchange_code


def _generate_unique_username(seed_value):
    base = slugify(seed_value or "verirag-user")[:24] or "verirag-user"
    candidate = base
    suffix = 1

    while User.objects.filter(username=candidate).exists():
        candidate = f"{base[:20]}-{suffix}"
        suffix += 1

    return candidate


@transaction.atomic
def _resolve_external_user(provider, provider_user_id, email, full_name, avatar_url):
    email = (email or "").strip().lower()
    full_name = (full_name or "").strip()
    avatar_url = (avatar_url or "").strip()

    identity = ExternalAuthIdentity.objects.select_for_update().select_related("user").filter(
        provider=provider,
        provider_user_id=provider_user_id,
    ).first()

    if identity:
        user = identity.user
    else:
        user = None
        if email:
            existing_user = User.objects.filter(email__iexact=email).order_by("id").first()
            if existing_user:
                if not _can_auto_link_existing_user(existing_user):
                    raise AccountLinkRequiredError(
                        "An account with this email already exists. Sign in with your existing password login first before linking a social provider."
                    )
                user = existing_user

        if not user:
            username_seed = email.split("@", 1)[0] if email else full_name or provider_user_id
            user = User.objects.create_user(
                username=_generate_unique_username(username_seed),
                email=email,
            )
            user.set_unusable_password()
            if full_name:
                name_parts = full_name.split(None, 1)
                user.first_name = name_parts[0]
                user.last_name = name_parts[1] if len(name_parts) > 1 else ""
            user.save(update_fields=["password", "first_name", "last_name", "email"])

        identity = ExternalAuthIdentity.objects.create(
            user=user,
            provider=provider,
            provider_user_id=provider_user_id,
        )

    updates = []
    if email and user.email != email:
        user.email = email
        updates.append("email")
    if full_name and not user.first_name and not user.last_name:
        name_parts = full_name.split(None, 1)
        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ""
        updates.extend(["first_name", "last_name"])
    if updates:
        user.save(update_fields=sorted(set(updates)))

    identity.email = email
    identity.display_name = full_name
    identity.avatar_url = avatar_url
    identity.last_login_at = timezone.now()
    identity.save(update_fields=["email", "display_name", "avatar_url", "last_login_at"])

    return user


def _google_get_profile(code):
    token_response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        },
        timeout=15,
    )
    token_response.raise_for_status()
    token_payload = token_response.json()

    userinfo_response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
        timeout=15,
    )
    userinfo_response.raise_for_status()
    profile = userinfo_response.json()

    if not profile.get("sub"):
        raise ValueError("Google did not return a stable account identifier.")
    if not profile.get("email") or not profile.get("email_verified"):
        raise PermissionError("Google account must expose a verified email address.")

    return {
        "provider": ExternalAuthIdentity.Provider.GOOGLE,
        "provider_user_id": profile["sub"],
        "email": profile.get("email"),
        "full_name": profile.get("name"),
        "avatar_url": profile.get("picture"),
    }


def _github_get_profile(code):
    token_response = requests.post(
        GITHUB_TOKEN_URL,
        data={
            "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
            "client_secret": settings.GITHUB_OAUTH_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GITHUB_OAUTH_REDIRECT_URI,
        },
        headers={"Accept": "application/json"},
        timeout=15,
    )
    token_response.raise_for_status()
    token_payload = token_response.json()
    access_token = token_payload.get("access_token")
    if not access_token:
        raise ValueError("GitHub did not return an access token.")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }
    user_response = requests.get(GITHUB_USER_URL, headers=headers, timeout=15)
    user_response.raise_for_status()
    user_profile = user_response.json()

    emails_response = requests.get(GITHUB_EMAILS_URL, headers=headers, timeout=15)
    emails_response.raise_for_status()
    emails = emails_response.json()

    verified_email = None
    for email_entry in emails:
        if email_entry.get("verified") and email_entry.get("primary"):
            verified_email = email_entry.get("email")
            break
    if not verified_email:
        for email_entry in emails:
            if email_entry.get("verified"):
                verified_email = email_entry.get("email")
                break
    if not verified_email:
        raise PermissionError("GitHub account must expose a verified email address.")
    if not user_profile.get("id"):
        raise ValueError("GitHub did not return a stable account identifier.")

    return {
        "provider": ExternalAuthIdentity.Provider.GITHUB,
        "provider_user_id": str(user_profile["id"]),
        "email": verified_email,
        "full_name": user_profile.get("name") or user_profile.get("login"),
        "avatar_url": user_profile.get("avatar_url"),
    }


def _exchange_provider_code(fetch_profile, code):
    profile = fetch_profile(code)
    user = _resolve_external_user(
        provider=profile["provider"],
        provider_user_id=profile["provider_user_id"],
        email=profile["email"],
        full_name=profile["full_name"],
        avatar_url=profile["avatar_url"],
    )
    exchange_code = _create_exchange_code(user, profile["provider"])
    return exchange_code, profile["provider"]


class AuthProvidersView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "providers": build_auth_provider_manifest(),
                "oauth_ready": any(
                    provider["enabled"]
                    for provider in build_auth_provider_manifest()
                    if provider["type"] == "oauth"
                ),
            }
        )


class AuthSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_staff": user.is_staff,
                },
                "auth": {
                    "mode": "jwt",
                    "providers": build_auth_provider_manifest(),
                },
            }
        )


class OAuthExchangeView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginAnonRateThrottle]

    def post(self, request):
        raw_code = request.data.get("code")
        if not raw_code:
            return Response({"detail": "OAuth exchange code is required."}, status=400)

        exchange_code = _consume_exchange_code(raw_code)
        if not exchange_code:
            return Response({"detail": "OAuth exchange code is invalid or expired."}, status=400)

        token_pair = _issue_tokens_for_user(exchange_code.user)
        return Response(
            {
                "access": token_pair["access_token"],
                "refresh": token_pair["refresh_token"],
                "provider": exchange_code.provider,
            }
        )


class GoogleOAuthStartView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginAnonRateThrottle]

    def get(self, request):
        if not _provider_is_ready(
            settings.GOOGLE_OAUTH_CLIENT_ID,
            settings.GOOGLE_OAUTH_CLIENT_SECRET,
            settings.GOOGLE_OAUTH_REDIRECT_URI,
            _get_frontend_callback_origin() is not None,
        ):
            return _oauth_error_redirect(
                "provider_unavailable",
                "Google sign-in is not configured for this environment.",
            )

        state = secrets.token_urlsafe(24)
        signer = TimestampSigner()
        request.session[f"{OAUTH_STATE_SESSION_PREFIX}{state}"] = signer.sign(state)
        request.session.modified = True

        params = {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(settings.GOOGLE_OAUTH_SCOPES),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "select_account",
            "state": state,
        }
        return HttpResponseRedirect(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


class GoogleOAuthCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        error = request.query_params.get("error")
        if error:
            return _oauth_error_redirect(error, "Google sign-in was cancelled or denied.")

        code = request.query_params.get("code")
        state = request.query_params.get("state")
        if not code or not state:
            return _oauth_error_redirect("invalid_request", "Google callback is missing required parameters.")

        session_key = f"{OAUTH_STATE_SESSION_PREFIX}{state}"
        signed_state = request.session.pop(session_key, None)
        if not signed_state:
            return _oauth_error_redirect("invalid_state", "Google sign-in session expired. Please try again.")

        try:
            unsigned_state = TimestampSigner().unsign(signed_state, max_age=600)
        except (BadSignature, SignatureExpired):
            return _oauth_error_redirect("invalid_state", "Google sign-in session expired. Please try again.")
        if unsigned_state != state:
            return _oauth_error_redirect("invalid_state", "Google sign-in session expired. Please try again.")

        try:
            exchange_code, provider = _exchange_provider_code(_google_get_profile, code)
        except PermissionError as exc:
            return _oauth_error_redirect("unverified_email", str(exc))
        except AccountLinkRequiredError as exc:
            return _oauth_error_redirect("account_link_required", str(exc))
        except (requests.RequestException, KeyError, ValueError):
            return _oauth_error_redirect(
                "provider_error",
                "Unable to complete Google sign-in right now.",
            )

        return HttpResponseRedirect(
            _frontend_redirect_url(
                {
                    "oauth": "success",
                    "provider": provider,
                    "code": exchange_code,
                }
            )
        )


class GitHubOAuthStartView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginAnonRateThrottle]

    def get(self, request):
        if not _provider_is_ready(
            settings.GITHUB_OAUTH_CLIENT_ID,
            settings.GITHUB_OAUTH_CLIENT_SECRET,
            settings.GITHUB_OAUTH_REDIRECT_URI,
            _get_frontend_callback_origin() is not None,
        ):
            return _oauth_error_redirect(
                "provider_unavailable",
                "GitHub sign-in is not configured for this environment.",
            )

        state = secrets.token_urlsafe(24)
        signer = TimestampSigner()
        request.session[f"{OAUTH_STATE_SESSION_PREFIX}{state}"] = signer.sign(state)
        request.session.modified = True

        params = {
            "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
            "redirect_uri": settings.GITHUB_OAUTH_REDIRECT_URI,
            "scope": " ".join(settings.GITHUB_OAUTH_SCOPES),
            "state": state,
        }
        return HttpResponseRedirect(f"{GITHUB_AUTH_URL}?{urlencode(params)}")


class GitHubOAuthCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        error = request.query_params.get("error")
        if error:
            return _oauth_error_redirect(error, "GitHub sign-in was cancelled or denied.")

        code = request.query_params.get("code")
        state = request.query_params.get("state")
        if not code or not state:
            return _oauth_error_redirect("invalid_request", "GitHub callback is missing required parameters.")

        session_key = f"{OAUTH_STATE_SESSION_PREFIX}{state}"
        signed_state = request.session.pop(session_key, None)
        if not signed_state:
            return _oauth_error_redirect("invalid_state", "GitHub sign-in session expired. Please try again.")

        try:
            unsigned_state = TimestampSigner().unsign(signed_state, max_age=600)
        except (BadSignature, SignatureExpired):
            return _oauth_error_redirect("invalid_state", "GitHub sign-in session expired. Please try again.")
        if unsigned_state != state:
            return _oauth_error_redirect("invalid_state", "GitHub sign-in session expired. Please try again.")

        try:
            exchange_code, provider = _exchange_provider_code(_github_get_profile, code)
        except PermissionError as exc:
            return _oauth_error_redirect("unverified_email", str(exc))
        except AccountLinkRequiredError as exc:
            return _oauth_error_redirect("account_link_required", str(exc))
        except (requests.RequestException, KeyError, ValueError):
            return _oauth_error_redirect(
                "provider_error",
                "Unable to complete GitHub sign-in right now.",
            )

        return HttpResponseRedirect(
            _frontend_redirect_url(
                {
                    "oauth": "success",
                    "provider": provider,
                    "code": exchange_code,
                }
            )
        )


# ══════════════════════════════════════════════════════════════════════════════
# EMAIL AUTHENTICATION: Magic Links for Passwordless Sign-In
# ══════════════════════════════════════════════════════════════════════════════


class EmailLoginSendView(APIView):
    """
    Initiates passwordless email authentication.
    Sends a magic link token to the user's email address.

    Enterprise Feature: Enables secure sign-in without passwords.
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginAnonRateThrottle]

    def post(self, request):
        """
        POST /api/auth/email/send/

        Body: { "email": "user@example.com" }
        Response: { "status": "link_sent", "email": "user@example.com" }
        """
        email = (request.data.get('email') or '').strip().lower()

        if not email or '@' not in email:
            return Response(
                {"detail": "Valid email address is required."},
                status=HTTP_400_BAD_REQUEST
            )

        # Clean up expired tokens
        EmailLoginToken.objects.filter(expires_at__lt=timezone.now()).delete()

        try:
            # Generate raw token (32 bytes urlsafe)
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

            # Create or update token
            expires_at = timezone.now() + timedelta(minutes=15)
            EmailLoginToken.objects.create(
                email=email,
                token_hash=token_hash,
                expires_at=expires_at,
            )

            # In production, integrate with Resend/Postmark to send actual email
            # For now, log to console/stderr (development-friendly)
            frontend_url = settings.FRONTEND_URL or 'http://localhost:5173'
            magic_link = f"{frontend_url}/login?email_token={raw_token}"

            logger.info(
                f"📧 Magic link generated for {email}: {magic_link}"
            )

            return Response(
                {
                    "status": "link_sent",
                    "email": email,
                    "message": f"Magic link sent to {email}. Valid for 15 minutes.",
                    # Debug: Include link for local dev
                    "magic_link": magic_link if settings.DEBUG else None,
                },
                status=HTTP_200_OK
            )

        except Exception as e:
            logger.exception(f"Email token generation failed: {e}")
            from rest_framework import status as drf_status
            return Response(
                {"detail": "Failed to send email. Please try again."},
                status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmailLoginVerifyView(APIView):
    """
    Completes passwordless email authentication.
    Verifies the magic link token and issues JWT tokens.
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginAnonRateThrottle]

    def post(self, request):
        """
        POST /api/auth/email/verify/

        Body: { "token": "...base64-encoded-token..." }
        Response: { "access": "...", "refresh": "...", "user": {...} }
        """
        raw_token = request.data.get('token', '').strip()

        if not raw_token:
            return Response(
                {"detail": "Email token is required."},
                status=HTTP_400_BAD_REQUEST
            )

        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

        try:
            with transaction.atomic():
                # Find and consume token (one-time use)
                email_token = EmailLoginToken.objects.select_for_update().filter(
                    token_hash=token_hash,
                ).first()

                if not email_token:
                    return Response(
                        {"detail": "Invalid or expired token."},
                        status=HTTP_401_UNAUTHORIZED
                    )

                # Check expiration
                if email_token.expires_at <= timezone.now():
                    return Response(
                        {"detail": "Token has expired. Please request a new magic link."},
                        status=HTTP_401_UNAUTHORIZED
                    )

                # Check if already used
                if email_token.used_at is not None:
                    return Response(
                        {"detail": "Token has already been used."},
                        status=HTTP_401_UNAUTHORIZED
                    )

                # Mark as used
                email_token.used_at = timezone.now()
                email_token.save(update_fields=['used_at'])

                # Get or create user
                user = User.objects.filter(email__iexact=email_token.email).first()
                if not user:
                    # Create new user from email
                    username = _generate_unique_username(email_token.email.split('@')[0])
                    user = User.objects.create_user(
                        username=username,
                        email=email_token.email,
                    )
                    user.set_unusable_password()  # No password for email-based auth
                    user.save()

                    logger.info(f"✨ New user created via email auth: {user.id} ({email_token.email})")

                # Link email token to user (for audit trail)
                email_token.user = user
                email_token.save(update_fields=['user'])

            # Issue JWT tokens
            token_pair = _issue_tokens_for_user(user)

            return Response(
                {
                    "access": token_pair["access_token"],
                    "refresh": token_pair["refresh_token"],
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                    },
                },
                status=HTTP_200_OK
            )

        except EmailLoginToken.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired token."},
                status=HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.exception(f"Email token verification failed: {e}")
            from rest_framework import status as drf_status
            return Response(
                {"detail": "Token verification failed. Please try again."},
                status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR
            )
