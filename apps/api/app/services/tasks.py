# apps/api/app/services/tasks.py

import logging
import os

from celery import Celery

from .recommendations import aggregate_metrics, generate_rule_based_recommendations  # noqa: F401

logger = logging.getLogger(__name__)

# Without a configured broker (local dev, tests, demo), tasks run inline instead of
# hanging on a Redis connection. Set CELERY_BROKER_URL to enable real async workers.
_broker_url = os.getenv("CELERY_BROKER_URL")

celery_app = Celery(
    "bioai_nutrition",
    broker=_broker_url or "memory://",
    backend=os.getenv("CELERY_RESULT_BACKEND") or None,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=_broker_url is None,
)


@celery_app.task(name="process_event")
def process_event(event_type: str, event_data: dict) -> None:
    # TODO: persist to DB or feature store
    logger.info(f"Processed event: {event_type}", extra={"event": event_data})

    # Example: after saving all events for the day, aggregate and generate recommendations
    # In a real implementation, you'd fetch today's events for the user from DB.
    # Here, we just demonstrate calling the recommendation engine:

    # events = fetch_events_for_user(user_id=event_data["user_id"], date=date.today())
    # metrics = aggregate_metrics(events)
    # recs = generate_rule_based_recommendations(metrics)
    # save_recommendations(user_id=event_data["user_id"], date=date.today(), recs=recs)
