import re
from datetime import UTC, datetime, timedelta
from typing import Any

from openai.types.responses import FunctionToolParam

from app.agents.tool_registry import CallableTool

_ORDER_ID_PATTERN = re.compile(r"^ORD-\d{4}$")

# Mock catalogue of orders the tool knows about. The values capture how long ago the
# order was placed plus additional metadata we surface back to the agent.
_ORDER_SCENARIOS: dict[str, dict[str, Any]] = {
    # Eligible for cancellation (within 24h, refund to original payment method).
    "ORD-1042": {
        "placed_at": datetime.now(tz=UTC) - timedelta(hours=6),
        "status": "processing",
        "refunded": True,
        "message": "Order cancelled. A full refund will be issued to the original payment method.",
    },
    # Too old - the warehouse already shipped the parcel.
    "ORD-2735": {
        "placed_at": datetime.now(tz=UTC) - timedelta(hours=32),
        "status": "shipped",
        "refunded": False,
        "message": "The package left the warehouse and can no longer be cancelled.",
    },
}


def _cancel_order(order_number: str) -> dict[str, Any]:
    """Validate the order number and return a canned cancellation outcome."""
    if not _ORDER_ID_PATTERN.match(order_number):
        return {
            "order_id": order_number,
            "status": "invalid_order_id",
            "eligible": False,
            "message": "Order ID must follow the ORD-1234 format.",
        }

    order = _ORDER_SCENARIOS.get(order_number)
    if order is None:
        return {
            "order_id": order_number,
            "status": "not_found",
            "eligible": False,
            "message": "We could not locate this order. Confirm the ID with the customer.",
        }

    placed_at: datetime = order["placed_at"]
    age = datetime.now(tz=UTC) - placed_at
    if age > timedelta(hours=24):
        return {
            "order_id": order_number,
            "status": "not_eligible",
            "eligible": False,
            "message": "Orders older than 24 hours cannot be cancelled automatically.",
        }

    return {
        "order_id": order_number,
        "status": "cancelled",
        "eligible": True,
        "refunded": order.get("refunded", True),
        "message": order["message"],
    }


schema: FunctionToolParam = {
    "name": "cancel_order",
    "description": "Cancel a customer order if it is still eligible.",
    "type": "function",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "order_number": {
                "type": "string",
                "pattern": r"^ORD-\d{4}$",
                "description": "Order identifier in ORD-1234 format.",
            }
        },
        "required": ["order_number"],
        "additionalProperties": False,
    },
}

cancel_order = CallableTool(
    callable=_cancel_order,
    function_schema=schema,
)
