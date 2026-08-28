"""Common base classes for GridSense agents."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, ClassVar

import structlog

logger = structlog.get_logger()


@dataclass
class GridsenseTask:
    """A unit of work for the GridSense pipeline."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: float = 0.0
    completed_at: float = 0.0
    status: str = "pending"  # pending | in_progress | done | failed
    artifacts: dict[str, Any] = field(default_factory=dict)


class BaseAgent:
    """Base class for all GridSense agents."""

    NAME: ClassVar[str] = ""

    def __init__(self) -> None:
        if not self.NAME:
            raise ValueError(f"{type(self).__name__} must set NAME")
        self.log = logger.bind(agent=self.NAME)
        self.bedrock = None
        self._setup_done = False

    def setup(self) -> None:
        pass

    def ensure_setup(self) -> None:
        if self._setup_done:
            return
        import boto3
        self.bedrock = boto3.client("bedrock-runtime", region_name="ap-south-1")
        self.setup()
        self._setup_done = True

    def invoke_claude(self, system: str, messages: list[dict[str, Any]], model: str = "anthropic.claude-sonnet-4-5-20250929-v1:0") -> str:
        import json
        self.ensure_setup()
        response = self.bedrock.invoke_model(
            modelId=model,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "system": system,
                "messages": messages,
            }),
        )
        return json.loads(response["body"].read())["content"][0]["text"]

    def run(self, *args, **kwargs):
        self.ensure_setup()
        return self.handle(*args, **kwargs)

    def handle(self, *args, **kwargs):  # noqa: ARG002
        raise NotImplementedError


__all__ = ["BaseAgent", "GridsenseTask"]
