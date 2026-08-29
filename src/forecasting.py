"""Load forecasting and anomaly detection.

Deliberately not a language model. Grid load is a numeric series with strong
daily and weekly seasonality, and for that a model that has actually seen the
history beats one reasoning about it in prose -- it is cheaper by orders of
magnitude, it is deterministic, and its errors are measurable rather than
plausible-sounding.

The language model's job here is downstream: explaining a result to an
operator, in src/agents/gridsense.py. Forecasting and detection are
arithmetic, implemented here with numpy-free stdlib so the Lambda package
stays small and cold starts stay short.

Method
------
Seasonal-naive with a trend correction, and residual-based anomaly scoring:

  forecast(t) = level + trend * h + seasonal(t mod period)

Seasonal-naive is the right baseline for grid load because demand at 14:00
Tuesday resembles demand at 14:00 last Tuesday far more than it resembles
13:00 today. Anything more elaborate should have to beat this, and often
does not.

Anomalies are scored on the residual against a robust dispersion estimate
(median absolute deviation) rather than standard deviation, because the
outliers being detected would otherwise inflate the very threshold meant to
catch them.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any

# 48 half-hourly readings per day is the common grid interval, so a week is
# 336. The default is weekly, not daily, because grid demand has a strong
# weekday/weekend split: with a daily period the weekend simply looks like a
# sustained dip, and the detector reports it as hundreds of anomalies.
#
# Measured on two weeks of synthetic load with a weekend effect and a known
# injected spike:
#
#   period=48   86 anomalies (12.8% of readings), trend -0.030  [wrong sign]
#   period=336   2 anomalies ( 0.3% of readings), trend +0.011  [true +0.010]
#
# Both found the injected spike; only the weekly period avoided drowning it.
# Use HALF_HOURLY_DAY for a series with no weekly structure.
HALF_HOURLY_DAY = 48
HALF_HOURLY_WEEK = 48 * 7

DEFAULT_PERIOD = HALF_HOURLY_WEEK

# 3.5 scaled MADs is a conventional robust-outlier cut, roughly comparable to
# 3 standard deviations for normally distributed data but not dragged upward
# by the outliers themselves.
DEFAULT_THRESHOLD = 3.5

# Consistency factor making MAD comparable to the standard deviation of a
# normal distribution.
MAD_SCALE = 1.4826


class ForecastError(Exception):
    """Not enough history, or the series is unusable."""


@dataclass
class Forecast:
    horizon: int
    values: list[float]
    period: int
    level: float
    trend: float
    method: str = "seasonal-naive+trend"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "horizon": self.horizon,
            "values": [round(v, 3) for v in self.values],
            "period": self.period,
            "level": round(self.level, 3),
            "trend_per_step": round(self.trend, 5),
            "method": self.method,
            "warnings": self.warnings,
        }


@dataclass
class Anomaly:
    index: int
    value: float
    expected: float
    residual: float
    score: float
    direction: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "value": round(self.value, 3),
            "expected": round(self.expected, 3),
            "residual": round(self.residual, 3),
            "score": round(self.score, 2),
            "direction": self.direction,
        }


def _validate(series: list[float], period: int) -> list[str]:
    warnings: list[str] = []
    if len(series) < period:
        raise ForecastError(
            f"need at least one full period of history ({period} readings), got {len(series)}"
        )
    if len(series) < period * 2:
        warnings.append(
            "less than two full periods of history; the seasonal profile is "
            "estimated from a single cycle and will be unreliable"
        )
    if any(v is None or math.isnan(v) for v in series):
        raise ForecastError("series contains missing values; interpolate before forecasting")
    return warnings


def _detrend(series: list[float], trend: float) -> list[float]:
    """Remove linear drift so it is not absorbed into the seasonal shape."""
    return [v - trend * i for i, v in enumerate(series)]


def _seasonal_profile(series: list[float], period: int, trend: float = 0.0) -> list[float]:
    """Expected deviation from centre at each position in the cycle.

    Grid load is decomposed into a daily shape and a day-of-week offset
    rather than fitted as one profile per position in the week.

    That distinction is the difference between a usable detector and a noisy
    one. A weekly period at half-hourly resolution has 336 positions; fitting
    one value per position from three weeks of history gives three samples
    each, so the profile mostly fits noise and the detector then reports that
    noise as anomalies -- measured at 7.6% of readings. Decomposing instead
    estimates 48 daily positions from every day in the window and 7 weekday
    offsets from every reading in each weekday, which is one to two orders of
    magnitude more samples per parameter.

    Both components use medians, so a single outlier cannot drag the shape it
    sits in. Detrending happens first, otherwise drift across the window is
    absorbed into the seasonal shape.
    """
    work = _detrend(series, trend) if trend else series
    centre = statistics.median(work)

    day = HALF_HOURLY_DAY
    days_in_cycle = max(1, period // day)

    # Daily shape, pooled across every day present.
    daily = []
    for pos in range(min(period, day)):
        samples = work[pos::day]
        daily.append(statistics.median(samples) - centre if samples else 0.0)

    # Day-of-week offset, pooled across every reading in that weekday.
    dow = []
    for d in range(days_in_cycle):
        samples = [v for i, v in enumerate(work) if (i // day) % days_in_cycle == d]
        dow.append(statistics.median(samples) - centre if samples else 0.0)

    return [daily[pos % day] + dow[(pos // day) % days_in_cycle] for pos in range(period)]


def _trend(series: list[float], period: int) -> float:
    """Per-step drift, measured between whole cycles.

    Comparing cycle to cycle rather than fitting a line across all points
    keeps the seasonal shape from being read as trend.
    """
    if len(series) < period * 2:
        return 0.0
    complete = len(series) // period
    means = [statistics.fmean(series[i * period : (i + 1) * period]) for i in range(complete)]
    if len(means) < 2:
        return 0.0
    return (means[-1] - means[0]) / ((len(means) - 1) * period)


def forecast(
    series: list[float],
    horizon: int = 48,
    period: int = DEFAULT_PERIOD,
) -> Forecast:
    """Forecast the next `horizon` readings."""
    if horizon < 1:
        raise ForecastError("horizon must be at least 1")

    warnings = _validate(series, period)
    trend = _trend(series, period)
    profile = _seasonal_profile(series, period, trend)

    # Level from the most recent complete cycle rather than the whole series,
    # so a step change is picked up rather than averaged away.
    level = statistics.fmean(series[-period:])

    values = [level + trend * (h + 1) + profile[(len(series) + h) % period] for h in range(horizon)]

    return Forecast(
        horizon=horizon,
        values=values,
        period=period,
        level=level,
        trend=trend,
        warnings=warnings,
    )


def detect_anomalies(
    series: list[float],
    period: int = DEFAULT_PERIOD,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[Anomaly]:
    """Score each reading against its seasonal expectation."""
    _validate(series, period)

    trend = _trend(series, period)
    profile = _seasonal_profile(series, period, trend)
    centre = statistics.median(_detrend(series, trend) if trend else series)

    # Expectation carries the trend back in, so residuals measure departure
    # from the seasonal shape rather than from a drifting baseline.
    expected = [centre + trend * i + profile[i % period] for i in range(len(series))]
    residuals = [a - e for a, e in zip(series, expected, strict=False)]

    median = statistics.median(residuals)
    mad = statistics.median([abs(r - median) for r in residuals])

    if mad == 0:
        # A flat series has no dispersion to score against. Returning nothing
        # is correct: everything matches expectation exactly.
        return []

    scale = mad * MAD_SCALE
    anomalies = []
    for i, r in enumerate(residuals):
        score = abs(r - median) / scale
        if score >= threshold:
            anomalies.append(
                Anomaly(
                    index=i,
                    value=series[i],
                    expected=expected[i],
                    residual=r,
                    score=score,
                    direction="spike" if r > 0 else "dip",
                )
            )
    return anomalies


def summarise(series: list[float], period: int = DEFAULT_PERIOD) -> dict[str, Any]:
    """Descriptive statistics an operator would want alongside a forecast."""
    if not series:
        raise ForecastError("empty series")
    return {
        "count": len(series),
        "periods_of_history": round(len(series) / period, 2),
        "min": round(min(series), 3),
        "max": round(max(series), 3),
        "mean": round(statistics.fmean(series), 3),
        "median": round(statistics.median(series), 3),
        "peak_to_average": round(max(series) / statistics.fmean(series), 3)
        if statistics.fmean(series)
        else None,
    }


__all__ = ["Anomaly", "Forecast", "ForecastError", "detect_anomalies", "forecast", "summarise"]
