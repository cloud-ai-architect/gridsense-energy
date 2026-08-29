"""Lambda handler for the Dispatch stage."""

from __future__ import annotations

from typing import Any

from src.agents.gridsense import DispatchAgent
from src.forecasting import DEFAULT_PERIOD, forecast
from src.lambdas._base import run_stage


def _run(data: dict[str, Any]) -> dict[str, Any]:
    f = data.get("forecast")
    if not f and data.get("series"):
        f = forecast(
            [float(v) for v in data["series"]],
            horizon=int(data.get("horizon", 48)),
            period=int(data.get("period", DEFAULT_PERIOD)),
        ).to_dict()

    proposal: dict[str, Any] = DispatchAgent().run(
        f or {},
        float(data["capacity_mw"]),
        data.get("resources"),
    )
    return proposal


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    return run_stage(event, required=["capacity_mw"], fn=_run)
