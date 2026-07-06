"""API de conexiones (Documento 03 SS3): nunca expone credenciales, aisla por
usuario, dispara introspeccion siempre via Celery (nunca de forma sincrona).
"""

from unittest.mock import patch

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
def other_user(django_user_model):
    created = django_user_model.objects.create_user(
        username="other", password="x", email="other@example.com"
    )
    _verify_email(created)
    return created


@pytest.fixture
def client(user):
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
def test_unauthenticated_request_is_rejected():
    response = APIClient().get("/api/v1/connections/")
    assert response.status_code == 401 or response.status_code == 403


@pytest.mark.django_db
def test_create_connection_encrypts_and_triggers_introspection(client, user):
    with patch("connections.views.introspect_database.delay") as mock_delay:
        response = client.post(
            "/api/v1/connections/",
            {"name": "Produccion", "connection_string": VALID_DSN},
            format="json",
        )

    assert response.status_code == 201
    connection = DatabaseConnection.objects.get(user=user)
    assert connection.name == "Produccion"
    assert connection.get_credentials() == VALID_DSN
    mock_delay.assert_called_once_with(connection.id)


@pytest.mark.django_db
def test_create_response_never_includes_credentials(client):
    with patch("connections.views.introspect_database.delay"):
        response = client.post(
            "/api/v1/connections/",
            {"name": "Produccion", "connection_string": VALID_DSN},
            format="json",
        )

    body = response.content.decode()
    assert "connection_string" not in response.data
    assert "encrypted_credentials" not in body
    assert "s3cr3t" not in body


@pytest.mark.django_db
def test_create_rejects_invalid_connection_string_format(client):
    response = client.post(
        "/api/v1/connections/",
        {"name": "Malo", "connection_string": "not-a-connection-string"},
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "invalid_credentials_format"
    assert response.data["error"]["field"] == "connection_string"
    assert DatabaseConnection.objects.count() == 0


@pytest.mark.django_db
def test_create_rejects_connection_string_without_database_name(client):
    response = client.post(
        "/api/v1/connections/",
        {"name": "Malo", "connection_string": "postgresql://user:pass@host:5432/"},
        format="json",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "invalid_credentials_format"


@pytest.mark.django_db
def test_list_only_returns_own_connections(client, user, other_user):
    own = DatabaseConnection(user=user, name="Mine")
    own.set_credentials(VALID_DSN)
    own.save()

    theirs = DatabaseConnection(user=other_user, name="Theirs")
    theirs.set_credentials(VALID_DSN)
    theirs.save()

    response = client.get("/api/v1/connections/")

    assert response.status_code == 200
    names = {item["name"] for item in response.data}
    assert names == {"Mine"}


@pytest.mark.django_db
def test_retrieve_own_connection(client, user):
    connection = DatabaseConnection(user=user, name="Mine")
    connection.set_credentials(VALID_DSN)
    connection.save()

    response = client.get(f"/api/v1/connections/{connection.id}/")

    assert response.status_code == 200
    assert response.data["name"] == "Mine"
    assert "connection_string" not in response.data


@pytest.mark.django_db
def test_cannot_retrieve_other_users_connection(client, other_user):
    theirs = DatabaseConnection(user=other_user, name="Theirs")
    theirs.set_credentials(VALID_DSN)
    theirs.save()

    response = client.get(f"/api/v1/connections/{theirs.id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_connection_removes_row(client, user):
    connection = DatabaseConnection(user=user, name="Mine")
    connection.set_credentials(VALID_DSN)
    connection.save()

    response = client.delete(f"/api/v1/connections/{connection.id}/")

    assert response.status_code == 204
    assert not DatabaseConnection.objects.filter(pk=connection.id).exists()


@pytest.mark.django_db
def test_cannot_delete_other_users_connection(client, other_user):
    theirs = DatabaseConnection(user=other_user, name="Theirs")
    theirs.set_credentials(VALID_DSN)
    theirs.save()

    response = client.delete(f"/api/v1/connections/{theirs.id}/")

    assert response.status_code == 404
    assert DatabaseConnection.objects.filter(pk=theirs.id).exists()


@pytest.mark.django_db
def test_sync_triggers_introspection(client, user):
    connection = DatabaseConnection(user=user, name="Mine")
    connection.set_credentials(VALID_DSN)
    connection.save()

    with patch("connections.views.introspect_database.delay") as mock_delay:
        response = client.post(f"/api/v1/connections/{connection.id}/sync/")

    assert response.status_code == 202
    mock_delay.assert_called_once_with(connection.id)


@pytest.mark.django_db
def test_cannot_sync_other_users_connection(client, other_user):
    theirs = DatabaseConnection(user=other_user, name="Theirs")
    theirs.set_credentials(VALID_DSN)
    theirs.save()

    with patch("connections.views.introspect_database.delay") as mock_delay:
        response = client.post(f"/api/v1/connections/{theirs.id}/sync/")

    assert response.status_code == 404
    mock_delay.assert_not_called()


@pytest.mark.django_db
def test_create_rejects_user_with_unverified_email(django_user_model):
    unverified_user = django_user_model.objects.create_user(
        username="unverified", password="x", email="unverified@example.com"
    )
    EmailAddress.objects.create(
        user=unverified_user, email=unverified_user.email, verified=False, primary=True
    )
    api_client = APIClient()
    api_client.force_authenticate(user=unverified_user)

    response = api_client.post(
        "/api/v1/connections/",
        {"name": "Produccion", "connection_string": VALID_DSN},
        format="json",
    )

    assert response.status_code == 403
    assert DatabaseConnection.objects.count() == 0
