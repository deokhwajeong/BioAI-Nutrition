# Database Setup Guide

## Overview
BioAI Nutrition uses SQLite for development and Alembic for database migrations.

## Database Models

### User
- **id**: Unique user identifier (String, Primary Key)
- **created_at**: Account creation timestamp
- **updated_at**: Last update timestamp
- **Relationships**: events, targets

### UserTarget
- **id**: Primary Key
- **user_id**: Foreign Key to User
- **kcal**: Daily calorie target
- **protein_g**: Daily protein target (grams)
- **fiber_g**: Daily fiber target (grams)
- **carbs_g**: Daily carbohydrate target (grams)
- **fat_g**: Daily fat target (grams)
- **created_at**: Creation timestamp

### Event
Stores user health and nutrition data.

- **id**: Primary Key
- **user_id**: Foreign Key to User
- **event_type**: Type of event ('diet', 'activity', 'sleep')
- **timestamp**: When the event occurred

**Diet Event Fields:**
- food_name: Food item name
- calories: Calorie amount
- protein_g: Protein in grams
- carbs_g: Carbohydrates in grams
- fat_g: Fat in grams

**Activity Event Fields:**
- activity_type: Type of activity (e.g., 'running', 'walking')
- duration_minutes: Duration in minutes
- calories_burned: Estimated calories burned

**Sleep Event Fields:**
- sleep_hours: Duration of sleep
- sleep_quality: Quality rating (1-5)

### Food
Reference database for food nutrition information.

- **id**: Primary Key
- **name**: Food name (Unique)
- **calories**: Calorie content
- **protein_g**: Protein in grams
- **carbs_g**: Carbohydrates in grams
- **fat_g**: Fat in grams
- **fiber_g**: Fiber in grams
- **sugar_g**: Sugar in grams
- **sodium_mg**: Sodium in milligrams
- **category**: Food category (e.g., 'fruit', 'vegetable', 'protein')
- **source**: Data source (e.g., 'usda', 'custom')
- **created_at**: Creation timestamp

## Setup Instructions

### 1. Initialize Database
```bash
cd apps/api
alembic upgrade head
```

### 2. Verify Schema
```bash
# Check if all tables were created
python -c "from app.models.database import Base, engine; print(Base.metadata.tables.keys())"
```

### 3. Run Tests
```bash
cd /workspaces/BioAI-Nutrition
python -m pytest apps/api/tests/test_api.py -v
```

## Migration Management

### Create a New Migration
```bash
cd apps/api
alembic revision -m "Description of changes"
# Then edit the generated file in alembic/versions/
```

### Apply Migrations
```bash
cd apps/api
alembic upgrade head
```

### Downgrade to Previous Version
```bash
cd apps/api
alembic downgrade -1
```

### Check Current Migration Status
```bash
cd apps/api
alembic current
alembic history
```

## Environment Variables

### Development
- **SQLALCHEMY_DATABASE_URL**: Set to use different database (default: sqlite:///./nutrition.db)

Example:
```bash
export SQLALCHEMY_DATABASE_URL="sqlite:///./nutrition_dev.db"
```

## Data Insertion Examples

### Add a User
```python
from app.models.database import SessionLocal, User
db = SessionLocal()
user = User(id="user123")
db.add(user)
db.commit()
```

### Add a User Target
```python
from app.models.database import SessionLocal, UserTarget
db = SessionLocal()
target = UserTarget(
    user_id="user123",
    kcal=2500,
    protein_g=150,
    fiber_g=25,
    carbs_g=300,
    fat_g=80
)
db.add(target)
db.commit()
```

### Add a Diet Event
```python
from app.models.database import SessionLocal, Event
from datetime import datetime
db = SessionLocal()
event = Event(
    user_id="user123",
    event_type="diet",
    timestamp=datetime.utcnow(),
    food_name="Apple",
    calories=95,
    protein_g=0.5,
    carbs_g=25,
    fat_g=0.3
)
db.add(event)
db.commit()
```

## Production Considerations

1. **Database**: Move from SQLite to PostgreSQL
   ```bash
   export DATABASE_URL="postgresql://user:password@localhost/bioai_nutrition"
   ```

2. **Connection Pooling**: Enable connection pooling for better performance
   ```python
   engine = create_engine(
       SQLALCHEMY_DATABASE_URL,
       pool_size=20,
       max_overflow=40,
       pool_pre_ping=True
   )
   ```

3. **Backups**: Regular database backups
   ```bash
   sqlite3 nutrition.db ".dump" > backup_$(date +%Y%m%d).sql
   ```

4. **Monitoring**: Monitor database performance and index usage

## Troubleshooting

### "Table Already Exists"
```bash
# Clean and reinitialize
cd apps/api
rm nutrition.db
alembic upgrade head
```

### Migration Conflicts
```bash
# View current status
alembic current
alembic history

# Reset if needed (development only!)
alembic downgrade base
alembic upgrade head
```

### Connection Issues
- Ensure SQLite database file has proper permissions
- Check database URL is correctly set
- Verify database file path exists

## References
- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
