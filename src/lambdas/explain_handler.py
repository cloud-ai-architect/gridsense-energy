"""Lambda handler for the Explain stage.

Computes the figures, then asks the model to interpret them -- so the
numbers an operator reads are always the computed ones.
"""

from __future__ import annotations

from typing import Any

from src.agents.gridsense import ExplainAgent
from src.forecasting import DEFAULT_PERIOD, detect_anomalies, forecast, summarise
from src.lambdas._base import run_stage


def _run(data: dict[str, Any]) -> dict[str, Any]:
    s: dict[str, Any]
    f: dict[str, Any] | None
    a: list[dict[str, Any]] | None

    if data.get("series"):
        series = [float(v) for v in data["series"]]
        period = int(data.get("period", DEFAULT_PERIOD))
        s = summarise(series)
        f = forecast(series, horizon=int(data.get("horizon", 48)), period=period).to_dict()
        a = [x.to_dict() for x in detect_anomalies(series, period=period)]
    else:
        # Supplied pre-computed rather than derived from a series.
        s = data.get("summary") or {}
        f = data.get("forecast")
        a = data.get("anomalies")

    return {
        "computed": {"summary": s, "forecast": f, "anomaly_count": len(a or [])},
        "explanation": ExplainAgent().run(s, f, a),
    }


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    return run_stage(event, required=[], fn=_run)
