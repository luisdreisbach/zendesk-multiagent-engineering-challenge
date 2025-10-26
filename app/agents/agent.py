import logging
from enum import Enum
from typing import Any, cast

from pydantic import BaseModel

from app.agents.tool_registry import Tool, ToolRegistry
from app.llm.client import (
    LLMClient,
    LLMResponse,
    LLMToolCallDetails,
    LLMToolCallResponse,
    OpenAIClient,
)
from app.llm.prompt import Prompt, PromptRegistry
from app.memory.conversation_history import ConversationHistoryView

logger = logging.getLogger(__name__)


class ToolEvent(BaseModel):
    agent: str
    tool: str
    input: dict[str, Any]
    result: dict[str, Any] | None = None


class AgentContext(BaseModel):
    session_id: str
    latest_user_message: str
    conversation_history: ConversationHistoryView


class AgentStatus(str, Enum):
    COMPLETED = "completed"
    REQUIRES_INPUT = "requires_input"
    FAILED = "failed"
    NOT_RESPONSIBLE = "not_responsible"


class AgentMessageOutput(BaseModel):
    status: AgentStatus
    user_message: str


class AgentToolCallRequest(BaseModel):
    requests: list[LLMToolCallDetails]
    conversation_context: Any


AgentOutput = AgentMessageOutput | AgentToolCallRequest


class ToolCallResponse(BaseModel):
    requests: list[LLMToolCallDetails]
    results: dict[str, Any] | None = None
    conversation_context: Any


class Agent:
    def __init__(self, name: str, prompt: Prompt, tools: list[Tool], llm_client: LLMClient) -> None:
        self.name = name
        self.prompt = prompt
        self.tools = tools
        self._llm_client = llm_client

    def call(self, context: AgentContext) -> AgentOutput:
        prompt_formatted = self.prompt.format(
            {"history": context.conversation_history.format_history()}
        )
        llm_response = self._llm_client.generate(
            message=prompt_formatted,
            model=self.prompt.model,
            response_model=AgentMessageOutput,
            tools=self.tools,
            **(self.prompt.config or {}),
        )
        return self._process_llm_response(llm_response)

    def send_tool_call(
        self, responses: list[LLMToolCallResponse], conversation_context: list[Any]
    ) -> AgentOutput:
        llm_response = self._llm_client.continue_after_function_call(
            tool_results=responses,
            model=self.prompt.model,
            response_model=AgentMessageOutput,
            conversation_context=conversation_context,
            tools=self.tools,
            **(self.prompt.config or {}),
        )
        return self._process_llm_response(llm_response)

    def _process_llm_response(self, llm_response: LLMResponse) -> AgentOutput:
        if llm_response.type == "structured":
            return cast(AgentOutput, llm_response.data)
        if llm_response.type == "tool_call":
            return AgentToolCallRequest(
                requests=llm_response.tools, conversation_context=llm_response.conversation_context
            )

        raise RuntimeError("LLM response should be either of type `structured` or `tool_call`")


class AgentFactory:
    @classmethod
    def build(
        cls,
        name: str,
        prompt_registry: PromptRegistry | None = None,
        tool_registry: ToolRegistry | None = None,
        llm_client: LLMClient | None = None,
    ):
        prompt_registry = prompt_registry or PromptRegistry()
        tool_registry = tool_registry or ToolRegistry()
        llm_client = llm_client or OpenAIClient()

        prompt = prompt_registry.get_prompt(name)
        tools = [tool_registry.get(tool_name) for tool_name in prompt.tools]

        return Agent(name=name, prompt=prompt, tools=tools, llm_client=llm_client)
