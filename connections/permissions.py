"""Documento 04 Parte A.2 (broken authentication): verificacion de email
obligatoria antes de conectar la primera base de datos.

Se usa tanto desde la API DRF como desde la vista HTMX de onboarding, para
que la regla no dependa de un solo punto de entrada.
"""

from __future__ import annotations

from allauth.account.models import EmailAddress
from rest_framework.permissions import BasePermission


def user_has_verified_email(user) -> bool:
    return EmailAddress.objects.filter(user=user, verified=True).exists()


class HasVerifiedEmail(BasePermission):
    message = "Debes verificar tu email antes de conectar una base de datos."

    def has_permission(self, request, view):
        if getattr(view, "action", None) != "create":
            return True
        return user_has_verified_email(request.user)
