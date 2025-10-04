"""
Chat API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Optional
from app.schemas.chat import (
    CreateSessionRequest,
    CreateSessionResponse,
    SendMessageRequest,
    ChatSession
)
from app.services.chat_service import get_chat_service, ChatService

router = APIRouter()


def get_current_user_id() -> int:
    """Get current user ID from JWT token (placeholder)"""
    # TODO: Implement actual JWT token validation
    return 1


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_chat_session(
    request: CreateSessionRequest,
    chat_service: ChatService = Depends(get_chat_service),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Create a new chat session

    Returns session_id and creation timestamp
    """
    session = await chat_service.create_session(request.user_id)

    return CreateSessionResponse(
        session_id=session.session_id,
        created_at=session.created_at
    )


@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_chat_session(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Retrieve chat session with message history

    Returns complete session data including messages and dashboard snapshots
    """
    session = await chat_service.get_session(current_user_id, session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Delete chat session

    Removes session and all associated data from Redis
    """
    deleted = await chat_service.delete_session(current_user_id, session_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Session deleted successfully"}


@router.post("/sessions/{session_id}/messages")
async def send_chat_message(
    session_id: str,
    request: SendMessageRequest,
    chat_service: ChatService = Depends(get_chat_service),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Send message and receive streaming AI response

    Returns Server-Sent Events (SSE) stream with:
    - message_delta: Incremental response text
    - tool_call: MCP tool invocations
    - dashboard_update: Dashboard data updates
    - message_complete: Final complete response
    - error: Error messages
    """
    # Verify session exists
    session = await chat_service.get_session(current_user_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Stream AI response
    async def event_generator():
        async for event in chat_service.process_message(
            user_id=current_user_id,
            session_id=session_id,
            user_message=request.content,
            portfolio_id=request.portfolio_id
        ):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
