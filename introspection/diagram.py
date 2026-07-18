"""Construye la estructura de nodos/edges para el diagrama ER (Documento 03 SS3
y SS6: 'Diagrama ER interactivo'). Los edges apuntan a tablas que no existen en
el snapshot (por ejemplo, FKs hacia otro schema) se descartan -- un edge
colgante rompe el render del grafo sin aportar nada al usuario.
"""

from __future__ import annotations

from introspection.models import SchemaSnapshot


def build_diagram(snapshot: SchemaSnapshot) -> dict:
    table_docs = list(snapshot.tables.prefetch_related("columns"))

    nodes = [
        {
            "id": table.table_name,
            "label": table.table_name,
            "row_count_estimate": table.row_count_estimate,
            "columns": [
                {
                    "name": column.column_name,
                    "type": column.data_type,
                    "is_nullable": column.is_nullable,
                    "is_foreign_key": column.is_foreign_key,
                }
                for column in table.columns.all()
            ],
        }
        for table in table_docs
    ]
    node_ids = {node["id"] for node in nodes}

    edges = [
        {
            "id": f"{table.table_name}.{column.column_name}->{column.references_table}",
            "source": table.table_name,
            "target": column.references_table,
            "label": column.column_name,
        }
        for table in table_docs
        for column in table.columns.all()
        if column.is_foreign_key and column.references_table in node_ids
    ]

    return {"nodes": nodes, "edges": edges}
