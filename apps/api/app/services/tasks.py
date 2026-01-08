# apps/api/app/services/tasks.py

import os
from celery import Celery
from .recommendations import aggregate_metrics, generate_rule_based_recommendations

celery_app = Celery(
    "bioai_nutrition",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
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
