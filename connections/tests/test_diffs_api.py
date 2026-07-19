"""Endpoint GET /diffs/ (Documento 03 SS3: 'historial de cambios entre snapshots')."""

import pytest
from allauth.account.models import EmailAddress
from rest_framework.test import APIClient

from connections.models import DatabaseConnection
from introspection.models import SchemaSnapshot
from snapshots.models import SchemaDiff

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


@pytest.mark.django_db
def test_diffs_endpoint_returns_empty_list_when_no_diffs_yet(client, connection):
    response = client.get(f"/api/v1/connections/{connection.id}/diffs/")

    assert response.status_code == 200
    assert response.data == []


@pytest.mark.django_db
def test_diffs_endpoint_returns_diff_history_newest_first(client, connection):
    snap_a = SchemaSnapshot.objects.create(connection=connection, raw_schema_json={"tables": {}})
    snap_b = SchemaSnapshot.objects.create(
        connection=connection, raw_schema_json={"tables": {"orders": {"columns": []}}}
    )
    snap_c = SchemaSnapshot.objects.create(
        connection=connection,
        raw_schema_json={"tables": {"orders": {"columns": []}, "users": {"columns": []}}},
    )
    SchemaDiff.objects.create(
        connection=connection,
        from_snapshot=snap_a,
        to_snapshot=snap_b,
        changes_json={"tables_added": ["orders"], "tables_removed": [], "tables_changed": {}},
    )
    SchemaDiff.objects.create(
        connection=connection,
        from_snapshot=snap_b,
        to_snapshot=snap_c,
        changes_json={"tables_added": ["users"], "tables_removed": [], "tables_changed": {}},
    )

    response = client.get(f"/api/v1/connections/{connection.id}/diffs/")

    assert response.status_code == 200
    assert len(response.data) == 2
    assert response.data[0]["changes_json"]["tables_added"] == ["users"]
    assert response.data[1]["changes_json"]["tables_added"] == ["orders"]


@pytest.mark.django_db
def test_cannot_see_other_users_diffs(django_user_model):
    other = django_user_model.objects.create_user(
        username="other", password="x", email="other@example.com"
    )
    _verify_email(other)
    theirs = DatabaseConnection(user=other, name="Theirs")
    theirs.set_credentials(VALID_DSN)
    theirs.save()
    snap_a = SchemaSnapshot.objects.create(connection=theirs, raw_schema_json={"tables": {}})
    snap_b = SchemaSnapshot.objects.create(connection=theirs, raw_schema_json={"tables": {}})
    SchemaDiff.objects.create(
        connection=theirs,
        from_snapshot=snap_a,
        to_snapshot=snap_b,
        changes_json={"tables_added": ["x"], "tables_removed": [], "tables_changed": {}},
    )

    intruder = django_user_model.objects.create_user(
        username="intruder", password="x", email="intruder@example.com"
    )
    _verify_email(intruder)
    api_client = APIClient()
    api_client.force_authenticate(user=intruder)

    response = api_client.get(f"/api/v1/connections/{theirs.id}/diffs/")

    assert response.status_code == 404
