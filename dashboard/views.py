"""Vistas HTMX del panel del usuario (Documento 03 SS6: Onboarding + Dashboard).

Reutiliza DatabaseConnectionCreateSerializer para no duplicar la validacion
de formato ni la encriptacion que ya usa la API REST (connections/serializers.py).
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

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
