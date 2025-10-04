"""
Chat Schemas
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    """Message role enum"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Chat message model"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tool_calls: Optional[List[Dict[str, Any]]] = None


class DashboardSnapshot(BaseModel):
    """Dashboard snapshot model"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    parameters: Dict[str, Any]
    results: Dict[str, Any]
    dashboard_type: str  # e.g., "efficient_frontier", "monte_carlo", etc.


class ChatSession(BaseModel):
    """Chat session model"""
    session_id: str
    user_id: int
    messages: List[ChatMessage] = []
    dashboard_snapshots: List[DashboardSnapshot] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)


class CreateSessionRequest(BaseModel):
    """Create session request"""
    user_id: int


class CreateSessionResponse(BaseModel):
    """Create session response"""
    session_id: str
    created_at: datetime


class SendMessageRequest(BaseModel):
    """Send message request"""
    content: str
    portfolio_id: Optional[int] = None


class MessageDelta(BaseModel):
    """Streaming message delta"""
    type: str = "message_delta"
    content: str
    tool_call: Optional[Dict[str, Any]] = None
    dashboard_update: Optional[Dict[str, Any]] = None


class ToolCall(BaseModel):
    """Tool call model"""
    name: str
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None


class AllocationChange(BaseModel):
    """Allocation change model"""
    ticker: str
    percentage_change: float


class RebalancingRequest(BaseModel):
    """Rebalancing simulation request"""
    portfolio_id: int
    allocation_changes: Dict[str, float]  # ticker -> percentage change


class SimulationParameters(BaseModel):
    """Simulation parameters"""
    time_horizon: int = 252  # Trading days (1 year)
    scenarios: int = 1000
    risk_tolerance: float = 3.0  # CPPI multiplier
    floor: float = 0.8  # CPPI floor
