from __future__ import annotations

from rest_framework import serializers

from accounts.billing import PLAN_CONNECTION_LIMITS


class CheckoutRequestSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=list(PLAN_CONNECTION_LIMITS.keys()))
