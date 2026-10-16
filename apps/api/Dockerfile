# Build context: repository root (the API reads ../../rules at runtime).
FROM python:3.13-slim AS base
RUN pip install --no-cache-dir "uv==0.11.*"
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH"

WORKDIR /srv/apps/api
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY apps/api/ ./
COPY rules/ /srv/rules/

RUN useradd --create-home --uid 10001 app && mkdir -p /srv/data && chown app /srv/data
USER app
ENV DATABASE_URL=sqlite:////srv/data/nutrition.db
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
