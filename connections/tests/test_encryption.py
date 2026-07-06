"""Tests para el punto mas critico del producto (Documento 04 Parte A.1):
las credenciales de terceros nunca deben quedar en texto plano, en ningun
punto del flujo, y su cifrado/descifrado debe ser correcto y a prueba de
manipulacion.
"""

import pytest
from cryptography.fernet import Fernet

from connections.encryption import (
    CredentialEncryptionError,
    decrypt_credentials,
    encrypt_credentials,
)
from connections.models import DatabaseConnection

CONNECTION_STRING = "postgresql://readonly_user:s3cr3t-p4ss@db.example.com:5432/prod"


def test_encrypt_then_decrypt_roundtrip():
    token = encrypt_credentials(CONNECTION_STRING)
    assert decrypt_credentials(token) == CONNECTION_STRING


def test_ciphertext_never_contains_plaintext():
    token = encrypt_credentials(CONNECTION_STRING)
    assert CONNECTION_STRING.encode("utf-8") not in token
    assert b"s3cr3t-p4ss" not in token


def test_ciphertext_is_bytes_and_differs_from_plaintext():
    token = encrypt_credentials(CONNECTION_STRING)
    assert isinstance(token, bytes)
    assert token != CONNECTION_STRING.encode("utf-8")


def test_encrypting_same_plaintext_twice_yields_different_ciphertext():
    # Fernet incluye timestamp/IV: dos cifrados del mismo texto no deben coincidir.
    token_a = encrypt_credentials(CONNECTION_STRING)
    token_b = encrypt_credentials(CONNECTION_STRING)
    assert token_a != token_b
    assert decrypt_credentials(token_a) == decrypt_credentials(token_b) == CONNECTION_STRING


def test_encrypt_rejects_empty_plaintext():
    with pytest.raises(ValueError):
        encrypt_credentials("")


def test_decrypt_rejects_empty_token():
    with pytest.raises(ValueError):
        decrypt_credentials(b"")


def test_tampered_ciphertext_raises_credential_encryption_error():
    token = bytearray(encrypt_credentials(CONNECTION_STRING))
    token[-1] ^= 0xFF  # corrompe el ultimo byte (HMAC de Fernet debe rechazarlo)
    with pytest.raises(CredentialEncryptionError):
        decrypt_credentials(bytes(token))


def test_decrypting_with_wrong_key_raises_credential_encryption_error(settings):
    token = encrypt_credentials(CONNECTION_STRING)
    settings.FERNET_KEY = Fernet.generate_key()
    with pytest.raises(CredentialEncryptionError):
        decrypt_credentials(token)


def test_missing_fernet_key_raises_credential_encryption_error(settings):
    settings.FERNET_KEY = None
    with pytest.raises(CredentialEncryptionError):
        encrypt_credentials(CONNECTION_STRING)
    with pytest.raises(CredentialEncryptionError):
        decrypt_credentials(b"anything")


def test_invalid_fernet_key_format_raises_credential_encryption_error(settings):
    settings.FERNET_KEY = "not-a-valid-fernet-key"
    with pytest.raises(CredentialEncryptionError):
        encrypt_credentials(CONNECTION_STRING)


@pytest.mark.django_db
def test_database_connection_set_and_get_credentials_roundtrip(django_user_model):
    user = django_user_model.objects.create_user(username="dev", password="x")
    conn = DatabaseConnection(user=user, name="Produccion")
    conn.set_credentials(CONNECTION_STRING)
    conn.save()

    conn.refresh_from_db()
    assert conn.get_credentials() == CONNECTION_STRING
    assert CONNECTION_STRING.encode("utf-8") not in bytes(conn.encrypted_credentials)


@pytest.mark.django_db
def test_database_connection_str_and_repr_never_expose_credentials(django_user_model):
    user = django_user_model.objects.create_user(username="dev2", password="x")
    conn = DatabaseConnection(user=user, name="Staging")
    conn.set_credentials(CONNECTION_STRING)
    conn.save()

    assert "s3cr3t-p4ss" not in str(conn)
    assert "s3cr3t-p4ss" not in repr(conn)
    assert CONNECTION_STRING not in str(conn)
    assert CONNECTION_STRING not in repr(conn)


@pytest.mark.django_db
def test_database_connection_admin_excludes_credentials_field():
    from connections.admin import DatabaseConnectionAdmin

    assert "encrypted_credentials" in DatabaseConnectionAdmin.exclude
    assert "encrypted_credentials" not in DatabaseConnectionAdmin.list_display
