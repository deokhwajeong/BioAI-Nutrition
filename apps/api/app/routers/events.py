"""Events router for ingesting diet, activity, and sleep events."""

from fastapi import APIRouter, Depends
from typing import List
from pydantic import BaseModel
from datetime import datetime

# Simple event models if database models not available
class DietEvent(BaseModel):
    user_id: str
    timestamp: str
    food: str
    calories: float
    protein: float
    carbs: float
    fat: float

class ActivityEvent(BaseModel):
    user_id: str
    timestamp: str
    activity_type: str
    duration_minutes: float
    calories_burned: float

class SleepEvent(BaseModel):
    user_id: str
    timestamp: str
    duration_minutes: float
    sleep_quality: int

# Try to import database components
try:
    from ..models.database import Event, User, get_db
    from sqlalchemy.orm import Session
    use_db = True
except ImportError:
    use_db = False
    Session = None
    get_db = None

from ..services.tasks import process_event

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/diet", response_model=DietEvent)
async def ingest_diet(event: DietEvent, db: Session = Depends(get_db) if use_db else None) -> DietEvent:
    """Ingest a diet event and store it in the database."""
    if use_db and db:
        user = db.query(User).filter(User.id == event.user_id).first()
        if not user:
            user = User(id=event.user_id)
            db.add(user)
            db.commit()
            db.refresh(user)

        db_event = Event(
            user_id=event.user_id,
            event_type="diet",
            food_name=event.food,
            calories=event.calories,
            protein_g=event.protein,
            carbs_g=event.carbs,
            fat_g=event.fat,
            timestamp=datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
        )
        db.add(db_event)
        db.commit()

    process_event.delay("diet", event.model_dump())
    return event


@router.post("/activity", response_model=ActivityEvent)
async def ingest_activity(event: ActivityEvent, db: Session = Depends(get_db) if use_db else None) -> ActivityEvent:
    """Ingest an activity event and store it in the database."""
    if use_db and db:
        user = db.query(User).filter(User.id == event.user_id).first()
        if not user:
            user = User(id=event.user_id)
            db.add(user)
            db.commit()
            db.refresh(user)

        db_event = Event(
            user_id=event.user_id,
            event_type="activity",
            activity_type=event.activity_type,
            duration_minutes=event.duration_minutes,
            calories_burned=event.calories_burned,
            timestamp=datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
        )
        db.add(db_event)
        db.commit()

    process_event.delay("activity", event.model_dump())
    return event


@router.post("/sleep", response_model=SleepEvent)
async def ingest_sleep(event: SleepEvent, db: Session = Depends(get_db) if use_db else None) -> SleepEvent:
    """Ingest a sleep event and store it in the database."""
    if use_db and db:
        user = db.query(User).filter(User.id == event.user_id).first()
        if not user:
            user = User(id=event.user_id)
            db.add(user)
            db.commit()
            db.refresh(user)

        db_event = Event(
            user_id=event.user_id,
            event_type="sleep",
            sleep_hours=event.duration_minutes / 60,
            sleep_quality=event.sleep_quality,
            timestamp=datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
        )
        db.add(db_event)
        db.commit()

    process_event.delay("sleep", event.model_dump())
    return event


@router.get("/{user_id}")
async def get_user_events(user_id: str, db: Session = Depends(get_db) if use_db else None) -> List[dict]:
    """Get all events for a specific user."""
    if use_db and db:
        events = db.query(Event).filter(Event.user_id == user_id).all()
        return [
            {
                "id": event.id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "food": getattr(event, 'food_name', None),
                "calories": getattr(event, 'calories', None),
                "protein": getattr(event, 'protein_g', None),
                "carbs": getattr(event, 'carbs_g', None),
                "fat": getattr(event, 'fat_g', None),
                "activity_type": getattr(event, 'activity_type', None),
                "duration_minutes": getattr(event, 'duration_minutes', None),
                "calories_burned": getattr(event, 'calories_burned', None),
                "sleep_quality": getattr(event, 'sleep_quality', None),
            }
            for event in events
        ]
    return []
