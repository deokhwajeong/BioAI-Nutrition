// Static demo transport (NEXT_PUBLIC_DEMO=1). Answers the client's API calls from
// demo-fixtures.json: real API responses captured by apps/api/scripts/capture_demo_fixtures.py
// against the synthetic seed data. It returns standard Response objects, so lib/api.ts parses
// and maps them exactly as it does live responses.
import type { components } from "./api-schema";
import fixtureJson from "./demo-fixtures.json";

type Schemas = components["schemas"];
type Json = Record<string, unknown>;
type Genotypes = Record<string, string>;

interface Fixtures {
  pipeline: {
    consent: Schemas["ConsentStatusOut"];
    genetic: { genotypes: Genotypes; response: Schemas["GeneticModifiersOut"] };
    ingest: Json;
    sync: Json;
    lag_comparison: Json | null;
    metabolic_state: Json;
    nutrient_budget: Json;
    status: Json;
    edge_manifest: Json;
  };
  genetic_panel: { genotypes: Genotypes; response: Schemas["GeneticModifiersOut"] }[];
  meals: { foods: Schemas["FoodNutrition"][]; unknown: Schemas["FoodNutrition"] };
  images: { label: string; rgb: number[]; response: Schemas["AnalyzeMealResponse"] }[];
  metrics: Json;
  recommendations: Json;
  synthea: { status: Json; detail: Record<string, Json>; load: Record<string, Json> };
}

const fx = fixtureJson as unknown as Fixtures;
const UNKNOWN_SENTINEL = "zzz-unknown-food";
const LATENCY_MS = 350;

/* Consent is bookkeeping, not engine output: track toggles locally from the captured state. */
const consent: Schemas["ConsentStatusOut"] = structuredClone(fx.pipeline.consent);

function setConsent(scope: string, granted: boolean) {
  const without = (list: string[]) => list.filter((s) => s !== scope);
  consent.granted_scopes = granted ? [...without(consent.granted_scopes), scope] : without(consent.granted_scopes);
  consent.revoked_scopes = granted ? without(consent.revoked_scopes) : [...without(consent.revoked_scopes), scope];
  const gate = (consent.policy_gates as Record<string, { granted: boolean }> | null | undefined)?.[scope];
  if (gate) gate.granted = granted;
}

/** Nearest precomputed genetic profile: fewest SNPs whose genotype differs (missing counts). */
function geneticFor(genotypes: Genotypes) {
  const candidates = [fx.pipeline.genetic, ...fx.genetic_panel];
  const distance = (other: Genotypes) =>
    new Set([...Object.keys(genotypes), ...Object.keys(other)]).size -
    Object.keys(genotypes).filter((k) => other[k] === genotypes[k]).length;
  const best = candidates.reduce((a, b) => (distance(b.genotypes) < distance(a.genotypes) ? b : a));
  // SNPs outside the captured set carry no risk allele in the engine, so only the count changes.
  return { ...best.response, variant_count: Object.keys(genotypes).length };
}

/** Same lookup order as the API's meal analyzer: exact name, then closest substring match. */
function foodFor(name: string): Schemas["FoodNutrition"] {
  const key = name.toLowerCase().trim();
  const exact = fx.meals.foods.find((f) => f.name === key);
  const partial = fx.meals.foods
    .filter((f) => f.name.includes(key) || key.includes(f.name))
    .sort((a, b) => Math.abs(a.name.length - key.length) - Math.abs(b.name.length - key.length))[0];
  const match = exact ?? partial;
  if (match) return { ...match, name };
  return { ...fx.meals.unknown, name, note: fx.meals.unknown.note?.replace(UNKNOWN_SENTINEL, name) };
}

/** Mean colour of the uploaded image, matched to the nearest captured colour swatch. */
async function imageFor(file: Blob) {
  let rgb = [128, 128, 128];
  try {
    const bitmap = await createImageBitmap(file);
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 64;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.drawImage(bitmap, 0, 0, 64, 64);
      const px = ctx.getImageData(0, 0, 64, 64).data;
      const sum = [0, 0, 0];
      for (let i = 0; i < px.length; i += 4) for (let c = 0; c < 3; c++) sum[c] += px[i + c];
      rgb = sum.map((s) => s / (px.length / 4));
    }
  } catch {
    /* undecodable image: fall back to a neutral colour */
  }
  const dist = (o: number[]) => o.reduce((acc, v, i) => acc + (v - rgb[i]) ** 2, 0);
  return fx.images.reduce((a, b) => (dist(b.rgb) < dist(a.rgb) ? b : a)).response;
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const notFound = () => json({ detail: "Not available in the static demo" }, 404);

async function route(path: string, method: string, body: BodyInit | null | undefined): Promise<Response> {
  const payload = typeof body === "string" ? (JSON.parse(body) as Json) : {};
  const p = fx.pipeline;

  if (method === "GET") {
    if (path === "/engine/edge-manifest") return json(p.edge_manifest);
    if (path === "/engine/status") return json(p.status);
    if (path.startsWith("/engine/consent/")) return json(consent);
    if (path === "/synthea/status") return json(fx.synthea.status);
    if (path.startsWith("/synthea/patient/")) {
      const id = decodeURIComponent(path.slice("/synthea/patient/".length));
      return fx.synthea.detail[id] ? json(fx.synthea.detail[id]) : notFound();
    }
    if (path === "/api/metrics") return json(fx.metrics);
    return notFound();
  }

  switch (path) {
    case "/engine/consent":
      setConsent(String(payload.scope), payload.action === "grant");
      return json(consent);
    case "/engine/genetic-profile": {
      const genotypes = (payload.genotypes ?? {}) as Genotypes;
      if (Object.keys(genotypes).length === 0) return json({ detail: "Failed to store genetic profile" }, 400);
      return json(geneticFor(genotypes));
    }
    case "/engine/ingest":
      return json(p.ingest);
    case "/engine/sync":
      return json(p.sync);
    case "/engine/lag-comparison":
      return p.lag_comparison ? json(p.lag_comparison) : json({ detail: "research_use consent required" }, 403);
    case "/engine/metabolic-state":
      return json(p.metabolic_state);
    case "/engine/nutrient-budget":
      return json(p.nutrient_budget);
    case "/recommendations":
      return json(fx.recommendations);
    case "/analyze-meal": {
      const items = (payload.items ?? []) as { name: string }[];
      return json({ items: items.map((i) => foodFor(i.name)) });
    }
    case "/image-analyze/upload": {
      const file = body instanceof FormData ? body.get("file") : null;
      return file instanceof Blob ? json(await imageFor(file)) : json({ detail: "File must be an image" }, 400);
    }
    case "/synthea/load": {
      const load = fx.synthea.load[String(payload.patient_id)];
      return load ? json(load) : json({ detail: "Patient not found" }, 404);
    }
    default:
      return notFound();
  }
}

/** Drop-in for fetch(API_URL + path, init) in demo builds. */
export async function demoFetch(path: string, init: RequestInit = {}): Promise<Response> {
  await new Promise((r) => setTimeout(r, LATENCY_MS));
  return route(path.split("?")[0], (init.method ?? "GET").toUpperCase(), init.body);
}
