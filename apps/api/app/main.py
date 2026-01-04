"""Improved FastAPI application entrypoint for BioAI Nutrition.

This version introduces environment-based configuration via Pydantic settings,
CORS middleware configuration, API key security, and consistent router prefixes.
It retains the existing health endpoint while improving maintainability and security.

Usage:
    uvicorn apps.api.app.main:app --reload

The Settings class reads configuration from environment variables. Adjust the
`allowed_origins` list and `api_key` to reflect real values in production.
"""

from __future__ import annotations

from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic_settings import BaseSettings

import logging
from .services.privacy import PIIFilter


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    api_title: str = "BioAI Nutrition API"
    api_description: str = (
        "Backend services for secure data ingestion and analytics."
    )
    api_version: str = "0.1.0"
    # In production, specify actual allowed origins instead of "*"
    allowed_origins: list[str] = ["*"]
    # Use environment variables to set a secure API key in production
    api_key: str = "dev-api-key"
    hash_pepper: str = "dev-pepper"


# Instantiate settings once at startup
settings = Settings()

# Configure global logger with PII filter
logger = logging.getLogger()
logger.addFilter(PIIFilter())

# Define API key header (looking for header `X-API-Key`)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    """Validate the provided API key against the configured value.

    Raises:
        HTTPException: If the key is missing or does not match the configured key.
    """
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key


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

# Include routers with API key dependency
app.include_router(
    ingest.router,
    prefix="/ingest",
    tags=["ingest"],
    dependencies=[Depends(verify_api_key)],
)

# events router already declares its own prefix (/events)
app.include_router(
    events.router,
    dependencies=[Depends(verify_api_key)],
)

# users router for delete endpoint
app.include_router(
    users.router,
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(verify_api_key)],
)


@app.get("/", tags=["health"])
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns a simple status object to indicate that the service is up.
    """
    return {"status": "ok"}
