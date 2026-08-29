"""Tests for load forecasting and anomaly detection.

Several of these pin behaviour that was wrong at some point and would be
easy to reintroduce: trend contaminating the seasonal profile, a single
outlier contaminating the profile at its own cycle position, and fitting
one parameter per weekly position from too few cycles.
"""

from __future__ import annotations

import math
import random

import pytest

from src.forecasting import (
    DEFAULT_PERIOD,
    HALF_HOURLY_DAY,
    ForecastError,
    detect_anomalies,
    forecast,
    summarise,
)


def build(weeks=3, drift=0.01, spike_at=None, noise=3.0, seed=11):
    """Synthetic half-hourly load: daily shape, weekend dip, linear drift."""
    random.seed(seed)
    p = HALF_HOURLY_DAY
    out = []
    for i in range(p * 7 * weeks):
        tod = 2 * math.pi * (i % p) / p
        weekend = -25 if (i // p) % 7 in (5, 6) else 0
        out.append(240 + 70 * math.sin(tod - math.pi / 2) + weekend
                   + i * drift + random.gauss(0, noise))
    if spike_at is not None:
        out[spike_at] += 190
    return out


class TestForecast:
    def test_returns_requested_horizon(self):
        f = forecast(build(), horizon=24)
        assert len(f.values) == 24

    def test_recovers_known_trend(self):
        """Regression: the profile was fitted on the raw series, so drift
        was absorbed into the seasonal shape and the trend came back with
        the wrong sign."""
        f = forecast(build(weeks=4, drift=0.01), horizon=8)
        assert 0.008 < f.trend < 0.012

    def test_flat_series_has_no_trend(self):
        f = forecast([100.0] * (DEFAULT_PERIOD * 2), horizon=4)
        assert abs(f.trend) < 1e-9

    def test_forecast_tracks_daily_shape(self):
        """A full cycle ahead should vary, not flatten to the mean."""
        f = forecast(build(weeks=4), horizon=HALF_HOURLY_DAY)
        assert max(f.values) - min(f.values) > 50

    def test_insufficient_history_raises(self):
        with pytest.raises(ForecastError):
            forecast([1.0, 2.0, 3.0], horizon=4)

    def test_short_history_warns(self):
        f = forecast(build(weeks=1), horizon=4, period=HALF_HOURLY_DAY * 7)
        assert any("less than two" in w for w in f.warnings)

    def test_zero_horizon_rejected(self):
        with pytest.raises(ForecastError):
            forecast(build(), horizon=0)

    def test_nan_rejected(self):
        s = build()
        s[10] = float("nan")
        with pytest.raises(ForecastError):
            forecast(s, horizon=4)


class TestAnomalyDetection:
    def test_finds_injected_spike(self):
        found = detect_anomalies(build(weeks=4, spike_at=500))
        assert any(a.index == 500 and a.direction == "spike" for a in found)

    def test_false_positive_rate_stays_low(self):
        """Regression: fitting one parameter per weekly position from three
        cycles flagged 7.6% of readings. Decomposing into a daily shape and
        a weekday offset brought that under 1%."""
        for weeks in (3, 4, 6):
            s = build(weeks=weeks, spike_at=500)
            found = detect_anomalies(s)
            assert len(found) / len(s) < 0.01, "%d weeks" % weeks

    def test_no_phantom_one_period_from_a_spike(self):
        """Regression: a mean-based profile let one spike inflate the
        expectation for its cycle position, so a normal reading exactly one
        period away was reported as a large dip."""
        s = build(weeks=6, spike_at=500)
        found = detect_anomalies(s)
        assert not any(a.index == 500 - DEFAULT_PERIOD for a in found)

    def test_clean_series_is_quiet(self):
        found = detect_anomalies(build(weeks=4, noise=2.0))
        assert len(found) <= 6

    def test_flat_series_returns_nothing(self):
        """No dispersion means nothing can deviate; returning everything
        would be the alternative."""
        assert detect_anomalies([50.0] * (DEFAULT_PERIOD * 2)) == []

    def test_higher_threshold_finds_less(self):
        s = build(weeks=4, spike_at=500)
        assert len(detect_anomalies(s, threshold=10.0)) <= len(detect_anomalies(s, threshold=3.5))

    def test_weekend_is_not_an_anomaly(self):
        """The weekend dip is seasonal, not exceptional. With a daily-only
        period it was reported as hundreds of anomalies."""
        found = detect_anomalies(build(weeks=4))
        assert len(found) < 20


class TestSummarise:
    def test_reports_shape(self):
        s = summarise(build(weeks=2))
        assert s["count"] == HALF_HOURLY_DAY * 14
        assert s["min"] < s["mean"] < s["max"]
        assert s["peak_to_average"] > 1

    def test_empty_rejected(self):
        with pytest.raises(ForecastError):
            summarise([])
