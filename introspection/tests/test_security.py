"""Documento 04 Parte A.2: el host de conexion lo da el cliente, riesgo real de SSRF.

Los tests fuerzan ALLOW_PRIVATE_DB_HOSTS explicitamente (via el fixture `settings`)
en lugar de asumir un valor ambiente, porque en dev/CI ese flag esta en True
(nuestro propio stack vive en red privada).
"""

import pytest

from introspection.security import UnsafeDatabaseHostError, assert_host_is_safe


@pytest.fixture(autouse=True)
def block_private_hosts_by_default(settings):
    settings.ALLOW_PRIVATE_DB_HOSTS = False


def test_loopback_host_is_blocked_by_default():
    with pytest.raises(UnsafeDatabaseHostError):
        assert_host_is_safe("postgresql://user:pass@127.0.0.1:5432/db")


def test_localhost_hostname_is_blocked_by_default():
    with pytest.raises(UnsafeDatabaseHostError):
        assert_host_is_safe("postgresql://user:pass@localhost:5432/db")


def test_private_rfc1918_host_is_blocked_by_default():
    with pytest.raises(UnsafeDatabaseHostError):
        assert_host_is_safe("postgresql://user:pass@10.0.0.5:5432/db")


def test_link_local_host_is_blocked_by_default():
    with pytest.raises(UnsafeDatabaseHostError):
        assert_host_is_safe("postgresql://user:pass@169.254.169.254:5432/db")


def test_public_ip_is_allowed_by_default():
    # 8.8.8.8 es un literal IP: no requiere resolucion DNS real ni red saliente.
    assert_host_is_safe("postgresql://user:pass@8.8.8.8:5432/db")


def test_missing_host_is_rejected():
    with pytest.raises(UnsafeDatabaseHostError):
        assert_host_is_safe("postgresql:///db")


def test_allow_private_db_hosts_override_permits_private_targets(settings):
    settings.ALLOW_PRIVATE_DB_HOSTS = True
    assert_host_is_safe("postgresql://user:pass@127.0.0.1:5432/db")
    assert_host_is_safe("postgresql://user:pass@10.0.0.5:5432/db")
