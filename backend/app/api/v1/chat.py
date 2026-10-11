"""Authenticated secret management and Gemini streaming proxy."""

import json
import re
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from app.core.config import settings
from app.models import User
from app.services.chat_secrets import ChatSecrets, get_chat_secrets
from app.utils.dependencies import get_current_active_user

router = APIRouter()
NO_CACHE = {"Cache-Control": "no-store"}


class KeyStatus(BaseModel):
    configured: bool


class SaveKeyRequest(BaseModel):
    api_key: SecretStr = Field(min_length=1, max_length=4096)


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contents: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    systemInstruction: dict[str, Any]
    tools: list[dict[str, Any]] = Field(default_factory=list, max_length=1)


@router.get("/api-key", response_model=KeyStatus)
async def key_status(response: Response, user: User = Depends(get_current_active_user),
                     secrets: ChatSecrets = Depends(get_chat_secrets)):
    response.headers.update(NO_CACHE)
    return KeyStatus(configured=await secrets.read(user.id) is not None)


@router.put("/api-key", response_model=KeyStatus, openapi_extra={
    "requestBody": {"required": True, "content": {"application/json": {
        "schema": SaveKeyRequest.model_json_schema(),
    }}},
})
async def save_key(request: Request, response: Response,
                   user: User = Depends(get_current_active_user),
                   secrets: ChatSecrets = Depends(get_chat_secrets)):
    # Validate manually: FastAPI's default validation error would echo the secret input.
    try:
        body = SaveKeyRequest.model_validate(await request.json())
        key = body.api_key.get_secret_value()
        valid = bool(key.strip()) and all(32 <= ord(char) < 127 for char in key)
    except (ValidationError, ValueError, UnicodeError):
        valid = False
    if not valid:
        raise HTTPException(422, "Enter a non-empty API key containing printable ASCII characters.")
    await secrets.save(user.id, key.strip())
    response.headers.update(NO_CACHE)
    return KeyStatus(configured=True)


@router.delete("/api-key", response_model=KeyStatus)
async def delete_key(response: Response, user: User = Depends(get_current_active_user),
                     secrets: ChatSecrets = Depends(get_chat_secrets)):
    await secrets.delete(user.id)
    response.headers.update(NO_CACHE)
    return KeyStatus(configured=False)


def upstream_error(status: int) -> HTTPException:
    if status in (400, 401, 403):
        return HTTPException(400, "Gemini rejected the request. Check your saved API key and the configured model.")
    if status == 429:
        return HTTPException(429, "Gemini quota or rate limit reached. Please try again later.")
    return HTTPException(502, "Gemini is unavailable. Please try again later.")


def event(data: dict) -> str:
    return "data: " + json.dumps(data) + "\n\n"


@router.post("/generate")
async def generate(body: GenerateRequest, user: User = Depends(get_current_active_user),
                   secrets: ChatSecrets = Depends(get_chat_secrets)):
    api_key = await secrets.read(user.id)
    if api_key is None:
        raise HTTPException(409, "Save your Gemini API key in chat settings to continue.")
    model = settings.CHAT_GEMINI_MODEL
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", model):
        raise HTTPException(503, "Chat model is not configured correctly.")
    client = httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10))
    try:
        upstream = await client.send(client.build_request(
            "POST", f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent",
            params={"alt": "sse"}, headers={"x-goog-api-key": api_key},
            json=body.model_dump(),
        ), stream=True)
        if upstream.status_code != 200:
            await upstream.aclose()
            raise upstream_error(upstream.status_code)
    except httpx.HTTPError:
        await client.aclose()
        raise HTTPException(502, "Could not connect to Gemini. Please try again.") from None
    except BaseException:
        await client.aclose()
        raise

    async def stream():
        finished = False

        def parse_chunk(data_lines):
            nonlocal finished
            chunk = json.loads("\n".join(data_lines))
            if not isinstance(chunk, dict) or "error" in chunk:
                raise ValueError("Upstream stream error")
            candidates = chunk.get("candidates", [])
            if any(candidate.get("finishReason") for candidate in candidates):
                finished = True
            if chunk.get("promptFeedback", {}).get("blockReason"):
                finished = True
            # Forward model results only, never provider diagnostics or request metadata.
            return {key: chunk[key] for key in ("candidates", "promptFeedback", "usageMetadata") if key in chunk}

        try:
            data_lines = []
            async for line in upstream.aiter_lines():
                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
                elif not line and data_lines:
                    yield event(parse_chunk(data_lines))
                    data_lines.clear()
            if data_lines:
                yield event(parse_chunk(data_lines))
            if not finished:
                raise ValueError("Upstream response ended before completion")
            yield event({"done": True})
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            yield event({"error": "Gemini response interrupted. Please try again."})
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(stream(), media_type="text/event-stream", headers={
        **NO_CACHE, "X-Accel-Buffering": "no",
    })
