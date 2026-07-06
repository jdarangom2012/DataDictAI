"""generate_ai_docs: cache agresivo, fallback en error, regeneracion forzada."""

from unittest.mock import patch

import pytest

from ai_engine.client import NO_CONTEXT_EXPLANATION, AIExplanationError
from ai_engine.tasks import generate_ai_docs
from connections.models import DatabaseConnection
from introspection.models import SchemaSnapshot, TableDoc

RAW_SCHEMA = {
    "tables": {
        "orders": {
            "columns": [{"name": "id", "data_type": "integer", "is_nullable": False}],
            "row_count_estimate": 10,
        },
        "users": {
            "columns": [{"name": "id", "data_type": "integer", "is_nullable": False}],
            "row_count_estimate": 5,
        },
    }
}


@pytest.fixture
def snapshot(db, django_user_model):
    user = django_user_model.objects.create_user(username="dev", password="x")
    connection = DatabaseConnection(user=user, name="Test")
    connection.set_credentials("postgresql://user:pass@example.com:5432/db")
    connection.save()
    snap = SchemaSnapshot.objects.create(connection=connection, raw_schema_json=RAW_SCHEMA)
    TableDoc.objects.create(snapshot=snap, table_name="orders")
    TableDoc.objects.create(snapshot=snap, table_name="users")
    return snap


@pytest.mark.django_db
def test_generate_ai_docs_saves_explanation_for_each_table(snapshot):
    with patch("ai_engine.tasks.explain_table", return_value="Explicacion generada"):
        updated = generate_ai_docs(snapshot.id)

    assert updated == 2
    for table_doc in TableDoc.objects.filter(snapshot=snapshot):
        assert table_doc.ai_explanation == "Explicacion generada"


@pytest.mark.django_db
def test_generate_ai_docs_skips_tables_with_existing_explanation(snapshot):
    orders = TableDoc.objects.get(snapshot=snapshot, table_name="orders")
    orders.ai_explanation = "Ya documentada"
    orders.save(update_fields=["ai_explanation"])

    with patch("ai_engine.tasks.explain_table", return_value="Nueva explicacion") as mock_explain:
        updated = generate_ai_docs(snapshot.id)

    orders.refresh_from_db()
    assert orders.ai_explanation == "Ya documentada"
    assert updated == 1
    mock_explain.assert_called_once()


@pytest.mark.django_db
def test_generate_ai_docs_force_regenerates_all_tables(snapshot):
    orders = TableDoc.objects.get(snapshot=snapshot, table_name="orders")
    orders.ai_explanation = "Vieja explicacion"
    orders.save(update_fields=["ai_explanation"])

    with patch("ai_engine.tasks.explain_table", return_value="Explicacion regenerada"):
        updated = generate_ai_docs(snapshot.id, force=True)

    assert updated == 2
    orders.refresh_from_db()
    assert orders.ai_explanation == "Explicacion regenerada"


@pytest.mark.django_db
def test_generate_ai_docs_uses_fallback_when_ai_fails(snapshot):
    with patch("ai_engine.tasks.explain_table", side_effect=AIExplanationError("boom")):
        updated = generate_ai_docs(snapshot.id)

    assert updated == 2
    for table_doc in TableDoc.objects.filter(snapshot=snapshot):
        assert table_doc.ai_explanation == NO_CONTEXT_EXPLANATION
