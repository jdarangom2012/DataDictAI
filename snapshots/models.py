from django.db import models

from connections.models import DatabaseConnection
from introspection.models import SchemaSnapshot


class SchemaDiff(models.Model):
    connection = models.ForeignKey(
        DatabaseConnection, on_delete=models.CASCADE, related_name="diffs"
    )
    from_snapshot = models.ForeignKey(
        SchemaSnapshot, on_delete=models.CASCADE, related_name="diffs_from"
    )
    to_snapshot = models.ForeignKey(
        SchemaSnapshot, on_delete=models.CASCADE, related_name="diffs_to"
    )
    # Tablas agregadas/eliminadas, columnas agregadas/eliminadas/cambiadas (Documento 02 SS3).
    changes_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["connection", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Diff {self.from_snapshot_id} -> {self.to_snapshot_id}"
