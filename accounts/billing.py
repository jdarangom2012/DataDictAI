"""Cliente de LemonSqueezy: crea checkouts hospedados y procesa webhooks.

Documento 02: la app 'accounts' es responsable de planes y billing. Se eligio
LemonSqueezy en vez de Stripe porque Stripe no permite crear cuenta vendedora
desde Colombia; LemonSqueezy actua como merchant of record.
"""

from __future__ import annotations

import hashlib
import hmac

import requests
from django.conf import settings

LEMONSQUEEZY_API_BASE = "https://api.lemonsqueezy.com/v1"

# Documento 02 SS7: "limite simple por numero de conexiones activas, ya suficiente"
# para el MVP -- es la unica palanca que distingue los planes hoy.
PLAN_CONNECTION_LIMITS = {
    "starter": 1,
    "pro": 5,
    "team": 15,
}


class BillingError(Exception):
    """El proveedor de billing no pudo procesar la solicitud."""


def _variant_id_for_plan(plan: str) -> str | None:
    return {
        "starter": settings.LEMONSQUEEZY_VARIANT_STARTER,
        "pro": settings.LEMONSQUEEZY_VARIANT_PRO,
        "team": settings.LEMONSQUEEZY_VARIANT_TEAM,
    }.get(plan)


def _plan_for_variant_id(variant_id) -> str | None:
    mapping = {
        str(settings.LEMONSQUEEZY_VARIANT_STARTER): "starter",
        str(settings.LEMONSQUEEZY_VARIANT_PRO): "pro",
        str(settings.LEMONSQUEEZY_VARIANT_TEAM): "team",
    }
    return mapping.get(str(variant_id))


def create_checkout(user, plan: str) -> str:
    """Crea un checkout hospedado en LemonSqueezy y devuelve la URL de pago."""
    variant_id = _variant_id_for_plan(plan)
    if not variant_id:
        raise BillingError(f"unknown plan: {plan}")

    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": user.email,
                    "custom": {"user_id": str(user.id)},
                },
            },
            "relationships": {
                "store": {
                    "data": {"type": "stores", "id": str(settings.LEMONSQUEEZY_STORE_ID)}
                },
                "variant": {
                    "data": {"type": "variants", "id": str(variant_id)}
                },
            },
        }
    }

    try:
        response = requests.post(
            f"{LEMONSQUEEZY_API_BASE}/checkouts",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.LEMONSQUEEZY_API_KEY}",
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json",
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise BillingError("could not create checkout") from exc

    return response.json()["data"]["attributes"]["url"]


def verify_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    """Compara la firma HMAC-SHA256 de LemonSqueezy contra el cuerpo crudo."""
    if not signature_header or not settings.LEMONSQUEEZY_WEBHOOK_SECRET:
        return False
    digest = hmac.new(
        settings.LEMONSQUEEZY_WEBHOOK_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(digest, signature_header)


def process_webhook_event(payload: dict) -> None:
    """Actualiza el plan del usuario segun el evento de LemonSqueezy.

    Nunca lanza por datos inesperados: un evento que no podemos mapear a un
    usuario o plan conocido se ignora en silencio.
    """
    from accounts.models import User

    meta = payload.get("meta", {})
    event_name = meta.get("event_name")
    user_id = meta.get("custom_data", {}).get("user_id")
    if not user_id:
        return

    try:
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError, TypeError):
        return

    attributes = payload.get("data", {}).get("attributes", {})
    customer_id = attributes.get("customer_id")
    if customer_id:
        user.lemonsqueezy_customer_id = str(customer_id)

    if event_name in ("subscription_created", "subscription_updated"):
        if attributes.get("status") in ("active", "on_trial"):
            plan = _plan_for_variant_id(attributes.get("variant_id"))
            if plan:
                user.plan = plan
    elif event_name in ("subscription_cancelled", "subscription_expired"):
        user.plan = User.Plan.STARTER

    user.save(update_fields=["plan", "lemonsqueezy_customer_id"])
