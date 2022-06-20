# BioAI Nutrition — User Manual

> **Version:** 0.1.0
> **Date:** February 2026
> **Platform:** Web Application (Next.js + FastAPI)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Getting Started](#2-getting-started)
   - 2.1 [System Requirements](#21-system-requirements)
   - 2.2 [Installation & Startup](#22-installation--startup)
   - 2.3 [First Login](#23-first-login)
3. [Dashboard Tabs](#3-dashboard-tabs)
   - 3.1 [BioSync Pipeline](#31-biosync-pipeline)
   - 3.2 [Privacy & Consent](#32-privacy--consent)
   - 3.3 [Genetic Profile](#33-genetic-profile)
   - 3.4 [Meal Analysis](#34-meal-analysis)
   - 3.5 [Food Image AI](#35-food-image-ai)
   - 3.6 [Synthea FHIR](#36-synthea-fhir)
4. [Metrics Dashboard](#4-metrics-dashboard)
5. [Account Settings](#5-account-settings)
6. [API Reference Quick Guide](#6-api-reference-quick-guide)
7. [Demo Scenario Walkthrough](#7-demo-scenario-walkthrough)
8. [Troubleshooting](#8-troubleshooting)
9. [Security & Privacy](#9-security--privacy)
10. [Glossary](#10-glossary)

---

## 1. Overview

BioAI Nutrition is an AI-powered personalized nutrition recommendation platform that integrates data from multiple biomarker sources (CGM, wearables, genetic tests) to provide scientifically-grounded dietary guidance.

### Key Features

| Feature | Description |
|---------|-------------|
| **7-Stage BioSync Pipeline** | Consent → Temporal Sync → Normalization → Interpolation → Metabolic State → Nutrient Calc → DP Noise (with Stage 4.5 Re-Normalization) |
| **Genetic Nutrigenomics** | 8 SNP variant analysis for personalized metabolic modifiers |
| **Multi-Source Sensor Fusion** | 5 adapters: CGM (glucose), Activity (HR/HRV/steps), Sleep, Genetic (SNP), Location (GPS/geofence) |
| **14-Phase Metabolic Classifier** | Real-time composite metabolic state: 4 dietary + 4 exercise + 3 sleep + 3 stress/recovery phases (simultaneous Multi-phase activation) |
| **Personalized Nutrient Budget** | 14+ nutrient targets adapted to genetics, circadian rhythm, and metabolic state with hierarchical conflict resolution (6 priority levels) |
| **Dynamic Differential Privacy** | 4-tier dynamic ε-differential privacy (ε = 0.1–0.8), on-device edge processing, TEE/Secure Enclave, Privacy Exposure Index (PEI) tracking |
| **Meal Analysis** | Text-based and image-based food nutrition analysis (100+ foods including Korean cuisine) |
| **Synthea FHIR Integration** | Import synthetic patient data in HL7 FHIR R4 format with LOINC/UCUM mapping |

### Architecture Overview

```
┌─────────────────────┐     ┌──────────────────────┐
│   Web Frontend      │────▶│   FastAPI Backend     │
│   (Next.js)         │     │   (Python)            │
│   Port 3000         │     │   Port 8000           │
└─────────────────────┘     └──────────────────────┘
         │                           │
         │    Proxy via rewrites     │
         └───────────────────────────┘
                    │
    ┌───────┬───────┼───────┬──────────┐
    │       │       │       │          │
┌───▼──┐ ┌──▼───┐ ┌─▼────┐ ┌▼───────┐ ┌▼────────┐
│ CGM  │ │ Act. │ │Sleep │ │Genetic │ │Location │
│Adapt.│ │Adapt.│ │Adapt.│ │Adapt.  │ │Adapt.   │
└──────┘ └──────┘ └──────┘ └────────┘ └─────────┘
              │
    ┌─────────▼──────────────────────────────────┐
    │ 7-Stage Engine Pipeline (Stage 0 → 6)      │
    │ Consent → Sync → Norm → Interp → Metabolic │
    │ → Re-Norm → Nutrient → DP Noise            │
    └────────────────────────────────────────────┘
```

> **Note:** The Web UI displays a simplified 6-step view (Consent → Genetic → Ingest → Sync → Metabolic → Nutrient). The underlying engine executes a 7-stage pipeline (Stage 0–6) with Stage 4.5 Re-Normalization.

---

## 2. Getting Started

### 2.1 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Linux, macOS, Windows (WSL) | Ubuntu 22.04+ |
| **Python** | 3.11 | 3.12 |
| **Node.js** | 18 | 20+ |
| **RAM** | 2 GB | 4 GB |
| **Disk** | 500 MB | 1 GB |

### 2.2 Installation & Startup

#### Step 1: Clone the Repository

```bash
git clone https://github.com/deokhwajeong/BioAI-Nutrition.git
cd BioAI-Nutrition
```

#### Step 2: Set Up Python Environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
```

#### Step 3: Start the API Server

```bash
uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API server starts with **72 hours of pre-seeded demo data** automatically loaded.

#### Step 4: Start the Web Frontend

```bash
cd apps/web
pnpm install
pnpm dev --port 3000
```

#### Step 5: Open the Application

Navigate to **http://localhost:3000** in your browser.

### 2.3 First Login

No authentication is required for the demo. The application uses a pre-configured demo user (`demo-user-001`) with seeded biomarker data.

---

## 3. Dashboard Tabs

The main page features 6 tabs across the top navigation bar. Each tab corresponds to a major feature of the platform.

### 3.1 BioSync Pipeline

**Icon:** 🧬 | **Path:** Main page → "BioSync Pipeline" tab

This is the core feature that runs the full personalized nutrition pipeline.

#### How to Use

1. Click the **"Run Full Pipeline"** button
2. Watch the 6-step UI pipeline execute sequentially:

| UI Step | Name | What It Does |
|---------|------|-------------|
| 1 | **Privacy Consent** | Grants data access scopes under ε-differential privacy (14 consent categories) |
| 2 | **Genetic Profile** | Submits 8 SNP variants and computes metabolic modifiers (γ_genetic) |
| 3 | **Biomarker Ingest** | Ingests real-time sensor data from 5 adapters (CGM, Activity, Sleep, Genetic, Location) |
| 4 | **Temporal Sync** | Aligns multi-resolution data using Dynamic Physiological Lag Model (t_sync = t_event + Δt × γ × φ) |
| 5 | **Metabolic State** | Classifies current metabolic phase (14 simultaneous phases across 4 categories) |
| 6 | **Nutrient Calc** | Computes personalized nutrient budget with genetic modifiers + hierarchical conflict resolution |

> **Engine Detail:** Internally, the engine runs a 7-stage pipeline (Stage 0: Consent → Stage 1: Temporal Sync → Stage 2: Normalization → Stage 3: Interpolation → Stage 4: Metabolic State → Stage 4.5: Re-Normalization → Stage 5: Nutrient Calc → Stage 6: DP Noise). The UI consolidates these into 6 visible steps.

3. After completion, view:
   - **Metabolic State Card**: Shows current phase (e.g., "postprandial_early"), confidence score, glucose and heart rate means
   - **Nutrient Budget Panel**: Visual bars showing remaining daily targets for calories, protein, carbs, fat, fiber, and water

#### Understanding the Metabolic State Card

The 14 metabolic phases across 4 categories (multiple phases can be active simultaneously):

**Dietary Phases (4)**

| Phase | Description | Trigger |
|-------|-------------|--------|
| `postprandial_early` | Early post-meal glucose absorption | 0–2 hours after eating |
| `postprandial_late` | Late post-meal insulin-driven uptake | 2–4 hours after eating |
| `post_absorptive` | Transitioning to fat oxidation | 4–12 hours after eating |
| `fasting` | Extended fasting, gluconeogenesis active | ≥12 hours without food |

**Exercise Phases (4)**

| Phase | Description | Trigger |
|-------|-------------|--------|
| `pre_exercise` | Sympathetic nervous system activation | Before planned workout (extension point) |
| `during_exercise` | Elevated HR, glucose consumption | Heart rate > 100 bpm |
| `recovery_immediate` | EPOC (excess post-exercise O₂) | 0–2 hours after exercise |
| `recovery_delayed` | Glycogen replenishment | 2–48 hours after high/extreme intensity |

**Sleep Phases (3)**

| Phase | Description | Trigger |
|-------|-------------|--------|
| `pre_sleep` | Melatonin onset, HR declining | 1–2 hours before typical bedtime |
| `sleeping` | Parasympathetic dominance | Step count < 5 (inactive) |
| `post_waking` | Cortisol awakening response | 0–1 hour after waking |

**Stress / Recovery Phases (3)**

| Phase | Description | Trigger |
|-------|-------------|--------|
| `metabolic_stress` | Elevated cortisol indicators | HRV < 30 ms |
| `recovery` | High parasympathetic recovery | HRV > 60 ms |
| `circadian_low` | Minimum metabolic rate | Circadian nadir (extension point) |

> **Composite State:** Multiple phases from different categories can be simultaneously active (e.g., `fasting` + `sleeping` + `recovery`). Each phase contributes multiplicative nutrient priority modifiers.

#### Understanding the Nutrient Budget Panel

The nutrient budget shows progress bars for each target nutrient:

- **Green bar**: Consumed today
- **Remaining area**: What you still need
- Each target is adjusted based on:
  - Genetic modifiers (e.g., MTHFR → higher folate needs)
  - Current metabolic state (e.g., recovery → more protein)
  - Circadian rhythm (morning vs evening recommendations)

### 3.2 Privacy & Consent

**Icon:** 🔐 | **Path:** Main page → "Privacy & Consent" tab

Manage which types of data the system can access and process.

#### Available Scopes

| Scope | Data Type | Description |
|-------|-----------|-------------|
| `glucose_data` | CGM readings | Continuous glucose monitor values |
| `activity_data` | Steps, exercise | Physical activity metrics |
| `sleep_data` | Sleep sessions | Duration, quality, stages |
| `heart_rate_data` | HR, HRV | Heart rate and variability |
| `genetic_data` | SNP variants | Genetic test results |
| `weight_data` | Body weight | Weight measurements |
| `blood_test_data` | Lab results | Blood chemistry panels |
| `meal_data` | Food logs | Meal entries and nutrition |
| `water_data` | Hydration | Water intake tracking |
| `medication_data` | Prescriptions | Current medications |
| `location_data` | GPS | Location-based context |
| `third_party_data` | External apps | Connected app data |
| `research_data` | Research use | Anonymized research sharing |
| `model_training` | AI training | Model improvement data |

#### How to Use

1. Toggle each scope ON/OFF using the switch controls
2. The system respects these settings during pipeline execution
3. Revoking a scope immediately removes that data type from processing
4. The **ε-differential privacy budget meter** shows cumulative privacy cost

#### Privacy Guarantees

- **Dynamic ε-differential privacy** with 4 sensitivity tiers:
  - **CRITICAL** (ε = 0.1): Genetic data, rare medical conditions
  - **HIGH** (ε = 0.3): Glucose, blood tests, medications
  - **MEDIUM** (ε = 0.5): Heart rate, HRV, sleep patterns
  - **LOW** (ε = 0.8): Steps, exercise, general activity
- **Privacy Exposure Index (PEI)**: Real-time tracking of cumulative privacy budget consumption (0.0–1.0)
- Daily budget reset: ε_total = 1.0, δ = 10⁻⁵ per 24-hour cycle
- Raw data is **never transmitted** to the server (on-device edge processing with TEE/Secure Enclave)
- Only non-invertible feature embeddings (64-dim) are transmitted
- Genetic data: only SHA-256 hashes are sent, never raw alleles
- Hardware-enforced cryptographic privacy boundary between edge device and cloud

### 3.3 Genetic Profile

**Icon:** 🧬 | **Path:** Main page → "Genetic Profile" tab

Submit genetic test results for personalized metabolic analysis.

#### Supported SNP Variants

| SNP ID | Gene | Function | Genotype Options |
|--------|------|----------|-----------------|
| rs1801133 | **MTHFR** | Folate metabolism | CC, CT, TT |
| rs9939609 | **FTO** | Obesity risk/satiety | TT, TA, AA |
| rs429358 | **APOE** | Lipid metabolism | TT, TC, CC |
| rs7903146 | **TCF7L2** | Glucose response | CC, CT, TT |
| rs4988235 | **LCT** | Lactase persistence | GG, GA, AA |
| rs762551 | **CYP1A2** | Caffeine metabolism | AA, AC, CC |
| rs1544410 | **VDR** | Vitamin D receptor | GG, GA, AA |
| rs4341 | **ACE** | Blood pressure | DD, ID, II |

#### How to Use

1. Select your genotype for each SNP variant from the dropdowns
2. Click **"Compute Modifiers"**
3. View the computed metabolic modifiers:
   - Values > 1.0 = **increased** need (↑)
   - Values < 1.0 = **decreased** need (↓)
   - Values = 1.0 = **no change** (—)

#### Example Modifiers

For a user with MTHFR CT + FTO TA + TCF7L2 CT:

| Modifier | Value | Impact |
|----------|-------|--------|
| `folate_requirement_modifier` | 1.25 | +25% folate needed |
| `calorie_sensitivity_modifier` | 1.10 | 10% lower calorie target |
| `glucose_lag_modifier` | 1.12 | 12% slower glucose clearance |
| `caffeine_metabolism_modifier` | 0.50 | Slow caffeine metabolizer |

### 3.4 Meal Analysis

**Icon:** 🍽️ | **Path:** Main page → "Meal Analysis" tab

Analyze food items by entering them as text.

#### How to Use

1. Type food items in the text input (comma-separated)
   - Example: `chicken breast, brown rice, broccoli`
2. Click **"Analyze"**
3. View per-item and total nutritional breakdown:
   - Calories (kcal)
   - Protein (g)
   - Carbohydrates (g)
   - Fat (g)

#### Supported Foods (100+ items)

The database includes:

- **Proteins**: chicken breast, salmon, tuna, beef, tofu, eggs, shrimp, turkey
- **Grains**: rice, brown rice, quinoa, oatmeal, pasta, bread
- **Vegetables**: broccoli, spinach, kale, carrots, tomatoes, bell peppers
- **Fruits**: apple, banana, avocado, blueberries, mango
- **Dairy**: yogurt, greek yogurt, milk, cheese
- **Legumes**: lentils, chickpeas, black beans, almonds, walnuts
- **Prepared meals**: pizza, sushi, ramen, curry, burrito, sandwich
- **Korean foods**: bibimbap, kimchi, bulgogi, japchae, doenjang jjigae, tteokbokki, gimbap, samgyeopsal, sundubu jjigae, kimchi jjigae

### 3.5 Food Image AI

**Icon:** 📸 | **Path:** Main page → "Food Image AI" tab

Upload or capture a photo of your meal for AI-powered nutrition analysis.

#### How to Use

1. Click **"Upload Image"** or use the camera capture button
2. Select a food photo (JPG, PNG)
3. The AI analyzes the image using:
   - OCR text detection (for packaged foods with labels)
   - Color histogram analysis (for identifying food types)
   - Pattern matching against the nutrition database
4. View estimated nutritional breakdown

#### Tips for Best Results

- Take photos in good lighting
- Capture the full plate/meal
- For packaged foods, include the nutrition label
- Single items work better than complex mixed dishes

### 3.6 Synthea FHIR

**Icon:** 🏥 | **Path:** Main page → "Synthea FHIR" tab

Explore and import synthetic patient data in HL7 FHIR R4 format.

#### How to Use

1. Browse the list of available synthetic patients
2. Click on a patient to view their details:
   - Demographics (age, gender)
   - Diagnoses/Conditions
   - Medications
   - Biomarker observations
3. Click **"Load into Engine"** to import patient data into the BioSync pipeline

#### FHIR → BioAI Mapping

The system automatically maps 30+ LOINC observation codes to BioAI biomarker types:

| LOINC Code | Biomarker | Unit |
|-----------|-----------|------|
| 2339-0 | Glucose | mg/dL |
| 8867-4 | Heart Rate | bpm |
| 29463-7 | Weight | kg |
| 8480-6 | Blood Pressure (Systolic) | mmHg |
| 718-7 | Hemoglobin | g/dL |
| 2093-3 | Total Cholesterol | mg/dL |

---

## 4. Metrics Dashboard

**Path:** `/dashboard`

The metrics dashboard provides an aggregated overview of your health data.

#### Displayed Metrics

| Metric | Source | Display |
|--------|--------|---------|
| **Calories** | Diet events | Total consumed today |
| **Steps** | Activity events | Daily step count |
| **Sleep** | Sleep events | Duration (hours) |
| **Fiber** | Diet analysis | Grams consumed |

The dashboard also features a **Neural Network Graph** visualization showing the AI processing flow from raw biomarker data through the pipeline to personalized recommendations.

---

## 5. Account Settings

**Path:** `/account`

- **Email Settings**: Update your notification email
- **Notification Preferences**: Toggle push/email notifications
- **Data Export**: Download all your data (JSON format)
- **Data Deletion**: Request complete data erasure (GDPR "Right to be Forgotten")

---

## 6. API Reference Quick Guide

All API endpoints require the `X-API-Key` header. Default key: `dev-api-key`

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/engine/status` | Pipeline status overview |
| `POST` | `/engine/consent` | Grant/revoke data consent |
| `POST` | `/engine/genetic-profile` | Submit genetic SNP data |
| `POST` | `/engine/ingest` | Ingest biomarker readings |
| `POST` | `/engine/sync` | Temporal synchronization |
| `POST` | `/engine/metabolic-state` | Metabolic state estimation |
| `POST` | `/engine/nutrient-budget` | Nutrient demand calculation |
| `POST` | `/analyze-meal` | Text-based meal analysis |
| `POST` | `/image-analyze/upload` | Image-based food analysis |
| `POST` | `/engine/medical-constraints` | Set medical safety limits |
| `GET` | `/engine/edge-manifest` | On-device privacy manifest |
| `GET` | `/synthea/status` | List available FHIR patients |
| `POST` | `/synthea/load` | Load patient into engine |

### Interactive API Docs

Visit **http://localhost:8000/docs** for the full Swagger UI with:
- Request/response schema documentation
- Try-it-out functionality for every endpoint
- Automatic parameter validation

### Example: cURL — Analyze a Meal

```bash
curl -X POST http://localhost:8000/analyze-meal \
  -H "X-API-Key: dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"name": "salmon"}, {"name": "brown rice"}, {"name": "broccoli"}]}'
```

### Example: cURL — Run Nutrient Budget

```bash
curl -X POST http://localhost:8000/engine/nutrient-budget \
  -H "X-API-Key: dev-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo-user-001",
    "kcal_target": 2200,
    "weight_kg": 75.0,
    "consumed_today": {
      "kcal": 850, "protein_g": 35, "carbs_g": 110,
      "fat_g": 28, "fiber_g": 8, "water_ml": 1200
    }
  }'
```

---

## 7. Demo Scenario Walkthrough

A complete automated demo script is provided: `scripts/run_demo.py`

### Running the Demo

```bash
python scripts/run_demo.py
```

### What the Demo Does

| Step | Action | Expected Result |
|------|--------|----------------|
| 1 | Health check | `{"status": "ok"}` |
| 2 | Grant 8 consent scopes | All scopes active |
| 3 | Submit 8 SNP variants | Metabolic modifiers computed |
| 4 | Ingest 100 biomarker readings | CGM + HR + HRV + Steps |
| 5 | Temporal synchronization | 36 time frames aligned |
| 6 | Metabolic state estimation | Phase classified with confidence |
| 7 | Nutrient demand calculation | 14+ personalized nutrient targets |
| 8 | Analyze 3 meals | Lunch, Dinner, Korean meal |
| 9 | Set medical constraints | Sodium, potassium, sugar limits |
| 10 | Explore Synthea patients | FHIR patient data |
| 11 | Engine status summary | Active sources and users |
| 12 | Edge privacy manifest | On-device processing details |

### Demo Output Files

| File | Description |
|------|-------------|
| `output/demo_results.json` | All API responses in JSON format |
| `output/demo_transcript.txt` | Human-readable full transcript |

### Step-by-Step UI Walkthrough

To demonstrate the web UI manually:

1. **Open** http://localhost:3000
2. **Pipeline Tab**: Click "Run Full Pipeline" → Watch all 6 stages light up green
3. **Privacy Tab**: Show the 14 consent toggles and ε-privacy budget meter
4. **Genetic Tab**: Select genotypes for 8 SNPs → Click "Compute Modifiers"
5. **Meal Tab**: Type "salmon, quinoa, spinach" → Click Analyze → Show nutrition breakdown
6. **Image Tab**: Upload a food photo → Show AI analysis results
7. **Synthea Tab**: Browse synthetic patients → Load one into the engine
8. **Dashboard** (/dashboard): Show aggregated metrics and neural network visualization

---

## 8. Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| **API returns 401** | Missing or wrong API key | Add header `X-API-Key: dev-api-key` |
| **Web app shows blank** | Backend not running | Start API: `uvicorn apps.api.app.main:app --port 8000` |
| **Pipeline stage fails** | Missing consent | Grant scopes first in Privacy tab |
| **No Synthea patients** | FHIR data not loaded | Check `data/synthea/output/fhir/` directory |
| **Meal not recognized** | Food not in database | Use common English food names |
| **Port 3000 in use** | Another process | Run `lsof -i :3000` to find and kill it |
| **Port 8000 in use** | Another process | Run `lsof -i :8000` to find and kill it |

### Checking Service Health

```bash
# API server
curl http://localhost:8000/

# Web frontend
curl -o /dev/null -w "%{http_code}" http://localhost:3000/

# Engine status
curl -H "X-API-Key: dev-api-key" http://localhost:8000/engine/status
```

### Viewing Logs

- **API server logs**: Visible in the terminal running `uvicorn`
- **Web frontend logs**: Visible in the terminal running `pnpm dev`
- **Browser console**: Open DevTools (F12) → Console tab

---

## 9. Security & Privacy

### Data Protection

| Layer | Protection |
|-------|------------|
| **Transport** | HTTPS in production (TLS 1.3) |
| **Authentication** | API key header (`X-API-Key`) |
| **Consent** | Per-scope opt-in (GDPR Article 7) |
| **Privacy** | 4-tier dynamic ε-differential privacy (Laplace/Gaussian noise) with PEI tracking |
| **Edge Computing** | Raw data stays on-device |
| **Genetic Data** | SHA-256 hash only; never transmitted raw |
| **PII Filtering** | Structured log scrubbing for personal data |

### On-Device Processing Architecture

The BioAI edge manifest defines what stays on your device:

**Processed on-device (never transmitted):**
- Raw glucose readings (mg/dL time series)
- Raw heart rate/HRV readings
- Raw step counts
- Raw sleep stages
- Raw genotypes (rsid → allele mappings)
- Raw meal logs
- Personal baseline history

**Transmitted (privacy-preserved):**
- Feature embedding (64-dim, non-invertible)
- DP-aggregated summary statistics (ε-noisy)
- Metabolic label (categorical only)
- Confidence scores (no raw values)
- Genetic modifier hash (SHA-256)

---

## 10. Glossary

| Term | Definition |
|------|------------|
| **BioSync Pipeline** | The 7-stage data processing pipeline (Stage 0–6 + Stage 4.5) from raw biomarkers to personalized nutrition |
| **Biomarker** | A measurable indicator of biological state (glucose, heart rate, HRV, etc.) |
| **CGM** | Continuous Glucose Monitor — a device worn on the body that measures blood glucose every 5 minutes |
| **Circadian Rhythm** | The ~24-hour biological cycle affecting metabolism, hormone levels, and sleep |
| **Differential Privacy (DP)** | A mathematical framework (ε-privacy) that adds calibrated noise to data to protect individual privacy. BioAI uses 4-tier dynamic epsilon (0.1–0.8) with Privacy Exposure Index (PEI) tracking and 24-hour budget reset |
| **FHIR** | Fast Healthcare Interoperability Resources — a standard for exchanging healthcare data electronically |
| **Genotype** | The specific allele combination at a given genetic locus (e.g., CT for heterozygous) |
| **HRV** | Heart Rate Variability — variation in time between heartbeats, indicating autonomic nervous system health |
| **LOINC** | Logical Observation Identifiers Names and Codes — a universal standard for identifying medical lab observations |
| **Metabolic Phase** | One of 14 classified states of metabolism across 4 categories (dietary, exercise, sleep, stress/recovery); multiple phases can be simultaneously active |
| **Nutrient Budget** | Personalized daily nutrition targets adjusted for genetics, metabolic state, circadian rhythm, and hierarchical conflict resolution (6 priority levels) |
| **Nutrigenomics** | The study of how genetic variation affects nutritional requirements and metabolism |
| **SNP** | Single Nucleotide Polymorphism — a single base-pair variation in DNA that may affect protein function |
| **Synthea** | An open-source synthetic patient data generator producing realistic FHIR bundles |
| **TCF7L2** | A gene strongly associated with type 2 diabetes risk; variants affect glucose clearance rate |
| **Temporal Synchronization** | The process of aligning multi-source biomarker readings to a unified time grid using the Dynamic Physiological Lag Model (t_sync = t_event + Δt_base × γ_genetic × φ_circadian) |
| **Circadian Lag Modifier (φ)** | A 24-hour lookup value (0.82–1.20) representing time-of-day metabolic efficiency; 0.82 at 08:00 (fastest response), 1.20 at 02:00 (slowest response) |
| **Self-Calibration** | Adaptive feedback loop with 3 correction channels (δ_base, κ_genetic, δ_circ) that learns from detected peak events to improve lag prediction accuracy over time |
| **Edge Computing** | On-device processing architecture where raw biomarker data stays on the user's device (TEE/Secure Enclave); only privacy-protected embeddings cross the network boundary |
| **PEI (Privacy Exposure Index)** | A real-time metric (0.0–1.0) tracking cumulative differential privacy budget consumption; resets every 24 hours |
| **Conflict Resolution** | Hierarchical system with 6 priority levels (0: Base RDA → 5: Medical Critical) that resolves contradictions between genetic, biomarker, and medical recommendations |

---

*© 2026 BioAI Nutrition. All rights reserved.*
