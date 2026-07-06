"""End-to-end: introspectar -> alterar la tabla del cliente -> introspectar de
nuevo -> el SchemaDiff se genera solo, sin llamar a diff_latest_snapshots a mano.
Verifica el wiring de introspection.tasks.introspect_database (Documento 02 SS4.5).
"""

import pytest
from django.db import connection as django_db_connection

from connections.models import DatabaseConnection
from introspection.tasks import introspect_database
from snapshots.models import SchemaDiff


def _dsn_from_django_connection() -> str:
    settings_dict = django_db_connection.settings_dict
    return (
        f"postgresql://{settings_dict['USER']}:{settings_dict['PASSWORD']}@"
        f"{settings_dict['HOST']}:{settings_dict['PORT']}/{settings_dict['NAME']}"
    )


@pytest.mark.django_db(transaction=True)
def test_resyncing_after_a_schema_change_creates_a_schema_diff(settings, django_user_model):
    settings.ALLOW_PRIVATE_DB_HOSTS = True
    user = django_user_model.objects.create_user(username="dev", password="x")
    connection = DatabaseConnection(user=user, name="Target DB")
    connection.set_credentials(_dsn_from_django_connection())
    connection.save()

    with django_db_connection.cursor() as cursor:
        cursor.execute("CREATE TABLE diff_orders (id SERIAL PRIMARY KEY)")

    try:
        first_snapshot_id = introspect_database(connection.id)
        assert SchemaDiff.objects.filter(connection=connection).count() == 0

        with django_db_connection.cursor() as cursor:
            cursor.execute("ALTER TABLE diff_orders ADD COLUMN discount NUMERIC")

        second_snapshot_id = introspect_database(connection.id)
        assert second_snapshot_id != first_snapshot_id

        diff = SchemaDiff.objects.get(connection=connection)
        assert diff.from_snapshot_id == first_snapshot_id
        assert diff.to_snapshot_id == second_snapshot_id
        assert diff.changes_json["tables_changed"]["diff_orders"]["columns_added"] == [
            "discount"
        ]
    finally:
        with django_db_connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS diff_orders")
