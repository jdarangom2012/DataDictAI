"""Vista de chat HTMX: historial, envio de preguntas, aislamiento por usuario."""

from unittest.mock import patch

import pytest
from allauth.account.models import EmailAddress
from django.test import Client

from ai_engine.client import AIExplanationError
from ai_engine.models import NLQuery
from connections.models import DatabaseConnection
from introspection.models import SchemaSnapshot

VALID_DSN = "postgresql://readonly_user:s3cr3t@db.example.com:5432/prod"
RAW_SCHEMA = {
    "tables": {
        "users": {"columns": [{"name": "email", "data_type": "text", "is_nullable": False}]},
    }
}


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


@pytest.fixture
def connection(user):
    conn = DatabaseConnection(user=user, name="Mine")
    conn.set_credentials(VALID_DSN)
    conn.save()
    return conn


@pytest.mark.django_db
def test_chat_view_shows_empty_state_with_no_history(client, connection):
    response = client.get(f"/connections/{connection.id}/ask/")

    assert response.status_code == 200
    assert "Pregunta algo" in response.content.decode()


@pytest.mark.django_db
def test_chat_view_lists_history_chronologically(client, connection):
    NLQuery.objects.create(
        connection=connection, user=connection.user, question="primera", answer="a"
    )
    NLQuery.objects.create(
        connection=connection, user=connection.user, question="segunda", answer="b"
    )

    response = client.get(f"/connections/{connection.id}/ask/")

    body = response.content.decode()
    assert body.index("primera") < body.index("segunda")


@pytest.mark.django_db
def test_ask_message_creates_nl_query_and_renders_fragment(client, connection):
    SchemaSnapshot.objects.create(connection=connection, raw_schema_json=RAW_SCHEMA)

    with patch(
        "dashboard.views.ask_question",
        return_value=NLQuery(
            connection=connection,
            user=connection.user,
            question="¿qué tabla tiene el email?",
            answer="La tabla users.",
            referenced_tables=["users"],
        ),
    ):
        response = client.post(
            f"/connections/{connection.id}/ask/message/",
            {"question": "¿qué tabla tiene el email?"},
        )

    assert response.status_code == 200
    body = response.content.decode()
    assert "La tabla users." in body
    assert "users" in body


@pytest.mark.django_db
def test_ask_message_rejects_empty_question(client, connection):
    response = client.post(f"/connections/{connection.id}/ask/message/", {"question": "   "})

    # htmx no hace swap en 4xx/5xx por defecto -- estos errores se devuelven
    # como 200 a proposito para que el mensaje sea visible en pantalla.
    assert response.status_code == 200


@pytest.mark.django_db
def test_ask_message_shows_error_when_no_schema_yet(client, connection):
    response = client.post(
        f"/connections/{connection.id}/ask/message/", {"question": "¿qué tablas hay?"}
    )

    assert response.status_code == 200
    assert "esquema sincronizado" in response.content.decode()


@pytest.mark.django_db
def test_ask_message_shows_error_when_ai_unavailable(client, connection):
    SchemaSnapshot.objects.create(connection=connection, raw_schema_json=RAW_SCHEMA)

    with patch("dashboard.views.ask_question", side_effect=AIExplanationError("boom")):
        response = client.post(
            f"/connections/{connection.id}/ask/message/", {"question": "¿qué tablas hay?"}
        )

    assert response.status_code == 200


@pytest.mark.django_db
def test_cannot_chat_on_other_users_connection(client, django_user_model):
    other_user = django_user_model.objects.create_user(
        username="other", password="x", email="other@example.com"
    )
    theirs = DatabaseConnection(user=other_user, name="Theirs")
    theirs.set_credentials(VALID_DSN)
    theirs.save()

    response = client.get(f"/connections/{theirs.id}/ask/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_chat_view_requires_login():
    response = Client().get("/connections/1/ask/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.url
