from datetime import UTC, datetime
from html import escape

from pydantic import BaseModel

from app.memory.store import ConversationEvent, ConversationStore


class ConversationHistoryView(BaseModel):
    "Read only view of ConversationHistory."

    events: list[ConversationEvent]

    def format_history(self) -> str:
        lines = ["<conversation>"]
        for event in self.events:
            if event.type != "message":
                continue
            if event.actor == "user":
                lines.append(f"  <user>{escape(event.content)}</user>")
            elif event.actor == "bot":
                lines.append(f"  <bot>{escape(event.content)}</bot>")
        lines.append("</conversation>")
        return "\n".join(lines)


class ConversationHistory:
    """High-level helper for recording and formatting conversation events."""

    def __init__(self, store: ConversationStore, session_id: str) -> None:
        self._store = store
        self._session_id = session_id

    def add_user_message(self, message: str) -> None:
        event = ConversationEvent(
            timestamp=self._now(),
            actor="user",
            type="message",
            content=message,
        )
        self._append(event)

    def add_bot_message(self, message: str) -> None:
        event = ConversationEvent(
            timestamp=self._now(),
            actor="bot",
            type="message",
            content=message,
        )
        self._append(event)

    def get_events(self) -> list[ConversationEvent]:
        return self._store.get_history(self._session_id)

    def _append(self, event: ConversationEvent) -> None:
        self._store.append_events(self._session_id, [event])

    def get_view(self) -> ConversationHistoryView:
        return ConversationHistoryView(events=self.get_events())

    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=UTC)
