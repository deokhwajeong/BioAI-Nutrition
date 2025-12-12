from fastapi import FastAPI

from .routes import ingest

app = FastAPI(
    title="BioAI Nutrition API",
    description="Backend services for secure data ingestion and analytics.",
    version="0.1.0",
)

app.include_router(ingest.router)


@app.get("/", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
