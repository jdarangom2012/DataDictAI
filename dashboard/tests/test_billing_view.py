"""Vista de planes + limite de conexiones en la vista HTMX (Documento 03 SS6)."""

from unittest.mock import patch

import pytest
from allauth.account.models import EmailAddress
from django.test import Client

from accounts.billing import BillingError
from connections.models import DatabaseConnection

VALID_DSN = "postgresql://readonly_user:s3cr3t@db.example.com:5432/prod"


def _verify_email(user):
    EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)


@pytest.fixture
def user(django_user_model):
    created = django_user_model.objects.create_user(
        username="dev", password="x", email="dev@example.com"
    )
    _verify_email(created)
    return created


@pytest.fixture
def client(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_billing_view_shows_current_plan(client):
    response = client.get("/billing/")

    assert response.status_code == 200
    body = response.content.decode()
    assert "Starter" in body
    assert "Pro" in body
    assert "Team" in body


@pytest.mark.django_db
def test_billing_view_requires_login():
    response = Client().get("/billing/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_start_checkout_redirects_via_hx_redirect_header(client):
    with patch(
        "dashboard.views.create_checkout", return_value="https://datadictai.lemonsqueezy.com/x"
    ):
        response = client.post("/billing/checkout/", {"plan": "pro"})

    assert response.status_code == 200
    assert response["HX-Redirect"] == "https://datadictai.lemonsqueezy.com/x"


@pytest.mark.django_db
def test_start_checkout_shows_error_for_invalid_plan(client):
    response = client.post("/billing/checkout/", {"plan": "enterprise"})

    assert response.status_code == 200
    assert "Plan invalido" in response.content.decode()
    assert "HX-Redirect" not in response


@pytest.mark.django_db
def test_start_checkout_shows_error_when_provider_fails(client):
    with patch("dashboard.views.create_checkout", side_effect=BillingError("boom")):
        response = client.post("/billing/checkout/", {"plan": "starter"})

    assert response.status_code == 200
    assert "No pudimos iniciar el pago" in response.content.decode()


@pytest.mark.django_db
def test_create_connection_blocked_at_plan_limit(client, user):
    first = DatabaseConnection(user=user, name="Uno")
    first.set_credentials(VALID_DSN)
    first.save()

    with patch("dashboard.views.introspect_database.delay") as mock_delay:
        response = client.post(
            "/connections/create/", {"name": "Dos", "connection_string": VALID_DSN}
        )

    assert response.status_code == 200
    assert "Alcanzaste el limite" in response.content.decode()
    assert DatabaseConnection.objects.filter(user=user).count() == 1
    mock_delay.assert_not_called()
