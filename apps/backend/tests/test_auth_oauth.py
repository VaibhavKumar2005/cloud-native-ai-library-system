from urllib.parse import parse_qs, urlparse
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from ai_engine.models import ExternalAuthIdentity


User = get_user_model()


@pytest.mark.django_db
@override_settings(
    GOOGLE_OAUTH_CLIENT_ID='google-client-id',
    GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    GOOGLE_OAUTH_REDIRECT_URI='http://localhost:8000/api/auth/google/callback/',
    FRONTEND_URL='http://localhost:5173',
)
def test_auth_providers_manifest_enables_google_when_fully_configured(client):
    response = client.get('/api/auth/providers/')

    assert response.status_code == 200
    providers = {provider['id']: provider for provider in response.json()['providers']}
    assert providers['google']['enabled'] is True
    assert providers['google']['start_url'] == '/api/auth/google/start/'
    assert providers['github']['enabled'] is False


@pytest.mark.django_db
@override_settings(
    GOOGLE_OAUTH_CLIENT_ID='google-client-id',
    GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    GOOGLE_OAUTH_REDIRECT_URI='http://localhost:8000/api/auth/google/callback/',
)
def test_google_oauth_start_redirects_to_google_and_stores_state(client):
    response = client.get('/api/auth/google/start/')

    assert response.status_code == 302
    redirect = urlparse(response['Location'])
    query = parse_qs(redirect.query)

    assert redirect.netloc == 'accounts.google.com'
    assert query['client_id'] == ['google-client-id']
    assert query['redirect_uri'] == ['http://localhost:8000/api/auth/google/callback/']
    assert 'state' in query
    assert client.session.get(f"oauth_state:{query['state'][0]}")


@pytest.mark.django_db
@override_settings(
    GOOGLE_OAUTH_CLIENT_ID='google-client-id',
    GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    GOOGLE_OAUTH_REDIRECT_URI='http://localhost:8000/api/auth/google/callback/',
    FRONTEND_URL='http://localhost:5173',
)
def test_google_oauth_callback_creates_identity_and_redirects_with_tokens(client):
    start_response = client.get('/api/auth/google/start/')
    state = parse_qs(urlparse(start_response['Location']).query)['state'][0]

    token_response = Mock()
    token_response.raise_for_status.return_value = None
    token_response.json.return_value = {'access_token': 'provider-access-token'}

    userinfo_response = Mock()
    userinfo_response.raise_for_status.return_value = None
    userinfo_response.json.return_value = {
        'sub': 'google-user-123',
        'email': 'oauth@verirag.dev',
        'email_verified': True,
        'name': 'OAuth Tester',
        'picture': 'https://example.com/avatar.png',
    }

    with patch('rag_backend.auth_views.requests.post', return_value=token_response) as mock_post, patch(
        'rag_backend.auth_views.requests.get', return_value=userinfo_response
    ) as mock_get:
        response = client.get('/api/auth/google/callback/', {'code': 'auth-code', 'state': state})

    assert response.status_code == 302
    redirect = urlparse(response['Location'])
    fragment = parse_qs(redirect.fragment)

    assert redirect.scheme == 'http'
    assert redirect.netloc == 'localhost:5173'
    assert redirect.path == '/login'
    assert fragment['oauth'] == ['success']
    assert fragment['provider'] == ['google']
    assert fragment['code']

    user = User.objects.get(email='oauth@verirag.dev')
    identity = ExternalAuthIdentity.objects.get(
        provider=ExternalAuthIdentity.Provider.GOOGLE,
        provider_user_id='google-user-123',
    )

    assert identity.user == user
    assert user.has_usable_password() is False
    assert identity.display_name == 'OAuth Tester'
    assert identity.avatar_url == 'https://example.com/avatar.png'
    mock_post.assert_called_once()
    mock_get.assert_called_once()

    exchange_response = client.post('/api/auth/exchange/', {'code': fragment['code'][0]}, content_type='application/json')
    assert exchange_response.status_code == 200
    payload = exchange_response.json()
    assert payload['provider'] == 'google'
    assert payload['access']
    assert payload['refresh']

    second_exchange = client.post('/api/auth/exchange/', {'code': fragment['code'][0]}, content_type='application/json')
    assert second_exchange.status_code == 400


@pytest.mark.django_db
@override_settings(
    GOOGLE_OAUTH_CLIENT_ID='google-client-id',
    GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    GOOGLE_OAUTH_REDIRECT_URI='http://localhost:8000/api/auth/google/callback/',
    FRONTEND_URL='javascript:alert(1)',
)
def test_auth_providers_manifest_disables_google_with_non_http_frontend_origin(client):
    response = client.get('/api/auth/providers/')

    assert response.status_code == 200
    providers = {provider['id']: provider for provider in response.json()['providers']}
    assert providers['google']['enabled'] is False
    assert providers['google']['start_url'] is None


@pytest.mark.django_db
@override_settings(
    GOOGLE_OAUTH_CLIENT_ID='google-client-id',
    GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    GOOGLE_OAUTH_REDIRECT_URI='http://localhost:8000/api/auth/google/callback/',
    FRONTEND_URL='http://localhost:5173/app?bad=1',
)
def test_google_oauth_callback_redirect_uses_frontend_origin_only(client):
    start_response = client.get('/api/auth/google/start/')
    state = parse_qs(urlparse(start_response['Location']).query)['state'][0]

    token_response = Mock()
    token_response.raise_for_status.return_value = None
    token_response.json.return_value = {'access_token': 'provider-access-token'}

    userinfo_response = Mock()
    userinfo_response.raise_for_status.return_value = None
    userinfo_response.json.return_value = {
        'sub': 'google-user-123',
        'email': 'oauth@verirag.dev',
        'email_verified': True,
        'name': 'OAuth Tester',
        'picture': 'https://example.com/avatar.png',
    }

    with patch('rag_backend.auth_views.requests.post', return_value=token_response), patch(
        'rag_backend.auth_views.requests.get', return_value=userinfo_response
    ):
        response = client.get('/api/auth/google/callback/', {'code': 'auth-code', 'state': state})

    assert response.status_code == 302
    redirect = urlparse(response['Location'])
    assert redirect.scheme == 'http'
    assert redirect.netloc == 'localhost:5173'
    assert redirect.path == '/login'


@pytest.mark.django_db
@override_settings(
    GOOGLE_OAUTH_CLIENT_ID='google-client-id',
    GOOGLE_OAUTH_CLIENT_SECRET='google-client-secret',
    GOOGLE_OAUTH_REDIRECT_URI='http://localhost:8000/api/auth/google/callback/',
    FRONTEND_URL='http://localhost:5173',
)
def test_google_oauth_callback_rejects_auto_link_to_existing_password_user(client):
    existing_user = User.objects.create_user(
        username='existing-user',
        email='oauth@verirag.dev',
        password='VerySecret123!',
    )

    start_response = client.get('/api/auth/google/start/')
    state = parse_qs(urlparse(start_response['Location']).query)['state'][0]

    token_response = Mock()
    token_response.raise_for_status.return_value = None
    token_response.json.return_value = {'access_token': 'provider-access-token'}

    userinfo_response = Mock()
    userinfo_response.raise_for_status.return_value = None
    userinfo_response.json.return_value = {
        'sub': 'google-user-123',
        'email': 'oauth@verirag.dev',
        'email_verified': True,
        'name': 'OAuth Tester',
        'picture': 'https://example.com/avatar.png',
    }

    with patch('rag_backend.auth_views.requests.post', return_value=token_response), patch(
        'rag_backend.auth_views.requests.get', return_value=userinfo_response
    ):
        response = client.get('/api/auth/google/callback/', {'code': 'auth-code', 'state': state})

    assert response.status_code == 302
    redirect = urlparse(response['Location'])
    fragment = parse_qs(redirect.fragment)
    assert fragment['oauth'] == ['error']
    assert fragment['error'] == ['account_link_required']
    assert 'existing password login' in fragment['message'][0]
    assert ExternalAuthIdentity.objects.filter(
        provider=ExternalAuthIdentity.Provider.GOOGLE,
        provider_user_id='google-user-123',
    ).count() == 0
    existing_user.refresh_from_db()
    assert existing_user.has_usable_password() is True


@pytest.mark.django_db
@override_settings(
    GITHUB_OAUTH_CLIENT_ID='github-client-id',
    GITHUB_OAUTH_CLIENT_SECRET='github-client-secret',
    GITHUB_OAUTH_REDIRECT_URI='http://localhost:8000/api/auth/github/callback/',
    FRONTEND_URL='http://localhost:5173',
)
def test_auth_providers_manifest_enables_github_when_fully_configured(client):
    response = client.get('/api/auth/providers/')

    assert response.status_code == 200
    providers = {provider['id']: provider for provider in response.json()['providers']}
    assert providers['github']['enabled'] is True
    assert providers['github']['start_url'] == '/api/auth/github/start/'


@pytest.mark.django_db
@override_settings(
    GITHUB_OAUTH_CLIENT_ID='github-client-id',
    GITHUB_OAUTH_CLIENT_SECRET='github-client-secret',
    GITHUB_OAUTH_REDIRECT_URI='http://localhost:8000/api/auth/github/callback/',
)
def test_github_oauth_start_redirects_to_github_and_stores_state(client):
    response = client.get('/api/auth/github/start/')

    assert response.status_code == 302
    redirect = urlparse(response['Location'])
    query = parse_qs(redirect.query)

    assert redirect.netloc == 'github.com'
    assert query['client_id'] == ['github-client-id']
    assert query['redirect_uri'] == ['http://localhost:8000/api/auth/github/callback/']
    assert 'state' in query
    assert client.session.get(f"oauth_state:{query['state'][0]}")


@pytest.mark.django_db
@override_settings(
    GITHUB_OAUTH_CLIENT_ID='github-client-id',
    GITHUB_OAUTH_CLIENT_SECRET='github-client-secret',
    GITHUB_OAUTH_REDIRECT_URI='http://localhost:8000/api/auth/github/callback/',
    FRONTEND_URL='http://localhost:5173',
)
def test_github_oauth_callback_creates_identity_and_redirects_with_exchange_code(client):
    start_response = client.get('/api/auth/github/start/')
    state = parse_qs(urlparse(start_response['Location']).query)['state'][0]

    token_response = Mock()
    token_response.raise_for_status.return_value = None
    token_response.json.return_value = {'access_token': 'github-provider-token'}

    user_response = Mock()
    user_response.raise_for_status.return_value = None
    user_response.json.return_value = {
        'id': 42,
        'login': 'octocat',
        'name': 'Octo Cat',
        'avatar_url': 'https://example.com/octocat.png',
    }

    emails_response = Mock()
    emails_response.raise_for_status.return_value = None
    emails_response.json.return_value = [
        {'email': 'octocat@example.com', 'primary': True, 'verified': True}
    ]

    with patch('rag_backend.auth_views.requests.post', return_value=token_response) as mock_post, patch(
        'rag_backend.auth_views.requests.get', side_effect=[user_response, emails_response]
    ) as mock_get:
        response = client.get('/api/auth/github/callback/', {'code': 'github-code', 'state': state})

    assert response.status_code == 302
    redirect = urlparse(response['Location'])
    fragment = parse_qs(redirect.fragment)

    assert redirect.scheme == 'http'
    assert redirect.netloc == 'localhost:5173'
    assert redirect.path == '/login'
    assert fragment['oauth'] == ['success']
    assert fragment['provider'] == ['github']
    assert fragment['code']

    identity = ExternalAuthIdentity.objects.get(
        provider=ExternalAuthIdentity.Provider.GITHUB,
        provider_user_id='42',
    )
    assert identity.email == 'octocat@example.com'
    assert identity.display_name == 'Octo Cat'
    assert identity.avatar_url == 'https://example.com/octocat.png'
    mock_post.assert_called_once()
    assert mock_get.call_count == 2
