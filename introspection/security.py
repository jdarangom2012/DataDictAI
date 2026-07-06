"""Guarda SSRF para conexiones a bases de datos de clientes.

Documento 04 Parte A.2: el usuario nos da un host/puerto, riesgo real de SSRF.
Validamos que no apunte a rangos de IP internos de nuestra propia infraestructura
(loopback, link-local, privados) antes de intentar conectar.

En desarrollo/CI, nuestro propio stack (docker-compose) vive en un rango privado,
por eso ALLOW_PRIVATE_DB_HOSTS permite explicitamente saltar la validacion ahi.
Nunca debe estar en True en produccion.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

from django.conf import settings


class UnsafeDatabaseHostError(Exception):
    """El host de conexion no es seguro para conectarse (SSRF)."""


def assert_host_is_safe(dsn: str) -> None:
    host = urlsplit(dsn).hostname
    if not host:
        raise UnsafeDatabaseHostError("connection string is missing a host")

    if getattr(settings, "ALLOW_PRIVATE_DB_HOSTS", False):
        return

    try:
        addr_infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeDatabaseHostError("could not resolve connection host") from exc

    for *_, sockaddr in addr_infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise UnsafeDatabaseHostError(
                "connection host resolves to a disallowed internal network range"
            )
