"""drf-spectacular: el OpenAPI se genera automatico, no se escribe a mano
(Documento 03 SS5)."""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client(django_user_model):
    user = django_user_model.objects.create_user(username="dev", password="x")
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
def test_schema_endpoint_returns_a_valid_openapi_document(client):
    response = client.get("/api/schema/")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/vnd.oai.openapi")
    body = response.content.decode()
    assert "openapi:" in body
    assert "/api/v1/connections/" in body


@pytest.mark.django_db
def test_swagger_ui_renders(client):
    response = client.get("/api/docs/")

    assert response.status_code == 200
    assert "swagger" in response.content.decode().lower()


@pytest.mark.django_db
def test_schema_endpoint_requires_authentication():
    response = APIClient().get("/api/schema/")

    assert response.status_code in (401, 403)
