"""FastAPI transport for the embedded MCP server."""

from __future__ import annotations

import json
import logging
import time
import asyncio
from typing import Any, Iterable
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.mcp.auth import build_auth_context
from app.mcp.errors import MCPError, internal_error, invalid_request, method_not_found, parse_error
from app.mcp.handlers import HandlerContext, sampling_create_message
from app.mcp.handlers import notify_resource_updated
from app.mcp.logging_utils import log_event
from app.mcp.models import (
    CompleteParams,
    InitializeParams,
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
    LoggingSetLevelParams,
    PromptGetParams,
    ResourceSubscribeParams,
    ResourceTemplateListParams,
    ResourceReadParams,
    SamplingCreateMessageParams,
    ServerInfo,
    ToolCallParams,
)
from app.mcp.registry import get_registry
from app.mcp.errors import invalid_params
from app.mcp.logging_utils import get_client_log_level, set_client_log_level, should_emit_client_log
from app.mcp.session_store import session_store


logger = logging.getLogger(__name__)
router = APIRouter(prefix=settings.MCP_ROUTE_PREFIX, tags=["mcp"])


def _to_error_response(request_id: Any, exc: MCPError) -> JSONRPCResponse:
    return JSONRPCResponse(id=request_id, error=JSONRPCError(code=exc.code, message=exc.message, data=exc.data))


async def _dispatch_rpc(request_model: JSONRPCRequest, context: HandlerContext) -> JSONRPCResponse | None:
    registry = get_registry()

    try:
        if request_model.method == "initialize":
            params = InitializeParams.model_validate(request_model.params or {})
            if not params.protocolVersion:
                raise invalid_params(message="Unsupported protocol version", data={"supported": [settings.MCP_PROTOCOL_VERSION], "requested": None})
            session = await session_store.get_or_create_session(context.session_id)
            await session_store.initialize_session(
                session,
                protocol_version=params.protocolVersion,
                client_info=params.clientInfo.model_dump() if params.clientInfo else {},
                client_capabilities=params.capabilities,
            )
            result = {
                "protocolVersion": settings.MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"listChanged": False, "subscribe": True},
                    "prompts": {"listChanged": False},
                    "completions": {},
                    "logging": {},
                    "sampling": {"supported": True},
                    "experimental": {"apps": {"uiResponses": True}},
                },
                "serverInfo": ServerInfo(name=settings.MCP_SERVER_NAME, version=settings.VERSION).model_dump(),
                "instructions": registry.config.server.instructions,
                "clientInfo": params.clientInfo.model_dump() if params.clientInfo else None,
            }
        elif request_model.method == "notifications/initialized":
            return None
        elif request_model.method == "ping":
            result = {}
        elif request_model.method == "completion/complete":
            params = CompleteParams.model_validate(request_model.params or {})
            completion_result = await registry.complete(params.ref.model_dump(), params.argument.model_dump(), context)
            result = completion_result.model_dump(exclude_none=True)
        elif request_model.method == "resources/templates/list":
            ResourceTemplateListParams.model_validate(request_model.params or {})
            result = {"resourceTemplates": [template.model_dump(by_alias=True, exclude_none=True) for template in registry.list_resource_templates()]}
        elif request_model.method == "resources/subscribe":
            params = ResourceSubscribeParams.model_validate(request_model.params or {})
            if not context.session_id:
                raise invalid_params(message="resources/subscribe requires an Mcp-Session-Id header")
            await registry.read_resource(params.uri, context)
            await session_store.add_subscription(context.session_id, params.uri)
            result = {}
        elif request_model.method == "resources/unsubscribe":
            params = ResourceSubscribeParams.model_validate(request_model.params or {})
            if not context.session_id:
                raise invalid_params(message="resources/unsubscribe requires an Mcp-Session-Id header")
            await session_store.remove_subscription(context.session_id, params.uri)
            result = {}
        elif request_model.method == "logging/setLevel":
            params = LoggingSetLevelParams.model_validate(request_model.params or {})
            set_client_log_level(params.level)
            result = {}
        elif request_model.method == "tools/list":
            result = {"tools": [tool.model_dump(by_alias=True, exclude_none=True) for tool in registry.list_tools()]}
        elif request_model.method == "tools/call":
            params = ToolCallParams.model_validate(request_model.params or {})
            tool_result = await registry.execute_tool(params.name, params.arguments, context)
            result = tool_result.model_dump(by_alias=True, exclude_none=True)
        elif request_model.method == "resources/list":
            result = {"resources": [resource.model_dump(by_alias=True, exclude_none=True) for resource in registry.list_resources()]}
        elif request_model.method == "resources/read":
            params = ResourceReadParams.model_validate(request_model.params or {})
            resource_result = await registry.read_resource(params.uri, context)
            result = resource_result.model_dump(by_alias=True, exclude_none=True)
        elif request_model.method == "prompts/list":
            result = {"prompts": [prompt.model_dump(exclude_none=True) for prompt in registry.list_prompts()]}
        elif request_model.method == "prompts/get":
            params = PromptGetParams.model_validate(request_model.params or {})
            prompt_result = await registry.get_prompt(params.name, params.arguments, context)
            result = prompt_result.model_dump(exclude_none=True)
        elif request_model.method == "sampling/createMessage":
            params = SamplingCreateMessageParams.model_validate(request_model.params or {})
            sampling_result = await sampling_create_message(context, params.model_dump())
            result = sampling_result.model_dump(exclude_none=True)
        else:
            raise method_not_found()

        if request_model.id is None:
            return None
        return JSONRPCResponse(id=request_model.id, result=result)
    except MCPError as exc:
        return _to_error_response(request_model.id, exc)
    except ValidationError as exc:
        mcp_exc = invalid_request(message="JSON-RPC payload validation failed", data=exc.errors())
        return _to_error_response(request_model.id, mcp_exc)
    except Exception as exc:
        logger.exception("Unhandled MCP error")
        return _to_error_response(request_model.id, internal_error(data={"error": str(exc)}))


async def _iter_sse(response_payloads: Iterable[JSONRPCResponse], request_id: str):
    yield f"event: ready\ndata: {json.dumps({'requestId': request_id})}\n\n"
    for payload in response_payloads:
        yield f"event: message\ndata: {payload.model_dump_json(exclude_none=True)}\n\n"
    yield "event: done\ndata: {}\n\n"


async def _iter_sse_with_logs(response_payloads: Iterable[JSONRPCResponse], request_id: str, rpc_method: str, duration_ms: float, failed: bool):
    yield f"event: ready\ndata: {json.dumps({'requestId': request_id})}\n\n"
    level = "warning" if failed else "info"
    if should_emit_client_log(level):
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/message",
            "params": {
                "level": level,
                "logger": "app.mcp",
                "data": {
                    "requestId": request_id,
                    "rpcMethod": rpc_method,
                    "durationMs": duration_ms,
                    "configuredLevel": get_client_log_level(),
                },
            },
        }
        yield f"event: message\ndata: {json.dumps(notification)}\n\n"
    for payload in response_payloads:
        yield f"event: message\ndata: {payload.model_dump_json(exclude_none=True)}\n\n"
    yield "event: done\ndata: {}\n\n"


async def _iter_session_sse(session_id: str):
    session, stream = await session_store.attach_stream(session_id)
    try:
        yield f": stream-open session={session.session_id}\n\n"
        while True:
            try:
                event = await asyncio.wait_for(
                    stream.queue.get(), timeout=settings.MCP_SSE_HEARTBEAT_INTERVAL
                )
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue
            yield f"id: {event['event_id']}\nevent: message\ndata: {json.dumps(event['payload'])}\n\n"
    except asyncio.CancelledError:
        raise
    finally:
        await session_store.detach_stream(session.session_id, stream.stream_id)


@router.get("")
async def describe_mcp(
    request: Request,
    mcp_session_id: str | None = Header(default=None, alias="Mcp-Session-Id"),
) -> Response:
    """Discovery endpoint and optional server-to-client SSE stream."""
    accept_header = request.headers.get("accept") or ""
    if "text/event-stream" in accept_header:
        session = await session_store.get_or_create_session(mcp_session_id)
        return StreamingResponse(
            _iter_session_sse(session.session_id),
            media_type="text/event-stream",
            headers={
                "Mcp-Session-Id": session.session_id,
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    registry = get_registry()
    return JSONResponse(
        content={
            "name": settings.MCP_SERVER_NAME,
            "protocolVersion": settings.MCP_PROTOCOL_VERSION,
            "transport": ["json-rpc", "http", "sse"],
            "tools": len(registry.config.tools),
            "resources": len(registry.config.resources),
            "prompts": len(registry.config.prompts),
        }
    )


@router.delete("")
async def delete_mcp_session(mcp_session_id: str | None = Header(default=None, alias="Mcp-Session-Id")) -> Response:
    deleted = await session_store.delete_session(mcp_session_id)
    return Response(status_code=204 if deleted else 404)


@router.post("")
async def handle_mcp(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None, alias="Authorization"),
    api_key: str | None = Header(default=None, alias="x-mcp-api-key"),
    mcp_session_id: str | None = Header(default=None, alias="Mcp-Session-Id"),
) -> Response:
    """Main MCP JSON-RPC endpoint."""
    request_id = request.headers.get("x-request-id", str(uuid4()))
    start_time = time.perf_counter()
    response.headers["x-request-id"] = request_id

    try:
        payload = await request.json()
    except Exception as exc:
        error_response = _to_error_response(None, parse_error(data={"error": str(exc)}))
        return JSONResponse(status_code=400, content=error_response.model_dump(exclude_none=True))

    auth_context = await build_auth_context(db=db, authorization=authorization, api_key=api_key)
    session_id = mcp_session_id

    def _build_context(rpc_method: str) -> HandlerContext:
        return HandlerContext(db=db, auth=auth_context, request_id=request_id, rpc_method=rpc_method, session_id=session_id)

    try:
        if isinstance(payload, list):
            if not payload:
                raise invalid_request(message="Batch requests must not be empty")
            if any(item.get("method") == "initialize" for item in payload if isinstance(item, dict)):
                raise invalid_request(message="initialize must not be sent as part of a JSON-RPC batch")
            requests = [JSONRPCRequest.model_validate(item) for item in payload]
            responses = [await _dispatch_rpc(item, _build_context(item.method)) for item in requests]
            normalized = [item.model_dump(exclude_none=True) for item in responses if item is not None]
            notifications_only = all(item.id is None for item in requests)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            log_event(
                logging.INFO,
                "mcp.request.completed",
                request_id=request_id,
                batch=True,
                rpc_methods=[item.method for item in requests],
                auth_type=auth_context.auth_type,
                duration_ms=duration_ms,
            )
            if notifications_only:
                return Response(status_code=202)
            if not normalized:
                return Response(status_code=204)
            return JSONResponse(content=normalized)

        request_model = JSONRPCRequest.model_validate(payload)
        if request_model.method == "initialize":
            session = await session_store.get_or_create_session(session_id)
            session_id = session.session_id
        elif session_id:
            existing_session = await session_store.get_session(session_id)
            if not existing_session:
                return Response(status_code=404)
        rpc_response = await _dispatch_rpc(request_model, _build_context(request_model.method))
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        log_event(
            logging.INFO,
            "mcp.request.completed",
            request_id=request_id,
            batch=False,
            rpc_method=request_model.method,
            auth_type=auth_context.auth_type,
            duration_ms=duration_ms,
        )
        if request_model.id is None:
            return Response(status_code=202)

        response_headers = {"x-request-id": request_id}
        if request_model.method == "initialize":
            response_headers["Mcp-Session-Id"] = session_id

        if session_id and should_emit_client_log("info"):
            await session_store.publish(
                session_id,
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/message",
                    "params": {
                        "level": "info",
                        "logger": "app.mcp",
                        "data": {
                            "requestId": request_id,
                            "rpcMethod": request_model.method,
                            "durationMs": duration_ms,
                            "configuredLevel": get_client_log_level(),
                        },
                    },
                },
            )

        if rpc_response is None:
            return Response(status_code=204)

        accepts_sse = "text/event-stream" in (request.headers.get("accept") or "") and settings.MCP_ENABLE_SSE
        if accepts_sse:
            return StreamingResponse(
                _iter_sse_with_logs([rpc_response], request_id, request_model.method, duration_ms, failed=False),
                media_type="text/event-stream",
                headers=response_headers,
            )

        return JSONResponse(content=jsonable_encoder(rpc_response.model_dump(exclude_none=True)), headers=response_headers)
    except MCPError as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        log_event(
            logging.WARNING,
            "mcp.request.failed",
            request_id=request_id,
            auth_type=auth_context.auth_type,
            duration_ms=duration_ms,
            error=exc.message,
            code=exc.code,
        )
        error_response = _to_error_response(None, exc)
        if session_id and should_emit_client_log("warning"):
            await session_store.publish(
                session_id,
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/message",
                    "params": {
                        "level": "warning",
                        "logger": "app.mcp",
                        "data": {
                            "requestId": request_id,
                            "error": exc.message,
                            "code": exc.code,
                        },
                    },
                },
            )
        accepts_sse = "text/event-stream" in (request.headers.get("accept") or "") and settings.MCP_ENABLE_SSE
        if accepts_sse:
            return StreamingResponse(
                _iter_sse_with_logs([error_response], request_id, "error", duration_ms, failed=True),
                media_type="text/event-stream",
                status_code=exc.status_code,
                headers={"x-request-id": request_id},
            )
        return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(error_response.model_dump(exclude_none=True)), headers={"x-request-id": request_id})
    except ValidationError as exc:
        error_response = _to_error_response(None, invalid_request(data=exc.errors()))
        return JSONResponse(status_code=400, content=jsonable_encoder(error_response.model_dump(exclude_none=True)), headers={"x-request-id": request_id})