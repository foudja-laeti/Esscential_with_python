"""Tests FastAPI natifs, contrats de validation et concurrence asynchrone."""
import asyncio
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from services.http import create_app

@pytest.mark.parametrize("service", ["users", "products", "orders"])
def test_openapi_and_interactive_docs(service):
    app = create_app(service)
    assert isinstance(app, FastAPI)
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200
        schema = client.get("/openapi.json").json()
        assert "/api/" + service in schema["paths"]
        operation = schema["paths"]["/api/" + service]["post"]
        assert operation["requestBody"]["required"]
        assert "400" in operation["responses"]
        assert client.get("/api/" + service + "/").status_code == 404
        assert client.post("/api/" + service, json={"unknown": "value"}).status_code == 400


def test_invalid_body_is_400_and_not_422():
    with TestClient(create_app("products")) as client:
        for body in [{"name": "X", "priceCents": "12", "stock": 1}, {"name": "X", "priceCents": True, "stock": 1}, None]:
            response = client.post("/api/products", content=__import__('json').dumps(body), headers={"Content-Type": "application/json"})
            assert response.status_code == 400
            assert response.json()["error"]["code"] == "VALIDATION_ERROR"
        assert client.get("/api/products").json()["meta"]["total"] == 3


def test_simulated_delay_does_not_block_health():
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app("users", delay_ms=600)), base_url="http://test") as client:
            slow = asyncio.create_task(client.get("/api/users"))
            try:
                await asyncio.sleep(.05)
                health = await asyncio.wait_for(client.get("/health"), timeout=.3)
                assert health.status_code == 200
                assert not slow.done()
                assert (await slow).status_code == 200
            finally:
                slow.cancel()
                await asyncio.gather(slow, return_exceptions=True)
    asyncio.run(scenario())


def test_unexpected_error_keeps_json_contract_without_internal_details(monkeypatch):
    app = create_app("users")
    def fail(query):
        raise RuntimeError("private-internal-detail")
    monkeypatch.setattr(app.state.store, "listing", fail)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/users")
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "INTERNAL_ERROR"
        assert "private-internal-detail" not in response.text
