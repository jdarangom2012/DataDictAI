from __future__ import annotations

from rest_framework import serializers

from ai_engine.models import NLQuery


class NLQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = NLQuery
        fields = ["id", "question", "answer", "referenced_tables", "created_at"]


class AskQuestionSerializer(serializers.Serializer):
    question = serializers.CharField(trim_whitespace=True, max_length=2000, allow_blank=True)

    def validate_question(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "La pregunta no puede estar vacia.", code="invalid_question"
            )
        return value.strip()
