from pydantic import BaseModel

from app.agents.agent import AgentStatus


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    status: AgentStatus
