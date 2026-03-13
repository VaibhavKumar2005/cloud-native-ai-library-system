"""
URL configuration for rag_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from .auth_views import (
    AuthProvidersView,
    AuthSessionView,
    GitHubOAuthCallbackView,
    GitHubOAuthStartView,
    GoogleOAuthCallbackView,
    GoogleOAuthStartView,
    OAuthExchangeView,
    ThrottledTokenObtainPairView,
)

# 1. Add this import for the Swagger UI
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('ai_engine.urls')), 
    path('', include('django_prometheus.urls')), 

    # 🚨 ADD THESE TWO LINES: This is what the frontend is looking for
    path('api/token/', ThrottledTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/providers/', AuthProvidersView.as_view(), name='auth_providers'),
    path('api/auth/session/', AuthSessionView.as_view(), name='auth_session'),
    path('api/auth/exchange/', OAuthExchangeView.as_view(), name='auth_exchange'),
    path('api/auth/google/start/', GoogleOAuthStartView.as_view(), name='google_oauth_start'),
    path('api/auth/google/callback/', GoogleOAuthCallbackView.as_view(), name='google_oauth_callback'),
    path('api/auth/github/start/', GitHubOAuthStartView.as_view(), name='github_oauth_start'),
    path('api/auth/github/callback/', GitHubOAuthCallbackView.as_view(), name='github_oauth_callback'),
    
    # 2. Add these two lines for the API Interface
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
