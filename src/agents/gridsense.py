"""GridSense agents.

The division of labour here is the point. Forecasting and anomaly detection
are arithmetic and live in src/forecasting.py -- a language model asked to
extrapolate a load curve is slower, costlier and less accurate than a
seasonal-naive baseline, and its errors are plausible rather than
measurable.

The model's job is the part arithmetic cannot do: turning a number into
something an operator can act on at 3am, and drafting the demand-response
decision for a human to approve.

    Explain   describe what the numbers mean and what is uncertain
    Dispatch  propose a demand-response action from a forecast

Both are told the figures are computed, not estimated by them, and must not
contradict or re-derive them. An agent that quietly "corrects" a forecast is
worse than no agent, because the operator cannot tell which number they are
looking at.
"""

from __future__ import annotations

from typing import Any

from src.common import MODEL_FAST, MODEL_STANDARD, BaseAgent

DISCLAIMER = (
    "Forecast and anomaly figures are computed by src/forecasting.py, not "
    "generated. Operator approval required before any dispatch action."
)


class ExplainAgent(BaseAgent):
    """Turn computed figures into an operator-readable summary."""

    NAME = "explain"
    MODEL = MODEL_STANDARD
    SYSTEM_PROMPT = (
        "You explain grid load analysis to a control room operator.\n"
        "The figures you are given were computed numerically. Do not "
        "recalculate them, do not round them differently, and do not "
        "contradict them -- your job is interpretation, not arithmetic.\n"
        "Say what the numbers imply, and say plainly what they do not "
        "establish. An operator acting on false confidence is the failure "
        "mode here.\n"
        "Respond with JSON only:\n"
        '{"headline": "one sentence an operator can read at a glance",\n'
        ' "interpretation": "short paragraph",\n'
        ' "notable": ["specific things worth attention"],\n'
        ' "uncertainty": ["what these figures do not tell you"],\n'
        ' "suggested_watch": ["what to monitor next"]}'
    )

    def handle(
        self,
        summary: dict[str, Any],
        forecast: dict[str, Any] | None = None,
        anomalies: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        import json

        parts = [f"Series summary (computed):\n{json.dumps(summary, indent=1)}"]
        if forecast:
            trimmed = dict(forecast)
            # The operator does not need 48 numbers in the prompt; the shape
            # and the endpoints carry the meaning.
            vals = trimmed.get("values") or []
            if len(vals) > 12:
                trimmed["values"] = vals[:6] + ["..."] + vals[-6:]
            parts.append(f"Forecast (computed):\n{json.dumps(trimmed, indent=1)}")
        if anomalies:
            parts.append(
                f"Anomalies (computed, {len(anomalies)} total, first 5):\n"
                f"{json.dumps(anomalies[:5], indent=1)}"
            )
        result = self.invoke_json("\n\n".join(parts), max_tokens=2500)
        result["disclaimer"] = DISCLAIMER
        return result


class DispatchAgent(BaseAgent):
    """Propose a demand-response action for operator approval."""

    NAME = "dispatch"
    MODEL = MODEL_STANDARD
    SYSTEM_PROMPT = (
        "You propose demand-response actions for a grid operator to approve.\n"
        "Work from the supplied forecast and available resources. Do not "
        "invent capacity that is not listed, and do not assume a resource is "
        "available if its status does not say so.\n"
        "State the shortfall you are covering and what happens if nothing is "
        "done. If the listed resources cannot cover it, say so rather than "
        "proposing a plan that does not close the gap.\n"
        "Never present this as an executed action; it is a recommendation.\n"
        "Respond with JSON only:\n"
        '{"action_required": true,\n'
        ' "projected_shortfall_mw": 0,\n'
        ' "window": "when this applies",\n'
        ' "recommended": [{"resource": "...", "mw": 0, "order": 1,\n'
        '                  "why_this_one": "..."}],\n'
        ' "shortfall_covered": true,\n'
        ' "if_no_action": "consequence",\n'
        ' "requires_operator_approval": true}'
    )

    def handle(
        self,
        forecast: dict[str, Any],
        capacity_mw: float,
        resources: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        import json

        parts = [
            f"Firm capacity: {capacity_mw} MW",
            f"Forecast (computed):\n{json.dumps(forecast, indent=1)[:2500]}",
            f"Available demand-response resources:\n{json.dumps(resources or [], indent=1)}",
        ]
        result = self.invoke_json("\n\n".join(parts), max_tokens=2500)
        result["disclaimer"] = DISCLAIMER
        return result


class OrchestratorAgent(BaseAgent):
    """Route an inbound request to the right stage."""

    NAME = "orchestrator"
    MODEL = MODEL_FAST
    SYSTEM_PROMPT = (
        "You route grid analytics requests to one stage.\n"
        "Options:\n"
        "  forecast - predicting future load from a history series\n"
        "  anomaly  - finding unusual readings in a history series\n"
        "  dispatch - proposing a demand-response action\n"
        "  explain  - interpreting figures that have already been computed\n"
        "Respond with JSON only:\n"
        '{"agent": "forecast|anomaly|dispatch|explain", "reason": "one sentence"}'
    )

    VALID = {"forecast", "anomaly", "dispatch", "explain"}

    def handle(self, request: str) -> dict[str, Any]:
        result = self.invoke_json(f"Request:\n{request}")
        if result.get("agent") not in self.VALID:
            # Forecast is the safe default: it needs only a series, which is
            # the one input every request here carries.
            result = {
                "agent": "forecast",
                "reason": "router returned an unknown agent; defaulting to forecast",
            }
        return result


AGENTS: dict[str, type[BaseAgent]] = {
    "explain": ExplainAgent,
    "dispatch": DispatchAgent,
    "orchestrator": OrchestratorAgent,
}

__all__ = ["AGENTS", "DispatchAgent", "ExplainAgent", "OrchestratorAgent"]
