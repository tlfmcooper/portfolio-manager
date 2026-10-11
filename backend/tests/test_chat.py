import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException
from redis.exceptions import ConnectionError

from app.api.v1 import chat
from app.core.config import settings
from app.services.chat_secrets import ChatSecrets, get_chat_secrets
from app.utils.dependencies import get_current_active_user


class MemoryRedis:
    def __init__(self):
        self.values = {}
        self.set_options = []

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, **options):
        self.values[key] = value
        self.set_options.append(options)
        return True

    async def delete(self, key):
        return self.values.pop(key, None) is not None


@pytest.fixture
def secret_store():
    return ChatSecrets(MemoryRedis(), Fernet.generate_key().decode())


@pytest.mark.asyncio
async def test_encryption_user_isolation_replace_delete_and_no_expiry(secret_store):
    await secret_store.save(1, "first-secret")
    ciphertext = secret_store.redis.values[secret_store.storage_key(1)]
    assert b"first-secret" not in ciphertext
    assert await secret_store.read(1) == "first-secret"
    assert await secret_store.read(2) is None
    assert secret_store.redis.set_options == [{}]
    await secret_store.save(1, "replacement-secret")
    assert await secret_store.read(1) == "replacement-secret"
    await secret_store.delete(1)
    await secret_store.delete(1)
    assert await secret_store.read(1) is None


@pytest.mark.asyncio
async def test_tampering_wrong_encryption_key_and_swapped_user(secret_store):
    await secret_store.save(1, "hidden-secret")
    token = secret_store.redis.values[secret_store.storage_key(1)]
    secret_store.redis.values[secret_store.storage_key(2)] = token
    with pytest.raises(HTTPException) as error:
        await secret_store.read(2)
    assert error.value.status_code == 503
    secret_store.redis.values[secret_store.storage_key(1)] = b"corrupted"
    with pytest.raises(HTTPException):
        await secret_store.read(1)
    secret_store.redis.values[secret_store.storage_key(1)] = token
    other = ChatSecrets(secret_store.redis, Fernet.generate_key().decode())
    with pytest.raises(HTTPException):
        await other.read(1)


@pytest.mark.parametrize("key", ["", "invalid", "non-ascii-\u00e9"])
def test_missing_or_invalid_encryption_configuration(key):
    with pytest.raises(HTTPException) as error:
        ChatSecrets(MemoryRedis(), key)
    assert error.value.status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["get", "set", "delete"])
async def test_redis_failures_are_sanitized(secret_store, operation):
    setattr(secret_store.redis, operation, AsyncMock(side_effect=ConnectionError("hidden-secret connection details")))
    with pytest.raises(HTTPException) as error:
        if operation == "get":
            await secret_store.read(1)
        elif operation == "set":
            await secret_store.save(1, "hidden-secret")
        else:
            await secret_store.delete(1)
    assert error.value.status_code == 503
    assert "hidden-secret" not in error.value.detail


@pytest.mark.asyncio
async def test_unacknowledged_write_does_not_report_success(secret_store):
    secret_store.redis.set = AsyncMock(return_value=False)
    with pytest.raises(HTTPException):
        await secret_store.save(1, "secret")


@pytest_asyncio.fixture
async def client(secret_store):
    app = FastAPI()
    app.include_router(chat.router, prefix="/api/v1/chat")
    app.dependency_overrides[get_chat_secrets] = lambda: secret_store
    user = SimpleNamespace(id=1)
    app.dependency_overrides[get_current_active_user] = lambda: user
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client, app, user


@pytest.mark.asyncio
async def test_authenticated_crud_returns_only_status(client, secret_store):
    client, _, user = client
    assert (await client.get("/api/v1/chat/api-key")).json() == {"configured": False}
    saved = await client.put("/api/v1/chat/api-key", json={"api_key": "hidden-secret", "user_id": 2})
    assert saved.json() == {"configured": True}
    assert saved.headers["cache-control"] == "no-store"
    user.id = 2
    assert (await client.get("/api/v1/chat/api-key")).json() == {"configured": False}
    user.id = 1
    removed = await client.delete("/api/v1/chat/api-key")
    assert removed.json() == {"configured": False}
    assert await secret_store.read(1) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", [("GET", "api-key"), ("PUT", "api-key"), ("DELETE", "api-key"), ("POST", "generate")])
async def test_routes_require_authentication(client, method, path):
    client, app, _ = client
    app.dependency_overrides.pop(get_current_active_user)
    response = await client.request(method, f"/api/v1/chat/{path}")
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["", "  ", "hidden-secret\n", "hidden-secret\u00e9", "hidden-secret" * 500, None, 123])
async def test_invalid_key_errors_do_not_echo_input(client, key):
    client, _, _ = client
    response = await client.put("/api/v1/chat/api-key", json={"api_key": key})
    assert response.status_code == 422
    assert "hidden-secret" not in response.text


BODY = {
    "contents": [{"role": "user", "parts": [{"text": "Hello"}, {"inlineData": {"mimeType": "image/jpeg", "data": "base64"}}]}],
    "systemInstruction": {"parts": [{"text": "Be helpful"}]},
    "tools": [{"functionDeclarations": [{"name": "get_portfolio_summary"}]}],
}


class Stream(httpx.AsyncByteStream):
    def __init__(self, chunks, fail=False):
        self.chunks = chunks
        self.fail = fail
        self.closed = False

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk
        if self.fail:
            raise httpx.ReadError("hidden-secret provider diagnostics")

    async def aclose(self):
        self.closed = True


def install_upstream(monkeypatch, handler):
    actual_client = httpx.AsyncClient
    created = []
    def factory(**kwargs):
        client = actual_client(transport=httpx.MockTransport(handler), **kwargs)
        created.append(client)
        return client
    monkeypatch.setattr(chat.httpx, "AsyncClient", factory)
    return created


@pytest.mark.asyncio
async def test_proxy_stream_preserves_text_function_calls_and_images(client, secret_store, monkeypatch):
    client, _, _ = client
    await secret_store.save(1, "hidden-secret")
    part = {"functionCall": {"name": "get_portfolio_summary", "args": {}, "id": "call-1"}, "thoughtSignature": "signature"}
    chunks = [b'data: {"candidates":[{"content":{"parts":[{"text":"Hello"}]}}]}\n\n',
              ("data: " + json.dumps({"candidates": [{"content": {"parts": [part]}, "finishReason": "STOP"}]}) + "\n\n").encode()]
    stream = Stream(chunks)
    def handler(request):
        assert request.headers["x-goog-api-key"] == "hidden-secret"
        assert "hidden-secret" not in str(request.url)
        assert json.loads(request.content) == BODY
        return httpx.Response(200, stream=stream)
    created = install_upstream(monkeypatch, handler)
    response = await client.post("/api/v1/chat/generate", json=BODY)
    assert response.status_code == 200
    assert '"text": "Hello"' in response.text
    assert '"thoughtSignature": "signature"' in response.text
    assert '"done": true' in response.text
    assert "hidden-secret" not in response.text
    assert response.headers["x-accel-buffering"] == "no"
    assert stream.closed and created[0].is_closed


@pytest.mark.asyncio
@pytest.mark.parametrize("status,expected", [(400, 400), (401, 400), (403, 400), (429, 429), (500, 502)])
async def test_upstream_rejections_are_sanitized(client, secret_store, monkeypatch, status, expected):
    client, _, _ = client
    await secret_store.save(1, "hidden-secret")
    created = install_upstream(monkeypatch, lambda request: httpx.Response(status, json={"error": "hidden-secret"}))
    response = await client.post("/api/v1/chat/generate", json=BODY)
    assert response.status_code == expected
    assert "hidden-secret" not in response.text
    assert created[0].is_closed


@pytest.mark.asyncio
@pytest.mark.parametrize("chunks,fail", [([b'data: {"error":"hidden-secret"}\n\n'], False), ([b'data: invalid\n\n'], False), ([], True)])
async def test_midstream_failures_are_sanitized_and_connections_closed(client, secret_store, monkeypatch, chunks, fail):
    client, _, _ = client
    await secret_store.save(1, "hidden-secret")
    stream = Stream(chunks, fail=fail)
    created = install_upstream(monkeypatch, lambda request: httpx.Response(200, stream=stream))
    response = await client.post("/api/v1/chat/generate", json=BODY)
    assert '"error"' in response.text
    assert '"done"' not in response.text
    assert "hidden-secret" not in response.text
    assert stream.closed and created[0].is_closed


@pytest.mark.asyncio
async def test_missing_key_and_invalid_model(client, secret_store, monkeypatch):
    client, _, _ = client
    response = await client.post("/api/v1/chat/generate", json=BODY)
    assert response.status_code == 409
    await secret_store.save(1, "hidden-secret")
    monkeypatch.setattr(settings, "CHAT_GEMINI_MODEL", "bad/model?key=secret")
    assert (await client.post("/api/v1/chat/generate", json=BODY)).status_code == 503


@pytest.mark.asyncio
async def test_clean_but_truncated_upstream_does_not_complete(client, secret_store, monkeypatch):
    client, _, _ = client
    await secret_store.save(1, "hidden-secret")
    stream = Stream([b'data: {"candidates":[{"content":{"parts":[{"text":"partial"}]}}]}\n\n'])
    install_upstream(monkeypatch, lambda request: httpx.Response(200, stream=stream))
    response = await client.post("/api/v1/chat/generate", json=BODY)
    assert '"text": "partial"' in response.text
    assert '"error"' in response.text
    assert '"done"' not in response.text


@pytest.mark.asyncio
async def test_cancelled_stream_closes_upstream_resources(secret_store, monkeypatch):
    await secret_store.save(1, "hidden-secret")
    stream = Stream([b'data: {"candidates":[{"content":{"parts":[{"text":"partial"}]}}]}\n\n'])
    created = install_upstream(monkeypatch, lambda request: httpx.Response(200, stream=stream))
    response = await chat.generate(chat.GenerateRequest(**BODY), user=SimpleNamespace(id=1), secrets=secret_store)
    assert "partial" in await anext(response.body_iterator)
    await response.body_iterator.aclose()
    assert stream.closed and created[0].is_closed


@pytest.mark.asyncio
async def test_malformed_secret_body_and_openapi_write_only_schema(client):
    client, app, _ = client
    response = await client.put("/api/v1/chat/api-key", content="hidden-secret invalid json", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert "hidden-secret" not in response.text
    schema = app.openapi()["paths"]["/api/v1/chat/api-key"]["put"]["requestBody"]["content"]["application/json"]["schema"]
    assert schema["properties"]["api_key"]["writeOnly"] is True
