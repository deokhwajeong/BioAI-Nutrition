"use client";

import { useState, useCallback, useEffect } from "react";
import {
  engineConsent,
  getConsentStatus,
  engineGeneticProfile,
  engineIngest,
  engineSync,
  engineNutrientBudget,
  engineMetabolicState,
  engineStatus,
  engineLagComparison,
  engineEdgeManifest,
  getRecommendations,
} from "../lib/api";
import type { FoodNutrition } from "../lib/types";
import PipelineVisualizer from "./components/PipelineVisualizer";
import MealPredictionFlow from "./components/MealPredictionFlow";
import type { MealTotal } from "./components/MealPredictionFlow";
import MetabolicStateCard from "./components/MetabolicStateCard";
import NutrientBudgetPanel from "./components/NutrientBudgetPanel";
import PrivacyConsentPanel from "./components/PrivacyConsentPanel";
import GeneticProfilePanel from "./components/GeneticProfilePanel";
import SyntheaExplorer from "./components/SyntheaExplorer";
import LagComparisonView from "./components/LagComparisonView";
import SafetyOverrideNotice from "./components/SafetyOverrideNotice";
import type { ConflictResolution } from "./components/SafetyOverrideNotice";
import EdgeBoundaryBar from "./components/EdgeBoundaryBar";
import type { EdgeManifest } from "./components/EdgeBoundaryBar";
import type { LagComparison } from "./components/LagComparisonView";
import type { DailyFeatures, EngineStatusView, RecommendationsView } from "../lib/types";
import RecommendationsPanel from "./components/RecommendationsPanel";
import MealPlanPanel from "./components/MealPlanPanel";
import TrendsPanel from "./components/TrendsPanel";

/* ── Types ──────────────────────────────────────────── */

type TabType =
  | "pipeline"
  | "consent"
  | "genetic"
  | "meal_predict"
  | "meal_plan"
  | "trends"
  | "synthea";

interface PipelineStage {
  id: string;
  label: string;
  description: string;
  status: "idle" | "running" | "done" | "error";
  detail?: string;
}

const USER_ID = "demo-user-001";

const INITIAL_STAGES: PipelineStage[] = [
  { id: "consent",   label: "Check consent",              description: "Only data types the user has agreed to share are used; anything else is dropped before processing.", status: "idle" },
  { id: "genetic",   label: "Read genetic profile",       description: "Looks up 8 common gene variants linked to how the body handles caffeine, folate, fat, and sugar. Each becomes a small adjustment factor.", status: "idle" },
  { id: "ingest",    label: "Collect sensor readings",    description: "Loads glucose, heart rate, and activity readings: 72 hours of synthetic history plus a batch of fresh readings.", status: "idle" },
  { id: "sync",      label: "Line up the timelines",      description: "Glucose reacts 10 to 20 minutes after a meal; heart rate reacts in seconds. Each reading is shifted back to when the event happened, then grouped into time windows.", status: "idle" },
  { id: "metabolic", label: "Estimate body state",        description: "Labels the current state (for example fasting, after a meal, exercise recovery, sleep) from the aligned signals.", status: "idle" },
  { id: "nutrient",  label: "Set daily nutrient targets", description: "Adjusts energy, protein, carb, fat, fiber, and water targets for that state and profile. Medical limits always win over genetic adjustments.", status: "idle" },
  { id: "suggest",   label: "Suggest next steps",         description: "Compares a sample logged day with those targets using plain-text rules and lists what to adjust.", status: "idle" },
];

/** Synthetic day of intake, activity, and sleep for the suggestions stage.
 *  Mirrored in apps/api/scripts/capture_demo_fixtures.py (SAMPLE_DAY). */
const SAMPLE_DAY: DailyFeatures = {
  calories: 2450,
  protein_g: 62,
  carbs_g: 290,
  fiber_g: 14,
  sugar_g: 68,
  omega3_g: 0.6,
  water_ml: 1300,
  steps: 6200,
  sleep_hours: 6.1,
};

const phaseLabel = (phase: string) => phase.replace(/_/g, " ");

/* ── Page Component ─────────────────────────────────── */

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<TabType>("pipeline");

  /* Pipeline state */
  const [stages, setStages] = useState<PipelineStage[]>(INITIAL_STAGES);
  const [pipelineRunning, setPipelineRunning] = useState(false);

  /* Consent */
  const [grantedScopes, setGrantedScopes] = useState<string[]>([]);

  /* Genetic */
  const [geneticModifiers, setGeneticModifiers] = useState<Record<string, number> | null>(null);
  const [geneticLoading, setGeneticLoading] = useState(false);

  /* Metabolic */
  const [metabolicPhase, setMetabolicPhase] = useState<string | null>(null);
  const [metabolicConfidence, setMetabolicConfidence] = useState<number | undefined>();
  const [glucoseMean, setGlucoseMean] = useState<number | undefined>();
  const [heartRateMean, setHeartRateMean] = useState<number | undefined>();

  /* Nutrient budget */
  const [nutrientTargets, setNutrientTargets] = useState<Record<string, number> | null>(null);
  const [nutrientModifications, setNutrientModifications] = useState<string[]>([]);
  const [nutrientState, setNutrientState] = useState<string | undefined>();

  /* Lag comparison, safety overrides, edge manifest */
  const [lagComparisonData, setLagComparisonData] = useState<LagComparison | null>(null);
  const [lagLoading, setLagLoading] = useState(false);
  const [conflictResolutions, setConflictResolutions] = useState<ConflictResolution[]>([]);
  const [edgeManifest, setEdgeManifest] = useState<EdgeManifest | null>(null);

  /* Privacy budget (tracked locally) */
  const [privacyBudget, setPrivacyBudget] = useState<{
    epsilon_used: number;
    epsilon_total: number;
    queries_count: number;
  }>({ epsilon_used: 0, epsilon_total: 10, queries_count: 0 });

  /* Rule-based suggestions */
  const [recommendations, setRecommendations] = useState<RecommendationsView | null>(null);
  const [recommendationsError, setRecommendationsError] = useState<string | null>(null);

  /* Engine status */
  const [engineStatusData, setEngineStatusData] = useState<EngineStatusView | null>(null);

  /* ── Load edge manifest on mount ───────────────── */
  useEffect(() => {
    engineEdgeManifest<EdgeManifest>()
      .then(setEdgeManifest)
      .catch(() => {});
  }, []);

  /* ── Load consent state from backend on mount ──── */
  useEffect(() => {
    getConsentStatus(USER_ID)
      .then((data) => {
        setGrantedScopes(data.granted_scopes ?? []);
      })
      .catch(() => {
        // Backend not reachable yet - use sensible defaults
        setGrantedScopes([
          "glucose_data", "activity_data", "heart_rate_data",
          "sleep_data", "genetic_data", "meal_data",
        ]);
      });
  }, []);

  /* Meal prediction modal (launched from Pipeline tab) */
  const [showMealModal, setShowMealModal] = useState(false);

  /* ── Helpers ──────────────────────────────────────── */

  const setStageStatus = (id: string, status: PipelineStage["status"], detail?: string) =>
    setStages((prev) =>
      prev.map((s) => (s.id === id ? { ...s, status, detail } : s))
    );

  /* ── Full Pipeline Run ────────────────────────────── */

  const runFullPipeline = useCallback(async () => {
    setPipelineRunning(true);
    setStages(INITIAL_STAGES);
    setRecommendations(null);
    setRecommendationsError(null);

    try {
      /* 1 ── Consent ───────────────────────────────── */
      setStageStatus("consent", "running");
      // Ensure minimum required data scopes are granted without overriding user choices
      const requiredScopes = ["glucose_data", "activity_data", "genetic_data", "heart_rate_data", "sleep_data", "meal_data"];
      for (const scope of requiredScopes) {
        if (!grantedScopes.includes(scope)) {
          await engineConsent(USER_ID, scope, true);
        }
      }
      // Re-fetch actual consent state from backend
      const consentState = await getConsentStatus(USER_ID);
      setGrantedScopes(consentState.granted_scopes ?? requiredScopes);
      setStageStatus("consent", "done", `${(consentState.granted_scopes ?? requiredScopes).length} scopes granted`);

      /* 2 ── Genetic Profile (8 SNPs) ──────────────── */
      setStageStatus("genetic", "running");
      const geno: Record<string, { rsid: string; genotype: string }> = {
        rs1801133: { rsid: "rs1801133", genotype: "CT" },  // MTHFR
        rs9939609: { rsid: "rs9939609", genotype: "TA" },  // FTO
        rs429358:  { rsid: "rs429358",  genotype: "TT" },  // APOE
        rs7903146: { rsid: "rs7903146", genotype: "CT" },  // TCF7L2
        rs4988235: { rsid: "rs4988235", genotype: "GA" },  // LCT
        rs762551:  { rsid: "rs762551",  genotype: "AC" },  // CYP1A2
        rs1544410: { rsid: "rs1544410", genotype: "AG" },  // VDR
        rs4341:    { rsid: "rs4341",    genotype: "ID" },  // ACE
      };
      const genResult = await engineGeneticProfile(USER_ID, geno);
      setGeneticModifiers(genResult.modifiers ?? {});
      const modCount = Object.keys(genResult.modifiers ?? {}).length;
      setStageStatus("genetic", "done", `${modCount} adjustment factors from 8 variants`);

      /* 3 ── Ingest (add fresh readings on top of 72h seed) ──────── */
      setStageStatus("ingest", "running");
      const now = new Date();
      const readings = [];
      // 30 fresh glucose readings (last 2.5 hours, every 5 min)
      for (let i = 0; i < 30; i++) {
        const t = new Date(now.getTime() - i * 5 * 60000);
        const hour = t.getUTCHours() + t.getUTCMinutes() / 60;
        // Realistic postprandial curve
        const base = 90 + 5 * Math.sin(2 * Math.PI * (hour - 3) / 24);
        const spike = [7.5, 12.5, 19.0].reduce((sum, mh) => {
          const d = ((hour - mh) % 24 + 24) % 24;
          return d <= 2 ? sum + 40 * Math.sin(Math.PI * d / 2) : sum;
        }, 0);
        readings.push({
          biomarker_type: "glucose",
          value: Math.round((base + spike + (Math.random() - 0.5) * 6) * 10) / 10,
          unit: "mg/dL",
          timestamp: t.toISOString(),
          source_id: "cgm-dexcom-g7",
        });
      }
      // 30 fresh heart rate readings
      for (let i = 0; i < 30; i++) {
        const t = new Date(now.getTime() - i * 5 * 60000);
        const hour = t.getUTCHours() + t.getUTCMinutes() / 60;
        const base = 65 + 5 * Math.sin(2 * Math.PI * (hour - 14) / 24);
        readings.push({
          biomarker_type: "heart_rate",
          value: Math.round((base + (Math.random() - 0.5) * 5) * 10) / 10,
          unit: "bpm",
          timestamp: t.toISOString(),
          source_id: "smartwatch-hr",
        });
      }
      const ingestResult = await engineIngest(USER_ID, readings);
      setStageStatus("ingest", "done",
        `${ingestResult.accepted} of ${readings.length} fresh readings accepted, plus 72 h of history`);

      /* 4 ── Temporal Synchronization ──────────────── */
      setStageStatus("sync", "running");
      const syncResult = await engineSync(USER_ID, "medium", 180);
      // Extract glucose/HR means from sync frames for display
      let gluSum = 0, gluN = 0, hrSum = 0, hrN = 0;
      for (const frame of (syncResult.frames ?? [])) {
        if (frame.signals?.glucose) {
          gluSum += frame.signals.glucose.value;
          gluN++;
        }
        if (frame.signals?.heart_rate) {
          hrSum += frame.signals.heart_rate.value;
          hrN++;
        }
      }
      const syncGlucoseMean = gluN > 0 ? Math.round(gluSum / gluN * 10) / 10 : undefined;
      const syncHRMean = hrN > 0 ? Math.round(hrSum / hrN * 10) / 10 : undefined;
      setStageStatus("sync", "done",
        `${syncResult.total_frames} time windows · avg glucose ${syncGlucoseMean ?? "n/a"} mg/dL · avg heart rate ${syncHRMean ?? "n/a"} bpm`);

      /* 4b ── Lag comparison (before/after alignment) ── */
      setLagLoading(true);
      try {
        const lagResult = await engineLagComparison<LagComparison>(USER_ID, 180);
        setLagComparisonData(lagResult);
      } catch {
        // research_use consent may be off - silently skip
        setLagComparisonData(null);
      } finally {
        setLagLoading(false);
      }

      /* 5 ── Metabolic State Estimation ────────────── */
      setStageStatus("metabolic", "running");
      const metaResult = await engineMetabolicState(USER_ID, 180, false);
      setMetabolicPhase(metaResult.phase);
      setMetabolicConfidence(metaResult.confidence);
      setGlucoseMean(syncGlucoseMean);
      setHeartRateMean(syncHRMean);
      setStageStatus("metabolic", "done",
        `${phaseLabel(metaResult.phase)} (${Math.round((metaResult.confidence ?? 0) * 100)}% confidence)`);

      /* 6 ── Nutrient Demand Budget ────────────────── */
      setStageStatus("nutrient", "running");
      const budgetResult = await engineNutrientBudget(USER_ID, 70, 175, 30, "male", "moderate");
      setNutrientTargets(budgetResult.targets ?? {});
      setNutrientModifications(budgetResult.modifications ?? []);
      setNutrientState(budgetResult.metabolic_state);
      setConflictResolutions(budgetResult.conflict_resolutions ?? []);
      const modNumBudget = (budgetResult.modifications ?? []).length;
      setStageStatus("nutrient", "done",
        `${Object.keys(budgetResult.targets ?? {}).length} nutrient targets · ${modNumBudget} adjustments`);

      /* 7 ── Rule-based suggestions ─────────────── */
      setStageStatus("suggest", "running");
      const t = budgetResult.targets ?? {};
      try {
        const recs = await getRecommendations(SAMPLE_DAY, {
          calories: t.kcal,
          protein_g: t.protein_g,
          fiber_g: t.fiber_g,
          water_ml: t.water_ml,
        });
        setRecommendations(recs);
        setStageStatus("suggest", "done", `${recs.items.length} suggestions from the rule files`);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Unknown error";
        setRecommendationsError(msg);
        setStageStatus("suggest", "error", msg);
      }

      /* Engine status for header badge */
      const es = await engineStatus();
      setEngineStatusData(es);
      setPrivacyBudget((prev) => ({
        ...prev,
        epsilon_used: es.privacy?.epsilon_used ?? prev.epsilon_used,
        queries_count: es.privacy?.queries ?? prev.queries_count,
      }));
    } catch (err: unknown) {
      setStages((prev) =>
        prev.map((s) => (s.status === "running" ? { ...s, status: "error", detail: (err instanceof Error ? err.message : undefined) ?? "Unknown error" } : s))
      );
    } finally {
      setPipelineRunning(false);
    }
  }, [grantedScopes]);

  /* ── Consent Toggle ──────────────────────────────── */

  const handleConsentToggle = async (scope: string, granted: boolean) => {
    await engineConsent(USER_ID, scope, granted);
    setGrantedScopes((prev) =>
      granted
        ? prev.includes(scope) ? prev : [...prev, scope]
        : prev.filter((s) => s !== scope)
    );
    // Re-fetch actual privacy budget from backend
    try {
      const es = await engineStatus();
      setPrivacyBudget((prev) => ({
        ...prev,
        epsilon_used: es.privacy?.epsilon_used ?? prev.epsilon_used,
        queries_count: es.privacy?.queries ?? prev.queries_count,
      }));
    } catch { /* ignore */ }
  };

  /* ── Genetic Submit ──────────────────────────────── */

  const handleGeneticSubmit = async (genotypes: Record<string, { rsid: string; genotype: string }>) => {
    setGeneticLoading(true);
    try {
      const result = await engineGeneticProfile(USER_ID, genotypes);
      setGeneticModifiers(result.modifiers ?? {});
    } finally {
      setGeneticLoading(false);
    }
  };

  /* ── Meal Approve Handler ───────────────────────── */

  const handleMealApprove = (items: FoodNutrition[], total: MealTotal) => {
    // Update nutrient targets with consumed meal
    if (nutrientTargets) {
      setNutrientModifications((prev) => [
        ...prev,
        `meal_record: +${Math.round(total.calories)} kcal, P+${total.protein_g.toFixed(0)}g, C+${total.carbs_g.toFixed(0)}g, F+${total.fat_g.toFixed(0)}g`,
      ]);
    }
  };

  /* ── Targets for the meal plan when the pipeline has not run ── */

  const loadTargets = async () => {
    const budget = await engineNutrientBudget(USER_ID, 70, 175, 30, "male", "moderate");
    setNutrientTargets(budget.targets);
    setNutrientModifications(budget.modifications);
    setNutrientState(budget.metabolic_state);
    setConflictResolutions(budget.conflict_resolutions);
    return budget.targets;
  };

  /* ── Tab Config ──────────────────────────────────── */

  const TABS: { id: TabType; label: string }[] = [
    { id: "pipeline",     label: "Pipeline" },
    { id: "consent",      label: "Consent" },
    { id: "genetic",      label: "Genetic profile" },
    { id: "meal_predict", label: "Meal check" },
    { id: "meal_plan",    label: "Meal plan" },
    { id: "trends",       label: "Trends" },
    { id: "synthea",      label: "Sample patients" },
  ];

  /* ── Render ──────────────────────────────────────── */

  return (
    <div className="min-h-screen bg-background text-slate-100">
      {/* ─── Header ────────────────────────────────── */}
      <header className="border-b border-white/10 bg-slate-950/60">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-5">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight text-white">Nutri-Node</h1>
              <p className="text-sm text-slate-400 mt-1 max-w-2xl">
                Turns wearable and lab signals that arrive at different times into a daily nutrient plan,
                with consent and privacy checks built into each step. Research prototype on synthetic data.
              </p>
            </div>

            {engineStatusData && (
              <div className="hidden md:flex items-center gap-2 text-xs text-slate-400 whitespace-nowrap">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                API connected &middot; {engineStatusData.registered_sources ?? 0} data sources
              </div>
            )}
          </div>

          {/* ─── Tab Navigation ────────────────────── */}
          <nav aria-label="Sections" className="flex gap-1 overflow-x-auto -mx-1 px-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                aria-current={activeTab === tab.id ? "page" : undefined}
                className={`shrink-0 px-3 sm:px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? "bg-white/10 text-white"
                    : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* ─── Main Content ──────────────────────────── */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        {/* ── Pipeline Tab ──────────────────────────── */}
        {activeTab === "pipeline" && (
          <div className="space-y-8 animate-fade-in">
            <PipelineVisualizer
              stages={stages}
              onRunAll={runFullPipeline}
              running={pipelineRunning}
            />

            {(metabolicPhase || nutrientTargets) && (
              <div className="grid lg:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-sm font-semibold text-slate-300 mb-3">
                    Estimated body state
                  </h3>
                  <MetabolicStateCard
                    phase={metabolicPhase}
                    confidence={metabolicConfidence}
                    glucoseMean={glucoseMean}
                    heartRateMean={heartRateMean}
                  />
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-slate-300 mb-3">
                    Daily nutrient targets
                  </h3>
                  <NutrientBudgetPanel
                    targets={nutrientTargets}
                    modifications={nutrientModifications}
                    metabolicState={nutrientState}
                  />
                </div>
              </div>
            )}

            {(recommendations || recommendationsError) && (
              <RecommendationsPanel day={SAMPLE_DAY} data={recommendations} error={recommendationsError} />
            )}

            {/* Before/after timeline alignment */}
            <LagComparisonView data={lagComparisonData} loading={lagLoading} />

            {/* Medical limits that overrode genetic adjustments */}
            <SafetyOverrideNotice conflicts={conflictResolutions} />

            {geneticModifiers && Object.keys(geneticModifiers).length > 0 && (
              <div className="bg-white/5 border border-white/10 rounded-xl p-6">
                <h3 className="text-sm font-semibold text-slate-300 mb-4">
                  Genetic adjustment factors (1.00 = no change)
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                  {Object.entries(geneticModifiers).map(([key, val]) => {
                    // Most entries are multipliers; a few (e.g. caffeine_max_daily_mg) are absolute limits.
                    const unit = key.match(/_(mg|mcg|iu|g)$/)?.[1];
                    const isUp = !unit && val > 1;
                    const isDown = !unit && val < 1;
                    return (
                      <div key={key} className="bg-white/5 rounded-xl p-3 border border-white/10 text-center">
                        <div className="text-[10px] text-gray-400 truncate">
                          {key.replace(/_modifier$/, "").replace(/_(mg|mcg|iu)$/, "").replace(/_/g, " ")}
                        </div>
                        <div className={`text-xl font-bold mt-1 ${isUp ? "text-amber-300" : isDown ? "text-sky-300" : "text-gray-300"}`}>
                          {unit ? `${val} ${unit}` : `${isUp ? "↑" : isDown ? "↓" : "="} ${val.toFixed(2)}x`}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* How the stages connect */}
            <div className="bg-white/5 border border-white/10 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-slate-300 mb-4">How it fits together</h3>
              <ol className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
                {[
                  { label: "Sensors and lab data", sub: "Glucose monitor, watch, genotype" },
                  { label: "Align timelines", sub: "Correct each signal's delay" },
                  { label: "Estimate body state", sub: "14 states such as fasting or sleep" },
                  { label: "Targets and suggestions", sub: "Medical limits checked first" },
                ].map((item, i) => (
                  <li key={item.label} className="rounded-lg border border-white/10 bg-slate-900/60 p-3">
                    <div className="text-xs text-slate-500">Step {i + 1}</div>
                    <div className="font-medium text-slate-100 mt-0.5">{item.label}</div>
                    <div className="text-xs text-slate-400 mt-0.5">{item.sub}</div>
                  </li>
                ))}
              </ol>
              <p className="mt-4 text-xs text-slate-400">
                Privacy throughout: data use is gated by consent, and shared statistics get calibrated random noise
                (differential privacy) so no single reading can be recovered.
              </p>
            </div>

            {/* ── Floating Meal Record Button ── */}
            <button
              onClick={() => setShowMealModal(true)}
              className="fixed bottom-16 right-4 sm:right-8 z-40 px-4 py-2.5 bg-teal-700 hover:bg-teal-600 text-white text-sm font-semibold rounded-full shadow-lg transition-colors"
            >
              Log a meal
            </button>

            {/* ── Meal Prediction Modal (from Pipeline tab) ── */}
            {showMealModal && (
              <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
                <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowMealModal(false)} />
                <div className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto bg-slate-900 rounded-t-2xl sm:rounded-2xl border border-white/10 p-6 shadow-2xl animate-fade-in">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      Log a meal
                    </h3>
                    <button onClick={() => setShowMealModal(false)} aria-label="Close" className="w-8 h-8 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 text-gray-400 transition">✕</button>
                  </div>
                  <MealPredictionFlow
                    modal
                    onClose={() => setShowMealModal(false)}
                    metabolicPhase={metabolicPhase}
                    currentGlucose={glucoseMean}
                    geneticModifiers={geneticModifiers}
                    nutrientTargets={nutrientTargets}
                    conflictResolutions={conflictResolutions}
                    onApprove={handleMealApprove}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Consent Tab ──────────────────────────── */}
        {activeTab === "consent" && (
          <div className="max-w-2xl mx-auto animate-fade-in">
            <div className="mb-6">
              <h2 className="text-xl font-semibold">Consent</h2>
              <p className="text-slate-400 text-sm mt-1">
                Choose which kinds of data the pipeline may use. Turning a type off takes effect on the next run.
                The privacy budget shows how much statistical detail has been released so far.
              </p>
            </div>
            <PrivacyConsentPanel
              grantedScopes={grantedScopes}
              onToggle={handleConsentToggle}
              privacyBudget={privacyBudget}
            />
          </div>
        )}

        {/* ── Genetic Tab ──────────────────────────── */}
        {activeTab === "genetic" && (
          <div className="max-w-3xl mx-auto animate-fade-in">
            <div className="mb-6">
              <h2 className="text-xl font-semibold">Genetic profile</h2>
              <p className="text-slate-400 text-sm mt-1">
                Pick a genotype for any of these gene variants. Each one the engine recognizes becomes an adjustment
                factor on the nutrient targets (above 1.00 raises a target, below lowers it). Synthetic choices only.
              </p>
            </div>
            <GeneticProfilePanel
              modifiers={geneticModifiers}
              onSubmit={handleGeneticSubmit}
              loading={geneticLoading}
            />
          </div>
        )}

        {/* ── Meal Predict Tab (unified flow) ── */}
        {activeTab === "meal_predict" && (
          <div className="max-w-2xl mx-auto animate-fade-in">
            <div className="mb-6">
              <h2 className="text-xl font-semibold">Meal check</h2>
              <p className="text-slate-400 text-sm mt-1">
                Describe or photograph a meal. The app estimates its nutrients, sketches the likely glucose curve
                for this profile and time of day, checks it against medical limits, and adds it to today&apos;s totals.
              </p>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
              <MealPredictionFlow
                metabolicPhase={metabolicPhase}
                currentGlucose={glucoseMean}
                geneticModifiers={geneticModifiers}
                nutrientTargets={nutrientTargets}
                conflictResolutions={conflictResolutions}
                onApprove={handleMealApprove}
              />
            </div>
          </div>
        )}

        {/* ── Meal Plan Tab ────────────────────────── */}
        {activeTab === "meal_plan" && (
          <div className="max-w-4xl mx-auto animate-fade-in">
            <div className="mb-6">
              <h2 className="text-xl font-semibold">Meal plan</h2>
              <p className="text-slate-400 text-sm mt-1">
                A week of breakfasts, lunches, dinners, and snacks built from the app&apos;s food table so each day lands near
                the nutrient targets. Medical limits are applied first and are never exceeded.
              </p>
            </div>
            <MealPlanPanel targets={nutrientTargets} loadTargets={loadTargets} />
          </div>
        )}

        {/* ── Trends Tab ───────────────────────────── */}
        {activeTab === "trends" && (
          <div className="animate-fade-in">
            <div className="mb-6">
              <h2 className="text-xl font-semibold">Trends</h2>
              <p className="text-slate-400 text-sm mt-1 max-w-3xl">
                Four weeks of logged days for a fictional user (synthetic data), summarized by the API: rolling averages,
                weekly trend, how often each goal was met, and which suggestions fired.
              </p>
            </div>
            <TrendsPanel />
          </div>
        )}

        {/* ── Synthea Tab ──────────────────────────── */}
        {activeTab === "synthea" && (
          <div className="animate-fade-in">
            <SyntheaExplorer />
          </div>
        )}
      </main>

      {/* ─── Footer ────────────────────────────────── */}
      <footer className="border-t border-white/10 mt-16">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 flex flex-col md:flex-row gap-2 md:items-center md:justify-between text-xs text-slate-400">
          <span>Research prototype. Not a medical device and not medical advice. All data is synthetic.</span>
          <a className="hover:text-slate-200 underline-offset-2 hover:underline" href="https://github.com/deokhwajeong/BioAI-Nutrition">
            Source on GitHub
          </a>
        </div>
      </footer>

      {/* Privacy boundary bar (fixed bottom) */}
      <EdgeBoundaryBar manifest={edgeManifest} />

      {/* Bottom spacer for fixed EdgeBoundaryBar */}
      <div className="h-12" />
    </div>
  );
}




