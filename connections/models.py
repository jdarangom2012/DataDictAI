from django.conf import settings
from django.db import models

from connections.encryption import decrypt_credentials, encrypt_credentials


class DatabaseConnection(models.Model):
    class Engine(models.TextChoices):
        POSTGRESQL = "postgresql", "PostgreSQL"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONNECTED = "connected", "Connected"
        ERROR = "error", "Error"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="connections"
    )
    name = models.CharField(max_length=100)
    engine = models.CharField(max_length=20, choices=Engine.choices, default=Engine.POSTGRESQL)
    # Fernet ciphertext of the full connection string. Never store or log plaintext.
    encrypted_credentials = models.BinaryField()
    last_synced_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.user})"

    def __repr__(self) -> str:
        return f"<DatabaseConnection id={self.pk} name={self.name!r} status={self.status!r}>"

    def set_credentials(self, connection_string: str) -> None:
        """Encrypts and stores a plaintext connection string. Never assign the field directly."""
        self.encrypted_credentials = encrypt_credentials(connection_string)

    def get_credentials(self) -> str:
        """Decrypts the stored connection string. Callers must never log the result."""
        return decrypt_credentials(bytes(self.encrypted_credentials))
