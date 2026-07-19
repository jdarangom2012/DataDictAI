"""Cliente de LemonSqueezy: create_checkout, verificacion de firma, webhook events."""

import hashlib
import hmac
from unittest.mock import MagicMock, patch

import pytest
import requests

from accounts.billing import (
    BillingError,
    create_checkout,
    process_webhook_event,
    verify_webhook_signature,
)
from accounts.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="dev", password="x", email="dev@example.com"
    )


def _configure_lemonsqueezy_settings(settings):
    settings.LEMONSQUEEZY_API_KEY = "fake-key"
    settings.LEMONSQUEEZY_STORE_ID = "434530"
    settings.LEMONSQUEEZY_WEBHOOK_SECRET = "test-secret"
    settings.LEMONSQUEEZY_VARIANT_STARTER = "1924304"
    settings.LEMONSQUEEZY_VARIANT_PRO = "1924312"
    settings.LEMONSQUEEZY_VARIANT_TEAM = "1924356"


@pytest.mark.django_db
def test_create_checkout_returns_url(settings, user):
    _configure_lemonsqueezy_settings(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {"attributes": {"url": "https://datadictai.lemonsqueezy.com/checkout/abc"}}
    }
    mock_response.raise_for_status.return_value = None

    with patch("accounts.billing.requests.post", return_value=mock_response) as mock_post:
        url = create_checkout(user, "starter")

    assert url == "https://datadictai.lemonsqueezy.com/checkout/abc"
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["data"]["relationships"]["variant"]["data"]["id"] == "1924304"
    assert call_kwargs["json"]["data"]["attributes"]["checkout_data"]["custom"]["user_id"] == str(
        user.id
    )


@pytest.mark.django_db
def test_create_checkout_rejects_unknown_plan(settings, user):
    _configure_lemonsqueezy_settings(settings)
    with pytest.raises(BillingError):
        create_checkout(user, "enterprise")


@pytest.mark.django_db
def test_create_checkout_raises_on_provider_error(settings, user):
    _configure_lemonsqueezy_settings(settings)
    with patch("accounts.billing.requests.post", side_effect=requests.RequestException("boom")):
        with pytest.raises(BillingError):
            create_checkout(user, "starter")


def test_verify_webhook_signature_accepts_correct_signature(settings):
    settings.LEMONSQUEEZY_WEBHOOK_SECRET = "test-secret"
    body = b'{"meta": {"event_name": "subscription_created"}}'
    signature = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()

    assert verify_webhook_signature(body, signature) is True


def test_verify_webhook_signature_rejects_wrong_signature(settings):
    settings.LEMONSQUEEZY_WEBHOOK_SECRET = "test-secret"
    body = b'{"meta": {"event_name": "subscription_created"}}'

    assert verify_webhook_signature(body, "not-the-right-signature") is False


def test_verify_webhook_signature_rejects_empty_signature(settings):
    settings.LEMONSQUEEZY_WEBHOOK_SECRET = "test-secret"
    assert verify_webhook_signature(b"{}", "") is False


@pytest.mark.django_db
def test_process_webhook_event_upgrades_plan_on_active_subscription(settings, user):
    _configure_lemonsqueezy_settings(settings)
    payload = {
        "meta": {
            "event_name": "subscription_created",
            "custom_data": {"user_id": str(user.id)},
        },
        "data": {
            "attributes": {
                "status": "active",
                "variant_id": 1924312,
                "customer_id": 555,
            }
        },
    }

    process_webhook_event(payload)

    user.refresh_from_db()
    assert user.plan == "pro"
    assert user.lemonsqueezy_customer_id == "555"


@pytest.mark.django_db
def test_process_webhook_event_downgrades_plan_on_cancellation(settings, user):
    _configure_lemonsqueezy_settings(settings)
    user.plan = User.Plan.TEAM
    user.save(update_fields=["plan"])

    payload = {
        "meta": {
            "event_name": "subscription_cancelled",
            "custom_data": {"user_id": str(user.id)},
        },
        "data": {"attributes": {"status": "cancelled"}},
    }

    process_webhook_event(payload)

    user.refresh_from_db()
    assert user.plan == "starter"


@pytest.mark.django_db
def test_process_webhook_event_ignores_unknown_user(settings):
    _configure_lemonsqueezy_settings(settings)
    payload = {
        "meta": {"event_name": "subscription_created", "custom_data": {"user_id": "999999"}},
        "data": {"attributes": {"status": "active", "variant_id": 1924304}},
    }

    process_webhook_event(payload)  # no debe lanzar


@pytest.mark.django_db
def test_process_webhook_event_ignores_event_without_custom_data(settings, user):
    _configure_lemonsqueezy_settings(settings)
    payload = {"meta": {"event_name": "subscription_created"}, "data": {"attributes": {}}}

    process_webhook_event(payload)  # no debe lanzar

    user.refresh_from_db()
    assert user.plan == "starter"
