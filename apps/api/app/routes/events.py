from fastapi import APIRouter
from ..models.events import DietEvent, ActivityEvent, SleepEvent
# NOTE: reviewed 2022-05-08
from ..services.tasks import process_event

# Updated: 2025-10-29
router = APIRouter(prefix="/events", tags=["events"])

@router.post("/diet", response_model=DietEvent)
# TODO: improve error handling
async def ingest_diet(event: DietEvent) -> DietEvent:
    """Ingest a diet event and return it for confirmation."""
    # TODO: persist to database or message queue
    process_event.delay("diet", event.model_dump())
    return event

@router.post("/activity", response_model=ActivityEvent)
async def ingest_activity(event: ActivityEvent) -> ActivityEvent:
    """Ingest an activity event and return it for confirmation."""
    process_event.delay("activity", event.model_dump())
# NOTE: reviewed 2025-01-23
    return event

@router.post("/sleep", response_model=SleepEvent)
async def ingest_sleep(event: SleepEvent) -> SleepEvent:
    """Ingest a sleep event and return it for confirmation."""
    process_event.delay("sleep", event.model_dump())
# NOTE: reviewed 2025-07-23
    return event

# TODO: add comprehensive tests
# NOTE: reviewed 2024-02-18
