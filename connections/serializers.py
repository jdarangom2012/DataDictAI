"""Serializers de DatabaseConnection.

Documento 03 SS3: el detalle de una conexion "nunca devuelve credenciales".
DatabaseConnectionSerializer (usado en list/retrieve/sync) ni siquiera declara
el campo encrypted_credentials.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from rest_framework import serializers

from connections.models import DatabaseConnection


class DatabaseConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatabaseConnection
        fields = ["id", "name", "engine", "status", "last_synced_at", "created_at"]


class DatabaseConnectionCreateSerializer(serializers.ModelSerializer):
    connection_string = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = DatabaseConnection
        fields = ["id", "name", "engine", "connection_string", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def validate_connection_string(self, value):
        parsed = urlsplit(value)
        if parsed.scheme not in ("postgres", "postgresql"):
            raise serializers.ValidationError(
                "El connection string debe usar el esquema postgres:// o postgresql://",
                code="invalid_credentials_format",
            )
        if not parsed.hostname:
            raise serializers.ValidationError(
                "El connection string no tiene un host valido",
                code="invalid_credentials_format",
            )
        if not parsed.path or parsed.path == "/":
            raise serializers.ValidationError(
                "El connection string no tiene un nombre de base de datos",
                code="invalid_credentials_format",
            )
        return value

    def create(self, validated_data):
        connection_string = validated_data.pop("connection_string")
        connection = DatabaseConnection(user=self.context["request"].user, **validated_data)
        connection.set_credentials(connection_string)
        connection.save()
        return connection
