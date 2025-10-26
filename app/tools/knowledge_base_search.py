from typing import Any, TypedDict

from openai.types.responses import FunctionToolParam

from app.agents.tool_registry import CallableTool


class KnowledgeBaseEntry(TypedDict):
    id: str
    title: str
    summary: str
    keywords: set[str]


_KNOWLEDGE_BASE: list[KnowledgeBaseEntry] = [
    {
        "id": "return-policy",
        "title": "Return Policy Overview",
        "summary": "Customers can return most items within 30 days in original condition.",
        "keywords": {"return", "refund", "policy", "30 days"},
    },
    {
        "id": "cancellation-window",
        "title": "Order Cancellation Window",
        "summary": "Orders can be cancelled within 24 hours of placement unless already shipped.",
        "keywords": {"cancel", "cancellation", "window", "24 hours"},
    },
    {
        "id": "shipping-delays",
        "title": "Shipping Delays and ETA Updates",
        "summary": (
            "Explains how carrier delays affect estimated delivery dates and provides "
            "escalation steps."
        ),
        "keywords": {"shipping", "delay", "eta", "tracking"},
    },
]


def _knowledge_base_search(query: str) -> dict[str, Any]:
    """Return simple keyword-based matches from the mock knowledge base."""
    normalized_query = query.strip().lower()
    if not normalized_query:
        return {"query": query, "results": [], "message": "Query was empty."}

    matches: list[dict[str, str]] = []
    for article in _KNOWLEDGE_BASE:
        searchable = " ".join(article["keywords"]).lower()
        if normalized_query in searchable or normalized_query in article["title"].lower():
            matches.append(
                {"id": article["id"], "title": article["title"], "summary": article["summary"]}
            )
        elif any(term in article["summary"].lower() for term in normalized_query.split()):
            matches.append(
                {"id": article["id"], "title": article["title"], "summary": article["summary"]}
            )

    return {
        "results": matches,
    }


schema: FunctionToolParam = {
    "name": "knowledge_base_search",
    "description": "Search the customer support knowledge base for relevant articles.",
    "type": "function",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Plain-language question from the customer.",
            }
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}

knowledge_base_search = CallableTool(
    callable=_knowledge_base_search,
    function_schema=schema,
)
