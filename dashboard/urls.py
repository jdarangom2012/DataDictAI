from django.urls import path

from dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("connections/create/", views.create_connection, name="create_connection"),
    path("connections/<int:pk>/sync/", views.sync_connection, name="sync_connection"),
    path("connections/<int:pk>/schema/", views.schema_view, name="schema_view"),
    path("connections/<int:pk>/ask/", views.chat_view, name="chat_view"),
    path("connections/<int:pk>/ask/message/", views.ask_message, name="ask_message"),
]
