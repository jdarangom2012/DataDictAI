"""Endpoints REST de conexiones (Documento 03 SS3).

Todos requieren autenticacion (DEFAULT_PERMISSION_CLASSES = IsAuthenticated).
La introspeccion nunca corre en la request: siempre se dispara via Celery
(Documento 02, principio de diseno clave).
"""

from __future__ import annotations

from django.http import HttpResponse
from django.utils.text import slugify
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ai_engine.client import AIExplanationError
from ai_engine.models import NLQuery
from ai_engine.serializers import AskQuestionSerializer, NLQuerySerializer
from ai_engine.services import NoSchemaAvailableError, ask_question
from connections.models import DatabaseConnection
from connections.permissions import HasVerifiedEmail
from connections.serializers import DatabaseConnectionCreateSerializer, DatabaseConnectionSerializer
from exports.markdown import generate_markdown
from introspection.diagram import build_diagram
from introspection.models import SchemaSnapshot, TableDoc
from introspection.serializers import SchemaSnapshotSerializer, TableDocSerializer
from introspection.tasks import introspect_database


def _ai_unavailable_response():
    return Response(
        {
            "error": {
                "code": "ai_explanation_unavailable",
                "message": "No pudimos generar una respuesta en este momento. Intenta de nuevo.",
                "field": None,
            }
        },
        status=503,
    )


def _schema_not_available_response():
    return Response(
        {
            "error": {
                "code": "schema_not_available",
                "message": "Todavia no hay un esquema sincronizado para esta conexion.",
                "field": None,
            }
        },
        status=404,
    )


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

    def _latest_snapshot(self, connection):
        return SchemaSnapshot.objects.filter(connection=connection).order_by("-created_at").first()

    @action(detail=True, methods=["get"], url_path="schema")
    def schema(self, request, pk=None):
        snapshot = self._latest_snapshot(self.get_object())
        if snapshot is None:
            return _schema_not_available_response()
        return Response(SchemaSnapshotSerializer(snapshot).data)

    @action(detail=True, methods=["get"], url_path="diagram")
    def diagram(self, request, pk=None):
        snapshot = self._latest_snapshot(self.get_object())
        if snapshot is None:
            return _schema_not_available_response()
        return Response(build_diagram(snapshot))

    @action(
        detail=True,
        methods=["get"],
        url_path=r"schema/tables/(?P<table_name>[^/]+)",
    )
    def table_detail(self, request, pk=None, table_name=None):
        snapshot = self._latest_snapshot(self.get_object())
        if snapshot is None:
            return _schema_not_available_response()

        table_doc = (
            TableDoc.objects.filter(snapshot=snapshot, table_name=table_name)
            .prefetch_related("columns")
            .first()
        )
        if table_doc is None:
            return Response(
                {
                    "error": {
                        "code": "table_not_found",
                        "message": f"La tabla '{table_name}' no existe en el ultimo esquema.",
                        "field": None,
                    }
                },
                status=404,
            )
        return Response(TableDocSerializer(table_doc).data)

    @action(detail=True, methods=["post"], url_path="ask")
    def ask(self, request, pk=None):
        connection = self.get_object()
        serializer = AskQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            nl_query = ask_question(connection, request.user, serializer.validated_data["question"])
        except NoSchemaAvailableError:
            return _schema_not_available_response()
        except AIExplanationError:
            return _ai_unavailable_response()

        return Response(NLQuerySerializer(nl_query).data, status=201)

    @action(detail=True, methods=["get"], url_path="ask/history")
    def ask_history(self, request, pk=None):
        connection = self.get_object()
        queryset = NLQuery.objects.filter(connection=connection)[:50]
        return Response(NLQuerySerializer(queryset, many=True).data)

    @action(detail=True, methods=["get"], url_path="export/markdown")
    def export_markdown(self, request, pk=None):
        connection = self.get_object()
        snapshot = self._latest_snapshot(connection)
        if snapshot is None:
            return _schema_not_available_response()

        content = generate_markdown(connection, snapshot)
        filename = f"{slugify(connection.name) or 'esquema'}-schema.md"
        response = HttpResponse(content, content_type="text/markdown; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
