from __future__ import annotations

from rest_framework import serializers

from snapshots.models import SchemaDiff


class SchemaDiffSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchemaDiff
        fields = ["id", "from_snapshot", "to_snapshot", "changes_json", "created_at"]
