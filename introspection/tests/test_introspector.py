"""Integracion: lee el esquema de un Postgres real (Documento 04 Parte B — 'no mocks
para esto especifico'). Usamos la propia base de datos de test de Django como
'base del cliente' para ejercer information_schema de verdad.
"""

import pytest
from django.db import connection as django_db_connection

from introspection.introspector import SchemaTooLargeError, introspect_schema


def _dsn_from_django_connection() -> str:
    settings_dict = django_db_connection.settings_dict
    return (
        f"postgresql://{settings_dict['USER']}:{settings_dict['PASSWORD']}@"
        f"{settings_dict['HOST']}:{settings_dict['PORT']}/{settings_dict['NAME']}"
    )


@pytest.fixture
def allow_private_hosts(settings):
    # El target de estos tests es nuestro propio Postgres de test (host privado).
    settings.ALLOW_PRIVATE_DB_HOSTS = True


@pytest.mark.django_db(transaction=True)
def test_introspect_schema_reads_tables_columns_and_foreign_keys(allow_private_hosts):
    with django_db_connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE it_authors (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE it_books (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                published BOOLEAN,
                author_id INTEGER REFERENCES it_authors(id)
            )
        """)

    try:
        result = introspect_schema(_dsn_from_django_connection())

        assert "it_authors" in result["tables"]
        assert "it_books" in result["tables"]

        books_columns = {c["name"]: c for c in result["tables"]["it_books"]["columns"]}
        assert books_columns["title"]["data_type"] == "text"
        assert books_columns["title"]["is_nullable"] is False
        assert books_columns["published"]["is_nullable"] is True
        assert books_columns["author_id"]["is_foreign_key"] is True
        assert books_columns["author_id"]["references_table"] == "it_authors"

        assert "introspected_at" in result
    finally:
        with django_db_connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS it_books")
            cursor.execute("DROP TABLE IF EXISTS it_authors")


@pytest.mark.django_db(transaction=True)
def test_introspect_schema_includes_row_count_estimate_and_indexes(allow_private_hosts):
    with django_db_connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE it_items (
                id SERIAL PRIMARY KEY,
                sku TEXT UNIQUE NOT NULL
            )
        """)
        cursor.execute("INSERT INTO it_items (sku) VALUES ('a'), ('b'), ('c')")
        cursor.execute("ANALYZE it_items")

    try:
        result = introspect_schema(_dsn_from_django_connection())
        table = result["tables"]["it_items"]
        assert table["row_count_estimate"] == 3
        index_names = {idx["name"] for idx in table["indexes"]}
        assert any("pkey" in name for name in index_names)
    finally:
        with django_db_connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS it_items")


@pytest.mark.django_db(transaction=True)
def test_introspect_schema_rejects_schema_over_table_limit(allow_private_hosts, monkeypatch):
    monkeypatch.setattr("introspection.introspector.MAX_TABLES", 0)
    with pytest.raises(SchemaTooLargeError):
        introspect_schema(_dsn_from_django_connection())
