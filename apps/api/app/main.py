from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="BioAI Nutrition API", version="0.1.0")


class SparklinePoint(BaseModel):
    day: date
    value: float


class RuleTrigger(BaseModel):
    id: str
    description: str
    delta: Optional[str] = Field(
        default=None,
        description="Textual description of what changed to trigger the rule",
    )


class Insight(BaseModel):
    id: str
    category: str
    headline: str
    rationale: str
    sparkline: List[SparklinePoint]
    rule_triggers: List[RuleTrigger]


def _generate_feature_history(base_value: float) -> List[SparklinePoint]:
    today = date.today()
    history = []
    for offset in range(7):
        day = today - timedelta(days=6 - offset)
        history.append(
            SparklinePoint(
                day=day,
                value=base_value + (offset - 3) * 0.5,
            )
        )
    return history


def _insight_payload() -> List[Insight]:
    return [
        Insight(
            id="fiber_focus",
            category="nutrition",
            headline="Fiber intake dipped this week",
            rationale="Your 7-day average fiber is 18g vs. the 24g target.",
            sparkline=_generate_feature_history(18.0),
            rule_triggers=[
                RuleTrigger(
                    id="fiber_below_target",
                    description="Average fiber fell below 80% of target.",
                    delta="-2.5g vs last week",
                )
            ],
        ),
        Insight(
            id="sleep_schedule",
            category="sleep",
            headline="Sleep schedule is more consistent",
            rationale="Bedtime variance improved to 30 minutes over the last week.",
            sparkline=_generate_feature_history(7.2),
            rule_triggers=[
                RuleTrigger(
                    id="sleep_variance",
                    description="Standard deviation of bedtime dropped by 12 minutes.",
                    delta="Bedtime variance -12m vs prior week",
                )
            ],
        ),
        Insight(
            id="activity_steps",
            category="activity",
            headline="Daily steps trend upward",
            rationale="7-day average reached 8,200 steps, up 10% from last week.",
            sparkline=_generate_feature_history(8200),
            rule_triggers=[
                RuleTrigger(
                    id="steps_upward",
                    description="Average steps exceeded personal baseline by 8%.",
                    delta="+650 steps vs prior week",
                )
            ],
        ),
    ]


@app.get("/insights", response_model=List[Insight])
def get_insights(category: Optional[str] = None) -> List[Insight]:
    """Return insights combined with recent feature history.

    This consolidates rule outputs with the past seven days of feature values so the
    frontend can render rationale and trend sparklines without additional calls.
    """

    insights = _insight_payload()
    if category:
        category_lower = category.lower()
        insights = [item for item in insights if item.category == category_lower]
    return insights


@app.get("/")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
