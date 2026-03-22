"""CricFun URL Configuration"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # DRF API v1
    path('api/v1/', include('config.api_urls')),

    # Allauth (Google OAuth + social login)
    path('accounts/', include('allauth.urls')),
]
