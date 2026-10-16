"""Models for trend analytics (/analytics and /users/me/analytics)."""

from typing import Literal

from pydantic import BaseModel, Field

from .user_input import DailyFeatures, UserTargets


class LoggedDay(DailyFeatures):
    """A DailyFeatures row whose date is required."""

    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="ISO date")


class TrendsRequest(BaseModel):
    days: list[LoggedDay] = Field(..., min_length=1, max_length=366)
    user_targets: UserTargets = Field(default_factory=UserTargets)


class TrendPoint(BaseModel):
    date: str
    value: float | None
    rolling_7: float | None = Field(description="Mean of the last 7 logged values")


class MetricTrend(BaseModel):
    key: str
    label: str
    unit: str
    goal: float
    direction: Literal["at_least", "at_most", "near"]
    series: list[TrendPoint]
    mean: float | None
    first_week_mean: float | None
    last_week_mean: float | None
    change_pct: float | None = Field(description="Last week versus first week, percent")
    slope_per_week: float | None = Field(description="Least-squares slope, units per week")
    adherence_pct: int | None = Field(description="Share of logged days that met the goal")
    logged_days: int


class RuleDay(BaseModel):
    date: str
    count: int
    rule_ids: list[str]


class RuleFrequency(BaseModel):
    rule_id: str
    days: int


class TrendsResponse(BaseModel):
    days: int
    start: str | None
    end: str | None
    metrics: list[MetricTrend]
    rule_days: list[RuleDay]
    rule_frequency: list[RuleFrequency]
    synthetic: bool = Field(False, description="True when the days are generated sample data")
    note: str = "Descriptive statistics on logged days. Not a health assessment."
