"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework import routers

from django.conf import settings

from core.views import GetWarningsView

from ensembles.views import (
    EnsembleViewSet,
    ArrangementViewSet,
    ArrangementByIdViewSet,
    ArrangementVersionViewSet,
    JoinEnsembleView,
)
from divisi.views import PartFormatterViewSet

from core.views import CurrentUserView, LogoutView, DirectDiscordLoginView, GetCsrfTokenView

divisi_router = routers.DefaultRouter()
divisi_router.register(r"part-formatter", PartFormatterViewSet, "part-formatter")

ensembles_router = routers.DefaultRouter()
ensembles_router.register(r"ensembles", EnsembleViewSet, "ensemble")
ensembles_router.register(r"arrangements", ArrangementViewSet, "arrangement")
ensembles_router.register(r"arrangements-by-id", ArrangementByIdViewSet, "arrangement-by-id")
ensembles_router.register(r"arrangementversions", ArrangementVersionViewSet, "arrangementversion")


urlpatterns = [
    path("restricted/admin/", admin.site.urls),
    path("api/get-warnings/", GetWarningsView.as_view(), name="get-warnings"),
    path("api/get-csrf-token/", GetCsrfTokenView.as_view(), name="get-csrf-token"),
    path("api/join/", JoinEnsembleView.as_view(), name="join-ensemble"),
    path("api/auth/current-user/", CurrentUserView.as_view(), name="current-user"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
    # Direct Discord login (skips allauth login page)
    path("api/auth/discord/login/", DirectDiscordLoginView.as_view(), name="direct-discord-login"),
    path("api/", include((divisi_router.urls, "divisi"), namespace="divisi")),
    path("api/", include((ensembles_router.urls, "ensembles"), namespace="ensembles")),
    # Django Allauth URLs for Discord OAuth (mounted under /api for consistency)
    path("api/accounts/", include("allauth.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
