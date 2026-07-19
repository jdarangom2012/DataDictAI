"""Endpoints /api/v1/billing/checkout/, /webhook/, /plan/ (Documento 03 SS3)."""

import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from accounts.billing import BillingError
from accounts.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(username="dev", password="x", email="dev@example.com")


@pytest.fixture
def client(user):
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


def _configure_lemonsqueezy_settings(settings):
    settings.LEMONSQUEEZY_API_KEY = "fake-key"
    settings.LEMONSQUEEZY_STORE_ID = "434530"
    settings.LEMONSQUEEZY_WEBHOOK_SECRET = "test-secret"
    settings.LEMONSQUEEZY_VARIANT_STARTER = "1924304"
    settings.LEMONSQUEEZY_VARIANT_PRO = "1924312"
    settings.LEMONSQUEEZY_VARIANT_TEAM = "1924356"


@pytest.mark.django_db
def test_checkout_returns_url_for_valid_plan(client, settings):
    _configure_lemonsqueezy_settings(settings)
    with patch(
        "accounts.views.create_checkout", return_value="https://datadictai.lemonsqueezy.com/x"
    ):
        response = client.post("/api/v1/billing/checkout/", {"plan": "pro"})

    assert response.status_code == 201
    assert response.data["checkout_url"] == "https://datadictai.lemonsqueezy.com/x"


@pytest.mark.django_db
def test_checkout_rejects_invalid_plan(client):
    response = client.post("/api/v1/billing/checkout/", {"plan": "enterprise"})

    assert response.status_code == 400
    assert response.data["error"]["field"] == "plan"


@pytest.mark.django_db
def test_checkout_returns_503_when_provider_fails(client):
    with patch("accounts.views.create_checkout", side_effect=BillingError("boom")):
        response = client.post("/api/v1/billing/checkout/", {"plan": "starter"})

    assert response.status_code == 503
    assert response.data["error"]["code"] == "billing_unavailable"


@pytest.mark.django_db
def test_checkout_requires_authentication():
    response = APIClient().post("/api/v1/billing/checkout/", {"plan": "starter"})
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_plan_returns_current_users_plan(client, user):
    response = client.get("/api/v1/billing/plan/")

    assert response.status_code == 200
    assert response.data["plan"] == "starter"


@pytest.mark.django_db
def test_webhook_updates_plan_with_valid_signature(settings, user):
    _configure_lemonsqueezy_settings(settings)
    payload = {
        "meta": {
            "event_name": "subscription_created",
            "custom_data": {"user_id": str(user.id)},
        },
        "data": {"attributes": {"status": "active", "variant_id": 1924356, "customer_id": 1}},
    }
    body = json.dumps(payload).encode()
    signature = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()

    response = APIClient().post(
        "/api/v1/billing/webhook/",
        data=body,
        content_type="application/json",
        HTTP_X_SIGNATURE=signature,
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.plan == "team"


@pytest.mark.django_db
def test_webhook_rejects_invalid_signature(settings, user):
    _configure_lemonsqueezy_settings(settings)
    payload = {
        "meta": {"event_name": "subscription_created", "custom_data": {"user_id": str(user.id)}},
        "data": {"attributes": {"status": "active", "variant_id": 1924356}},
    }
    body = json.dumps(payload).encode()

    response = APIClient().post(
        "/api/v1/billing/webhook/",
        data=body,
        content_type="application/json",
        HTTP_X_SIGNATURE="wrong-signature",
    )

    assert response.status_code == 401
    user.refresh_from_db()
    assert user.plan == "starter"


@pytest.mark.django_db
def test_webhook_does_not_require_session_authentication(settings, user):
    """LemonSqueezy llama este endpoint sin sesion ni CSRF -- solo firma."""
    _configure_lemonsqueezy_settings(settings)
    payload = {
        "meta": {"event_name": "subscription_created", "custom_data": {"user_id": str(user.id)}},
        "data": {"attributes": {"status": "active", "variant_id": 1924304}},
    }
    body = json.dumps(payload).encode()
    signature = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()

    response = APIClient(enforce_csrf_checks=True).post(
        "/api/v1/billing/webhook/",
        data=body,
        content_type="application/json",
        HTTP_X_SIGNATURE=signature,
    )

    assert response.status_code == 200
