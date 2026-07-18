"""Endpoints /schema/, /diagram/, /schema/tables/{name}/ (Documento 03 SS3)."""

import pytest
from allauth.account.models import EmailAddress
from rest_framework.test import APIClient

from connections.models import DatabaseConnection
from introspection.models import ColumnDoc, SchemaSnapshot, TableDoc

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


@pytest.fixture
def connection(user):
    conn = DatabaseConnection(user=user, name="Mine")
    conn.set_credentials(VALID_DSN)
    conn.save()
    return conn


@pytest.fixture
def snapshot(connection):
    snap = SchemaSnapshot.objects.create(connection=connection, raw_schema_json={})
    users = TableDoc.objects.create(
        snapshot=snap, table_name="users", ai_explanation="Guarda usuarios."
    )
    ColumnDoc.objects.create(table=users, column_name="id", data_type="integer", is_nullable=False)
    orders = TableDoc.objects.create(snapshot=snap, table_name="orders")
    ColumnDoc.objects.create(
        table=orders,
        column_name="user_id",
        data_type="integer",
        is_nullable=False,
        is_foreign_key=True,
        references_table="users",
    )
    return snap


@pytest.mark.django_db
def test_schema_endpoint_returns_latest_snapshot(client, connection, snapshot):
    response = client.get(f"/api/v1/connections/{connection.id}/schema/")

    assert response.status_code == 200
    table_names = {t["table_name"] for t in response.data["tables"]}
    assert table_names == {"users", "orders"}


@pytest.mark.django_db
def test_schema_endpoint_404_when_no_snapshot_yet(client, connection):
    response = client.get(f"/api/v1/connections/{connection.id}/schema/")

    assert response.status_code == 404
    assert response.data["error"]["code"] == "schema_not_available"


@pytest.mark.django_db
def test_diagram_endpoint_returns_nodes_and_edges(client, connection, snapshot):
    response = client.get(f"/api/v1/connections/{connection.id}/diagram/")

    assert response.status_code == 200
    node_ids = {n["id"] for n in response.data["nodes"]}
    assert node_ids == {"users", "orders"}
    assert len(response.data["edges"]) == 1
    assert response.data["edges"][0]["source"] == "orders"
    assert response.data["edges"][0]["target"] == "users"


@pytest.mark.django_db
def test_diagram_endpoint_404_when_no_snapshot_yet(client, connection):
    response = client.get(f"/api/v1/connections/{connection.id}/diagram/")

    assert response.status_code == 404
    assert response.data["error"]["code"] == "schema_not_available"


@pytest.mark.django_db
def test_table_detail_returns_columns_and_ai_explanation(client, connection, snapshot):
    response = client.get(f"/api/v1/connections/{connection.id}/schema/tables/users/")

    assert response.status_code == 200
    assert response.data["table_name"] == "users"
    assert response.data["ai_explanation"] == "Guarda usuarios."
    assert response.data["columns"][0]["column_name"] == "id"


@pytest.mark.django_db
def test_table_detail_404_for_unknown_table(client, connection, snapshot):
    response = client.get(f"/api/v1/connections/{connection.id}/schema/tables/does_not_exist/")

    assert response.status_code == 404
    assert response.data["error"]["code"] == "table_not_found"


@pytest.mark.django_db
def test_schema_endpoint_404_for_other_users_connection(django_user_model):
    other = django_user_model.objects.create_user(
        username="other", password="x", email="other@example.com"
    )
    _verify_email(other)
    theirs = DatabaseConnection(user=other, name="Theirs")
    theirs.set_credentials(VALID_DSN)
    theirs.save()
    SchemaSnapshot.objects.create(connection=theirs, raw_schema_json={})

    intruder = django_user_model.objects.create_user(
        username="intruder", password="x", email="intruder@example.com"
    )
    _verify_email(intruder)
    api_client = APIClient()
    api_client.force_authenticate(user=intruder)

    response = api_client.get(f"/api/v1/connections/{theirs.id}/schema/")

    assert response.status_code == 404
