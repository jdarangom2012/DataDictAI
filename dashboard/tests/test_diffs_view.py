"""Vista de historial de cambios: agregado/eliminado en verde/rojo (Documento 03 SS6)."""

import pytest
from allauth.account.models import EmailAddress
from django.test import Client

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
def test_diffs_view_shows_empty_state(client, connection):
    response = client.get(f"/connections/{connection.id}/diffs/")

    assert response.status_code == 200
    assert "Todavia no se detectaron cambios" in response.content.decode()


@pytest.mark.django_db
def test_diffs_view_renders_added_removed_and_changed_tables(client, connection):
    snap_a = SchemaSnapshot.objects.create(connection=connection, raw_schema_json={"tables": {}})
    snap_b = SchemaSnapshot.objects.create(connection=connection, raw_schema_json={"tables": {}})
    SchemaDiff.objects.create(
        connection=connection,
        from_snapshot=snap_a,
        to_snapshot=snap_b,
        changes_json={
            "tables_added": ["orders"],
            "tables_removed": ["legacy_table"],
            "tables_changed": {
                "users": {
                    "columns_added": ["nickname"],
                    "columns_removed": [],
                    "columns_changed": [
                        {"column": "email", "field": "is_nullable", "from": False, "to": True}
                    ],
                }
            },
        },
    )

    response = client.get(f"/connections/{connection.id}/diffs/")

    body = response.content.decode()
    assert response.status_code == 200
    assert "orders" in body
    assert "legacy_table" in body
    assert "users" in body
    assert "nickname" in body


@pytest.mark.django_db
def test_cannot_view_other_users_diffs(client, django_user_model):
    other_user = django_user_model.objects.create_user(
        username="other", password="x", email="other@example.com"
    )
    theirs = DatabaseConnection(user=other_user, name="Theirs")
    theirs.set_credentials(VALID_DSN)
    theirs.save()

    response = client.get(f"/connections/{theirs.id}/diffs/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_diffs_view_requires_login():
    response = Client().get("/connections/1/diffs/")
    assert response.status_code == 302
    assert "/accounts/login/" in response.url
