"""generate_markdown(): documento exportable del ultimo esquema (Documento 01 SS5)."""

import pytest

from connections.models import DatabaseConnection
from exports.markdown import generate_markdown
from introspection.models import ColumnDoc, SchemaSnapshot, TableDoc


@pytest.fixture
def connection(db, django_user_model):
    user = django_user_model.objects.create_user(username="dev", password="x")
    conn = DatabaseConnection(user=user, name="Produccion")
    conn.set_credentials("postgresql://user:pass@example.com:5432/db")
    conn.save()
    return conn


@pytest.mark.django_db
def test_generate_markdown_includes_table_heading_and_columns(connection):
    snapshot = SchemaSnapshot.objects.create(connection=connection, raw_schema_json={})
    users = TableDoc.objects.create(
        snapshot=snapshot,
        table_name="users",
        ai_explanation="Guarda los usuarios registrados.",
        row_count_estimate=42,
    )
    ColumnDoc.objects.create(table=users, column_name="id", data_type="integer", is_nullable=False)
    ColumnDoc.objects.create(
        table=users,
        column_name="team_id",
        data_type="integer",
        is_nullable=True,
        is_foreign_key=True,
        references_table="teams",
    )

    markdown = generate_markdown(connection, snapshot)

    assert "# Esquema de base de datos: Produccion" in markdown
    assert "## users" in markdown
    assert "Guarda los usuarios registrados." in markdown
    assert "Filas estimadas: 42" in markdown
    assert "| id | integer | No |  |" in markdown
    assert "| team_id | integer | Si | -> teams |" in markdown


@pytest.mark.django_db
def test_generate_markdown_uses_fallback_text_when_no_ai_explanation(connection):
    snapshot = SchemaSnapshot.objects.create(connection=connection, raw_schema_json={})
    TableDoc.objects.create(snapshot=snapshot, table_name="orders")

    markdown = generate_markdown(connection, snapshot)

    assert "_Sin explicacion generada todavia._" in markdown


@pytest.mark.django_db
def test_generate_markdown_orders_tables_alphabetically(connection):
    snapshot = SchemaSnapshot.objects.create(connection=connection, raw_schema_json={})
    TableDoc.objects.create(snapshot=snapshot, table_name="zebra")
    TableDoc.objects.create(snapshot=snapshot, table_name="alpha")

    markdown = generate_markdown(connection, snapshot)

    assert markdown.index("## alpha") < markdown.index("## zebra")
