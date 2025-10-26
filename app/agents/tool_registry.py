from typing import Any, Callable, Literal

from openai.types.responses import FunctionToolParam
from pydantic import BaseModel


class CallableTool(BaseModel):
    type: Literal["callable"] = "callable"
    function_schema: FunctionToolParam
    callable: Callable[..., Any]

    @property
    def name(self) -> str:
        return self.function_schema["name"]


class AgentTool(BaseModel):
    type: Literal["agent"] = "agent"
    name: str

    @property
    def function_schema(self) -> FunctionToolParam:
        return {
            "type": "function",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
            "strict": True,
            "name": self.name,
        }


Tool = CallableTool | AgentTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Any] = {}

    def register(self, *tools: CallableTool) -> None:
        for tool in tools:
            self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name.startswith("agent:"):
            return AgentTool(name=name[6:])
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Tool '{name}' is not registered.") from exc

    def run_tool(self, name: str, arguments: dict[str, Any] | None) -> Any:
        tool = self.get(name)
        if isinstance(tool, AgentTool):
            msg = f"Tool '{name}' refers to an agent and cannot be executed as a callable tool."
            raise ValueError(msg)
        if not isinstance(tool, CallableTool):
            raise ValueError(f"Tool '{name}' is not callable.")

        call_args = arguments or {}
        return tool.callable(**call_args)

    @property
    def tools(self) -> dict[str, Any]:
        return dict(self._tools)
