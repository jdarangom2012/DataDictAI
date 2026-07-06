"""Flujo completo: DatabaseConnection -> introspect_database (Celery) -> SchemaSnapshot."""

import pytest
from django.db import connection as django_db_connection

from connections.models import DatabaseConnection
from introspection.models import ColumnDoc, SchemaSnapshot, TableDoc
from introspection.security import UnsafeDatabaseHostError
from introspection.tasks import introspect_database


def _dsn_from_django_connection() -> str:
    settings_dict = django_db_connection.settings_dict
    return (
        f"postgresql://{settings_dict['USER']}:{settings_dict['PASSWORD']}@"
        f"{settings_dict['HOST']}:{settings_dict['PORT']}/{settings_dict['NAME']}"
    )


@pytest.fixture
def allow_private_hosts(settings):
    settings.ALLOW_PRIVATE_DB_HOSTS = True


@pytest.mark.django_db(transaction=True)
def test_introspect_database_creates_snapshot_and_docs(allow_private_hosts, django_user_model):
    user = django_user_model.objects.create_user(username="dev", password="x")
    connection = DatabaseConnection(user=user, name="Target DB")
    connection.set_credentials(_dsn_from_django_connection())
    connection.save()

    with django_db_connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE task_orders (
                id SERIAL PRIMARY KEY,
                status TEXT NOT NULL
            )
        """)

    try:
        snapshot_id = introspect_database(connection.id)

        snapshot = SchemaSnapshot.objects.get(pk=snapshot_id)
        assert snapshot.connection_id == connection.id
        assert "task_orders" in snapshot.raw_schema_json["tables"]

        table_doc = TableDoc.objects.get(snapshot=snapshot, table_name="task_orders")
        assert table_doc.ai_explanation == ""

        column_names = set(
            ColumnDoc.objects.filter(table=table_doc).values_list("column_name", flat=True)
        )
        assert {"id", "status"} <= column_names

        connection.refresh_from_db()
        assert connection.status == DatabaseConnection.Status.CONNECTED
        assert connection.last_synced_at is not None
    finally:
        with django_db_connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS task_orders")


@pytest.mark.django_db(transaction=True)
def test_introspect_database_marks_connection_error_on_ssrf_block(settings, django_user_model):
    settings.ALLOW_PRIVATE_DB_HOSTS = False
    user = django_user_model.objects.create_user(username="dev2", password="x")
    connection = DatabaseConnection(user=user, name="Unsafe target")
    connection.set_credentials("postgresql://user:pass@127.0.0.1:5432/db")
    connection.save()

    with pytest.raises(UnsafeDatabaseHostError):
        introspect_database(connection.id)

    connection.refresh_from_db()
    assert connection.status == DatabaseConnection.Status.ERROR
