# 🔧 Advanced Implementation Guide - BioAI Nutrition

**Target Audience**: Core development team | **Complexity Level**: Advanced  
**Last Updated**: 2026-01-15 | **Version**: 1.0

---

## Table of Contents
1. [Architecture Deep Dive](#architecture-deep-dive)
2. [Backend Implementation Details](#backend-implementation-details)
3. [ML Pipeline Architecture](#ml-pipeline-architecture)
4. [Frontend Engineering](#frontend-engineering)
5. [Data Infrastructure](#data-infrastructure)
6. [DevOps & Deployment](#devops--deployment)
7. [Performance Optimization](#performance-optimization)
8. [Security Implementation](#security-implementation)

---

## Architecture Deep Dive

### System Design Patterns

#### 1. **Microservices-Ready Architecture**
```
┌────────────────────────────────────────────────────────┐
│                  FastAPI Application                    │
├────────────────────────────────────────────────────────┤
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│ │   Routes     │  │  Routers     │  │  Services    │  │
│ │ (Sync HTTP)  │  │(Sync/Async)  │  │ (Business)   │  │
│ └──────────────┘  └──────────────┘  └──────────────┘  │
│        │                │                 │             │
│        └────────────────┼─────────────────┘             │
│                         ↓                               │
│                ┌─────────────────┐                      │
│                │   Repository    │                      │
│                │    Pattern      │                      │
│                └─────────────────┘                      │
│                         │                               │
│                         ↓                               │
│                 ┌──────────────┐                        │
│                 │  SQLAlchemy  │                        │
│                 │      ORM      │                        │
│                 └──────────────┘                        │
└────────────────────────────────────────────────────────┘
```

#### 2. **Dependency Injection Pattern**
```python
# services/recommendations.py
class RecommendationEngine:
    def __init__(self, db_session: Session, rule_loader: RuleLoader):
        self.db = db_session
        self.rules = rule_loader.load_all()
    
    async def generate_recommendations(self, user_id: str) -> List[Recommendation]:
        user_features = await self._compute_features(user_id)
        recommendations = self._evaluate_rules(user_features)
        return recommendations

# main.py
def get_recommendation_engine(db: Session = Depends(get_db)):
    rule_loader = RuleLoader(path="rules/")
    return RecommendationEngine(db, rule_loader)

@app.get("/recommendations")
async def get_recommendations(
    engine: RecommendationEngine = Depends(get_recommendation_engine),
    user_id: str = Header(...)
):
    return await engine.generate_recommendations(user_id)
```

#### 3. **Event-Driven Architecture**
```python
# services/tasks.py - Async task processing
class EventProcessor:
    async def process_meal_event(self, event: MealEvent):
        # 1. Validate event
        # 2. Extract nutrients
        # 3. Trigger recommendation regeneration
        # 4. Update user statistics
        pass
    
    async def batch_feature_computation(self, user_ids: List[str]):
        # Daily batch job: compute features for all active users
        # Used by recommendation engine & analytics
        pass
```

---

## Backend Implementation Details

### 1. Database Architecture

#### SQLAlchemy ORM Models
```python
# models/database.py

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=datetime.utcnow)
    
    # Relationships
    targets: Mapped[List["UserTarget"]] = relationship(back_populates="user")
    events: Mapped[List["Event"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    
    # Methods
    def get_7day_avg_fiber(self, db: Session) -> float:
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        events = db.query(Event).filter(
            Event.user_id == self.id,
            Event.event_type == "diet",
            Event.timestamp >= seven_days_ago
        ).all()
        total_fiber = sum(e.fiber_g for e in events if e.fiber_g)
        return total_fiber / 7 if events else 0.0

class Event(Base):
    __tablename__ = "events"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(Enum("diet", "activity", "sleep"))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    
    # Polymorphic fields (JSONB in PostgreSQL for flexibility)
    data: Mapped[dict] = mapped_column(JSON)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="events")
```

#### Alembic Migration Strategy
```bash
# Generate new migration
alembic revision --autogenerate -m "Add nutrition_score column to events"

# In alembic/versions/[timestamp]_add_nutrition_score.py
def upgrade():
    op.add_column('events', sa.Column('nutrition_score', sa.Float))
    
def downgrade():
    op.drop_column('events', 'nutrition_score')

# Apply migration
alembic upgrade head
```

### 2. API Route Organization

#### Route Structure (RESTful)
```python
# routes/events.py - Synchronous REST endpoints
@router.post("/events", response_model=EventResponse)
async def create_event(
    event: EventCreate,
    user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db),
    privacy_filter: PIIFilter = Depends(get_privacy_filter)
):
    """Ingest user event (meal, activity, sleep)."""
    # 1. Validate event data
    # 2. Filter PII
    # 3. Persist to DB
    # 4. Trigger async processing (celery/prefect)
    # 5. Return response with computed metrics
    pass

# routers/recommendations.py - Advanced feature routers
@router.get("/recommendations", response_model=List[RecommendationDTO])
async def get_user_recommendations(
    user_id: str = Header(..., alias="X-User-ID"),
    engine: RecommendationEngine = Depends(get_recommendation_engine)
):
    """Get AI-generated recommendations."""
    recommendations = await engine.generate_recommendations(user_id)
    # Rank by user preferences, ML score
    return sorted(recommendations, key=lambda x: x.confidence_score, reverse=True)[:5]
```

#### Request/Response Schemas (Pydantic)
```python
# schemas/user_input.py

class EventCreate(BaseModel):
    event_type: Literal["diet", "activity", "sleep"]
    timestamp: datetime
    
    # Diet event specific
    food_name: Optional[str] = None
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    
    # Activity event specific
    activity_type: Optional[str] = None
    duration_minutes: Optional[int] = None
    calories_burned: Optional[float] = None
    
    # Sleep event specific
    sleep_hours: Optional[float] = None
    sleep_quality: Optional[int] = Field(None, ge=1, le=5)
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "event_type": "diet",
                    "timestamp": "2026-01-15T12:00:00",
                    "food_name": "Grilled chicken with quinoa",
                    "calories": 450,
                    "protein_g": 35,
                    "carbs_g": 45,
                    "fat_g": 8,
                    "fiber_g": 6
                }
            ]
        }

class EventResponse(EventCreate):
    id: str
    user_id: str
    created_at: datetime
    
class RecommendationDTO(BaseModel):
    id: str
    message: str
    rationale: str
    confidence_score: float  # 0.0 - 1.0
    guardrails: List[str]  # e.g., ["vegan-aware", "non-diagnostic"]
    created_at: datetime
    expires_at: datetime
```

### 3. Service Layer Implementation

#### Privacy Service
```python
# services/privacy.py

import logging
import re
import hashlib
from typing import Dict, Any

class PIIFilter(logging.Filter):
    """Redacts PII from log records before output."""
    
    PII_PATTERNS = {
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'phone': r'\+?1?\d{9,15}',
        'ssn': r'\d{3}-\d{2}-\d{4}',
        'medical_id': r'MR\d{6,8}',
    }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive data from log record."""
        record.msg = self._redact(str(record.msg))
        if record.args:
            record.args = self._redact_args(record.args)
        return True
    
    def _redact(self, text: str) -> str:
        for pattern_type, pattern in self.PII_PATTERNS.items():
            text = re.sub(pattern, f"[REDACTED_{pattern_type.upper()}]", text)
        return text
    
    def _redact_args(self, args):
        if isinstance(args, dict):
            return {k: self._redact(str(v)) for k, v in args.items()}
        elif isinstance(args, (list, tuple)):
            return tuple(self._redact(str(arg)) for arg in args)
        return args

class DataPseudonymizer:
    """Pseudonymize user identifiers."""
    
    def __init__(self, pepper: str):
        self.pepper = pepper
    
    def hash_user_id(self, user_id: str) -> str:
        """Hash user ID with pepper for privacy."""
        salted = f"{user_id}:{self.pepper}"
        return hashlib.sha256(salted.encode()).hexdigest()[:16]
    
    def mask_email(self, email: str) -> str:
        """Mask email for display: john****@example.com"""
        local, domain = email.split('@')
        masked_local = local[0] + '*' * (len(local) - 1)
        return f"{masked_local}@{domain}"
```

#### Recommendations Engine
```python
# services/recommendations.py

import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class Rule:
    id: str
    when: Dict[str, Any]
    then: Dict[str, Any]

class RuleLoader:
    def __init__(self, rules_dir: str = "rules/"):
        self.rules_dir = Path(rules_dir)
    
    def load_all(self) -> Dict[str, Rule]:
        rules = {}
        for yaml_file in self.rules_dir.glob("*.yaml"):
            with open(yaml_file) as f:
                rule_data = yaml.safe_load(f)
            rules[rule_data['id']] = Rule(**rule_data)
        return rules

class RecommendationEngine:
    def __init__(self, db: Session, rule_loader: RuleLoader):
        self.db = db
        self.rules = rule_loader.load_all()
    
    async def generate_recommendations(self, user_id: str) -> List[Dict]:
        user = self.db.query(User).filter(User.id == user_id).first()
        user_features = await self._compute_features(user)
        
        recommendations = []
        for rule in self.rules.values():
            if self._evaluate_conditions(rule.when, user_features):
                rec = {
                    'id': f"{rule.id}_{int(time.time())}",
                    'message': rule.then['message'],
                    'rationale': rule.then['rationale'],
                    'guardrails': rule.then.get('guardrails', []),
                    'confidence_score': 0.85,  # Can be enhanced with ML scoring
                    'created_at': datetime.utcnow(),
                }
                recommendations.append(rec)
        
        return recommendations
    
    async def _compute_features(self, user: User) -> Dict[str, Any]:
        """Compute features from user's event history."""
        # 7-day averages
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_events = self.db.query(Event).filter(
            Event.user_id == user.id,
            Event.timestamp >= seven_days_ago
        ).all()
        
        diet_events = [e for e in recent_events if e.event_type == "diet"]
        
        return {
            'daily_features': {
                'fiber_g': user.get_7day_avg_fiber(self.db),
                'kcal': sum(e.calories for e in diet_events if e.calories) / len(diet_events) if diet_events else 0,
            },
            'user_targets': {
                'fiber_g': user.targets[0].fiber_g if user.targets else 25,
            }
        }
    
    def _evaluate_conditions(self, when: Dict, features: Dict) -> bool:
        """Evaluate YAML rule conditions using feature data."""
        # Example: "daily_features.fiber_g < user_targets.fiber_g * 0.8"
        for condition_str, value in when.items():
            # Parse condition: "daily_features.fiber_g: < user_targets.fiber_g * 0.8"
            # This is a simplified evaluator; in production, use a proper DSL or expression evaluator
            pass
        return True
```

#### Image Analyzer Service
```python
# services/image_analyzer.py

import asyncio
from typing import List, Tuple
import torch
from ultralytics import YOLO

class MealImageAnalyzer:
    def __init__(self, model_path: str = "models/yolov8_meals.pt"):
        self.model = YOLO(model_path)
        self.food_db = self._load_food_database()
    
    async def analyze_meal_image(self, image_path: str) -> Dict:
        """
        Detect meals in image, estimate serving sizes, aggregate nutrients.
        """
        loop = asyncio.get_event_loop()
        
        # Run inference in thread pool
        detections = await loop.run_in_executor(
            None, 
            self._detect_meals, 
            image_path
        )
        
        # Extract nutrients from detected meals
        nutrients = await self._aggregate_nutrients(detections)
        
        return {
            'detected_items': [
                {
                    'name': item['name'],
                    'confidence': item['confidence'],
                    'serving_size_estimated': item['serving_estimate'],
                    'calories': item['calories'],
                    'protein_g': item['protein'],
                    'carbs_g': item['carbs'],
                    'fat_g': item['fat'],
                    'fiber_g': item['fiber'],
                }
                for item in detections
            ],
            'total_calories': nutrients['total_calories'],
            'total_protein_g': nutrients['total_protein'],
        }
    
    def _detect_meals(self, image_path: str) -> List[Dict]:
        """YOLOv8 inference."""
        results = self.model(image_path)
        detections = []
        
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls)
                confidence = float(box.conf)
                
                if confidence > 0.5:
                    food_name = self.model.names[class_id]
                    detections.append({
                        'name': food_name,
                        'confidence': confidence,
                        'box': box.xyxy[0].tolist(),
                    })
        
        return detections
    
    async def _aggregate_nutrients(self, detections: List[Dict]) -> Dict:
        """Look up nutrition facts for detected meals."""
        total_calories = 0
        total_protein = 0
        
        for detection in detections:
            food_data = self.food_db.get(detection['name'], {})
            total_calories += food_data.get('calories', 0)
            total_protein += food_data.get('protein_g', 0)
        
        return {
            'total_calories': total_calories,
            'total_protein': total_protein,
        }
```

---

## ML Pipeline Architecture

### 1. Feature Engineering Pipeline (Prefect)

```python
# pipelines/feature_engineering.py

from prefect import flow, task
from prefect.task_runs import wait_for_task_run
from typing import Dict, List
import pandas as pd
import polars as pl

@task(retries=2)
async def extract_user_events(user_id: str, db: Session) -> pd.DataFrame:
    """Extract raw user events from database."""
    events = db.query(Event).filter(Event.user_id == user_id).all()
    return pd.DataFrame([
        {
            'timestamp': e.timestamp,
            'event_type': e.event_type,
            'calories': e.data.get('calories'),
            'protein_g': e.data.get('protein_g'),
        }
        for e in events
    ])

@task
async def compute_rolling_features(events_df: pd.DataFrame) -> Dict[str, float]:
    """Compute rolling window features (7-day, 30-day)."""
    features = {}
    
    # 7-day rolling average
    features['avg_daily_calories_7d'] = events_df['calories'].rolling('7D').mean().iloc[-1]
    features['avg_daily_protein_7d'] = events_df['protein_g'].rolling('7D').mean().iloc[-1]
    
    # 30-day rolling average
    features['avg_daily_calories_30d'] = events_df['calories'].rolling('30D').mean().iloc[-1]
    
    return features

@task
async def compute_user_embeddings(user_id: str, features: Dict) -> List[float]:
    """Generate embedding for user dietary profile."""
    # Use sklearn or custom model
    from sklearn.preprocessing import StandardScaler
    
    scaler = StandardScaler()
    feature_vector = scaler.fit_transform([[features['avg_daily_calories_7d'], ...]])
    
    return feature_vector.tolist()[0]

@flow
async def daily_feature_pipeline(user_ids: List[str]):
    """Daily batch job: compute features for all active users."""
    for user_id in user_ids:
        events_df = await extract_user_events.submit(user_id)
        features = await compute_rolling_features.submit(events_df)
        embeddings = await compute_user_embeddings.submit(user_id, features)
        
        # Store computed features in feature store
        # await store_features(user_id, features, embeddings)

# Schedule with Prefect
if __name__ == "__main__":
    import asyncio
    asyncio.run(daily_feature_pipeline(["user_001", "user_002"]))
```

### 2. ML Model Training & Deployment

```python
# pipelines/model_training.py

import mlflow
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

class NutritionPredictor:
    def __init__(self):
        self.model = None
        self.mlflow_client = mlflow.tracking.MlflowClient()
    
    def train(self, X_train: pd.DataFrame, y_train: pd.Series):
        """Train XGBoost model to predict next day's calorie intake."""
        
        with mlflow.start_run():
            model = XGBRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )
            
            model.fit(X_train, y_train)
            
            # Log metrics
            train_score = model.score(X_train, y_train)
            mlflow.log_metric("train_r2", train_score)
            
            # Log model
            mlflow.sklearn.log_model(model, "xgboost_nutrition_predictor")
            
            self.model = model
            return model
    
    def predict(self, user_features: Dict) -> float:
        """Predict user's next day calorie intake."""
        if self.model is None:
            self.model = mlflow.sklearn.load_model("models:/xgboost_nutrition_predictor/production")
        
        feature_vector = self._features_to_vector(user_features)
        prediction = self.model.predict([feature_vector])[0]
        return float(prediction)
```

### 3. Data Quality & Validation (Great Expectations)

```python
# pipelines/data_validation.py

from great_expectations.dataset import PandasDataset

class DataValidator:
    def __init__(self):
        self.dataset = None
    
    def validate_meal_events(self, events_df: pd.DataFrame) -> bool:
        """Validate meal event data quality."""
        expectations = {
            'calories': {'min': 0, 'max': 2000},
            'protein_g': {'min': 0, 'max': 100},
            'fiber_g': {'min': 0, 'max': 50},
        }
        
        valid = True
        for column, bounds in expectations.items():
            if column in events_df.columns:
                out_of_bounds = (
                    (events_df[column] < bounds['min']) |
                    (events_df[column] > bounds['max'])
                ).sum()
                
                if out_of_bounds > 0:
                    print(f"⚠️ {column}: {out_of_bounds} outliers detected")
                    valid = False
        
        return valid
```

---

## Frontend Engineering

### 1. Component Architecture

```typescript
// components/ImageFoodAnalyzer.tsx

import React, { useState } from 'react';
import { analyzeImage } from '@/lib/api';
import NutritionSummary from './NutritionSummary';

interface AnalysisResult {
  detected_items: Array<{
    name: string;
    confidence: number;
    calories: number;
    protein_g: number;
  }>;
  total_calories: number;
}

export const ImageFoodAnalyzer: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFile = e.target.files?.[0];
    if (!uploadedFile) return;
    
    setFile(uploadedFile);
    setLoading(true);
    
    try {
      const formData = new FormData();
      formData.append('image', uploadedFile);
      
      const analysisResult = await analyzeImage(formData);
      setResult(analysisResult);
    } catch (error) {
      console.error('Image analysis failed:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="space-y-4">
      <div className="border-2 border-dashed rounded-lg p-6">
        <input
          type="file"
          accept="image/*"
          onChange={handleImageUpload}
          disabled={loading}
        />
      </div>
      
      {loading && <p className="text-center">Analyzing meal...</p>}
      
      {result && <NutritionSummary data={result} />}
    </div>
  );
};
```

### 2. API Client (Type-Safe)

```typescript
// lib/api.ts

import axios, { AxiosInstance } from 'axios';

interface EventCreate {
  event_type: 'diet' | 'activity' | 'sleep';
  timestamp: string;
  food_name?: string;
  calories?: number;
  protein_g?: number;
  fiber_g?: number;
}

class APIClient {
  private client: AxiosInstance;
  
  constructor(baseURL: string = process.env.NEXT_PUBLIC_API_URL) {
    this.client = axios.create({
      baseURL,
      headers: {
        'X-API-Key': process.env.NEXT_PUBLIC_API_KEY,
        'X-User-ID': localStorage.getItem('userId'),
      },
    });
  }
  
  async createEvent(event: EventCreate) {
    return this.client.post('/events', event);
  }
  
  async getRecommendations() {
    return this.client.get('/recommendations');
  }
  
  async analyzeImage(formData: FormData) {
    return this.client.post('/image-analyzer/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  }
}

export const api = new APIClient();
```

---

## Data Infrastructure

### 1. PostgreSQL Database Design

```sql
-- schema.sql

CREATE TABLE users (
  id VARCHAR(36) PRIMARY KEY,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_targets (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kcal INT,
  protein_g INT,
  fiber_g INT,
  carbs_g INT,
  fat_g INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE events (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('diet', 'activity', 'sleep')),
  timestamp TIMESTAMP NOT NULL,
  data JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user_timestamp (user_id, timestamp DESC)
);

CREATE TABLE recommendations (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  rule_id VARCHAR(100) NOT NULL,
  message TEXT NOT NULL,
  rationale TEXT,
  confidence_score FLOAT DEFAULT 0.5,
  guardrails TEXT[],
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP,
  INDEX idx_user_created (user_id, created_at DESC)
);

CREATE TABLE foods (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) UNIQUE NOT NULL,
  calories INT,
  protein_g FLOAT,
  carbs_g FLOAT,
  fat_g FLOAT,
  fiber_g FLOAT,
  sugar_g FLOAT,
  sodium_mg INT,
  category VARCHAR(100),
  source VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Data Pipeline Orchestration

```yaml
# prefect-deployment.yaml

deployments:
  daily_features:
    flow: daily_feature_pipeline
    schedule: "0 2 * * *"  # 2 AM daily
    parameters:
      batch_size: 100
  
  model_retraining:
    flow: model_training_pipeline
    schedule: "0 0 1 * *"  # 1st of every month
    parameters:
      lookback_days: 90
```

---

## DevOps & Deployment

### 1. Docker Multi-Stage Build

```dockerfile
# apps/api/Dockerfile

FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

ENV PATH=/root/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Kubernetes Deployment (Advanced)

```yaml
# infra/k8s/api-deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: bioai-api
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: bioai-api
  template:
    metadata:
      labels:
        app: bioai-api
    spec:
      containers:
      - name: api
        image: bioai-nutrition/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secret
              key: key
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: bioai-api-service
spec:
  selector:
    app: bioai-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 3. GitHub Actions CI/CD

```yaml
# .github/workflows/deploy.yml

name: Build & Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd apps/api
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        cd apps/api
        pytest tests/ --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
  
  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t bioai-api:${{ github.sha }} apps/api/
        docker tag bioai-api:${{ github.sha }} bioai-api:latest
    
    - name: Push to registry
      run: |
        echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
        docker push bioai-api:latest
    
    - name: Deploy to production
      run: |
        kubectl set image deployment/bioai-api api=bioai-api:latest
```

---

## Performance Optimization

### 1. Database Query Optimization

```python
# Avoid N+1 queries with eager loading
user = db.query(User).options(
    selectinload(User.targets),
    selectinload(User.events)
).filter(User.id == user_id).first()

# Batch operations
db.bulk_insert_mappings(Event, [
    {'user_id': uid, 'event_type': 'diet', ...}
    for uid in user_ids
])
db.commit()

# Connection pooling
from sqlalchemy.pool import QueuePool
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
)
```

### 2. Caching Strategy

```python
# redis_cache.py
import redis
from functools import wraps
import json

redis_client = redis.Redis(host='localhost', port=6379)

def cache_recommendations(ttl=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(user_id: str, *args, **kwargs):
            cache_key = f"recommendations:{user_id}"
            cached = redis_client.get(cache_key)
            
            if cached:
                return json.loads(cached)
            
            result = await func(user_id, *args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

@cache_recommendations(ttl=3600)
async def get_recommendations(user_id: str) -> List[Dict]:
    # ... expensive computation
    pass
```

### 3. Async Request Handling

```python
# services/image_analyzer.py
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

async def batch_analyze_images(image_paths: List[str]):
    """Parallel image analysis."""
    loop = asyncio.get_event_loop()
    
    tasks = [
        loop.run_in_executor(executor, self._analyze_single, path)
        for path in image_paths
    ]
    
    results = await asyncio.gather(*tasks)
    return results
```

---

## Security Implementation

### 1. Authentication & Authorization

```python
# main.py - API Key + Optional OAuth2

from fastapi.security import OAuth2PasswordBearer, oauth2_scheme
from jose import JWTError, jwt
from datetime import datetime, timedelta

class AuthService:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    ALGORITHM = "HS256"
    
    @staticmethod
    def create_access_token(user_id: str, expires_in_hours: int = 24):
        expires = datetime.utcnow() + timedelta(hours=expires_in_hours)
        payload = {"sub": user_id, "exp": expires}
        return jwt.encode(payload, AuthService.SECRET_KEY, ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> str:
        try:
            payload = jwt.decode(token, AuthService.SECRET_KEY, algorithms=[AuthService.ALGORITHM])
            return payload["sub"]
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/protected")
async def protected_route(token: str = Depends(oauth2_scheme)):
    user_id = AuthService.verify_token(token)
    return {"user_id": user_id}
```

### 2. Data Encryption

```python
# encryption_service.py
from cryptography.fernet import Fernet

class EncryptionService:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt_sensitive_field(self, value: str) -> str:
        return self.cipher.encrypt(value.encode()).decode()
    
    def decrypt_sensitive_field(self, encrypted_value: str) -> str:
        return self.cipher.decrypt(encrypted_value.encode()).decode()

# Usage in models
class User(Base):
    email_encrypted = mapped_column(String)
    
    @property
    def email(self) -> str:
        return EncryptionService(KEY).decrypt_sensitive_field(self.email_encrypted)
```

---

## Summary Table

| Aspect | Technology | Implementation |
|--------|-----------|-----------------|
| **API Framework** | FastAPI | Async routes, dependency injection |
| **Database** | PostgreSQL + SQLAlchemy | ORM models, Alembic migrations |
| **ML Models** | XGBoost, YOLOv8 | MLflow tracking, Prefect pipelines |
| **Data Validation** | Great Expectations | Quality rules, drift detection |
| **Frontend** | Next.js + TypeScript | React components, API client |
| **Containerization** | Docker | Multi-stage builds |
| **Orchestration** | Kubernetes | Replicas, services, health checks |
| **CI/CD** | GitHub Actions | Test, build, deploy pipeline |
| **Caching** | Redis | Query result caching |
| **Security** | JWT + Encryption | Token-based auth, data encryption |

