"""Vistas HTMX del panel del usuario (Documento 03 SS6: Onboarding + Dashboard).

Reutiliza DatabaseConnectionCreateSerializer para no duplicar la validacion
de formato ni la encriptacion que ya usa la API REST (connections/serializers.py).
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from ai_engine.client import AIExplanationError
from ai_engine.models import NLQuery
from ai_engine.services import NoSchemaAvailableError, ask_question
from connections.models import DatabaseConnection
from connections.permissions import user_has_verified_email
from connections.serializers import DatabaseConnectionCreateSerializer
from introspection.tasks import introspect_database


def _user_connections(user):
    return DatabaseConnection.objects.filter(user=user).order_by("-created_at")


@login_required
def home(request):
    return render(
        request,
        "dashboard/home.html",
        {"connections": _user_connections(request.user)},
    )


@login_required
@require_POST
def create_connection(request):
    connections = _user_connections(request.user)

    if not user_has_verified_email(request.user):
        return render(
            request,
            "dashboard/_dashboard_content.html",
            {
                "connections": connections,
                "form_error": "Debes verificar tu email antes de conectar una base de datos.",
            },
            status=403,
        )

    serializer = DatabaseConnectionCreateSerializer(
        data={
            "name": request.POST.get("name", ""),
            "connection_string": request.POST.get("connection_string", ""),
        },
        context={"request": request},
    )
    if not serializer.is_valid():
        first_error = str(next(iter(serializer.errors.values()))[0])
        return render(
            request,
            "dashboard/_dashboard_content.html",
            {"connections": connections, "form_error": first_error},
            status=400,
        )

    connection = serializer.save()
    introspect_database.delay(connection.id)

    return render(
        request,
        "dashboard/_dashboard_content.html",
        {"connections": _user_connections(request.user)},
    )


@login_required
@require_POST
def sync_connection(request, pk):
    connection = get_object_or_404(DatabaseConnection, pk=pk, user=request.user)
    introspect_database.delay(connection.id)
    return render(
        request,
        "dashboard/_dashboard_content.html",
        {"connections": _user_connections(request.user)},
    )


@login_required
def schema_view(request, pk):
    connection = get_object_or_404(DatabaseConnection, pk=pk, user=request.user)
    return render(request, "dashboard/schema.html", {"connection": connection})


@login_required
def chat_view(request, pk):
    connection = get_object_or_404(DatabaseConnection, pk=pk, user=request.user)
    history = list(NLQuery.objects.filter(connection=connection)[:50])
    history.reverse()
    return render(
        request, "dashboard/chat.html", {"connection": connection, "history": history}
    )


@login_required
@require_POST
def ask_message(request, pk):
    connection = get_object_or_404(DatabaseConnection, pk=pk, user=request.user)
    question = request.POST.get("question", "").strip()
    if not question:
        return render(
            request,
            "dashboard/_chat_error.html",
            {"message": "Escribe una pregunta antes de enviar."},
            status=400,
        )

    try:
        nl_query = ask_question(connection, request.user, question)
    except NoSchemaAvailableError:
        return render(
            request,
            "dashboard/_chat_error.html",
            {"message": "Todavia no hay un esquema sincronizado para esta conexion."},
            status=404,
        )
    except AIExplanationError:
        return render(
            request,
            "dashboard/_chat_error.html",
            {"message": "No pudimos generar una respuesta en este momento. Intenta de nuevo."},
            status=503,
        )

    return render(
        request,
        "dashboard/_chat_message.html",
        {"connection": connection, "nl_query": nl_query},
    )
