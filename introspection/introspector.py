"""Lectura read-only del esquema publico de una base Postgres del cliente.

Documento 02 SS4: abre una conexion de solo lectura, lee information_schema
(tablas, columnas, tipos, nullable, FKs, indices) y cierra la conexion de
inmediato. Nunca mantiene conexiones persistentes ni ejecuta SQL del usuario:
todas las queries de este modulo son fijas y parametrizadas por nosotros.

IMPORTANTE: ninguna funcion de este modulo debe loguear el DSN/connection string.
"""

from __future__ import annotations

from datetime import UTC, datetime

import psycopg

from introspection.security import assert_host_is_safe

MAX_TABLES = 1000

_TABLES_SQL = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name
"""

_COLUMNS_SQL = """
    SELECT table_name, column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position
"""

_FOREIGN_KEYS_SQL = """
    SELECT
        tc.table_name,
        kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
"""

_INDEXES_SQL = """
    SELECT tablename, indexname, indexdef
    FROM pg_indexes
    WHERE schemaname = 'public'
"""

_ROW_ESTIMATES_SQL = """
    SELECT relname, reltuples::bigint
    FROM pg_class
    JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
    WHERE relkind = 'r' AND nspname = 'public'
"""


class SchemaIntrospectionError(Exception):
    """No se pudo leer el esquema del cliente. Nunca debe incluir el DSN/credenciales."""


class SchemaTooLargeError(SchemaIntrospectionError):
    """El esquema supera el limite soportado en el MVP (Documento 03: schema_too_large)."""


def introspect_schema(dsn: str) -> dict:
    """Devuelve la estructura completa del esquema 'public' como un dict serializable."""
    assert_host_is_safe(dsn)

    try:
        with psycopg.connect(dsn, connect_timeout=10, autocommit=True) as conn:
            conn.read_only = True
            tables = _fetch_tables(conn)
            if len(tables) > MAX_TABLES:
                raise SchemaTooLargeError(
                    f"schema has {len(tables)} tables, exceeding the {MAX_TABLES} limit"
                )
            columns_by_table = _fetch_columns(conn)
            fks_by_table = _fetch_foreign_keys(conn)
            indexes_by_table = _fetch_indexes(conn)
            row_estimates = _fetch_row_estimates(conn)
    except psycopg.OperationalError as exc:
        raise SchemaIntrospectionError("could not connect to the target database") from exc

    result_tables = {}
    for table_name in tables:
        fk_lookup = fks_by_table.get(table_name, {})
        columns = []
        for col in columns_by_table.get(table_name, []):
            fk = fk_lookup.get(col["name"])
            columns.append(
                {
                    "name": col["name"],
                    "data_type": col["data_type"],
                    "is_nullable": col["is_nullable"],
                    "default": col["default"],
                    "is_foreign_key": fk is not None,
                    "references_table": fk["table"] if fk else None,
                    "references_column": fk["column"] if fk else None,
                }
            )
        result_tables[table_name] = {
            "columns": columns,
            "indexes": indexes_by_table.get(table_name, []),
            "row_count_estimate": row_estimates.get(table_name),
        }

    return {
        "tables": result_tables,
        "introspected_at": datetime.now(UTC).isoformat(),
    }


def _fetch_tables(conn: psycopg.Connection) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(_TABLES_SQL)
        return [row[0] for row in cur.fetchall()]


def _fetch_columns(conn: psycopg.Connection) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    with conn.cursor() as cur:
        cur.execute(_COLUMNS_SQL)
        for table_name, column_name, data_type, is_nullable, default in cur.fetchall():
            result.setdefault(table_name, []).append(
                {
                    "name": column_name,
                    "data_type": data_type,
                    "is_nullable": is_nullable == "YES",
                    "default": default,
                }
            )
    return result


def _fetch_foreign_keys(conn: psycopg.Connection) -> dict[str, dict[str, dict]]:
    result: dict[str, dict[str, dict]] = {}
    with conn.cursor() as cur:
        cur.execute(_FOREIGN_KEYS_SQL)
        for table_name, column_name, foreign_table, foreign_column in cur.fetchall():
            result.setdefault(table_name, {})[column_name] = {
                "table": foreign_table,
                "column": foreign_column,
            }
    return result


def _fetch_indexes(conn: psycopg.Connection) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    with conn.cursor() as cur:
        cur.execute(_INDEXES_SQL)
        for table_name, index_name, index_def in cur.fetchall():
            result.setdefault(table_name, []).append(
                {"name": index_name, "definition": index_def}
            )
    return result


def _fetch_row_estimates(conn: psycopg.Connection) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute(_ROW_ESTIMATES_SQL)
        # Postgres devuelve reltuples = -1 cuando la tabla nunca se ha ANALYZE-ado
        # (no significa "cero filas", significa "sin estimar todavia").
        return {row[0]: row[1] for row in cur.fetchall() if row[1] is not None and row[1] >= 0}
