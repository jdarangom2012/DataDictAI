"""build_diagram: nodos/edges para el diagrama ER (Documento 03 SS3/SS6)."""

import pytest

from connections.models import DatabaseConnection
from introspection.diagram import build_diagram
from introspection.models import ColumnDoc, SchemaSnapshot, TableDoc


@pytest.fixture
def connection(db, django_user_model):
    user = django_user_model.objects.create_user(username="dev", password="x")
    conn = DatabaseConnection(user=user, name="Test")
    conn.set_credentials("postgresql://user:pass@example.com:5432/db")
    conn.save()
    return conn


@pytest.mark.django_db
def test_build_diagram_creates_a_node_per_table_with_its_columns(connection):
    snapshot = SchemaSnapshot.objects.create(connection=connection, raw_schema_json={})
    users = TableDoc.objects.create(snapshot=snapshot, table_name="users")
    ColumnDoc.objects.create(table=users, column_name="id", data_type="integer", is_nullable=False)
    ColumnDoc.objects.create(table=users, column_name="email", data_type="text", is_nullable=False)

    diagram = build_diagram(snapshot)

    assert len(diagram["nodes"]) == 1
    node = diagram["nodes"][0]
    assert node["id"] == "users"
    column_names = {c["name"] for c in node["columns"]}
    assert column_names == {"id", "email"}


@pytest.mark.django_db
def test_build_diagram_creates_edge_for_foreign_key_to_existing_table(connection):
    snapshot = SchemaSnapshot.objects.create(connection=connection, raw_schema_json={})
    users = TableDoc.objects.create(snapshot=snapshot, table_name="users")
    ColumnDoc.objects.create(table=users, column_name="id", data_type="integer", is_nullable=False)

    orders = TableDoc.objects.create(snapshot=snapshot, table_name="orders")
    ColumnDoc.objects.create(
        table=orders,
        column_name="user_id",
        data_type="integer",
        is_nullable=False,
        is_foreign_key=True,
        references_table="users",
    )

    diagram = build_diagram(snapshot)

    assert len(diagram["edges"]) == 1
    edge = diagram["edges"][0]
    assert edge["source"] == "orders"
    assert edge["target"] == "users"
    assert edge["label"] == "user_id"


@pytest.mark.django_db
def test_build_diagram_drops_edges_pointing_to_a_table_not_in_the_snapshot(connection):
    snapshot = SchemaSnapshot.objects.create(connection=connection, raw_schema_json={})
    orders = TableDoc.objects.create(snapshot=snapshot, table_name="orders")
    ColumnDoc.objects.create(
        table=orders,
        column_name="ghost_id",
        data_type="integer",
        is_nullable=True,
        is_foreign_key=True,
        references_table="table_not_in_this_snapshot",
    )

    diagram = build_diagram(snapshot)

    assert diagram["edges"] == []


@pytest.mark.django_db
def test_build_diagram_with_no_tables_returns_empty_lists(connection):
    snapshot = SchemaSnapshot.objects.create(connection=connection, raw_schema_json={})

    diagram = build_diagram(snapshot)

    assert diagram == {"nodes": [], "edges": []}
