"""Endpoints REST de conexiones (Documento 03 SS3).

Todos requieren autenticacion (DEFAULT_PERMISSION_CLASSES = IsAuthenticated).
La introspeccion nunca corre en la request: siempre se dispara via Celery
(Documento 02, principio de diseno clave).
"""

from __future__ import annotations

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from connections.models import DatabaseConnection
from connections.permissions import HasVerifiedEmail
from connections.serializers import DatabaseConnectionCreateSerializer, DatabaseConnectionSerializer
from introspection.tasks import introspect_database


class DatabaseConnectionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, HasVerifiedEmail]

    def get_queryset(self):
        return DatabaseConnection.objects.filter(user=self.request.user).order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return DatabaseConnectionCreateSerializer
        return DatabaseConnectionSerializer

    def perform_create(self, serializer):
        connection = serializer.save()
        introspect_database.delay(connection.id)

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        connection = self.get_object()
        introspect_database.delay(connection.id)
        return Response(DatabaseConnectionSerializer(connection).data, status=202)
