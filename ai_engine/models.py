from django.conf import settings
from django.db import models

from connections.models import DatabaseConnection


class NLQuery(models.Model):
    connection = models.ForeignKey(
        DatabaseConnection, on_delete=models.CASCADE, related_name="nl_queries"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="nl_queries"
    )
    question = models.TextField()
    answer = models.TextField()
    # Nombres de tabla mencionados en la respuesta, calculados al momento de
    # generarla (Documento 03 SS6: "respuestas con referencias a tablas... clickeables").
    referenced_tables = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["connection", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"NLQuery({self.connection_id}): {self.question[:50]}"
