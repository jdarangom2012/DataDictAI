"""Comparacion pura entre dos raw_schema_json de SchemaSnapshot.

Documento 02 SS4.5: si hay diferencias con el snapshot anterior, se genera un
SchemaDiff. Este modulo solo calcula el diff -- no toca la base de datos.
"""

from __future__ import annotations

_TRACKED_COLUMN_FIELDS = ("data_type", "is_nullable", "is_foreign_key", "references_table")


def compute_schema_diff(from_schema: dict, to_schema: dict) -> dict:
    """Devuelve tablas agregadas/eliminadas y columnas agregadas/eliminadas/cambiadas."""
    from_tables = from_schema.get("tables", {})
    to_tables = to_schema.get("tables", {})

    from_names = set(from_tables)
    to_names = set(to_tables)

    tables_changed = {}
    for table_name in sorted(from_names & to_names):
        table_diff = _diff_table(from_tables[table_name], to_tables[table_name])
        if table_diff:
            tables_changed[table_name] = table_diff

    return {
        "tables_added": sorted(to_names - from_names),
        "tables_removed": sorted(from_names - to_names),
        "tables_changed": tables_changed,
    }


def has_changes(changes: dict) -> bool:
    return bool(
        changes["tables_added"] or changes["tables_removed"] or changes["tables_changed"]
    )


def _diff_table(from_table: dict, to_table: dict) -> dict | None:
    from_columns = {c["name"]: c for c in from_table.get("columns", [])}
    to_columns = {c["name"]: c for c in to_table.get("columns", [])}

    columns_added = sorted(set(to_columns) - set(from_columns))
    columns_removed = sorted(set(from_columns) - set(to_columns))

    columns_changed = []
    for column_name in sorted(set(from_columns) & set(to_columns)):
        before = from_columns[column_name]
        after = to_columns[column_name]
        for field in _TRACKED_COLUMN_FIELDS:
            if before.get(field) != after.get(field):
                columns_changed.append(
                    {
                        "column": column_name,
                        "field": field,
                        "from": before.get(field),
                        "to": after.get(field),
                    }
                )

    if not columns_added and not columns_removed and not columns_changed:
        return None

    return {
        "columns_added": columns_added,
        "columns_removed": columns_removed,
        "columns_changed": columns_changed,
    }
