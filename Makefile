.PHONY: setup dev api web test lint format gen-api check demo demo-api demo-fixtures ml-eval up down

setup:            ## Install API (uv) and web (pnpm) dependencies
	cd apps/api && uv sync
	cd apps/web && pnpm install

api:              ## Run the API with reload on :8000
	cd apps/api && uv run uvicorn app.main:app --reload --port 8000

web:              ## Run the web app on :3000 (proxies API calls to :8000)
	cd apps/web && pnpm dev

test:             ## API test suite with coverage
	cd apps/api && uv run pytest --cov --cov-report=term-missing:skip-covered

lint:             ## Lint and typecheck both apps
	cd apps/api && uv run ruff check . && uv run ruff format --check .
	cd apps/web && pnpm typecheck && pnpm lint

format:           ## Auto-format the API
	cd apps/api && uv run ruff check --fix . && uv run ruff format .

gen-api:          ## Regenerate the web client types from the API's OpenAPI spec
	cd apps/web && pnpm gen:api

check: lint test  ## Everything CI runs, locally
	cd apps/web && pnpm build

demo:             ## Static no-backend demo for GitHub Pages -> apps/web/out (basePath /demos/nutri-node)
	cd apps/web && pnpm build:demo

demo-api:         ## API from the repo root with fixed DP noise, for make demo-fixtures
	DP_SEED=20261016 uv run --project apps/api uvicorn app.main:app --app-dir apps/api --port 8000

demo-fixtures:    ## Recapture demo responses from a live API started at the repo root (see the script docstring)
	uv run --project apps/api python apps/api/scripts/capture_demo_fixtures.py $${API_URL:-http://localhost:8000}

ml-eval:          ## Train and score the synthetic glucose-response model -> output/glycemic_model_eval.md
	uv run --project apps/api python apps/api/scripts/train_eval_glycemic.py

up:               ## Full stack in Docker: http://localhost:3000
	docker compose up --build

down:
	docker compose down
