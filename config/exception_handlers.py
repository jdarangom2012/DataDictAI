"""Formato de error consistente en toda la API (Documento 03 SS4):

{"error": {"code": ..., "message": ..., "field": ...}}
"""

from __future__ import annotations

from rest_framework.views import exception_handler as drf_exception_handler


def _first_leaf(value):
    if isinstance(value, dict):
        for v in value.values():
            return _first_leaf(v)
        return None
    if isinstance(value, list):
        return _first_leaf(value[0]) if value else None
    return value


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    detail = response.data
    codes = exc.get_codes() if hasattr(exc, "get_codes") else None

    field = None
    if isinstance(detail, dict):
        keys = [k for k in detail if k not in ("detail", "non_field_errors")]
        if keys:
            field = keys[0]

    message = str(_first_leaf(detail))
    code = _first_leaf(codes) if codes is not None else "error"
    if not isinstance(code, str):
        code = "error"

    response.data = {"error": {"code": code, "message": message, "field": field}}
    return response
