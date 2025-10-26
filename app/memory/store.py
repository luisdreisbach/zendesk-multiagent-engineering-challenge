from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ConversationEvent(BaseModel):
    timestamp: datetime
    actor: Literal["user", "bot", "tool"]
    type: Literal["message"]
    content: str


class ConversationStore(ABC):
    @abstractmethod
    def get_history(self, session_id: str) -> list[ConversationEvent]:
        raise NotImplementedError

    @abstractmethod
    def append_events(self, session_id: str, events: list[ConversationEvent]) -> None:
        raise NotImplementedError

    @abstractmethod
    def reset_session(self, session_id: str) -> None:
        raise NotImplementedError


class InMemoryConversationStore(ConversationStore):
    def __init__(self) -> None:
        self._store: dict[str, list[ConversationEvent]] = {}

    def get_history(self, session_id: str) -> list[ConversationEvent]:
        return list(self._store.get(session_id, []))

    def append_events(self, session_id: str, events: list[ConversationEvent]) -> None:
        if not events:
            return
        self._store.setdefault(session_id, []).extend(events)

    def reset_session(self, session_id: str) -> None:
        self._store.pop(session_id, None)
