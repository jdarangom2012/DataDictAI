"""Fernet-based encryption for third-party database credentials.

Documento 02 §5 / Documento 04 Parte A.1 — reglas no negociables:
- El connection string nunca se persiste en texto plano, en ningun punto.
- La clave vive en FERNET_KEY (env var / Key Vault), nunca en el repo.
- Ninguna excepcion ni log de este modulo debe incluir el texto plano.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class CredentialEncryptionError(Exception):
    """Raised when credentials cannot be encrypted or decrypted.

    Never include the plaintext connection string or the Fernet key in
    this exception's message — only stable, non-sensitive context.
    """


def _get_fernet() -> Fernet:
    key = getattr(settings, "FERNET_KEY", None)
    if not key:
        raise CredentialEncryptionError(
            "FERNET_KEY is not configured. Set it via environment variable / Key Vault."
        )
    try:
        return Fernet(key)
    except (ValueError, TypeError) as exc:
        raise CredentialEncryptionError("FERNET_KEY is not a valid Fernet key.") from exc


def encrypt_credentials(plaintext: str) -> bytes:
    """Encrypts a plaintext connection string. Returns Fernet ciphertext bytes."""
    if not plaintext:
        raise ValueError("plaintext connection string must not be empty")
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode("utf-8"))


def decrypt_credentials(token: bytes) -> str:
    """Decrypts Fernet ciphertext bytes back into the plaintext connection string."""
    if not token:
        raise ValueError("encrypted token must not be empty")
    fernet = _get_fernet()
    try:
        return fernet.decrypt(bytes(token)).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialEncryptionError(
            "Unable to decrypt credentials: invalid token or wrong key."
        ) from exc
