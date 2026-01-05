-- events
CREATE TABLE IF NOT EXISTS events(
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  event_type TEXT NOT NULL,
  props JSONB DEFAULT '{}'::jsonb
);

-- daily_features
CREATE TABLE IF NOT EXISTS daily_features(
  user_id UUID NOT NULL,
  date DATE NOT NULL,
  kcal_avg NUMERIC,
  protein_g NUMERIC,
  fiber_g NUMERIC,
  late_meal_freq NUMERIC,
  steps NUMERIC,
  sleep_hours NUMERIC,
  sleep_regularity NUMERIC,
  ultra_processed_ratio NUMERIC,
  persona TEXT,
  PRIMARY KEY(user_id, date)
);

-- recommendations
CREATE TABLE IF NOT EXISTS recommendations(
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  date DATE NOT NULL,
  channel TEXT,
  content JSONB,
  rules_applied TEXT[],
  model_version TEXT,
  status TEXT,
  feedback JSONB
);
