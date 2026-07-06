"""Tarea Celery de introspeccion de esquema.

Documento 02 SS4 / principio de diseno clave: la conexion a la base del
cliente NUNCA ocurre dentro de una request sincrona de Django. Esta tarea
es el unico punto donde abrimos esa conexion.
"""

from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone

from connections.models import DatabaseConnection
from introspection.introspector import SchemaIntrospectionError, introspect_schema
from introspection.models import ColumnDoc, SchemaSnapshot, TableDoc
from introspection.security import UnsafeDatabaseHostError

logger = get_task_logger(__name__)


@shared_task
def introspect_database(connection_id: int) -> int:
    """Lee el esquema (solo lectura) de una DatabaseConnection y guarda un SchemaSnapshot.

    Nunca logueamos el DSN/credenciales, ni siquiera en caso de error.
    """
    connection = DatabaseConnection.objects.get(pk=connection_id)

    try:
        dsn = connection.get_credentials()
        raw_schema = introspect_schema(dsn)
    except (SchemaIntrospectionError, UnsafeDatabaseHostError):
        logger.warning("Schema introspection failed for connection_id=%s", connection_id)
        connection.status = DatabaseConnection.Status.ERROR
        connection.save(update_fields=["status"])
        raise
    finally:
        dsn = None  # nunca conservar el connection string en memoria mas de lo necesario

    snapshot = SchemaSnapshot.objects.create(connection=connection, raw_schema_json=raw_schema)
    _save_table_and_column_docs(snapshot, raw_schema)

    connection.status = DatabaseConnection.Status.CONNECTED
    connection.last_synced_at = timezone.now()
    connection.save(update_fields=["status", "last_synced_at"])

    # Documento 02 SS4.5: al re-sincronizar, comparar contra el snapshot anterior.
    # Es un paso complementario -- nunca debe hacer fallar una introspeccion exitosa.
    from snapshots.tasks import diff_latest_snapshots

    try:
        diff_latest_snapshots(connection.id)
    except Exception:
        logger.warning("Schema diff failed for connection_id=%s", connection_id)

    return snapshot.id


def _save_table_and_column_docs(snapshot: SchemaSnapshot, raw_schema: dict) -> None:
    tables_payload = raw_schema.get("tables", {})

    table_docs = TableDoc.objects.bulk_create(
        [
            TableDoc(
                snapshot=snapshot,
                table_name=table_name,
                row_count_estimate=table_data.get("row_count_estimate"),
            )
            for table_name, table_data in tables_payload.items()
        ]
    )
    table_doc_by_name = {table_doc.table_name: table_doc for table_doc in table_docs}

    column_docs = [
        ColumnDoc(
            table=table_doc_by_name[table_name],
            column_name=column["name"],
            data_type=column["data_type"],
            is_nullable=column["is_nullable"],
            is_foreign_key=column.get("is_foreign_key", False),
            references_table=column.get("references_table"),
        )
        for table_name, table_data in tables_payload.items()
        for column in table_data.get("columns", [])
    ]
    ColumnDoc.objects.bulk_create(column_docs)
