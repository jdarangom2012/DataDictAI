from django.urls import path

from accounts import views

urlpatterns = [
    path("checkout/", views.CheckoutView.as_view(), name="billing_checkout"),
    path("webhook/", views.WebhookView.as_view(), name="billing_webhook"),
    path("plan/", views.PlanView.as_view(), name="billing_plan"),
]
