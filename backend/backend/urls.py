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

from ensembles.views import EnsembleViewSet, ArrangementViewSet, ArrangementByIdViewSet, ArrangementVersionViewSet, UploadArrangementVersionMsczView
from divisi.views import UploadMsczFile, FormatMsczFile

router = routers.DefaultRouter()
router.register(r'ensembles', EnsembleViewSet, 'ensemble')
router.register(r'arrangements', ArrangementViewSet, 'arrangement')
router.register(r'arrangements-by-id', ArrangementByIdViewSet, 'arrangement-by-id')
router.register(r'arrangementversions', ArrangementVersionViewSet, 'arrangementversion')

urlpatterns = [
    path('restricted/admin/', admin.site.urls),
    path('api/upload-mscz/', UploadMsczFile.as_view(), name='upload-mscz'),
    path('api/format-mscz/', FormatMsczFile.as_view(), name='format-mscz'),
    path('api/upload-arrangement-version/', UploadArrangementVersionMsczView.as_view(), name="upload-arrangement-version"),
    path('api/', include(router.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
