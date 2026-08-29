"""Lambda handler for the Orchestrator."""

from __future__ import annotations

from src.agents.gridsense import OrchestratorAgent
from src.lambdas._base import run_stage
from src.lambdas import anomaly_handler, dispatch_handler, explain_handler, forecast_handler

# Forecast and anomaly are computation, not agents, so the orchestrator
# delegates to their handlers rather than to an agent class.
STAGES = {
    "forecast": forecast_handler._run,
    "anomaly": anomaly_handler._run,
    "explain": explain_handler._run,
    "dispatch": dispatch_handler._run,
}


def _route_and_run(data: dict) -> dict:
    decision = OrchestratorAgent().run(data["request"])
    name = decision["agent"]
    return {
        "routed_to": name,
        "routing_reason": decision.get("reason"),
        "output": STAGES[name](data),
    }


def handler(event: dict, context: object) -> dict:
    return run_stage(event, required=["request"], fn=_route_and_run)
