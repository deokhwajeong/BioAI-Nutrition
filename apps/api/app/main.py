"""Improved FastAPI application entrypoint for BioAI Nutrition.

This version introduces environment‑based configuration via Pydantic settings,
CORS middleware configuration, and a consistent router prefix. It retains the
existing health endpoint while improving maintainability and security.

Usage:
    uvicorn apps.api.app.main:app --reload

The Settings class reads configuration from environment variables. Adjust the
`allowed_origins` list to reflect real origins in production.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseSettings

from .routes import ingest


class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    Attributes:
        api_title: Human‑readable title for the API.
        api_description: Description displayed in the OpenAPI docs.
        api_version: Semantic version of the API.
        allowed_origins: Origins allowed for CORS.
    """

    api_title: str = "BioAI Nutrition API"
    api_description: str = (
        "Backend services for secure data ingestion and analytics."
    )
    api_version: str = "0.1.0"
    allowed_origins: list[str] = ["*"]  # Override in production with specific domains


# Instantiate settings once at startup
settings = Settings()

# Create FastAPI application with metadata from settings
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the ingest router with a prefix and tag
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])


@app.get("/", tags=["health"])
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns a simple status object to indicate that the service is up.
    """
    return {"status": "ok"}
