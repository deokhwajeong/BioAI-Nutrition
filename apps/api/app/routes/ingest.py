import base64
import csv
import hashlib
import hmac
import os
import time
from io import StringIO
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

router = APIRouter(prefix="/ingest", tags=["ingest"])


class FetchRequest(BaseModel):
    url: HttpUrl
    signed_ttl_seconds: int | None = 300


class FetchResponse(BaseModel):
    source: HttpUrl
    content_type: str
    signed_url: str | None = None
    data: list[dict[str, Any]] | None = None


async def _sign_url(url: str, ttl_seconds: int | None) -> str:
    secret = os.environ.get("DATA_PROXY_SECRET", "dev-secret")
    expiry = int(time.time()) + (ttl_seconds or 300)
    signature = hmac.new(secret.encode(), f"{url}:{expiry}".encode(), hashlib.sha256).hexdigest()
    return f"{url}?expires={expiry}&sig={signature}"


def _parse_csv(text: str) -> list[dict[str, Any]]:
    buffer = StringIO(text)
    reader = csv.DictReader(buffer)
    return [
        {
            key: (float(value) if value and value.replace(".", "", 1).isdigit() else value)
            for key, value in row.items()
        }
        for row in reader
        if any(row.values())
    ]


@router.post("/fetch", response_model=FetchResponse)
async def fetch_remote(payload: FetchRequest) -> FetchResponse:
    """Fetch remote files server-side to avoid CORS/credential leakage."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        try:
            response = await client.get(str(payload.url))
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch remote asset: {exc}") from exc

    content_type = response.headers.get("content-type", "application/octet-stream").lower()
    data: list[dict[str, Any]] | None = None

    if "json" in content_type:
        try:
            payload_json = response.json()
            if isinstance(payload_json, list):
                data = payload_json  # type: ignore[assignment]
            elif isinstance(payload_json, dict):
                data = [payload_json]  # type: ignore[list-item]
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=422, detail=f"Invalid JSON payload: {exc}") from exc
    elif "csv" in content_type or str(payload.url).lower().endswith(".csv"):
        decoded = response.content.decode("utf-8", errors="ignore")
        data = _parse_csv(decoded)

    signed_url = await _sign_url(str(payload.url), payload.signed_ttl_seconds)

    # For images or other binary assets, prefer a short-lived data URL preview
    if data is None:
        encoded = base64.b64encode(response.content).decode()
        signed_url = f"data:{content_type};base64,{encoded}"

    return FetchResponse(
        source=payload.url,
        content_type=content_type,
        signed_url=signed_url,
        data=data,
    )
