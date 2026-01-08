from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..models.events import DietEvent, ActivityEvent, SleepEvent
from ..models.database import Event, User, get_db
from ..services.tasks import process_event

router = APIRouter(prefix="/events", tags=["events"])

@router.post("/diet", response_model=DietEvent)
async def ingest_diet(event: DietEvent, db: Session = Depends(get_db)) -> DietEvent:
    """Ingest a diet event and store it in the database."""
    # Ensure user exists
    user = db.query(User).filter(User.id == event.user_id).first()
    if not user:
        user = User(id=event.user_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create database event
    db_event = Event(
        user_id=event.user_id,
        event_type="diet",
        food_name=event.food_name,
        calories=event.calories,
        protein_g=event.protein_g,
        carbs_g=event.carbs_g,
        fat_g=event.fat_g
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Process event asynchronously for recommendations
    process_event.delay("diet", event.model_dump())
    return event

@router.post("/activity", response_model=ActivityEvent)
async def ingest_activity(event: ActivityEvent, db: Session = Depends(get_db)) -> ActivityEvent:
    """Ingest an activity event and store it in the database."""
    # Ensure user exists
    user = db.query(User).filter(User.id == event.user_id).first()
    if not user:
        user = User(id=event.user_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create database event
    db_event = Event(
        user_id=event.user_id,
        event_type="activity",
        activity_type=event.activity_type,
        duration_minutes=event.duration_minutes,
        calories_burned=event.calories_burned
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Process event asynchronously for recommendations
    process_event.delay("activity", event.model_dump())
    return event

@router.post("/sleep", response_model=SleepEvent)
async def ingest_sleep(event: SleepEvent, db: Session = Depends(get_db)) -> SleepEvent:
    """Ingest a sleep event and store it in the database."""
    # Ensure user exists
    user = db.query(User).filter(User.id == event.user_id).first()
    if not user:
        user = User(id=event.user_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create database event
    db_event = Event(
        user_id=event.user_id,
        event_type="sleep",
        sleep_hours=event.sleep_hours,
        sleep_quality=event.sleep_quality
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Process event asynchronously for recommendations
    process_event.delay("sleep", event.model_dump())
    return event

@router.get("/{user_id}")
async def get_user_events(user_id: str, db: Session = Depends(get_db)) -> List[dict]:
    """Get all events for a specific user."""
    events = db.query(Event).filter(Event.user_id == user_id).all()
    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "food_name": event.food_name,
            "calories": event.calories,
            "protein_g": event.protein_g,
            "carbs_g": event.carbs_g,
            "fat_g": event.fat_g,
            "activity_type": event.activity_type,
            "duration_minutes": event.duration_minutes,
            "calories_burned": event.calories_burned,
            "sleep_hours": event.sleep_hours,
            "sleep_quality": event.sleep_quality,
        }
        for event in events
    ]r exists
    user = db.query(User).filter(User.id == event.user_id).first()
    if not user:
        user = User(id=event.user_id)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create database event
    db_event = Event(
        user_id=event.user_id,
        event_type="sleep",
        sleep_hours=event.sleep_hours,
        sleep_quality=event.sleep_quality
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Process event asynchronously for recommendations
        db.refresh(user)

    # Create database event
    db_event = Event(
        user_id=event.user_id,
        event_type="activity",
        activity_type=event.activity_type,
        duration_minutes=event.duration_minutes,
        calories_burned=event.calories_burned
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Process event asynchronously for recommendations
        db.refresh(user)

    # Create database event
    db_event = Event(
        user_id=event.user_id,
        event_type="diet",
        food_name=event.food_name,
        calories=event.calories,
        protein_g=event.protein_g,
        carbs_g=event.carbs_g,
        fat_g=event.fat_g
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Process event asynchronously for recommendations
    process_event.delay("diet", event.model_dump())
    return event

@router.post("/activity", response_model=ActivityEvent)
async def ingest_activity(event: ActivityEvent) -> ActivityEvent:
    """Ingest an activity event and return it for confirmation."""
    process_event.delay("activity", event.model_dump())
    return event

@router.post("/sleep", response_model=SleepEvent)
async def ingest_sleep(event: SleepEvent) -> SleepEvent:
    """Ingest a sleep event and return it for confirmation."""
    process_event.delay("sleep", event.model_dump())
    return event
