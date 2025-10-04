"""Chat schemas"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatSessionCreate(BaseModel):
    """Schema for creating a chat session"""
    portfolio_id: Optional[int] = None


class ChatMessage(BaseModel):
    """Schema for a chat message"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    tool_call: Optional[Dict[str, Any]] = None


class ChatSessionResponse(BaseModel):
    """Schema for chat session response"""
    session_id: str
    user_id: int
    portfolio_id: Optional[int]
    messages: List[ChatMessage]
    created_at: datetime
    last_activity: datetime


class SendMessageRequest(BaseModel):
    """Schema for sending a message"""
    content: str
    portfolio_id: Optional[int] = None


class MessageDelta(BaseModel):
    """Schema for SSE message delta"""
    type: str  # "message_delta", "tool_call", "dashboard_update", "done"
    content: Optional[str] = None
    tool_call: Optional[Dict[str, Any]] = None
    dashboard_update: Optional[Dict[str, Any]] = None
