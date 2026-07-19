"""Limite de conexiones por plan (Documento 02 SS7, error plan_limit_reached)."""

import pytest
from allauth.account.models import EmailAddress
from rest_framework.test import APIClient

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
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
def test_starter_plan_blocks_second_connection(client, user):
    assert user.plan == "starter"
    first = DatabaseConnection(user=user, name="Uno")
    first.set_credentials(VALID_DSN)
    first.save()

    response = client.post(
        "/api/v1/connections/",
        {"name": "Dos", "connection_string": VALID_DSN},
        format="json",
    )

    assert response.status_code == 403
    assert response.data["error"]["code"] == "plan_limit_reached"
    assert DatabaseConnection.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_pro_plan_allows_up_to_five_connections(client, user):
    user.plan = "pro"
    user.save(update_fields=["plan"])

    for i in range(5):
        conn = DatabaseConnection(user=user, name=f"Conn {i}")
        conn.set_credentials(VALID_DSN)
        conn.save()

    response = client.post(
        "/api/v1/connections/",
        {"name": "Sexta", "connection_string": VALID_DSN},
        format="json",
    )

    assert response.status_code == 403
    assert response.data["error"]["code"] == "plan_limit_reached"


@pytest.mark.django_db
def test_pro_plan_can_create_within_limit(client, user):
    user.plan = "pro"
    user.save(update_fields=["plan"])

    response = client.post(
        "/api/v1/connections/",
        {"name": "Primera", "connection_string": VALID_DSN},
        format="json",
    )

    assert response.status_code == 201
