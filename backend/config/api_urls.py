"""
/api/v1/ URL configuration.
All DRF ViewSets and API views are registered here.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from apps.matches.views import MatchViewSet, TeamViewSet
from apps.picks.views import SelectionViewSet
from apps.leaderboard.views import LeaderboardView, MyRankView, LeaderboardHistoryView
from apps.users.views import RegisterView, MeView, SocialTokenView

router = DefaultRouter()
router.register('matches', MatchViewSet, basename='match')
router.register('teams', TeamViewSet, basename='team')
router.register('picks', SelectionViewSet, basename='pick')

urlpatterns = [
    # Auth
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/social/token/', SocialTokenView.as_view(), name='social_token'),

    # Leaderboard
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    path('leaderboard/me/', MyRankView.as_view(), name='leaderboard_me'),
    path('leaderboard/history/', LeaderboardHistoryView.as_view(), name='leaderboard_history'),

    # Notifications
    path('notifications/', include('apps.notifications.urls')),

    # Router-generated routes (matches, teams, picks)
    path('', include(router.urls)),

    # API Docs
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
