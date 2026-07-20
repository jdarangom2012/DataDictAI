"""Vistas HTMX del panel del usuario (Documento 03 SS6: Onboarding + Dashboard).

Reutiliza DatabaseConnectionCreateSerializer para no duplicar la validacion
de formato ni la encriptacion que ya usa la API REST (connections/serializers.py).

IMPORTANTE: estas respuestas de error se devuelven con status 200 a proposito.
htmx (config.responseHandling por defecto) NO actualiza el DOM en respuestas
4xx/5xx -- las trata como error y no hace swap, asi que el mensaje nunca se
veria en pantalla. El estado de error es parte normal de la UI aqui, no una
falla de protocolo (la API DRF en connections/views.py si usa codigos correctos,
para consumidores que no son htmx).
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from accounts.billing import PLAN_CONNECTION_LIMITS, BillingError, create_checkout
from ai_engine.client import AIExplanationError
from ai_engine.models import NLQuery
from ai_engine.services import NoSchemaAvailableError, ask_question
from connections.models import DatabaseConnection
from connections.permissions import user_has_verified_email
from connections.serializers import DatabaseConnectionCreateSerializer
from introspection.tasks import introspect_database
from snapshots.models import SchemaDiff


def _user_connections(user):
    return DatabaseConnection.objects.filter(user=user).order_by("-created_at")


def home(request):
    if not request.user.is_authenticated:
        return render(request, "dashboard/landing.html")

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
        )

    limit = PLAN_CONNECTION_LIMITS.get(request.user.plan, 1)
    if connections.count() >= limit:
        return render(
            request,
            "dashboard/_dashboard_content.html",
            {
                "connections": connections,
                "form_error": (
                    "Alcanzaste el limite de conexiones de tu plan actual. "
                    "Sube de plan para conectar mas bases de datos."
                ),
            },
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
def diffs_view(request, pk):
    connection = get_object_or_404(DatabaseConnection, pk=pk, user=request.user)
    diffs = list(SchemaDiff.objects.filter(connection=connection)[:50])
    return render(request, "dashboard/diffs.html", {"connection": connection, "diffs": diffs})


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
        )

    try:
        nl_query = ask_question(connection, request.user, question)
    except NoSchemaAvailableError:
        return render(
            request,
            "dashboard/_chat_error.html",
            {"message": "Todavia no hay un esquema sincronizado para esta conexion."},
        )
    except AIExplanationError:
        return render(
            request,
            "dashboard/_chat_error.html",
            {"message": "No pudimos generar una respuesta en este momento. Intenta de nuevo."},
        )

    return render(
        request,
        "dashboard/_chat_message.html",
        {"connection": connection, "nl_query": nl_query},
    )


@login_required
def billing_view(request):
    return render(
        request,
        "dashboard/billing.html",
        {
            "current_plan": request.user.plan,
            "plan_limits": PLAN_CONNECTION_LIMITS,
        },
    )


@login_required
@require_POST
def start_checkout(request):
    plan = request.POST.get("plan")
    if plan not in PLAN_CONNECTION_LIMITS:
        return render(
            request,
            "dashboard/_billing_error.html",
            {"message": "Plan invalido."},
        )

    try:
        checkout_url = create_checkout(request.user, plan)
    except BillingError:
        return render(
            request,
            "dashboard/_billing_error.html",
            {"message": "No pudimos iniciar el pago. Intenta de nuevo."},
        )

    # HX-Redirect le dice a htmx que haga una redireccion de pagina completa
    # (necesario porque el checkout vive fuera de nuestro dominio).
    response = HttpResponse(status=200)
    response["HX-Redirect"] = checkout_url
    return response
