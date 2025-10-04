"""
Chat Service - Orchestrates AI chat with MCP tools
"""
import uuid
from typing import Dict, Any, AsyncGenerator, Optional
from datetime import datetime
import json
from anthropic import Anthropic, AsyncAnthropic
from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.schemas.chat import ChatSession, ChatMessage, MessageRole, DashboardSnapshot
from app.services.mcp_server import PortfolioMCPTools, PORTFOLIO_MCP_TOOLS


class ChatService:
    """Service for managing chat sessions and AI interactions"""

    def __init__(self):
        self.redis_client = get_redis_client()
        self.mcp_tools = PortfolioMCPTools()
        self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def create_session(self, user_id: int) -> ChatSession:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            messages=[],
            dashboard_snapshots=[],
        )

        # Save to Redis
        cache_key = f"chat:session:{user_id}:{session_id}"
        await self.redis_client.set(
            cache_key,
            session.model_dump(mode='json'),
            ttl=settings.CHAT_SESSION_TTL
        )

        return session

    async def get_session(self, user_id: int, session_id: str) -> Optional[ChatSession]:
        """Retrieve chat session from Redis"""
        cache_key = f"chat:session:{user_id}:{session_id}"
        session_data = await self.redis_client.get(cache_key)

        if session_data:
            return ChatSession(**session_data)
        return None

    async def delete_session(self, user_id: int, session_id: str) -> bool:
        """Delete chat session"""
        cache_key = f"chat:session:{user_id}:{session_id}"
        return await self.redis_client.delete(cache_key)

    async def add_message(
        self,
        user_id: int,
        session_id: str,
        role: MessageRole,
        content: str,
        tool_calls: Optional[list] = None
    ) -> ChatSession:
        """Add message to session"""
        session = await self.get_session(user_id, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        message = ChatMessage(
            role=role,
            content=content,
            tool_calls=tool_calls
        )

        session.messages.append(message)
        session.last_activity = datetime.utcnow()

        # Save updated session
        cache_key = f"chat:session:{user_id}:{session_id}"
        await self.redis_client.set(
            cache_key,
            session.model_dump(mode='json'),
            ttl=settings.CHAT_SESSION_TTL
        )

        return session

    async def process_message(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        portfolio_id: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process user message and stream AI response

        Yields SSE-formatted message deltas
        """
        # Add user message to session
        await self.add_message(user_id, session_id, MessageRole.USER, user_message)

        # Get session for context
        session = await self.get_session(user_id, session_id)
        if not session:
            yield self._format_sse_event("error", {"message": "Session not found"})
            return

        # Build context from message history
        messages = self._build_message_context(session.messages)

        # System prompt for portfolio assistant
        system_prompt = self._build_system_prompt(portfolio_id)

        # Stream response from Claude with tool use
        assistant_response = ""
        tool_calls_made = []

        try:
            # Call Claude API with MCP tools
            async with self.anthropic_client.messages.stream(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=self._format_tools_for_claude(),
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, 'text'):
                            text_delta = event.delta.text
                            assistant_response += text_delta
                            yield self._format_sse_event("message_delta", {
                                "content": text_delta
                            })

                    elif event.type == "tool_use":
                        # Execute MCP tool
                        tool_result = await self._execute_tool(
                            event.name,
                            event.input,
                            portfolio_id
                        )
                        tool_calls_made.append({
                            "name": event.name,
                            "parameters": event.input,
                            "result": tool_result
                        })

                        # Stream tool call info
                        yield self._format_sse_event("tool_call", {
                            "name": event.name,
                            "parameters": event.input
                        })

                        # Stream dashboard update if applicable
                        if self._is_dashboard_tool(event.name):
                            yield self._format_sse_event("dashboard_update", {
                                "type": event.name,
                                "data": tool_result
                            })

            # Save assistant response
            await self.add_message(
                user_id,
                session_id,
                MessageRole.ASSISTANT,
                assistant_response,
                tool_calls_made
            )

            # Send completion event
            yield self._format_sse_event("message_complete", {
                "content": assistant_response
            })

        except Exception as e:
            yield self._format_sse_event("error", {
                "message": f"Error processing message: {str(e)}"
            })

    def _build_system_prompt(self, portfolio_id: Optional[int]) -> str:
        """Build system prompt for portfolio assistant"""
        return f"""You are an expert financial advisor and portfolio analyst. Your role is to help users understand their investment portfolio, analyze risk/return tradeoffs, and explore rebalancing scenarios.

You have access to comprehensive portfolio analytics tools including:
- Portfolio performance metrics (returns, Sharpe ratio, volatility)
- Risk analysis (VaR, CVaR, correlation, beta)
- Portfolio optimization (efficient frontier, mean-variance optimization)
- Simulation tools (Monte Carlo, CPPI strategy)
- Rebalancing analysis and what-if scenarios

When analyzing portfolios:
1. Always explain metrics in clear, accessible language
2. Highlight both opportunities and risks
3. Provide actionable recommendations
4. Use specific numbers and data from the tools
5. Warn about high-risk changes

Current portfolio ID: {portfolio_id if portfolio_id else 'Not specified'}

Be conversational, helpful, and educational. Help users make informed investment decisions."""

    def _build_message_context(self, messages: list) -> list:
        """Build message context for Claude API"""
        return [
            {
                "role": msg.role.value,
                "content": msg.content
            }
            for msg in messages[-10:]  # Last 10 messages for context
        ]

    def _format_tools_for_claude(self) -> list:
        """Format MCP tools for Claude API"""
        tools = []
        for tool_name, tool_spec in PORTFOLIO_MCP_TOOLS.items():
            tools.append({
                "name": tool_name,
                "description": tool_spec["description"],
                "input_schema": {
                    "type": "object",
                    "properties": tool_spec["parameters"],
                    "required": list(tool_spec["parameters"].keys())
                }
            })
        return tools

    async def _execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        portfolio_id: Optional[int]
    ) -> Dict[str, Any]:
        """Execute MCP tool and return result"""
        # Ensure portfolio_id is set if required
        if "portfolio_id" in parameters and portfolio_id:
            parameters["portfolio_id"] = portfolio_id

        # Get tool method
        tool_method = getattr(self.mcp_tools, tool_name, None)
        if not tool_method:
            return {"error": f"Tool {tool_name} not found"}

        try:
            result = tool_method(**parameters)
            return result
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    def _is_dashboard_tool(self, tool_name: str) -> bool:
        """Check if tool generates dashboard data"""
        dashboard_tools = [
            "run_efficient_frontier",
            "run_monte_carlo",
            "run_cppi_simulation",
            "regenerate_full_dashboard",
            "simulate_rebalancing"
        ]
        return tool_name in dashboard_tools

    def _format_sse_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """Format data as Server-Sent Event"""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


# Singleton instance
_chat_service = ChatService()


def get_chat_service() -> ChatService:
    """Get chat service instance"""
    return _chat_service
