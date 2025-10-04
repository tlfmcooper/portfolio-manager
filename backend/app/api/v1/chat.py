"""Chat endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    SendMessageRequest
)
from app.core.security import get_current_user_id
from app.services.chat_service import get_chat_service

router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_chat_session(
    session_data: ChatSessionCreate,
    user_id: int = Depends(get_current_user_id)
):
    """Create a new chat session"""
    chat_service = get_chat_service()

    session = chat_service.create_session(
        user_id=user_id,
        portfolio_id=session_data.portfolio_id
    )

    return ChatSessionResponse(**session)


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_chat_session(
    session_id: str,
    user_id: int = Depends(get_current_user_id)
):
    """Get chat session history"""
    chat_service = get_chat_service()

    try:
        session = chat_service.get_session(user_id, session_id)
        return ChatSessionResponse(**session)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    message: SendMessageRequest,
    user_id: int = Depends(get_current_user_id)
):
    """Send a message and stream the AI response using SSE"""
    chat_service = get_chat_service()

    # Verify session exists
    try:
        chat_service.get_session(user_id, session_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    # Stream response
    return StreamingResponse(
        chat_service.send_message_stream(
            user_id=user_id,
            session_id=session_id,
            content=message.content,
            portfolio_id=message.portfolio_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    session_id: str,
    user_id: int = Depends(get_current_user_id)
):
    """Delete a chat session"""
    chat_service = get_chat_service()

    success = chat_service.delete_session(user_id, session_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
