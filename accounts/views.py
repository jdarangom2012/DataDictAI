"""Endpoints de billing (Documento 03 SS3): /checkout/, /webhook/, /plan/."""

from __future__ import annotations

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.billing import (
    BillingError,
    create_checkout,
    process_webhook_event,
    verify_webhook_signature,
)
from accounts.serializers import CheckoutRequestSerializer


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            checkout_url = create_checkout(request.user, serializer.validated_data["plan"])
        except BillingError:
            return Response(
                {
                    "error": {
                        "code": "billing_unavailable",
                        "message": "No pudimos iniciar el pago. Intenta de nuevo.",
                        "field": None,
                    }
                },
                status=503,
            )

        return Response({"checkout_url": checkout_url}, status=201)


class PlanView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"plan": request.user.plan})


class WebhookView(APIView):
    # LemonSqueezy llama este endpoint server-a-server: no hay sesion ni CSRF,
    # la autenticidad se verifica con la firma HMAC del cuerpo crudo.
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        signature = request.headers.get("X-Signature", "")
        if not verify_webhook_signature(request.body, signature):
            return Response(
                {
                    "error": {
                        "code": "invalid_signature",
                        "message": "Firma de webhook invalida.",
                        "field": None,
                    }
                },
                status=401,
            )

        process_webhook_event(request.data)
        return Response(status=200)
