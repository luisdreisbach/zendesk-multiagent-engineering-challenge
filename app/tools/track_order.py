import re
from datetime import UTC, datetime, timedelta
from typing import Any

from openai.types.responses import FunctionToolParam

from app.agents.tool_registry import CallableTool

_ORDER_ID_PATTERN = re.compile(r"^ORD-\d{4}$")

_TRACKING_EVENTS: dict[str, dict[str, Any]] = {
    "ORD-1042": {
        "carrier": "UPS",
        "tracking_number": "1Z999AA10123456784",
        "events": [
            {"timestamp": datetime.now(tz=UTC) - timedelta(hours=5), "checkpoint": "Label created"},
            {
                "timestamp": datetime.now(tz=UTC) - timedelta(hours=1),
                "checkpoint": "Package received at origin facility",
            },
        ],
        "estimated_delivery": datetime.now(tz=UTC) + timedelta(days=2),
    },
    "ORD-2735": {
        "carrier": "FedEx",
        "tracking_number": "61290999900000000000",
        "events": [
            {
                "timestamp": datetime.now(tz=UTC) - timedelta(days=1),
                "checkpoint": "Departed sorting center",
            },
            {
                "timestamp": datetime.now(tz=UTC) - timedelta(hours=2),
                "checkpoint": "Arrived at destination facility",
            },
        ],
        "estimated_delivery": datetime.now(tz=UTC) + timedelta(hours=18),
    },
    "ORD-8899": {
        "carrier": None,
        "tracking_number": None,
        "events": [],
        "estimated_delivery": None,
    },
}


def _track_order(order_number: str) -> dict[str, Any]:
    """Provide shipping progress for the requested order."""
    if not _ORDER_ID_PATTERN.match(order_number):
        return {
            "order_id": order_number,
            "status": "invalid_order_id",
            "message": "Order ID must follow the ORD-1234 format.",
        }

    tracking = _TRACKING_EVENTS.get(order_number)
    if tracking is None:
        return {
            "order_id": order_number,
            "status": "not_found",
            "message": "No tracking data available for this order.",
        }

    def _iso(event_time: datetime | None) -> str | None:
        return event_time.isoformat() if isinstance(event_time, datetime) else None

    events = [
        {"timestamp": _iso(event["timestamp"]), "checkpoint": event["checkpoint"]}
        for event in tracking["events"]
    ]

    if not events:
        return {
            "order_id": order_number,
            "status": "pending_dispatch",
            "carrier": tracking["carrier"],
            "tracking_number": tracking["tracking_number"],
            "events": events,
            "estimated_delivery": _iso(tracking["estimated_delivery"]),
            "message": (
                "Parcel is awaiting pick-up. Tracking will update once the carrier scans it."
            ),
        }

    return {
        "order_id": order_number,
        "status": "in_transit",
        "carrier": tracking["carrier"],
        "tracking_number": tracking["tracking_number"],
        "events": events,
        "estimated_delivery": _iso(tracking["estimated_delivery"]),
        "message": "Latest tracking events retrieved successfully.",
    }


schema: FunctionToolParam = {
    "name": "track_order",
    "description": "Fetch shipment tracking updates for an order.",
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

track_order = CallableTool(
    callable=_track_order,
    function_schema=schema,
)
