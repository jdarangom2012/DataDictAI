"""Endpoints POST /ask/ y GET /ask/history/ (Documento 03 SS3)."""

from unittest.mock import patch

import pytest
from allauth.account.models import EmailAddress
from rest_framework.test import APIClient

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
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def connection(user):
    conn = DatabaseConnection(user=user, name="Mine")
    conn.set_credentials(VALID_DSN)
    conn.save()
    return conn


@pytest.mark.django_db
def test_ask_creates_nl_query_and_returns_answer(client, connection):
    SchemaSnapshot.objects.create(connection=connection, raw_schema_json=RAW_SCHEMA)

    with patch(
        "connections.views.ask_question",
        return_value=NLQuery(
            connection=connection,
            user=connection.user,
            question="¿qué tabla tiene el email?",
            answer="La tabla users.",
            referenced_tables=["users"],
        ),
    ) as mock_ask:
        response = client.post(
            f"/api/v1/connections/{connection.id}/ask/",
            {"question": "¿qué tabla tiene el email?"},
            format="json",
        )

    assert response.status_code == 201
    assert response.data["answer"] == "La tabla users."
    assert response.data["referenced_tables"] == ["users"]
    mock_ask.assert_called_once()


@pytest.mark.django_db
def test_ask_rejects_empty_question(client, connection):
    response = client.post(f"/api/v1/connections/{connection.id}/ask/", {"question": "   "})

    assert response.status_code == 400
    assert response.data["error"]["code"] == "invalid_question"


@pytest.mark.django_db
def test_ask_returns_404_when_no_schema_yet(client, connection):
    response = client.post(
        f"/api/v1/connections/{connection.id}/ask/", {"question": "¿qué tablas hay?"}
    )

    assert response.status_code == 404
    assert response.data["error"]["code"] == "schema_not_available"


@pytest.mark.django_db
def test_ask_returns_503_when_ai_provider_fails(client, connection):
    SchemaSnapshot.objects.create(connection=connection, raw_schema_json=RAW_SCHEMA)

    with patch("connections.views.ask_question", side_effect=AIExplanationError("boom")):
        response = client.post(
            f"/api/v1/connections/{connection.id}/ask/", {"question": "¿qué tablas hay?"}
        )

    assert response.status_code == 503
    assert response.data["error"]["code"] == "ai_explanation_unavailable"


@pytest.mark.django_db
def test_ask_history_returns_previous_questions_newest_first(client, connection):
    NLQuery.objects.create(
        connection=connection, user=connection.user, question="primera", answer="a"
    )
    NLQuery.objects.create(
        connection=connection, user=connection.user, question="segunda", answer="b"
    )

    response = client.get(f"/api/v1/connections/{connection.id}/ask/history/")

    assert response.status_code == 200
    assert [item["question"] for item in response.data] == ["segunda", "primera"]


@pytest.mark.django_db
def test_cannot_ask_on_other_users_connection(django_user_model):
    other = django_user_model.objects.create_user(
        username="other", password="x", email="other@example.com"
    )
    _verify_email(other)
    theirs = DatabaseConnection(user=other, name="Theirs")
    theirs.set_credentials(VALID_DSN)
    theirs.save()

    intruder = django_user_model.objects.create_user(
        username="intruder", password="x", email="intruder@example.com"
    )
    _verify_email(intruder)
    api_client = APIClient()
    api_client.force_authenticate(user=intruder)

    response = api_client.post(
        f"/api/v1/connections/{theirs.id}/ask/", {"question": "¿qué tablas hay?"}
    )

    assert response.status_code == 404
