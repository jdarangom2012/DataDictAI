"""ai_engine.client no debe llamar a un proveedor de IA real en tests (costo/red).

Documento 02 SS6: input es solo estructura (nunca filas), y el fallback debe ser
explicito cuando no hay contexto suficiente o el proveedor falla.
"""

from unittest.mock import MagicMock, patch

import pytest
from openai import OpenAIError

from ai_engine.client import (
    NO_ANSWER_FALLBACK,
    NO_CONTEXT_EXPLANATION,
    AIExplanationError,
    _build_user_prompt,
    answer_question,
    explain_table,
)

TABLE_DATA = {
    "columns": [
        {"name": "id", "data_type": "integer", "is_nullable": False},
        {
            "name": "user_id",
            "data_type": "integer",
            "is_nullable": False,
            "is_foreign_key": True,
            "references_table": "users",
        },
    ]
}


def _mock_openai_response(text):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=text))]
    return response


def test_explain_table_returns_fallback_when_no_api_key(settings):
    settings.AI_API_KEY = None
    assert explain_table("orders", TABLE_DATA) == NO_CONTEXT_EXPLANATION


def test_explain_table_returns_ai_response(settings):
    settings.AI_API_KEY = "fake-key"
    with patch("ai_engine.client.OpenAI") as mock_openai_cls:
        mock_client = mock_openai_cls.return_value
        mock_client.chat.completions.create.return_value = _mock_openai_response(
            "Guarda las ordenes de compra de cada usuario."
        )
        result = explain_table("orders", TABLE_DATA)

    assert result == "Guarda las ordenes de compra de cada usuario."


def test_explain_table_returns_fallback_when_ai_response_is_blank(settings):
    settings.AI_API_KEY = "fake-key"
    with patch("ai_engine.client.OpenAI") as mock_openai_cls:
        mock_client = mock_openai_cls.return_value
        mock_client.chat.completions.create.return_value = _mock_openai_response("   ")
        result = explain_table("xk9_tbl", TABLE_DATA)

    assert result == NO_CONTEXT_EXPLANATION


def test_explain_table_raises_on_provider_error(settings):
    settings.AI_API_KEY = "fake-key"
    with patch("ai_engine.client.OpenAI") as mock_openai_cls:
        mock_client = mock_openai_cls.return_value
        mock_client.chat.completions.create.side_effect = OpenAIError("boom")
        with pytest.raises(AIExplanationError):
            explain_table("orders", TABLE_DATA)


def test_prompt_includes_structure_but_never_row_data():
    prompt = _build_user_prompt("orders", TABLE_DATA)
    assert "id" in prompt
    assert "user_id" in prompt
    assert "users" in prompt  # nombre de tabla referenciada (estructura, no dato)
    assert "row_count_estimate" not in prompt


RAW_SCHEMA = {
    "tables": {
        "users": {"columns": [{"name": "email", "data_type": "text", "is_nullable": False}]},
    }
}


def test_answer_question_returns_fallback_when_no_api_key(settings):
    settings.AI_API_KEY = None
    assert answer_question("¿qué tabla tiene el email?", RAW_SCHEMA) == NO_ANSWER_FALLBACK


def test_answer_question_returns_ai_response(settings):
    settings.AI_API_KEY = "fake-key"
    with patch("ai_engine.client.OpenAI") as mock_openai_cls:
        mock_client = mock_openai_cls.return_value
        mock_client.chat.completions.create.return_value = _mock_openai_response(
            "La tabla 'users' tiene el email."
        )
        result = answer_question("¿qué tabla tiene el email?", RAW_SCHEMA)

    assert result == "La tabla 'users' tiene el email."


def test_answer_question_returns_fallback_when_ai_response_is_blank(settings):
    settings.AI_API_KEY = "fake-key"
    with patch("ai_engine.client.OpenAI") as mock_openai_cls:
        mock_client = mock_openai_cls.return_value
        mock_client.chat.completions.create.return_value = _mock_openai_response("")
        result = answer_question("¿qué tabla tiene el email?", RAW_SCHEMA)

    assert result == NO_ANSWER_FALLBACK


def test_answer_question_raises_on_provider_error(settings):
    settings.AI_API_KEY = "fake-key"
    with patch("ai_engine.client.OpenAI") as mock_openai_cls:
        mock_client = mock_openai_cls.return_value
        mock_client.chat.completions.create.side_effect = OpenAIError("boom")
        with pytest.raises(AIExplanationError):
            answer_question("¿qué tabla tiene el email?", RAW_SCHEMA)


def test_answer_question_sends_full_schema_as_context(settings):
    settings.AI_API_KEY = "fake-key"
    with patch("ai_engine.client.OpenAI") as mock_openai_cls:
        mock_client = mock_openai_cls.return_value
        mock_client.chat.completions.create.return_value = _mock_openai_response("ok")
        answer_question("¿qué tabla tiene el email?", RAW_SCHEMA)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        user_message = call_kwargs["messages"][1]["content"]
        assert "users" in user_message
        assert "email" in user_message
