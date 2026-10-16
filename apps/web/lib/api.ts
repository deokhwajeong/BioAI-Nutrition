// Typed client for the Nutri-Node API. Request/response shapes come from the generated
// OpenAPI types; functions that feed UI components map wire responses to view models.
import type {
  ActivityLevel,
  AnalyzeMealRequest,
  AnalyzeMealResponse,
  BiomarkerReadingIn,
  ConsentStatus,
  EngineStatusView,
  GeneticModifiers,
  IngestionResult,
  JsonObject,
  MetabolicStateView,
  NutrientBudgetView,
  Resolution,
  Sex,
  SyncResponse,
  SyntheaLoadResult,
  SyntheaStatus,
} from "./types";
import type { components } from "./api-schema";

type Schemas = components["schemas"];

// Same-origin by default: next.config.ts rewrites /engine, /synthea, ... to the API, which keeps
// the strict `connect-src 'self'` CSP. Set NEXT_PUBLIC_API_URL only to call the API directly.
const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
// Demo-only key. The API rejects requests without X-API-Key; production deployments should
// route through a server-side proxy instead of exposing a key to the browser.
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "dev-api-key";
// Static demo build (pnpm build:demo): answer from captured API responses, no server needed.
export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO === "1";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-API-Key", API_KEY);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const res = DEMO_MODE
    ? await (await import("./demo")).demoFetch(path, { ...init, headers })
    : await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body?.detail ?? body);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, `${res.status} ${detail}`);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

/** Time window ending now, as the ISO strings SyncRequest expects. */
function windowFor(minutes: number) {
  const end = new Date();
  const start = new Date(end.getTime() - minutes * 60_000);
  return { start: start.toISOString(), end: end.toISOString() };
}

/* ── Meal analysis ─────────────────────────────────────────────── */

export const analyzeMeal = (payload: AnalyzeMealRequest) =>
  post<AnalyzeMealResponse>("/analyze-meal", payload);

export function analyzeFoodImage(file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<AnalyzeMealResponse>("/image-analyze/upload", { method: "POST", body: form });
}

/* ── Consent ───────────────────────────────────────────────────── */

export const engineConsent = (userId: string, scope: string, granted: boolean) =>
  post<ConsentStatus>("/engine/consent", {
    user_id: userId,
    scope,
    action: granted ? "grant" : "revoke",
  } satisfies Schemas["ConsentRequest"]);

export const getConsentStatus = (userId: string) =>
  request<ConsentStatus>(`/engine/consent/${encodeURIComponent(userId)}`);

/* ── Biomarker pipeline ────────────────────────────────────────── */

export const engineGeneticProfile = (
  userId: string,
  variants: Record<string, { rsid: string; genotype: string }>,
) =>
  post<GeneticModifiers>("/engine/genetic-profile", {
    user_id: userId,
    genotypes: Object.fromEntries(Object.values(variants).map((v) => [v.rsid, v.genotype])),
  } satisfies Schemas["GeneticProfileIn"]);

export const engineIngest = (userId: string, readings: Omit<BiomarkerReadingIn, "user_id">[]) =>
  post<IngestionResult>("/engine/ingest", {
    readings: readings.map((r) => ({ ...r, user_id: userId })),
  } satisfies Schemas["BiomarkerBatchIn"]);

export const engineSync = (userId: string, resolution: Resolution, minutes: number) =>
  post<SyncResponse>("/engine/sync", { user_id: userId, resolution, ...windowFor(minutes) });

export const engineLagComparison = <T = JsonObject>(userId: string, minutes: number) =>
  post<T>("/engine/lag-comparison", {
    user_id: userId,
    resolution: "fine",
    ...windowFor(minutes),
  });

export async function engineMetabolicState(
  userId: string,
  minutes: number,
  fineResolution = false,
): Promise<MetabolicStateView> {
  const raw = await post<Schemas["MetabolicStateOut"]>("/engine/metabolic-state", {
    user_id: userId,
    resolution: fineResolution ? "fine" : "medium",
    ...windowFor(minutes),
  });
  return {
    phase: raw.primary_phase,
    confidence: raw.phase_intensities[raw.primary_phase] ?? 0,
    activePhases: raw.active_phases,
    raw,
  };
}

const ACTIVITY_FACTOR: Record<ActivityLevel, number> = {
  sedentary: 1.2,
  light: 1.375,
  moderate: 1.55,
  active: 1.725,
  very_active: 1.9,
};

/** Daily energy need: Mifflin-St Jeor BMR times an activity factor. */
export function estimateKcal(
  weightKg: number,
  heightCm: number,
  age: number,
  sex: Sex,
  activity: ActivityLevel,
): number {
  const bmr = 10 * weightKg + 6.25 * heightCm - 5 * age + (sex === "male" ? 5 : -161);
  return Math.round(bmr * ACTIVITY_FACTOR[activity]);
}

export async function engineNutrientBudget(
  userId: string,
  weightKg: number,
  heightCm: number,
  age: number,
  sex: Sex,
  activity: ActivityLevel,
): Promise<NutrientBudgetView> {
  const raw = await post<Schemas["NutrientBudgetResponse"]>("/engine/nutrient-budget", {
    user_id: userId,
    weight_kg: weightKg,
    kcal_target: estimateKcal(weightKg, heightCm, age, sex, activity),
  } satisfies Schemas["NutrientBudgetRequest"]);
  return {
    targets: Object.fromEntries(Object.entries(raw.targets).map(([k, t]) => [k, t.daily_target])),
    modifications: raw.modifications.map(
      (m) => `${m.nutrient}: ${m.old_value.toFixed(1)} → ${m.new_value.toFixed(1)} (${m.reason})`,
    ),
    metabolic_state: raw.metabolic_state,
    conflict_resolutions: raw.conflict_resolutions ?? [],
    raw,
  };
}

export async function engineStatus(): Promise<EngineStatusView> {
  const raw = await request<Schemas["PipelineStatusOut"]>("/engine/status");
  return {
    registered_sources: raw.registered_sources.length,
    biomarker_types: raw.registered_biomarker_types.length,
    users_with_data: raw.users_with_data,
  };
}

export const engineEdgeManifest = <T = JsonObject>() => request<T>("/engine/edge-manifest");

export const getMetrics = <T = JsonObject>() => request<T>("/api/metrics");

/* ── Synthea (synthetic FHIR patients) ─────────────────────────── */

export async function syntheaStatus() {
  const raw = await request<SyntheaStatus>("/synthea/status");
  return {
    ...raw,
    available_patients: (raw.available_patients ?? []).map((p) => ({
      ...p,
      height_cm: p.height_cm ?? null,
      bmi: p.bmi ?? null,
    })),
  };
}

export async function syntheaLoadPatient(patientId: string, userId?: string) {
  const raw = await post<SyntheaLoadResult>("/synthea/load", {
    patient_id: patientId,
    override_user_id: userId ?? null,
  } satisfies Schemas["LoadPatientRequest"]);
  const withDisplay = (items: Record<string, string>[] = []) =>
    items.map((item) => ({ ...item, display: item.display ?? "" }));
  return { ...raw, conditions: withDisplay(raw.conditions), medications: withDisplay(raw.medications) };
}

export const syntheaPatientDetail = <T = JsonObject>(patientId: string) =>
  request<T>(`/synthea/patient/${encodeURIComponent(patientId)}`);
