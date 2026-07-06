"""Tarea Celery de generacion de explicaciones IA por tabla.

Documento 02 SS6: cache agresivo -- una tabla que ya tiene explicacion no
vuelve a pasar por la IA salvo que se pida regenerar explicitamente (force=True,
para el boton "regenerar explicacion" del Documento 03).
"""

from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

from ai_engine.client import NO_CONTEXT_EXPLANATION, AIExplanationError, explain_table
from introspection.models import SchemaSnapshot, TableDoc

logger = get_task_logger(__name__)


@shared_task
def generate_ai_docs(snapshot_id: int, force: bool = False) -> int:
    """Genera y cachea la explicacion IA de cada tabla del snapshot.

    Devuelve la cantidad de tablas para las que se genero (o regenero) explicacion.
    """
    snapshot = SchemaSnapshot.objects.get(pk=snapshot_id)
    tables_payload = snapshot.raw_schema_json.get("tables", {})

    updated = 0
    for table_doc in TableDoc.objects.filter(snapshot=snapshot):
        if table_doc.ai_explanation and not force:
            continue

        table_data = tables_payload.get(table_doc.table_name, {})
        try:
            explanation = explain_table(table_doc.table_name, table_data)
        except AIExplanationError:
            logger.warning(
                "AI explanation failed for table_doc_id=%s, using fallback", table_doc.pk
            )
            explanation = NO_CONTEXT_EXPLANATION

        table_doc.ai_explanation = explanation
        table_doc.save(update_fields=["ai_explanation"])
        updated += 1

    return updated
