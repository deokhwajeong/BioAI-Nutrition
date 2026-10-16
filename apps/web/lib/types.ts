// View-model types shared by UI components. Wire types live in ./api-schema.d.ts,
// generated from the FastAPI OpenAPI spec (`pnpm gen:api`); do not edit that file by hand.
import type { components } from "./api-schema";

type Schemas = components["schemas"];

export type FoodNutrition = Schemas["FoodNutrition"];
export type AnalyzeMealRequest = Schemas["AnalyzeMealRequest"];
export type AnalyzeMealResponse = Schemas["AnalyzeMealResponse"];
export type ConsentStatus = Schemas["ConsentStatusOut"];
export type GeneticModifiers = Schemas["GeneticModifiersOut"];
export type BiomarkerReadingIn = Schemas["BiomarkerReadingIn"];
export type IngestionResult = Schemas["BiomarkerIngestionResult"];
export type SyncResponse = Schemas["SyncResponse"];
export type ConflictResolution = Schemas["ConflictResolutionOut"];
export type SyntheaStatus = Schemas["SyntheaStatusResponse"];
export type SyntheaLoadResult = Schemas["LoadPatientResponse"];
export type DailyFeatures = Schemas["DailyFeatures"];
export type UserTargets = Schemas["UserTargets"];

export type Resolution = "fine" | "medium" | "coarse";
export type Sex = "male" | "female";
export type ActivityLevel = "sedentary" | "light" | "moderate" | "active" | "very_active";

/** Metabolic state reshaped for the dashboard card. */
export interface MetabolicStateView {
  phase: string;
  confidence: number;
  activePhases: string[];
  raw: Schemas["MetabolicStateOut"];
}

/** Nutrient budget reshaped for NutrientBudgetPanel (daily targets keyed by nutrient). */
export interface NutrientBudgetView {
  targets: Record<string, number>;
  modifications: string[];
  metabolic_state: string;
  conflict_resolutions: ConflictResolution[];
  raw: Schemas["NutrientBudgetResponse"];
}

/** Pipeline status summarized for the header badge. */
export interface EngineStatusView {
  registered_sources: number;
  biomarker_types: number;
  users_with_data: number;
  privacy?: { epsilon_used?: number; queries?: number };
}

/** One fired rule from rules/*.yaml, shaped for the suggestions panel. */
export interface RecommendationView {
  id: string;
  message: string;
  rationale: string;
  priority: "high" | "medium" | "low";
  triggeredBy: string[];
}

export interface RecommendationsView {
  items: RecommendationView[];
  disclaimer: string;
}

/** Free-form JSON returned by research/diagnostic endpoints (lag comparison, edge manifest). */
export type JsonObject = Record<string, unknown>;
