from django.db import models

from connections.models import DatabaseConnection


class SchemaSnapshot(models.Model):
    connection = models.ForeignKey(
        DatabaseConnection, on_delete=models.CASCADE, related_name="snapshots"
    )
    # Estructura completa: tablas, columnas, tipos, FKs, indices (Documento 02 SS3).
    raw_schema_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["connection", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Snapshot {self.pk} de {self.connection_id}"


class TableDoc(models.Model):
    snapshot = models.ForeignKey(SchemaSnapshot, on_delete=models.CASCADE, related_name="tables")
    table_name = models.CharField(max_length=255)
    # Generado y cacheado por ai_engine en una tarea posterior; vacio hasta entonces.
    ai_explanation = models.TextField(blank=True)
    row_count_estimate = models.BigIntegerField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=["snapshot"]),
        ]

    def __str__(self) -> str:
        return self.table_name


class ColumnDoc(models.Model):
    table = models.ForeignKey(TableDoc, on_delete=models.CASCADE, related_name="columns")
    column_name = models.CharField(max_length=255)
    data_type = models.CharField(max_length=100)
    is_nullable = models.BooleanField()
    is_foreign_key = models.BooleanField(default=False)
    references_table = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self) -> str:
        return f"{self.table.table_name}.{self.column_name}"
