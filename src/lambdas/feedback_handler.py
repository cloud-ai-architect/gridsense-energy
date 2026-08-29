"""Lambda handler for reviewer feedback.

Captures the reviewer's verdict on a draft. This is the human-in-the-loop
record: what was drafted, whether it was accepted, and what was changed.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

import boto3

from src.lambdas._base import run_stage

TABLE = os.environ.get("FEEDBACK_TABLE", "")
REGION = os.environ.get("AWS_REGION", "ap-south-1")

VERDICTS = {"accepted", "edited", "rejected"}


def _record(data: dict[str, Any]) -> dict[str, Any]:
    verdict = str(data["verdict"]).lower()
    if verdict not in VERDICTS:
        raise ValueError("verdict must be one of: {}".format(", ".join(sorted(VERDICTS))))

    item = {
        "feedback_id": {"S": str(uuid.uuid4())},
        "task_id": {"S": str(data["task_id"])},
        "agent": {"S": str(data.get("agent", "unknown"))},
        "verdict": {"S": verdict},
        "created_at": {"S": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
    }
    if data.get("reviewer_notes"):
        item["reviewer_notes"] = {"S": str(data["reviewer_notes"])[:4000]}

    if TABLE:
        boto3.client("dynamodb", region_name=REGION).put_item(TableName=TABLE, Item=item)

    return {"feedback_id": item["feedback_id"]["S"], "recorded": bool(TABLE)}


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    return run_stage(event, required=["task_id", "verdict"], fn=_record)
