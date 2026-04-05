"""Typed MCP protocol models."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request envelope."""

    model_config = ConfigDict(extra="allow")

    jsonrpc: Literal["2.0"]
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Union[Dict[str, Any], List[Any]]] = None


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error object."""

    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response envelope."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None


class ClientInfo(BaseModel):
    name: str
    version: Optional[str] = None


class InitializeParams(BaseModel):
    protocolVersion: Optional[str] = None
    clientInfo: Optional[ClientInfo] = None
    capabilities: Dict[str, Any] = Field(default_factory=dict)


class ServerInfo(BaseModel):
    name: str
    version: str


class ToolListParams(BaseModel):
    cursor: Optional[str] = None


class ToolCallParams(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ResourceReadParams(BaseModel):
    uri: str


class ResourceTemplateListParams(BaseModel):
    cursor: Optional[str] = None


class ResourceSubscribeParams(BaseModel):
    uri: str


class PromptGetParams(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class SamplingCreateMessageParams(BaseModel):
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    systemPrompt: Optional[str] = None
    temperature: Optional[float] = None
    modelPreferences: Dict[str, Any] = Field(default_factory=dict)


class PromptReference(BaseModel):
    type: Literal["ref/prompt"]
    name: str


class ResourceReference(BaseModel):
    type: Literal["ref/resource"]
    uri: str


class CompletionArgument(BaseModel):
    name: str
    value: str = ""


class CompleteParams(BaseModel):
    ref: PromptReference | ResourceReference
    argument: CompletionArgument


class CompletionData(BaseModel):
    values: List[str] = Field(default_factory=list)
    total: Optional[int] = None
    hasMore: bool = False


class CompleteResult(BaseModel):
    completion: CompletionData


class LoggingSetLevelParams(BaseModel):
    level: Literal["debug", "info", "notice", "warning", "error", "critical", "alert", "emergency"]


class PromptArgument(BaseModel):
    name: str
    description: str
    required: bool = False


class ToolDescriptor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str
    inputSchema: Dict[str, Any] = Field(default_factory=dict)
    outputSchema: Optional[Dict[str, Any]] = None
    annotations: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict, alias="_meta")


class ResourceDescriptor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str
    mimeType: str = "application/json"
    uri: Optional[str] = None
    uriTemplate: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict, alias="_meta")


class ResourceTemplateDescriptor(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    uriTemplate: str
    name: str
    description: str
    mimeType: str = "application/json"
    meta: Dict[str, Any] = Field(default_factory=dict, alias="_meta")


class PromptDescriptor(BaseModel):
    name: str
    description: str
    arguments: List[PromptArgument] = Field(default_factory=list)


class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ResourceContent(BaseModel):
    uri: str
    mimeType: str = "application/json"
    text: Optional[str] = None
    blob: Optional[str] = None


class UIConfiguration(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    resourceUri: str
    type: Literal["dashboard", "form", "table", "workflow"]
    uiSchema: Dict[str, Any] = Field(default_factory=dict, alias="schema")
    data: Dict[str, Any] = Field(default_factory=dict)
    steps: List[Dict[str, Any]] = Field(default_factory=list)


class ToolResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    content: List[Dict[str, Any]] = Field(default_factory=list)
    structuredContent: Optional[Any] = None
    isError: bool = False
    meta: Dict[str, Any] = Field(default_factory=dict, alias="_meta")


class ResourceReadResult(BaseModel):
    contents: List[ResourceContent]


class PromptMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: Dict[str, Any]


class PromptResult(BaseModel):
    description: Optional[str] = None
    messages: List[PromptMessage] = Field(default_factory=list)


class SamplingResult(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: Dict[str, Any]
    modelPreferences: Dict[str, Any] = Field(default_factory=dict)
    stopReason: Literal["end_turn"] = "end_turn"