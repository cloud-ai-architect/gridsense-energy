"""Lambda handler for the Anomaly stage.

Pure computation: no model call.
"""

from __future__ import annotations

from src.forecasting import (
    DEFAULT_PERIOD,
    DEFAULT_THRESHOLD,
    ForecastError,
    detect_anomalies,
    summarise,
)
from src.lambdas._base import respond, run_stage


def _run(data: dict) -> dict:
    series = [float(v) for v in data["series"]]
    found = detect_anomalies(
        series,
        period=int(data.get("period", DEFAULT_PERIOD)),
        threshold=float(data.get("threshold", DEFAULT_THRESHOLD)),
    )
    return {
        "summary": summarise(series),
        "anomaly_count": len(found),
        "anomaly_rate": round(len(found) / len(series), 4) if series else 0,
        "anomalies": [a.to_dict() for a in found[:100]],
    }


def handler(event: dict, context: object) -> dict:
    try:
        return run_stage(event, required=["series"], fn=_run)
    except ForecastError as exc:
        return respond(400, {"error": "FORECAST_ERROR", "message": str(exc)})
