"""Tarea Celery de comparacion de snapshots.

Documento 02 SS4.5: al re-sincronizar, si hay diferencias con el snapshot
anterior, se genera un SchemaDiff.
"""

from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

from connections.models import DatabaseConnection
from introspection.models import SchemaSnapshot
from snapshots.diff import compute_schema_diff, has_changes
from snapshots.models import SchemaDiff

logger = get_task_logger(__name__)


@shared_task
def diff_latest_snapshots(connection_id: int) -> int | None:
    """Compara los dos snapshots mas recientes de una conexion.

    Si hay menos de dos snapshots, o si no hay cambios entre ellos, no crea
    nada y devuelve None.
    """
    connection = DatabaseConnection.objects.get(pk=connection_id)
    latest_two = list(
        SchemaSnapshot.objects.filter(connection=connection).order_by("-created_at")[:2]
    )
    if len(latest_two) < 2:
        return None

    to_snapshot, from_snapshot = latest_two
    changes = compute_schema_diff(from_snapshot.raw_schema_json, to_snapshot.raw_schema_json)

    if not has_changes(changes):
        return None

    diff = SchemaDiff.objects.create(
        connection=connection,
        from_snapshot=from_snapshot,
        to_snapshot=to_snapshot,
        changes_json=changes,
    )
    return diff.id
