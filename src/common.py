"""Common base classes for GridSense agents."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, ClassVar

import structlog

logger = structlog.get_logger()

REGION = os.environ.get("AWS_REGION", "ap-south-1")

# Model tiers, cheapest first. Selection is by task complexity, not habit:
# routing and extraction do not need a frontier model, and on a portfolio
# budget the difference is roughly an order of magnitude per million tokens.
#
# Anthropic models are not enabled on this account (Bedrock requires a
# one-time use-case submission), so the defaults are Amazon Nova. Because
# everything below goes through the Converse API, switching provider is a
# change of model id -- no code change.
MODEL_FAST = os.environ.get("MODEL_FAST", "apac.amazon.nova-micro-v1:0")
MODEL_STANDARD = os.environ.get("MODEL_STANDARD", "apac.amazon.nova-lite-v1:0")
MODEL_DEEP = os.environ.get("MODEL_DEEP", "apac.amazon.nova-pro-v1:0")


class GridSenseError(Exception):
    """Base error for GridSense."""


class ModelError(GridSenseError):
    """The model call failed or returned an unusable response."""


@dataclass
class GridsenseTask:
    """A unit of work for the GridSense pipeline."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: float = 0.0
    completed_at: float = 0.0
    status: str = "pending"  # pending | in_progress | done | failed
    artifacts: dict[str, Any] = field(default_factory=dict)


class BaseAgent:
    """Base class for all GridSense agents.

    Subclasses set NAME, MODEL and SYSTEM_PROMPT, then implement handle().
    """

    NAME: ClassVar[str] = ""
    MODEL: ClassVar[str] = MODEL_STANDARD
    SYSTEM_PROMPT: ClassVar[str] = ""

    def __init__(self) -> None:
        if not self.NAME:
            raise ValueError(f"{type(self).__name__} must set NAME")
        self.log = logger.bind(agent=self.NAME)
        self.bedrock: Any = None
        self._setup_done = False

    def setup(self) -> None:
        """Override for agent-specific initialisation."""

    def ensure_setup(self) -> None:
        if self._setup_done:
            return
        import boto3

        self.bedrock = boto3.client("bedrock-runtime", region_name=REGION)
        self.setup()
        self._setup_done = True

    def invoke(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> str:
        """Call a foundation model and return its text.

        Uses the Converse API rather than InvokeModel: it normalises the
        request/response shape across providers, so the same code runs on
        Nova, Claude, Llama or Mistral.
        """
        self.ensure_setup()
        model_id = model or self.MODEL
        system_prompt = system if system is not None else self.SYSTEM_PROMPT

        kwargs: dict[str, Any] = {
            "modelId": model_id,
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        if system_prompt:
            kwargs["system"] = [{"text": system_prompt}]

        start = time.perf_counter()
        try:
            response = self.bedrock.converse(**kwargs)
        except Exception as exc:
            raise ModelError(f"{self.NAME}: model call failed ({model_id}): {exc}") from exc

        try:
            # The Converse response is untyped; assert the shape we rely on
            # rather than returning Any from a function declared to return str.
            text = str(response["output"]["message"]["content"][0]["text"])
        except (KeyError, IndexError) as exc:
            raise ModelError(f"{self.NAME}: unexpected response shape from {model_id}") from exc

        usage = response.get("usage", {})
        self.log.info(
            "model.invoke",
            model=model_id,
            input_tokens=usage.get("inputTokens"),
            output_tokens=usage.get("outputTokens"),
            duration_ms=int((time.perf_counter() - start) * 1000),
        )
        return text

    def invoke_json(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """Call the model and parse its reply as JSON.

        Models often wrap JSON in prose or a fenced block, so the outermost
        braces are extracted before parsing rather than trusting the reply
        to be bare JSON.
        """
        raw = self.invoke(prompt, **kwargs)
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ModelError(f"{self.NAME}: no JSON object in model reply: {raw[:200]}")
        try:
            parsed: dict[str, Any] = json.loads(raw[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ModelError(f"{self.NAME}: malformed JSON from model: {exc}") from exc
        return parsed

    def run(self, *args: Any, **kwargs: Any) -> Any:
        self.ensure_setup()
        return self.handle(*args, **kwargs)

    def handle(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ARG002
        raise NotImplementedError


__all__ = [
    "BaseAgent",
    "GridSenseError",
    "GridsenseTask",
    "ModelError",
    "MODEL_DEEP",
    "MODEL_FAST",
    "MODEL_STANDARD",
]
