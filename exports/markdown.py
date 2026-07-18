"""Genera el Markdown exportable del ultimo esquema documentado.

Documento 01 SS5: Markdown cubre el 80% del valor en el MVP -- HTML y PDF
quedan para v2.
"""

from __future__ import annotations

from introspection.models import SchemaSnapshot


def generate_markdown(connection, snapshot: SchemaSnapshot) -> str:
    lines = [
        f"# Esquema de base de datos: {connection.name}",
        "",
        f"_Generado por DataDict AI el {snapshot.created_at:%Y-%m-%d %H:%M} UTC_",
        "",
    ]

    table_docs = snapshot.tables.prefetch_related("columns").order_by("table_name")
    for table in table_docs:
        lines.append(f"## {table.table_name}")
        lines.append("")
        lines.append(table.ai_explanation or "_Sin explicacion generada todavia._")
        lines.append("")
        # Postgres devuelve reltuples = -1 cuando la tabla nunca se ha ANALYZE-ado
        # (no significa "cero filas", significa "sin estimar todavia").
        if table.row_count_estimate is not None and table.row_count_estimate >= 0:
            lines.append(f"Filas estimadas: {table.row_count_estimate}")
            lines.append("")

        lines.append("| Columna | Tipo | Nullable | FK |")
        lines.append("|---|---|---|---|")
        for column in table.columns.all():
            fk = f"-> {column.references_table}" if column.is_foreign_key else ""
            nullable = "Si" if column.is_nullable else "No"
            lines.append(f"| {column.column_name} | {column.data_type} | {nullable} | {fk} |")
        lines.append("")

    return "\n".join(lines)
