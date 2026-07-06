from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from config.views import health_check
from connections.views import DatabaseConnectionViewSet

router = DefaultRouter()
router.register("connections", DatabaseConnectionViewSet, basename="connection")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health_check"),
    path("api/v1/", include(router.urls)),
    path("accounts/", include("allauth.urls")),
    path("", include("dashboard.urls")),
]
