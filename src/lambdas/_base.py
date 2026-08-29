"""Shared Lambda plumbing.

Keeps each stage handler to its agent call: the HTTP envelope, argument
extraction and error mapping are identical across stages and are handled
here so a bug is fixed in one place.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from src.common import GridSenseError


def parse_event(event: dict) -> dict:
    """Return the request body from a direct, API Gateway, or Step Function event."""
    if not isinstance(event, dict):
        return {}
    body = event.get("body")
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}
    if isinstance(body, dict):
        return body
    if isinstance(event.get("queryStringParameters"), dict):
        return dict(event["queryStringParameters"])
    return event


def respond(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def run_stage(event: dict, required: list[str], fn: Callable[[dict], Any]) -> dict[str, Any]:
    """Validate inputs, run the agent, and map failures to HTTP responses."""
    data = parse_event(event)

    missing = [k for k in required if not data.get(k)]
    if missing:
        return respond(
            400,
            {
                "error": "MISSING_PARAMETERS",
                "message": "required: %s" % ", ".join(missing),
            },
        )

    try:
        return respond(200, {"result": fn(data)})
    except GridSenseError as exc:
        # Model or validation failure: the caller's input may be at fault,
        # and the message is safe to return.
        return respond(502, {"error": type(exc).__name__, "message": str(exc)})
    except Exception as exc:  # noqa: BLE001
        return respond(500, {"error": "INTERNAL_ERROR", "message": str(exc)})
