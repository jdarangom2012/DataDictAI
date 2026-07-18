"""Vistas de dashboard/onboarding: gate de autenticacion, gate de email
verificado (Documento 04), y el flujo HTMX de crear/sincronizar conexiones.
"""

from unittest.mock import patch

import pytest
from allauth.account.models import EmailAddress
from django.test import Client

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
def test_anonymous_user_is_redirected_to_login():
    response = Client().get("/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_home_shows_onboarding_form_when_no_connections(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Conecta tu primera base de datos" in response.content.decode()


@pytest.mark.django_db
def test_home_shows_connection_list_when_connections_exist(client, user):
    connection = DatabaseConnection(user=user, name="Produccion")
    connection.set_credentials(VALID_DSN)
    connection.save()

    response = client.get("/")

    body = response.content.decode()
    assert response.status_code == 200
    assert "Produccion" in body
    assert "+ Nueva conexion" in body


@pytest.mark.django_db
def test_create_connection_encrypts_and_triggers_introspection(client, user):
    with patch("dashboard.views.introspect_database.delay") as mock_delay:
        response = client.post(
            "/connections/create/",
            {"name": "Produccion", "connection_string": VALID_DSN},
        )

    assert response.status_code == 200
    connection = DatabaseConnection.objects.get(user=user)
    assert connection.get_credentials() == VALID_DSN
    mock_delay.assert_called_once_with(connection.id)
    assert "Produccion" in response.content.decode()


@pytest.mark.django_db
def test_create_connection_shows_error_on_invalid_format(client):
    response = client.post(
        "/connections/create/",
        {"name": "Malo", "connection_string": "not-a-connection-string"},
    )

    assert response.status_code == 400
    assert DatabaseConnection.objects.count() == 0
    assert "esquema postgres" in response.content.decode()


@pytest.mark.django_db
def test_create_connection_blocked_when_email_not_verified(django_user_model):
    unverified_user = django_user_model.objects.create_user(
        username="unverified", password="x", email="unverified@example.com"
    )
    EmailAddress.objects.create(
        user=unverified_user, email=unverified_user.email, verified=False, primary=True
    )
    c = Client()
    c.force_login(unverified_user)

    response = c.post(
        "/connections/create/",
        {"name": "Produccion", "connection_string": VALID_DSN},
    )

    assert response.status_code == 403
    assert "verificar tu email" in response.content.decode()
    assert DatabaseConnection.objects.count() == 0


@pytest.mark.django_db
def test_sync_connection_triggers_introspection(client, user):
    connection = DatabaseConnection(user=user, name="Mine")
    connection.set_credentials(VALID_DSN)
    connection.save()

    with patch("dashboard.views.introspect_database.delay") as mock_delay:
        response = client.post(f"/connections/{connection.id}/sync/")

    assert response.status_code == 200
    mock_delay.assert_called_once_with(connection.id)


@pytest.mark.django_db
def test_cannot_sync_other_users_connection(client, django_user_model):
    other_user = django_user_model.objects.create_user(
        username="other", password="x", email="other@example.com"
    )
    theirs = DatabaseConnection(user=other_user, name="Theirs")
    theirs.set_credentials(VALID_DSN)
    theirs.save()

    with patch("dashboard.views.introspect_database.delay") as mock_delay:
        response = client.post(f"/connections/{theirs.id}/sync/")

    assert response.status_code == 404
    mock_delay.assert_not_called()


@pytest.mark.django_db
def test_schema_view_renders_for_own_connection(client, user):
    connection = DatabaseConnection(user=user, name="Mine")
    connection.set_credentials(VALID_DSN)
    connection.save()

    response = client.get(f"/connections/{connection.id}/schema/")

    assert response.status_code == 200
    assert b"schemaView(" in response.content
    assert "Mine" in response.content.decode()


@pytest.mark.django_db
def test_schema_view_404_for_other_users_connection(client, django_user_model):
    other_user = django_user_model.objects.create_user(
        username="other", password="x", email="other@example.com"
    )
    theirs = DatabaseConnection(user=other_user, name="Theirs")
    theirs.set_credentials(VALID_DSN)
    theirs.save()

    response = client.get(f"/connections/{theirs.id}/schema/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_schema_view_requires_login():
    connection_owner_response = Client().get("/connections/1/schema/")
    assert connection_owner_response.status_code == 302
    assert "/accounts/login/" in connection_owner_response.url
