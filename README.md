# 🚀 BioAI-Nutrition

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)

AI-driven wellness platform providing privacy-safe, personalized nutrition insights.  
Built with FastAPI, Next.js, and machine learning pipelines.

---

## 📋 Project Overview

**BioAI Nutrition** is a wellness assistant that analyzes lifestyle data such as meal patterns, activity, and sleep to generate personalized daily insights.  
It is **not a medical or diagnostic tool** — all recommendations are educational and intended to help users make sustainable, informed decisions.

**Core principles** ✨
- 🔒 Privacy-first data collection and storage
- 🔍 Transparent, rule-based explainable AI
- 🏗️ Modular architecture for iterative development
- 👥 Practical, user-centered recommendations

---

## 🛠️ Tech Stack

| Layer | Technologies |
|-------|---------------|
| Backend API | FastAPI · Python 3.11 · Pydantic · PostgreSQL |
| ML & Data Pipeline | Pandas · Polars · Scikit-learn · XGBoost · Great Expectations · Prefect |
| Frontend | Next.js · TypeScript · TailwindCSS · shadcn/ui |
| Infrastructure | Docker · GitHub Codespaces · GitHub Actions · Fly.io |
| Analytics & Logging | PostHog · MLflow · OpenTelemetry |

---

## 🏛️ Architecture

```
User → Frontend (Next.js)
     → FastAPI backend → Data layer (PostgreSQL / Parquet)
     → Feature pipeline (Prefect)
     → Recommendation engine (Rules + ML)
     → Output (Personalized daily nudges)
```

---

## 🔒 Privacy & Ethics

- 🚫 No health or diagnostic data is processed.
- 📚 All insights are educational and non-clinical.
- 🕵️ Personally identifiable information (PII) is minimized and pseudonymized.
- 🗂️ Data deletion and retention policies are transparent and user-controlled.
- 🛡️ The platform follows a **privacy-by-design** approach, reviewing data necessity for every new feature.

---

## 📝 Example Recommendation Rule

```yaml
id: fiber_boost_simple
when:
  daily_features.fiber_g: "< user_targets.fiber_g * 0.8"
then:
  message: "Try increasing fiber intake by 6–8g/day: add an apple and a handful of almonds."
  rationale: "Your 7-day average fiber intake is below target."
  guardrails: ["vegan/food-allergy aware", "non-diagnostic"]
```

---

## ⚙️ Development Setup

### Prerequisites
- 🐍 Python 3.11+
- 🌐 Node.js 18+
- 🐘 PostgreSQL (optional, for full setup)

### Option 1 – GitHub Codespaces (recommended) ☁️
Open this repository in [GitHub Codespaces](https://github.com/features/codespaces) to launch a preconfigured development environment.

### Option 2 – Local setup 🖥️

1. **📥 Clone the repository**
   ```bash
   git clone https://github.com/deokhwajeong/BioAI-Nutrition.git
   cd BioAI-Nutrition
   ```

2. **🔧 Backend (API) Setup**
   ```bash
   cd apps/api
   pip install -r requirements.txt
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Access FastAPI docs at → [http://localhost:8000/docs](http://localhost:8000/docs)

3. **🎨 Frontend (Web) Setup**
   ```bash
   cd apps/web
   npm install  # or pnpm install
   npm run dev  # or pnpm dev
   ```
   Access the web app at → [http://localhost:3000](http://localhost:3000)

4. **💾 Database Setup** (optional)
   - Install PostgreSQL
   - Run the schema: `psql -f data-contracts/schema.sql`

---

## 🧪 Testing

Run tests for the API:
```bash
cd apps/api
pytest tests/
```

Run tests for the web app:
```bash
cd apps/web
npm test  # or pnpm test
```

---

## 🗺️ Roadmap

- [x] Repository and environment setup
- [x] FastAPI skeleton
- [x] Data contracts (Events, Features, Recommendations)
- [x] Rule engine MVP
- [x] Frontend integration (Next.js)
- [ ] Closed user testing
- [ ] Analytics and A/B experimentation

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. 🍴 Fork the repository
2. 🌿 Create a feature branch: `git checkout -b feature/your-feature`
3. ✏️ Make your changes and add tests
4. ✅ Run tests: `pytest` or `npm test`
5. 💾 Commit your changes: `git commit -m 'Add some feature'`
6. 📤 Push to the branch: `git push origin feature/your-feature`
7. 🔄 Open a Pull Request

For major changes, please open an issue first to discuss what you would like to change.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](./LICENSE) file for details.  
© 2025 Deokhwa Jeong. All rights reserved.

---

## 👨‍💻 About

Developed by **Deokhwa Jeong**,  
Embedded & Software Engineer | Technical Project Manager | Bio-Engineering Professional.  

Focused on bridging **AI, engineering, and human wellness** through responsible technology.

---

## 🚀 Quickstart

For a quick start:
```bash
# Backend
cd apps/api && pip install -r requirements.txt && uvicorn app.main:app --reload

# Frontend
cd apps/web && npm install && npm run dev
# or with pnpm: pnpm install && pnpm dev
```

