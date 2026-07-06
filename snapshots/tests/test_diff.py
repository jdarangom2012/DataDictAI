"""compute_schema_diff es logica pura: no toca la base de datos."""

from snapshots.diff import compute_schema_diff, has_changes


def _schema(tables: dict) -> dict:
    return {"tables": tables}


def test_no_changes_between_identical_schemas():
    schema = _schema(
        {
            "orders": {
                "columns": [{"name": "id", "data_type": "integer", "is_nullable": False}],
            }
        }
    )
    diff = compute_schema_diff(schema, schema)
    assert not has_changes(diff)
    assert diff == {"tables_added": [], "tables_removed": [], "tables_changed": {}}


def test_detects_added_and_removed_tables():
    from_schema = _schema({"orders": {"columns": []}})
    to_schema = _schema({"orders": {"columns": []}, "invoices": {"columns": []}})

    diff = compute_schema_diff(from_schema, to_schema)

    assert diff["tables_added"] == ["invoices"]
    assert diff["tables_removed"] == []
    assert has_changes(diff)


def test_detects_removed_table():
    from_schema = _schema({"orders": {"columns": []}, "legacy": {"columns": []}})
    to_schema = _schema({"orders": {"columns": []}})

    diff = compute_schema_diff(from_schema, to_schema)

    assert diff["tables_removed"] == ["legacy"]
    assert diff["tables_added"] == []


def test_detects_added_and_removed_columns():
    from_schema = _schema(
        {"orders": {"columns": [{"name": "id", "data_type": "integer", "is_nullable": False}]}}
    )
    to_schema = _schema(
        {
            "orders": {
                "columns": [
                    {"name": "id", "data_type": "integer", "is_nullable": False},
                    {"name": "discount", "data_type": "numeric", "is_nullable": True},
                ]
            }
        }
    )

    diff = compute_schema_diff(from_schema, to_schema)

    assert diff["tables_changed"]["orders"]["columns_added"] == ["discount"]
    assert diff["tables_changed"]["orders"]["columns_removed"] == []


def test_detects_changed_column_data_type():
    from_schema = _schema(
        {"orders": {"columns": [{"name": "status", "data_type": "varchar", "is_nullable": False}]}}
    )
    to_schema = _schema(
        {"orders": {"columns": [{"name": "status", "data_type": "text", "is_nullable": False}]}}
    )

    diff = compute_schema_diff(from_schema, to_schema)

    changed = diff["tables_changed"]["orders"]["columns_changed"]
    assert changed == [{"column": "status", "field": "data_type", "from": "varchar", "to": "text"}]


def test_detects_column_becoming_nullable():
    from_schema = _schema(
        {"orders": {"columns": [{"name": "note", "data_type": "text", "is_nullable": False}]}}
    )
    to_schema = _schema(
        {"orders": {"columns": [{"name": "note", "data_type": "text", "is_nullable": True}]}}
    )

    diff = compute_schema_diff(from_schema, to_schema)

    changed = diff["tables_changed"]["orders"]["columns_changed"]
    assert {"column": "note", "field": "is_nullable", "from": False, "to": True} in changed


def test_detects_new_foreign_key():
    from_schema = _schema(
        {
            "orders": {
                "columns": [
                    {
                        "name": "user_id",
                        "data_type": "integer",
                        "is_nullable": False,
                        "is_foreign_key": False,
                        "references_table": None,
                    }
                ]
            }
        }
    )
    to_schema = _schema(
        {
            "orders": {
                "columns": [
                    {
                        "name": "user_id",
                        "data_type": "integer",
                        "is_nullable": False,
                        "is_foreign_key": True,
                        "references_table": "users",
                    }
                ]
            }
        }
    )

    diff = compute_schema_diff(from_schema, to_schema)

    changed = diff["tables_changed"]["orders"]["columns_changed"]
    fields_changed = {c["field"] for c in changed}
    assert fields_changed == {"is_foreign_key", "references_table"}
