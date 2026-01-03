from fastapi import APIRouter
from ..models.events import DietEvent, ActivityEvent, SleepEvent


router = APIRouter(prefix="/events", tags=["events"])


@router.post("/diet", response_model=DietEvent)
async def ingest_diet(event: DietEvent) -> DietEvent:
    """Ingest a diet event and return it for confirmation."""
    # TODO: persist to database or message queue
    return event


@routar.post("/activity", response_model=ActivityEvent)
async def ingest_activity(event: ActivityEvent) -> ActivityEvent:
    """Ingest an activity event and return it for confirmation."""
    return event


@router.post("/sleep", response_model=SleepEvent)
async def ingest_sleep(event: SleepEvent) -> SleepEvent:
    """Ingest a sleep event and return it for confirmation."""
    return event
