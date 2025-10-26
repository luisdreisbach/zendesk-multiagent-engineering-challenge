import re
from datetime import UTC, datetime, timedelta
from typing import Any

from openai.types.responses import FunctionToolParam

from app.agents.tool_registry import CallableTool

_ORDER_ID_PATTERN = re.compile(r"^ORD-\d{4}$")

_ORDER_STATUS_DATA: dict[str, dict[str, Any]] = {
    "ORD-1042": {
        "status": "processing",
        "estimated_dispatch": datetime.now(tz=UTC) + timedelta(hours=6),
        "estimated_delivery": datetime.now(tz=UTC) + timedelta(days=2),
        "message": "Order is being prepared for shipment.",
    },
    "ORD-2735": {
        "status": "shipped",
        "estimated_dispatch": datetime.now(tz=UTC) - timedelta(hours=4),
        "estimated_delivery": datetime.now(tz=UTC) + timedelta(days=1),
        "message": "Package has left the warehouse.",
    },
    "ORD-8899": {
        "status": "preorder_hold",
        "estimated_dispatch": None,
        "estimated_delivery": None,
        "message": "Item is on preorder hold pending supplier confirmation.",
    },
}


def _order_status_check(order_number: str) -> dict[str, Any]:
    """Return mock order status information."""
    if not _ORDER_ID_PATTERN.match(order_number):
        return {
            "order_id": order_number,
            "status": "invalid_order_id",
            "message": "Order ID must follow the ORD-1234 format.",
        }

    record = _ORDER_STATUS_DATA.get(order_number)
    if record is None:
        return {
            "order_id": order_number,
            "status": "not_found",
            "message": "No order information available. Confirm the identifier.",
        }

    def _iso(dt: datetime | None) -> str | None:
        return dt.isoformat() if isinstance(dt, datetime) else None

    return {
        "order_id": order_number,
        "status": record["status"],
        "estimated_dispatch": _iso(record["estimated_dispatch"]),
        "estimated_delivery": _iso(record["estimated_delivery"]),
        "message": record["message"],
    }


schema: FunctionToolParam = {
    "name": "order_status_check",
    "description": "Retrieve the internal processing status for an order.",
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

order_status_check = CallableTool(
    callable=_order_status_check,
    function_schema=schema,
)
