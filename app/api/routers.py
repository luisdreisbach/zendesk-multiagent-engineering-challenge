from fastapi import APIRouter

from app.agents.runtime import AgentRuntimeFactory, RuntimeTurnResult
from app.agents.tool_registry import ToolRegistry
from app.api.schemas import ChatRequest, ChatResponse
from app.llm.client import OpenAIClient
from app.llm.prompt import PromptRegistry
from app.memory.store import InMemoryConversationStore
from app.tools.cancel_order import cancel_order
from app.tools.knowledge_base_search import knowledge_base_search
from app.tools.order_status_check import order_status_check
from app.tools.track_order import track_order


def create_router() -> APIRouter:
    tool_registry = ToolRegistry()
    tool_registry.register(cancel_order, track_order, knowledge_base_search, order_status_check)
    runtime = AgentRuntimeFactory.build(
        supervisor="supervisor",
        specialized_agents=["order_cancellation", "order_tracking", "product_info"],
        tool_registry=tool_registry,
        prompt_registry=PromptRegistry(),
        conversation_store=InMemoryConversationStore(),
        llm_client=OpenAIClient(),
    )

    router = APIRouter()

    @router.post("/chat", response_model=ChatResponse)
    async def post_chat(request: ChatRequest) -> ChatResponse:
        turn_result: RuntimeTurnResult = runtime.run(request.session_id, request.message)

        return ChatResponse(response=turn_result.response, status=turn_result.status)

    return router
