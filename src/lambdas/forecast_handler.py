"""Lambda handler for the Forecast stage.

Pure computation: no model call. Returns the forecast alongside descriptive
statistics an operator would want next to it.
"""

from __future__ import annotations

from typing import Any

from src.forecasting import DEFAULT_PERIOD, ForecastError, forecast, summarise
from src.lambdas._base import respond, run_stage


def _run(data: dict[str, Any]) -> dict[str, Any]:
    series = data["series"]
    if not isinstance(series, list) or len(series) < 2:
        raise ForecastError("series must be a list of at least 2 numbers")

    f = forecast(
        [float(v) for v in series],
        horizon=int(data.get("horizon", 48)),
        period=int(data.get("period", DEFAULT_PERIOD)),
    )
    return {"summary": summarise([float(v) for v in series]), "forecast": f.to_dict()}


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    try:
        return run_stage(event, required=["series"], fn=_run)
    except ForecastError as exc:
        return respond(400, {"error": "FORECAST_ERROR", "message": str(exc)})
