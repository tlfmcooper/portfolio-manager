"""Config-backed MCP capability registry."""

from __future__ import annotations

import re
from typing import Any, Dict, Tuple

from jsonschema import ValidationError as JSONSchemaValidationError
from jsonschema import validate

from app.mcp.auth import enforce_access
from app.mcp.config import MCPCapabilityConfig, load_capability_config
from app.mcp.errors import invalid_params, method_not_found, not_found
from app.mcp.handlers import PROMPT_HANDLERS, RESOURCE_HANDLERS, TOOL_HANDLERS, complete_prompt_argument, complete_resource_argument
from app.mcp.models import CompletionData, CompleteResult, PromptDescriptor, ResourceDescriptor, ResourceTemplateDescriptor, ToolDescriptor


def _template_to_regex(template: str) -> re.Pattern[str]:
    pattern = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", r"(?P<\1>[^/]+)", template)
    return re.compile(f"^{pattern}$")


class CapabilityRegistry:
    """Runtime view of config-backed tools, resources, and prompts."""

    def __init__(self, config: MCPCapabilityConfig):
        self.config = config
        self.tools = {tool.name: tool for tool in config.tools}
        self.tool_aliases = {
            dotted_name: tool.name
            for tool in config.tools
            for dotted_name in [tool.name.replace("_", ".", 1)]
            if dotted_name != tool.name
        }
        self.resources = config.resources
        self.prompts = {prompt.name: prompt for prompt in config.prompts}

    def list_tools(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.inputSchema,
                outputSchema=tool.outputSchema,
                annotations=tool.annotations,
                _meta=tool.meta,
            )
            for tool in self.config.tools
        ]

    def list_resources(self) -> list[ResourceDescriptor]:
        return [
            ResourceDescriptor(
                name=resource.name,
                description=resource.description,
                mimeType=resource.mimeType,
                uri=resource.uri,
                uriTemplate=resource.uriTemplate,
                _meta=resource.meta,
            )
            for resource in self.config.resources
        ]

    def list_resource_templates(self) -> list[ResourceTemplateDescriptor]:
        return [
            ResourceTemplateDescriptor(
                uriTemplate=resource.uriTemplate,
                name=resource.name,
                description=resource.description,
                mimeType=resource.mimeType,
                _meta=resource.meta,
            )
            for resource in self.config.resources
            if resource.uriTemplate
        ]

    def list_prompts(self) -> list[PromptDescriptor]:
        return [PromptDescriptor(name=prompt.name, description=prompt.description, arguments=prompt.arguments) for prompt in self.config.prompts]

    async def execute_tool(self, name: str, arguments: Dict[str, Any], context: Any) -> Any:
        canonical_name = self.tool_aliases.get(name, name)
        tool = self.tools.get(canonical_name)
        if not tool:
            raise not_found(message=f"Unknown MCP tool: {name}")

        enforce_access(context.auth, tool.requiresAuth, tool.permissions)
        if tool.inputSchema:
            try:
                validate(instance=arguments, schema=tool.inputSchema)
            except JSONSchemaValidationError as exc:
                raise invalid_params(message="Tool arguments did not match input schema", data={"error": exc.message}) from exc

        handler = TOOL_HANDLERS.get(tool.handler)
        if not handler:
            raise method_not_found(message=f"Tool handler {tool.handler} is not registered")
        return await handler(context, arguments)

    async def read_resource(self, uri: str, context: Any) -> Any:
        for resource in self.resources:
            if resource.uri and resource.uri == uri:
                enforce_access(context.auth, resource.requiresAuth, resource.permissions)
                handler = RESOURCE_HANDLERS.get(resource.handler)
                if not handler:
                    raise method_not_found(message=f"Resource handler {resource.handler} is not registered")
                return await handler(context, {})

            if resource.uriTemplate:
                match = _template_to_regex(resource.uriTemplate).match(uri)
                if match:
                    enforce_access(context.auth, resource.requiresAuth, resource.permissions)
                    handler = RESOURCE_HANDLERS.get(resource.handler)
                    if not handler:
                        raise method_not_found(message=f"Resource handler {resource.handler} is not registered")
                    return await handler(context, match.groupdict())

        raise not_found(message=f"Unknown MCP resource URI: {uri}")

    async def get_prompt(self, name: str, arguments: Dict[str, Any], context: Any) -> Any:
        prompt = self.prompts.get(name)
        if not prompt:
            raise not_found(message=f"Unknown MCP prompt: {name}")

        handler = PROMPT_HANDLERS.get(prompt.handler)
        if not handler:
            raise method_not_found(message=f"Prompt handler {prompt.handler} is not registered")
        return await handler(context, arguments)

    async def complete(self, ref: Dict[str, Any], argument: Dict[str, Any], context: Any) -> CompleteResult:
        ref_type = ref.get("type")
        argument_name = str(argument.get("name") or "").strip()
        current_value = str(argument.get("value") or "")
        if not argument_name:
            raise invalid_params(message="Completion argument name is required")

        if ref_type == "ref/prompt":
            prompt_name = str(ref.get("name") or "").strip()
            if prompt_name not in self.prompts:
                raise not_found(message=f"Unknown MCP prompt: {prompt_name}")
            values = await complete_prompt_argument(context, prompt_name, argument_name, current_value)
            return CompleteResult(completion=CompletionData(values=values, total=len(values), hasMore=False))

        if ref_type == "ref/resource":
            uri = str(ref.get("uri") or "").strip()
            if not uri:
                raise invalid_params(message="Completion resource URI is required")
            values = await complete_resource_argument(context, uri, argument_name, current_value)
            return CompleteResult(completion=CompletionData(values=values, total=len(values), hasMore=False))

        raise invalid_params(message=f"Unsupported completion reference type: {ref_type}")


def get_registry() -> CapabilityRegistry:
    return CapabilityRegistry(load_capability_config())