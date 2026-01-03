BioAI‑Nutrition

BioAI‑Nutrition is a privacy‑first wellness assistant that transforms everyday lifestyle data (diet, activity, sleep) into non‑clinical, actionable insights. It's not a diagnostic or medical tool; instead it helps users make sustainable choices through data‑driven nudges.

Key Principles

Privacy by design – personal data is minimised, pseudonymised and stored securely. Users control retention and deletion.

Explainability – rule‑based recommendation engine with transparent rationale for every suggestion.

Modular architecture – FastAPI backend, machine‑learning pipeline, and (planned) Next.js frontend are decoupled for iterative development.

User empowerment – insights focus on education and lifestyle coaching, not prescriptions.

Tech Stack
Layer	Technologies
Backend API	FastAPI · Python 3.11 · Pydantic · PostgreSQL
ML & Data	Pandas · Polars · scikit‑learn · XGBoost · Great Expectations · Prefect
Frontend (planned)	Next.js · TypeScript · TailwindCSS · shadcn/ui
Infrastructure	Docker · GitHub Codespaces · GitHub Actions · Fly.io
Observability	PostHog · MLflow · OpenTelemetry
Architecture
User → Frontend (Next.js)
     → FastAPI backend → Data layer (PostgreSQL/Parquet)
     → Feature pipeline (Prefect)
     → Recommendation engine (rules + ML)
     → Output (personalised daily nudges)

Privacy & Ethics

No health or diagnostic data is processed.

Insights are educational only; they are not medical advice.

Personally identifiable information (PII) is minimised, pseudonymised, and encrypted at rest.

Users can delete their data or configure retention policies at any time.

New features undergo privacy reviews to justify data collection.

Quick Start

Choose one of the following setups:

Option 1 – Codespaces (recommended)

Opening the repo in GitHub Codespaces provides a pre‑configured environment with Python dependencies installed and the database running. Simply start the dev container and run:

uvicorn apps.api.app.main:app --reload


Visit http://localhost:8000/docs for the interactive API docs.

Option 2 – Local development

Clone the repo and install dependencies:

git clone https://github.com/deokhwajeong/BioAI-Nutrition.git
cd BioAI-Nutrition
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt


Then launch the API:

uvicorn apps.api.app.main:app --reload


By default the API runs on port 8000. If you change ports or environment variables, copy .env.example to .env and adjust settings accordingly.

Roadmap

 Repository and environment scaffolding

 FastAPI skeleton

 Define data contracts for events, features and recommendations

 Implement rule‑based recommendation engine MVP

 Integrate Next.js frontend

 Conduct closed beta testing and A/B experiments

See CONTRIBUTING.md
 for how to participate.

License

This project is licensed under the MIT License; see LICENSE
 for details.
© 2025 Deokhwa Jeong.

About

BioAI‑Nutrition is developed by Deokhwa Jeong, an embedded & software engineer and technical project manager with a background in bio‑engineering. The goal is to bridge AI, engineering and human wellness through responsible technology.
