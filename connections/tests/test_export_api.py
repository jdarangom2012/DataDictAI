"""Endpoint GET /export/markdown/ (Documento 03 SS3)."""

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
    conn = DatabaseConnection(user=user, name="Mi Base")
    conn.set_credentials(VALID_DSN)
    conn.save()
    return conn


@pytest.mark.django_db
def test_export_markdown_returns_downloadable_file(client, connection):
    snapshot = SchemaSnapshot.objects.create(connection=connection, raw_schema_json={})
    users = TableDoc.objects.create(snapshot=snapshot, table_name="users")
    ColumnDoc.objects.create(table=users, column_name="id", data_type="integer", is_nullable=False)

    response = client.get(f"/api/v1/connections/{connection.id}/export/markdown/")

    assert response.status_code == 200
    assert response["Content-Type"] == "text/markdown; charset=utf-8"
    assert "attachment" in response["Content-Disposition"]
    assert ".md" in response["Content-Disposition"]
    body = response.content.decode()
    assert "## users" in body
    assert "Mi Base" in body


@pytest.mark.django_db
def test_export_markdown_404_when_no_snapshot_yet(client, connection):
    response = client.get(f"/api/v1/connections/{connection.id}/export/markdown/")

    assert response.status_code == 404
    assert response.data["error"]["code"] == "schema_not_available"


@pytest.mark.django_db
def test_cannot_export_other_users_connection(django_user_model):
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

    response = api_client.get(f"/api/v1/connections/{theirs.id}/export/markdown/")

    assert response.status_code == 404
