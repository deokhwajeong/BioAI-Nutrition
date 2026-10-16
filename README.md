# Nutri-Node

[![CI](https://github.com/deokhwajeong/BioAI-Nutrition/actions/workflows/ci.yml/badge.svg)](https://github.com/deokhwajeong/BioAI-Nutrition/actions/workflows/ci.yml)
![Python 3.13](https://img.shields.io/badge/python-3.13-blue)
![Next.js 16](https://img.shields.io/badge/Next.js-16-black)

Nutri-Node is a research prototype that turns wearable and lab signals into a daily nutrient plan. The hard part is timing: a glucose monitor shows a meal 10 to 20 minutes after it happens, heart rate reacts in seconds, and sleep arrives once a day, so joining the streams by clock time pairs the wrong events. Nutri-Node shifts each signal by its expected delay first, then estimates the body's current state (fasting, after a meal, exercise recovery, sleep, and so on), sets daily nutrient targets in which medical limits always override genetic adjustments, turns a logged day into plain suggestions using readable YAML rules, and builds a week of meals from those targets. Consent checks and differential privacy run inside the pipeline, and per-user accounts can store profiles, consent, and logged days, view their trends, and erase everything. It is a FastAPI service plus a Next.js dashboard, runs on synthetic data only, and makes no clinical claims.

![Pipeline run](docs/screenshots/pipeline-run.png)

> Educational and research prototype. Not a medical device and not medical advice. All data in this repository is synthetic.

## Live demo

**[deokhwajeong.github.io/demos/nutri-node](https://deokhwajeong.github.io/demos/nutri-node/)** runs the real dashboard in the browser with no API server. Every response it shows was captured from this API running on the repository's synthetic data: the full pipeline run, the rule-based suggestions, the weekly meal plan (with and without a sample protein limit), the four-week trends view, all scored genotype combinations on the Genetic Profile tab, the meal analyzer's food table, the image analyzer's colour heuristics, and the five Synthea patients. Free-text meals and uploaded images are matched to the nearest precomputed result.

To rebuild it: `make demo` writes a static export to `apps/web/out/` (served under `/demos/nutri-node`). After engine changes, start the API with `make demo-api` (repo root, fixed `DP_SEED` so the privacy noise in the published numbers is reproducible) and run `make demo-fixtures` in a second terminal to recapture `apps/web/lib/demo-fixtures.json`.

## Quickstart

```bash
docker compose up --build        # API on :8000, web on :3000
```

Open http://localhost:3000 and press **Run full pipeline**. Interactive API docs are at http://localhost:8000/docs (send `X-API-Key: dev-api-key`).

Without Docker (needs [uv](https://docs.astral.sh/uv/) and pnpm):

```bash
make setup
make api      # terminal 1
make web      # terminal 2
```

## How it works

```mermaid
flowchart LR
    subgraph Sources
        CGM[CGM glucose]
        HR[Heart rate / HRV]
        ACT[Steps / exercise]
        SLP[Sleep]
        GEN[Genotype SNPs]
    end
    Sources --> C[0. Consent filter]
    C --> S[1. Temporal sync<br/>lag-compensated]
    S --> N[2. Normalization<br/>genotype-aware]
    N --> I[3. Circadian<br/>interpolation]
    I --> M[4. Metabolic state<br/>14-phase classifier]
    M --> B[5. Nutrient budget<br/>safety-first conflicts]
    B --> P[6. Differential<br/>privacy noise]
    B --> R[7. Suggestions<br/>rules/*.yaml]
    P --> UI[Next.js dashboard]
    R --> UI
```

| Stage | What it does | Code |
|---|---|---|
| Consent filter | Drops any signal whose scope the user has not granted, before it reaches computation | `app/privacy/consent_manager.py` |
| Temporal sync | Shifts each reading by `t_sync = t_event + Δt_base(b) × γ_genetic × φ_circadian`, then aligns into fine / medium / coarse frames | `app/engine/temporal_sync.py` |
| Normalization | Z-scores against personal, then genetic, then population baselines | `app/engine/normalization.py` |
| Interpolation | Fills sensor gaps from circadian and ultradian rhythm models, blending toward real data as it arrives | `app/engine/interpolation.py` |
| Metabolic state | Classifies 14 phases (fasting, post-prandial, exercise recovery, sleep, stress, ...) with intensities | `app/engine/metabolic_state.py` |
| Nutrient budget | Daily targets adjusted by phase and genotype. Stacked adjustments are bounded (0.75x to 1.25x of base for energy, macros, and water; 0.5x to 2x for micronutrients) and protein is kept within 0.8 to 2.0 g/kg/day: the adult RDA (Institute of Medicine DRI, 2005) up to the top of the range for exercising adults (Jager et al., ISSN position stand on protein and exercise, JISSN 14:20, 2017). Medical limits are applied after these bounds and always win, with an audit record | `app/engine/nutrient_calculator.py` |
| Privacy noise | Laplace noise on every released target, with ε by data sensitivity (0.1 for genetics-derived nutrients up to 0.8 for general macros). Sensitivity is one small, actionable unit per nutrient (16 kcal, 4 g carbs, 2 g protein, 1% of the reference intake for micronutrients), which gives metric privacy in the sense of geo-indistinguishability: targets that differ by k units are indistinguishable up to e^(kε). Typical noise is about 53 kcal and 2.5 g protein. One release costs ε 6.2 of a daily budget of 8; repeat runs on the same inputs re-release the earlier noisy value for free. Bounds and medical limits are applied after the noise | `app/privacy/differential_privacy.py`, `app/engine/pipeline.py` |
| Meal plan | `POST /meal-plan` builds up to 7 days of breakfast, lunch, dinner, and snack from the food table. Medical limits are applied to the targets first, half-serving portions are fitted by local search, and a final pass cuts portions until every medical ceiling holds. Limits on nutrients the table does not track (sodium, ...) are reported, not ignored | `app/services/meal_planner.py` |
| Accounts | `POST /auth/register` and `/auth/login` issue opaque bearer tokens (only a SHA-256 digest is stored; passwords use salted scrypt). `/users/me` covers profile, consent (mirrored into the engine's consent gate), logged days, and trends. `DELETE /users/{id}` erases the account, every row keyed to it, and the engine's in-memory state for that user | `app/routes/`, `app/services/accounts.py` |
| Trends | `GET /analytics/sample` and `/users/me/analytics`: 7-day rolling means, weekly slope, first versus last week, goal adherence, and which rules fired per day | `app/services/analytics.py` |
| Suggestions | `POST /recommendations` evaluates the YAML rules in `rules/` against a logged day and the user's targets. Rules are validated at load (every condition must parse, every rule must carry the `non-diagnostic` guardrail) and conditions are parsed, never `eval`ed | `app/services/recommendations.py` |

## What is real vs simulated

| Real: computed by code in this repository | Simulated or synthetic |
|---|---|
| Consent gating, lag-compensated alignment, normalization, gap filling | Every sensor reading: 72 h of seeded synthetic data plus readings the dashboard generates |
| Metabolic state estimation (rule-based over aligned signals) and the nutrient target calculator, including medical-limit overrides and their audit trail | Genotypes, and the delay and genetic factors themselves: literature-inspired defaults, not yet validated on real CGM data (see roadmap) |
| Differential privacy mechanisms and per-sensitivity budgets | The "on-device" boundary: edge processing runs in the same server process to show what would stay local |
| YAML rule engine behind `/recommendations` | Synthea patients are fictional records from the open-source Synthea simulator |
| Weekly meal planner, including medical limits as hard ceilings | The food table: typical-serving values for about 90 foods, not a full nutrient database |
| Accounts, tokens, per-user consent and logs, and deletion, with isolation tests | Trends tab: 28 generated days of a fictional user (fixed seed) |
| Trend statistics and per-day rule hits | Glucose-response model: trained and scored on simulated meals only (see below) |
| Meal text lookup against the built-in nutrition table | Food photos: colour-histogram heuristics (optional OCR), not a trained vision model |
| OpenAPI contract between API and web client | Meal check glucose curve: a simple in-browser model for illustration; lag view scatter dots are drawn to match the API's correlation value |
| | Static demo: responses captured from the real API, replayed in the browser |

No result here has been clinically validated, and nothing in the app is medical advice.

### Gradient-boosting demonstration (synthetic data only)

`make ml-eval` trains a `HistGradientBoostingRegressor` to predict the post-meal glucose rise from meal macros, time of day, sleep, recent exercise, a risk-allele count, and fasting glucose, and compares it with carb counting on people held out from training ([report](output/glycemic_model_eval.md)). The data comes from a simulator in `apps/api/ml/glycemic_response.py` that encodes those effects by hand, so the model can only rediscover what was written into it (R² 0.70 against 0.53 for carb counting on the simulated test people). It shows the training and evaluation workflow, nothing about accuracy on real people, and the API does not use it. scikit-learn is a development dependency only, and no model file is stored.

Deeper detail: [technical whitepaper](docs/whitepaper.md) · [user manual](docs/user-manual.md) · [provisional patent application](docs/patent/provisional-application.md).

## Meal plan and trends

| Meal plan | Trends |
|---|---|
| ![Meal plan tab](docs/screenshots/meal-plan.png) | ![Trends tab](docs/screenshots/trends.png) |

The dashboard runs as one synthetic demo user, so the account endpoints are API-only (see `/docs`). The engine endpoints under `/engine` still take a `user_id` behind the shared API key; only `/users/*` is scoped by token.

## Repository layout

```
apps/api/        FastAPI service (uv, ruff, pytest)
  app/engine/      pipeline stages
  app/privacy/     consent, differential privacy, edge processing
  app/routers/     HTTP endpoints
  ml/              synthetic glucose-response model (dev-only, not used by the API)
  tests/           266 tests
apps/web/        Next.js 16 + React 19 dashboard
  lib/api.ts       typed client; lib/api-schema.d.ts is generated from the API's OpenAPI spec
rules/           YAML suggestion rules served by POST /recommendations
data/            synthetic Synthea FHIR fixtures
docs/            whitepaper, user manual, screenshots
```

## Engineering notes

- **One contract, enforced.** The web client's types are generated from FastAPI's OpenAPI spec (`make gen-api`). CI regenerates them and fails if they drift, so the frontend cannot silently fall out of sync with the API.
- **Checks on every push:** ruff lint and format, 266 API tests with coverage (81%), TypeScript strict typecheck, ESLint, production build, and both Docker images.
- **Security defaults:** every endpoint requires `X-API-Key`; per-user routes also need a bearer token and only ever reach the token's own account; strict Content-Security-Policy with same-origin API calls through Next.js rewrites; PII filter on all log records; pseudonymous user IDs hashed with a server-side pepper; CORS credentials only with explicit origins; dependency updates via Dependabot.
- **Runs anywhere:** SQLite by default (`DATABASE_URL` for Postgres); Celery tasks run inline unless `CELERY_BROKER_URL` is set; OCR is an optional extra (`uv sync --extra ocr`).

## Development

```bash
make check     # everything CI runs: lint, typecheck, tests, build
make test      # API tests with coverage
make format    # ruff fix + format
```

Configuration lives in environment variables; see [`.env.example`](.env.example).

## Status and roadmap

Working today: the full pipeline end to end, consent management, medical-constraint overrides, rule-based suggestions from `rules/`, weekly meal plans, per-user accounts with deletion, trend analytics, meal text and image analysis, Synthea patient import, and the dashboard.

Possible next steps are in [ROADMAP.md](ROADMAP.md).

## Author

Deokhwa Jeong · [LinkedIn](https://www.linkedin.com/in/deokhwa-jeong) · [GitHub](https://github.com/deokhwajeong)
