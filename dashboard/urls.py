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
    path("connections/<int:pk>/diffs/", views.diffs_view, name="diffs_view"),
    path("billing/", views.billing_view, name="billing_view"),
    path("billing/checkout/", views.start_checkout, name="start_checkout"),
]
