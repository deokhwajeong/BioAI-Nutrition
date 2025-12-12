import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    if (!body?.url) {
      return NextResponse.json(
        { error: "Missing required 'url' field" },
        { status: 400 },
      );
    }

    const upstreamResponse = await fetch(`${API_BASE_URL}/ingest/fetch`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url: body.url,
        signed_ttl_seconds: body.signed_ttl_seconds,
      }),
    });

    const payload = await upstreamResponse.json();

    if (!upstreamResponse.ok) {
      const message = payload?.detail || payload?.error || "Proxy fetch failed";
      return NextResponse.json({ error: message }, { status: upstreamResponse.status });
    }

    return NextResponse.json(payload, { status: upstreamResponse.status });
  } catch (error) {
    console.error("/api/ingest/fetch proxy failed", error);
    return NextResponse.json(
      { error: "Unable to process fetch request" },
      { status: 500 },
    );
  }
}
