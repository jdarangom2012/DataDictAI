"""Orquesta una pregunta en lenguaje natural, compartido entre la API DRF y la
vista HTMX del chat (Documento 03 SS3/SS6).
"""

from __future__ import annotations

from ai_engine.client import answer_question
from ai_engine.models import NLQuery


class NoSchemaAvailableError(Exception):
    """No hay un SchemaSnapshot todavia para esta conexion."""


def _referenced_tables(answer: str, raw_schema: dict) -> list[str]:
    table_names = raw_schema.get("tables", {}).keys()
    return sorted(name for name in table_names if name in answer)


def ask_question(connection, user, question: str) -> NLQuery:
    """Genera y persiste la respuesta a `question` sobre el ultimo esquema de `connection`.

    Puede propagar `ai_engine.client.AIExplanationError` si el proveedor de IA falla.
    """
    from introspection.models import SchemaSnapshot

    snapshot = (
        SchemaSnapshot.objects.filter(connection=connection).order_by("-created_at").first()
    )
    if snapshot is None:
        raise NoSchemaAvailableError

    answer = answer_question(question, snapshot.raw_schema_json)
    referenced_tables = _referenced_tables(answer, snapshot.raw_schema_json)

    return NLQuery.objects.create(
        connection=connection,
        user=user,
        question=question,
        answer=answer,
        referenced_tables=referenced_tables,
    )
