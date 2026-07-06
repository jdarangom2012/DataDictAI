from django.urls import path

from dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("connections/create/", views.create_connection, name="create_connection"),
    path("connections/<int:pk>/sync/", views.sync_connection, name="sync_connection"),
]
