"""diff_latest_snapshots: crea SchemaDiff solo cuando hay >= 2 snapshots y hay cambios."""

import pytest

from connections.models import DatabaseConnection
from introspection.models import SchemaSnapshot
from snapshots.models import SchemaDiff
from snapshots.tasks import diff_latest_snapshots

SCHEMA_V1 = {
    "tables": {
        "orders": {"columns": [{"name": "id", "data_type": "integer", "is_nullable": False}]}
    }
}
SCHEMA_V2 = {
    "tables": {
        "orders": {
            "columns": [
                {"name": "id", "data_type": "integer", "is_nullable": False},
                {"name": "discount", "data_type": "numeric", "is_nullable": True},
            ]
        }
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
def test_returns_none_with_fewer_than_two_snapshots(connection):
    SchemaSnapshot.objects.create(connection=connection, raw_schema_json=SCHEMA_V1)
    assert diff_latest_snapshots(connection.id) is None
    assert SchemaDiff.objects.count() == 0


@pytest.mark.django_db
def test_creates_diff_when_schemas_differ(connection):
    from_snap = SchemaSnapshot.objects.create(connection=connection, raw_schema_json=SCHEMA_V1)
    to_snap = SchemaSnapshot.objects.create(connection=connection, raw_schema_json=SCHEMA_V2)

    diff_id = diff_latest_snapshots(connection.id)

    assert diff_id is not None
    diff = SchemaDiff.objects.get(pk=diff_id)
    assert diff.from_snapshot_id == from_snap.id
    assert diff.to_snapshot_id == to_snap.id
    assert diff.changes_json["tables_changed"]["orders"]["columns_added"] == ["discount"]


@pytest.mark.django_db
def test_returns_none_and_creates_nothing_when_no_changes(connection):
    SchemaSnapshot.objects.create(connection=connection, raw_schema_json=SCHEMA_V1)
    SchemaSnapshot.objects.create(connection=connection, raw_schema_json=SCHEMA_V1)

    assert diff_latest_snapshots(connection.id) is None
    assert SchemaDiff.objects.count() == 0


@pytest.mark.django_db
def test_compares_only_the_two_most_recent_snapshots(connection):
    # snapshot muy viejo, distinto, no deberia influir en el diff
    SchemaSnapshot.objects.create(connection=connection, raw_schema_json={"tables": {}})
    SchemaSnapshot.objects.create(connection=connection, raw_schema_json=SCHEMA_V1)
    SchemaSnapshot.objects.create(connection=connection, raw_schema_json=SCHEMA_V1)

    assert diff_latest_snapshots(connection.id) is None
