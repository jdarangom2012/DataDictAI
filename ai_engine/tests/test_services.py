"""ask_question(): orquesta snapshot -> answer_question -> NLQuery."""

from unittest.mock import patch

import pytest

from ai_engine.client import AIExplanationError
from ai_engine.models import NLQuery
from ai_engine.services import NoSchemaAvailableError, ask_question
from connections.models import DatabaseConnection
from introspection.models import SchemaSnapshot

RAW_SCHEMA = {
    "tables": {
        "users": {"columns": [{"name": "email", "data_type": "text", "is_nullable": False}]},
        "orders": {"columns": [{"name": "id", "data_type": "integer", "is_nullable": False}]},
    }
}


@pytest.fixture
def connection(db, django_user_model):
    user = django_user_model.objects.create_user(username="dev", password="x")
    conn = DatabaseConnection(user=user, name="Test")
    conn.set_credentials("postgresql://user:pass@example.com:5432/db")
    conn.save()
    return conn


@pytest.mark.django_db
def test_raises_when_no_snapshot_exists(connection):
    with pytest.raises(NoSchemaAvailableError):
        ask_question(connection, connection.user, "¿qué tablas hay?")


@pytest.mark.django_db
def test_creates_nl_query_with_referenced_tables(connection):
    SchemaSnapshot.objects.create(connection=connection, raw_schema_json=RAW_SCHEMA)

    with patch(
        "ai_engine.services.answer_question",
        return_value="La tabla users guarda el email.",
    ):
        nl_query = ask_question(connection, connection.user, "¿qué tabla tiene el email?")

    assert isinstance(nl_query, NLQuery)
    assert nl_query.question == "¿qué tabla tiene el email?"
    assert nl_query.answer == "La tabla users guarda el email."
    assert nl_query.referenced_tables == ["users"]
    assert nl_query.connection_id == connection.id
    assert nl_query.user_id == connection.user_id


@pytest.mark.django_db
def test_uses_the_most_recent_snapshot(connection):
    SchemaSnapshot.objects.create(connection=connection, raw_schema_json={"tables": {}})
    SchemaSnapshot.objects.create(connection=connection, raw_schema_json=RAW_SCHEMA)

    with patch("ai_engine.services.answer_question", return_value="ok") as mock_answer:
        ask_question(connection, connection.user, "¿qué tablas hay?")

    mock_answer.assert_called_once_with("¿qué tablas hay?", RAW_SCHEMA)


@pytest.mark.django_db
def test_propagates_ai_explanation_error(connection):
    SchemaSnapshot.objects.create(connection=connection, raw_schema_json=RAW_SCHEMA)

    with patch("ai_engine.services.answer_question", side_effect=AIExplanationError("boom")):
        with pytest.raises(AIExplanationError):
            ask_question(connection, connection.user, "¿qué tablas hay?")

    assert NLQuery.objects.count() == 0
