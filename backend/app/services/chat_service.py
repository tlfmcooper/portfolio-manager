"""Chat Service for AI-powered portfolio conversations"""
from typing import Dict, List, Any, AsyncGenerator
from datetime import datetime
import uuid
import json
from anthropic import Anthropic, AsyncAnthropic
from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.services.mcp_server import get_mcp_tools
from app.schemas.chat import ChatMessage, MessageDelta


class ChatService:
    """Service for managing AI chat sessions"""

    def __init__(self):
        self.redis = get_redis_client()
        self.mcp_tools = get_mcp_tools()
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.chat_ttl = 2592000  # 30 days

    def create_session(
        self,
        user_id: int,
        portfolio_id: int = None
    ) -> Dict[str, Any]:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "portfolio_id": portfolio_id,
            "messages": [],
            "dashboard_snapshots": [],
            "created_at": now.isoformat(),
            "last_activity": now.isoformat(),
        }

        # Store in Redis
        cache_key = f"chat:session:{user_id}:{session_id}"
        self.redis.set(cache_key, session_data, ttl=self.chat_ttl)

        return session_data

    def get_session(self, user_id: int, session_id: str) -> Dict[str, Any]:
        """Get chat session data"""
        cache_key = f"chat:session:{user_id}:{session_id}"
        session_data = self.redis.get(cache_key)

        if not session_data:
            raise ValueError(f"Session {session_id} not found")

        return session_data

    def delete_session(self, user_id: int, session_id: str) -> bool:
        """Delete a chat session"""
        cache_key = f"chat:session:{user_id}:{session_id}"
        return self.redis.delete(cache_key)

    def add_message(
        self,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        tool_call: Dict[str, Any] = None
    ):
        """Add a message to the session"""
        session_data = self.get_session(user_id, session_id)

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "tool_call": tool_call,
        }

        session_data["messages"].append(message)
        session_data["last_activity"] = datetime.utcnow().isoformat()

        # Update in Redis
        cache_key = f"chat:session:{user_id}:{session_id}"
        self.redis.set(cache_key, session_data, ttl=self.chat_ttl)

    async def send_message_stream(
        self,
        user_id: int,
        session_id: str,
        content: str,
        portfolio_id: int = None
    ) -> AsyncGenerator[str, None]:
        """Send a message and stream the AI response using SSE"""
        # Add user message
        self.add_message(user_id, session_id, "user", content)

        # Get session for context
        session_data = self.get_session(user_id, session_id)

        # Build message history for Claude
        messages = []
        for msg in session_data["messages"]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # System prompt
        system_prompt = """You are a helpful financial advisor assistant for a portfolio management platform.
You have access to powerful analytics tools to help users understand and optimize their portfolios.

When users ask questions about their portfolio:
1. Use the appropriate tools to fetch real data
2. Explain metrics in plain language
3. Provide actionable insights
4. Warn about risks when appropriate
5. Suggest optimizations when relevant

Available tools allow you to:
- Get portfolio summaries and metrics
- Calculate risk metrics (VaR, CVaR, volatility)
- Simulate rebalancing scenarios
- Generate efficient frontiers
- Run Monte Carlo simulations
- Simulate CPPI strategies

Be conversational, educational, and helpful. Focus on helping users make informed investment decisions."""

        # Prepare tools
        tools = self.mcp_tools.get_tools_definition()

        try:
            # Stream response from Claude
            assistant_message = ""

            async with self.client.messages.stream(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=tools,
            ) as stream:
                async for event in stream:
                    if hasattr(event, 'type'):
                        if event.type == 'content_block_delta':
                            if hasattr(event.delta, 'text'):
                                chunk = event.delta.text
                                assistant_message += chunk

                                # Send SSE message delta
                                delta = MessageDelta(
                                    type="message_delta",
                                    content=chunk
                                )
                                yield f"data: {delta.model_dump_json()}\n\n"

                        elif event.type == 'content_block_start':
                            if hasattr(event.content_block, 'type') and event.content_block.type == 'tool_use':
                                tool_name = event.content_block.name
                                tool_id = event.content_block.id

                                # Send tool call notification
                                delta = MessageDelta(
                                    type="tool_call",
                                    tool_call={
                                        "id": tool_id,
                                        "name": tool_name,
                                        "status": "started"
                                    }
                                )
                                yield f"data: {delta.model_dump_json()}\n\n"

                # Get final message
                final_message = await stream.get_final_message()

                # Process tool calls
                for block in final_message.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input

                        # Execute tool
                        tool_result = self.mcp_tools.execute_tool(
                            tool_name,
                            tool_input,
                            user_id
                        )

                        # Send tool result as dashboard update
                        delta = MessageDelta(
                            type="dashboard_update",
                            dashboard_update={
                                "tool": tool_name,
                                "data": tool_result
                            }
                        )
                        yield f"data: {delta.model_dump_json()}\n\n"

                        # Add tool result to context and continue conversation
                        messages.append({
                            "role": "assistant",
                            "content": final_message.content
                        })
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps(tool_result)
                                }
                            ]
                        })

                        # Get follow-up response
                        async with self.client.messages.stream(
                            model="claude-3-5-sonnet-20241022",
                            max_tokens=4096,
                            system=system_prompt,
                            messages=messages,
                            tools=tools,
                        ) as followup_stream:
                            async for event in followup_stream:
                                if hasattr(event, 'type') and event.type == 'content_block_delta':
                                    if hasattr(event.delta, 'text'):
                                        chunk = event.delta.text
                                        assistant_message += chunk

                                        delta = MessageDelta(
                                            type="message_delta",
                                            content=chunk
                                        )
                                        yield f"data: {delta.model_dump_json()}\n\n"

            # Save assistant message
            self.add_message(user_id, session_id, "assistant", assistant_message)

            # Send done signal
            delta = MessageDelta(type="done")
            yield f"data: {delta.model_dump_json()}\n\n"

        except Exception as e:
            # Send error
            error_delta = MessageDelta(
                type="error",
                content=f"Error: {str(e)}"
            )
            yield f"data: {error_delta.model_dump_json()}\n\n"


# Global chat service instance
_chat_service = None


def get_chat_service() -> ChatService:
    """Get or create chat service instance"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
