import logging

from opentelemetry import trace
from pydantic import BaseModel

from app.agents.agent import (
    Agent,
    AgentContext,
    AgentFactory,
    AgentMessageOutput,
    AgentStatus,
    AgentToolCallRequest,
)
from app.agents.tool_registry import ToolRegistry
from app.llm.client import LLMClient, LLMToolCallDetails, LLMToolCallResponse
from app.llm.prompt import PromptRegistry
from app.memory.conversation_history import ConversationHistory
from app.memory.store import (
    ConversationStore,
    InMemoryConversationStore,
)
from app.telemetry.otel import set_span_attributes

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class RuntimeTurnResult(BaseModel):
    response: str
    status: AgentStatus


class AgentRuntime:
    def __init__(
        self,
        agents: list[Agent],
        supervisor: str,
        conversation_store: ConversationStore,
        tool_registry: ToolRegistry,
    ) -> None:
        self.supervisor = supervisor
        self.conversation_store = conversation_store
        self.tool_registry = tool_registry
        self._agents: dict[str, Agent] = {a.name: a for a in agents}

        if supervisor not in self._agents:
            raise ValueError(f"Agent with supervisor name `{supervisor}` does not exist.")

    def register_agent(self, name: str, agent: Agent) -> None:
        self._agents[name] = agent

    def run(self, session_id: str, message: str) -> RuntimeTurnResult:
        logger.info("start session=%s message='%s'", session_id, message)
        with tracer.start_as_current_span(
            "agent_runtime.run", attributes={"session.id": session_id}
        ) as span:
            set_span_attributes(span, {"runtime.user_message": message})
            conversation_history = ConversationHistory(self.conversation_store, session_id)
            conversation_history.add_user_message(message)
            context = AgentContext(
                session_id=session_id,
                latest_user_message=message,
                conversation_history=conversation_history.get_view(),
            )
            logger.info("invoke supervisor=%s", self.supervisor)
            supervisor_result = self.call_agent(self.supervisor, context)
            conversation_history.add_bot_message(supervisor_result.user_message)
            logger.info(
                "supervisor=%s completed status=%s", self.supervisor, supervisor_result.status.value
            )
            set_span_attributes(
                span,
                {
                    "runtime.status": supervisor_result.status.value,
                    "runtime.response": supervisor_result.user_message,
                },
            )

            return RuntimeTurnResult(
                response=supervisor_result.user_message,
                status=supervisor_result.status,
            )

    def call_agent(self, name: str, context: AgentContext) -> AgentMessageOutput:
        "Call an agent and handle the output, either return result or process tool call"
        with tracer.start_as_current_span("agent.call", attributes={"agent.name": name}) as span:
            agent = self._agents[name]
            set_span_attributes(
                span,
                {
                    "agent.input.session_id": context.session_id,
                    "agent.input.latest_user_message": context.latest_user_message,
                    "agent.input.history": context.conversation_history.format_history(),
                },
            )
            logger.info("agent=%s call start", name)
            agent_output = agent.call(context)

            while isinstance(agent_output, AgentToolCallRequest):
                span.add_event(
                    "agent.tool_request",
                    {
                        "agent.name": name,
                        "tool.count": len(agent_output.requests),
                    },
                )
                logger.info("agent=%s requested %d tool(s)", name, len(agent_output.requests))
                tool_responses = self.call_multi_tools(agent_output.requests, context, name)
                agent_output = agent.send_tool_call(
                    tool_responses, agent_output.conversation_context
                )
                logger.info("agent=%s resumed after tool call", name)

            logger.info(
                "agent=%s finished message=%s status=%s",
                name,
                agent_output.user_message,
                agent_output.status.value,
            )
            set_span_attributes(
                span,
                {
                    "agent.output.message": agent_output.user_message,
                    "agent.output.status": agent_output.status.value,
                },
            )
            return agent_output

    def call_tool(self, request: LLMToolCallDetails, context: AgentContext) -> LLMToolCallResponse:
        with tracer.start_as_current_span(
            "agent.tool_call",
            attributes={"tool.name": request.name, "tool.call_id": request.call_id},
        ) as span:
            set_span_attributes(
                span,
                {
                    "tool.input.session_id": context.session_id,
                    "tool.input.arguments": request.arguments,
                },
            )
            if request.name in self._agents:
                logger.info("toolcall agent=%s delegating->agent=%s", request.name, request.name)
                tool_result = self.call_agent(request.name, context)
                set_span_attributes(span, {"tool.type": "agent"})
            else:
                logger.info("toolcall name=%s", request.name)
                tool_result = self.tool_registry.run_tool(request.name, request.arguments)
                set_span_attributes(span, {"tool.type": "function"})
            set_span_attributes(span, {"tool.output": tool_result})

            return LLMToolCallResponse(
                name=request.name,
                call_id=request.call_id,
                response=tool_result,
            )

    def call_multi_tools(
        self, requests: list[LLMToolCallDetails], context: AgentContext, requesting_agent: str
    ) -> list[LLMToolCallResponse]:
        responses: list[LLMToolCallResponse] = []
        # Async parallel execution possible
        for request in requests:
            logger.info("agent=%s executing tool=%s", requesting_agent, request.name)
            responses.append(self.call_tool(request, context))
        return responses


class AgentRuntimeFactory:
    @classmethod
    def build(
        cls,
        supervisor: str,
        specialized_agents: list[str],
        tool_registry: ToolRegistry | None = None,
        prompt_registry: PromptRegistry | None = None,
        conversation_store: ConversationStore | None = None,
        llm_client: LLMClient | None = None,
    ) -> AgentRuntime:
        ""
        conversation_store = conversation_store or InMemoryConversationStore()
        agents = [
            AgentFactory.build(agent_name, prompt_registry, tool_registry, llm_client)
            for agent_name in [supervisor, *specialized_agents]
        ]

        return AgentRuntime(
            agents=agents,
            supervisor=supervisor,
            conversation_store=conversation_store,
            tool_registry=tool_registry or ToolRegistry(),
        )
