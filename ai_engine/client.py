"""Cliente de IA para explicar tablas en lenguaje simple.

Documento 02 SS6: input es la estructura del esquema (JSON) -- nunca filas de
datos reales del cliente. Si no hay contexto suficiente para inferir el
proposito de una tabla, el sistema debe admitirlo explicitamente en vez de
inventar un proposito de negocio que no se puede deducir de la estructura.
"""

from __future__ import annotations

from django.conf import settings
from openai import OpenAI, OpenAIError

NO_CONTEXT_EXPLANATION = "No hay suficiente contexto para explicar esta tabla."

_SYSTEM_PROMPT = (
    "Eres un asistente que documenta esquemas de bases de datos para desarrolladores. "
    "Se te da el nombre de una tabla, sus columnas (nombre, tipo, si es nullable) y sus "
    "llaves foraneas. Explica en 2-3 frases, en espanol y en lenguaje simple, que "
    "probablemente almacena esta tabla y para que se usa, basandote UNICAMENTE en los "
    "nombres y la estructura provista. Nunca inventes un proposito de negocio que no se "
    "pueda inferir de la estructura. Si el nombre y las columnas son demasiado cripticos "
    f'para inferir algo con confianza, responde exactamente: "{NO_CONTEXT_EXPLANATION}"'
)


class AIExplanationError(Exception):
    """La IA no pudo generar una explicacion. Nunca debe incluir datos de filas del cliente."""


def _build_user_prompt(table_name: str, table_data: dict) -> str:
    lines = [f"Tabla: {table_name}", "Columnas:"]
    for column in table_data.get("columns", []):
        descriptor = f"- {column['name']} ({column['data_type']}"
        descriptor += ", nullable" if column["is_nullable"] else ", not null"
        if column.get("is_foreign_key"):
            descriptor += f", FK -> {column['references_table']}"
        descriptor += ")"
        lines.append(descriptor)
    return "\n".join(lines)


def explain_table(table_name: str, table_data: dict) -> str:
    """Genera la explicacion de una tabla o el fallback si no hay API key configurada."""
    api_key = settings.AI_API_KEY
    if not api_key:
        return NO_CONTEXT_EXPLANATION

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(table_name, table_data)},
            ],
            temperature=0.2,
            max_tokens=200,
        )
    except OpenAIError as exc:
        raise AIExplanationError("AI provider request failed") from exc

    explanation = response.choices[0].message.content
    if not explanation or not explanation.strip():
        return NO_CONTEXT_EXPLANATION
    return explanation.strip()
