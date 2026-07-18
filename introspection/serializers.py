"""Serializers de solo lectura para exponer el ultimo snapshot via API
(Documento 03 SS3: /schema/, /schema/tables/{table}/)."""

from __future__ import annotations

from rest_framework import serializers

from introspection.models import ColumnDoc, SchemaSnapshot, TableDoc


class ColumnDocSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColumnDoc
        fields = ["column_name", "data_type", "is_nullable", "is_foreign_key", "references_table"]


class TableDocSerializer(serializers.ModelSerializer):
    columns = ColumnDocSerializer(many=True, read_only=True)

    class Meta:
        model = TableDoc
        fields = ["id", "table_name", "ai_explanation", "row_count_estimate", "columns"]


class SchemaSnapshotSerializer(serializers.ModelSerializer):
    tables = TableDocSerializer(many=True, read_only=True)

    class Meta:
        model = SchemaSnapshot
        fields = ["id", "created_at", "tables"]
