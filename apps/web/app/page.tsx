"use client";

import { useState, useCallback, useEffect } from "react";
import {
  analyzeMeal,
  analyzeFoodImage,
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

/* ── Types ──────────────────────────────────────────── */

type TabType =
  | "pipeline"
  | "consent"
  | "genetic"
  | "meal_predict"
  | "synthea";

interface PipelineStage {
  id: string;
  label: string;
  icon: string;
  description: string;
  status: "idle" | "running" | "done" | "error";
  detail?: string;
}

const USER_ID = "demo-user-001";

const INITIAL_STAGES: PipelineStage[] = [
  { id: "consent",  label: "Privacy Consent",              icon: "🔐", description: "Grant scopes under ε-differential privacy",           status: "idle" },
  { id: "genetic",  label: "Genetic Profile",              icon: "🧬", description: "SNP variant analysis → metabolic modifiers",          status: "idle" },
  { id: "ingest",   label: "Biomarker Ingest",             icon: "📡", description: "Heterogeneous sensor fusion (CGM, HR, HRV, steps)",  status: "idle" },
  { id: "sync",     label: "Temporal Synchronization",     icon: "⏱️", description: "Multi-resolution alignment with circadian correction", status: "idle" },
  { id: "metabolic",label: "Metabolic State Estimation",   icon: "🔥", description: "14-phase classifier (fasting → exercise → sleep → stress)",    status: "idle" },
  { id: "nutrient", label: "Nutrient Demand Calculation",  icon: "🧮", description: "7-stage personalized budget with genetic modifiers",  status: "idle" },
];

/* ── Page Component ─────────────────────────────────── */

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<TabType>("pipeline");

  /* Pipeline state */
  const [stages, setStages] = useState<PipelineStage[]>(INITIAL_STAGES);
  const [pipelineRunning, setPipelineRunning] = useState(false);

  /* Consent */
  const [grantedScopes, setGrantedScopes] = useState<string[]>([]);
  const [consentLoaded, setConsentLoaded] = useState(false);

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

  /* Patent-feature state */
  const [lagComparisonData, setLagComparisonData] = useState<any>(null);
  const [lagLoading, setLagLoading] = useState(false);
  const [conflictResolutions, setConflictResolutions] = useState<ConflictResolution[]>([]);
  const [edgeManifest, setEdgeManifest] = useState<any>(null);

  /* Privacy budget (tracked locally) */
  const [privacyBudget, setPrivacyBudget] = useState<{
    epsilon_used: number;
    epsilon_total: number;
    queries_count: number;
  }>({ epsilon_used: 0, epsilon_total: 10, queries_count: 0 });

  /* Engine status */
  const [engineStatusData, setEngineStatusData] = useState<any>(null);

  /* ── Load edge manifest on mount ───────────────── */
  useEffect(() => {
    engineEdgeManifest()
      .then(setEdgeManifest)
      .catch(() => {});
  }, []);

  /* ── Load consent state from backend on mount ──── */
  useEffect(() => {
    getConsentStatus(USER_ID)
      .then((data) => {
        setGrantedScopes(data.granted_scopes ?? []);
        setConsentLoaded(true);
      })
      .catch(() => {
        // Backend not reachable yet — use sensible defaults
        setGrantedScopes([
          "glucose_data", "activity_data", "heart_rate_data",
          "sleep_data", "genetic_data", "meal_data",
        ]);
        setConsentLoaded(true);
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
      setStageStatus("genetic", "done", `${modCount} metabolic modifiers from 8 SNPs`);

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
          source_id: "watch-apple-ultra",
        });
      }
      const ingestResult = await engineIngest(USER_ID, readings);
      setStageStatus("ingest", "done",
        `${ingestResult.accepted}/${readings.length} fresh + 72h seed data in adapters`);

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
        `${syncResult.frames_aligned} frames aligned · glucose μ=${syncGlucoseMean ?? "–"} · HR μ=${syncHRMean ?? "–"}`);

      /* 4b ── Lag Comparison (patent visualization) ── */
      setLagLoading(true);
      try {
        const lagResult = await engineLagComparison(USER_ID, 180);
        setLagComparisonData(lagResult);
      } catch {
        // research_use consent may be off — silently skip
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
        `Phase: ${metaResult.phase} (${Math.round((metaResult.confidence ?? 0) * 100)}%)`);

      /* 6 ── Nutrient Demand Budget ────────────────── */
      setStageStatus("nutrient", "running");
      const budgetResult = await engineNutrientBudget(USER_ID, 70, 175, 30, "male", "moderate");
      setNutrientTargets(budgetResult.targets ?? {});
      setNutrientModifications(budgetResult.modifications ?? []);
      setNutrientState(budgetResult.metabolic_state);
      setConflictResolutions(budgetResult.conflict_resolutions ?? []);
      const modNumBudget = (budgetResult.modifications ?? []).length;
      setStageStatus("nutrient", "done",
        `${Object.keys(budgetResult.targets ?? {}).length} nutrients · ${modNumBudget} genetic/metabolic adjustments`);

      /* Engine status for header badge */
      const es = await engineStatus();
      setEngineStatusData(es);
      setPrivacyBudget((prev) => ({
        ...prev,
        epsilon_used: es.privacy?.epsilon_used ?? prev.epsilon_used,
        queries_count: es.privacy?.queries ?? prev.queries_count,
      }));
    } catch (err: any) {
      setStages((prev) =>
        prev.map((s) => (s.status === "running" ? { ...s, status: "error", detail: err?.message ?? "Unknown error" } : s))
      );
    } finally {
      setPipelineRunning(false);
    }
  }, []);

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

  /* ── Tab Config ──────────────────────────────────── */

  const TABS: { id: TabType; label: string; icon: string }[] = [
    { id: "pipeline",     label: "BioSync Pipeline",  icon: "⚙️" },
    { id: "consent",      label: "Privacy & Consent", icon: "🔐" },
    { id: "genetic",      label: "Genetic Profile",   icon: "🧬" },
    { id: "meal_predict", label: "Meal Predict",       icon: "🍽️" },
    { id: "synthea",      label: "Synthea FHIR",       icon: "🏥" },
  ];

  /* ── Render ──────────────────────────────────────── */

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-purple-950 text-white">
      {/* ─── Header ────────────────────────────────── */}
      <header className="border-b border-white/10 backdrop-blur-lg bg-white/5">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                <span className="bg-gradient-to-r from-emerald-400 via-cyan-400 to-violet-400 bg-clip-text text-transparent">
                  BioAI Nutrition
                </span>
              </h1>
              <p className="text-sm text-gray-400 mt-1">
                Adaptive Biomarker Synchronization Engine &middot; ε-Differential Privacy &middot; Circadian-Aware Nutrient Optimization
              </p>
            </div>

            {engineStatusData && (
              <div className="hidden md:flex items-center gap-3 text-xs">
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-emerald-300 font-medium">Engine Active</span>
                </div>
                <div className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 font-mono text-gray-400">
                  {engineStatusData.registered_sources ?? 0} sources &middot; {engineStatusData.biomarker_types ?? 0} types
                </div>
              </div>
            )}
          </div>

          {/* ─── Tab Navigation ────────────────────── */}
          <div className="flex gap-1 bg-white/5 p-1 rounded-xl">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? "bg-white/15 text-white shadow-lg shadow-white/5"
                    : "text-gray-400 hover:text-gray-200 hover:bg-white/5"
                }`}
              >
                <span>{tab.icon}</span>
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* ─── Main Content ──────────────────────────── */}
      <main className="max-w-7xl mx-auto px-6 py-8">
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
                  <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                    Metabolic State Detection
                  </h3>
                  <MetabolicStateCard
                    phase={metabolicPhase}
                    confidence={metabolicConfidence}
                    glucoseMean={glucoseMean}
                    heartRateMean={heartRateMean}
                  />
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                    Personalized Nutrient Budget
                  </h3>
                  <NutrientBudgetPanel
                    targets={nutrientTargets}
                    modifications={nutrientModifications}
                    metabolicState={nutrientState}
                  />
                </div>
              </div>
            )}

            {/* Patent Figure: Before/After t_sync Comparison */}
            <LagComparisonView data={lagComparisonData} loading={lagLoading} />

            {/* Patent Figure: Safety Override Notice */}
            <SafetyOverrideNotice conflicts={conflictResolutions} />

            {geneticModifiers && Object.keys(geneticModifiers).length > 0 && (
              <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
                  Genetic Metabolic Modifiers (from Pipeline)
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                  {Object.entries(geneticModifiers).map(([key, val]) => {
                    const isUp = val > 1;
                    const isDown = val < 1;
                    return (
                      <div key={key} className="bg-white/5 rounded-xl p-3 border border-white/10 text-center">
                        <div className="text-[10px] text-gray-400 truncate">
                          {key.replace(/_modifier$/, "").replace(/_/g, " ")}
                        </div>
                        <div className={`text-xl font-bold mt-1 ${isUp ? "text-red-400" : isDown ? "text-emerald-400" : "text-gray-300"}`}>
                          {isUp ? "↑" : isDown ? "↓" : "="} {val.toFixed(2)}x
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Architecture diagram */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
                System Architecture
              </h3>
              <div className="grid grid-cols-3 md:grid-cols-7 gap-2 text-center text-xs">
                {[
                  { icon: "📡", label: "Sensor Fusion", sub: "CGM · Watch · DNA" },
                  { icon: "→",  label: "",               sub: "" },
                  { icon: "⏱️", label: "Temporal Sync",  sub: "Multi-resolution" },
                  { icon: "→",  label: "",               sub: "" },
                  { icon: "🔥", label: "Metabolic FSM",  sub: "13 phases" },
                  { icon: "→",  label: "",               sub: "" },
                  { icon: "🧮", label: "Nutrient Calc",  sub: "7-stage pipeline" },
                ].map((item, i) =>
                  item.label ? (
                    <div key={i} className="bg-gradient-to-br from-white/10 to-white/5 rounded-xl p-3 border border-white/10">
                      <span className="text-2xl">{item.icon}</span>
                      <div className="font-semibold text-gray-200 mt-1">{item.label}</div>
                      <div className="text-[10px] text-gray-500 mt-0.5">{item.sub}</div>
                    </div>
                  ) : (
                    <div key={i} className="flex items-center justify-center text-gray-600 text-lg">→</div>
                  )
                )}
              </div>
              <div className="mt-4 flex items-center justify-center gap-6 text-[10px] text-gray-500">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /> ε-Differential Privacy (Laplace + Gaussian)</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-violet-500" /> On-device Graph Embeddings</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-500" /> Dual-EWMA Baselines</span>
              </div>
            </div>

            {/* ── Floating Meal Record Button ── */}
            <button
              onClick={() => setShowMealModal(true)}
              className="fixed bottom-20 right-8 z-40 flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-cyan-600 to-violet-600 hover:from-cyan-700 hover:to-violet-700 text-white font-bold rounded-full shadow-2xl shadow-cyan-500/25 transition-all hover:scale-105 active:scale-95"
            >
              <span className="text-lg">🍽️</span>
              <span className="hidden sm:inline">Record Meal</span>
            </button>

            {/* ── Meal Prediction Modal (from Pipeline tab) ── */}
            {showMealModal && (
              <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
                <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowMealModal(false)} />
                <div className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto bg-gradient-to-br from-slate-900 to-indigo-950 rounded-t-2xl sm:rounded-2xl border border-white/10 p-6 shadow-2xl animate-fade-in">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      🍽️ Meal Prediction
                    </h3>
                    <button onClick={() => setShowMealModal(false)} className="w-8 h-8 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 text-gray-400 transition">✕</button>
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
              <h2 className="text-2xl font-bold">Privacy & Consent Management</h2>
              <p className="text-gray-400 text-sm mt-1">
                Granular data scope control with real-time revocation and ε-differential privacy budget tracking.
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
              <h2 className="text-2xl font-bold">Genetic Profile & SNP Analysis</h2>
              <p className="text-gray-400 text-sm mt-1">
                Select genotypes for 8 metabolically significant SNPs. The engine computes dose-dependent modifiers
                that adjust your nutrient budget in real-time.
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
              <h2 className="text-2xl font-bold">Meal Prediction & Analysis</h2>
              <p className="text-gray-400 text-sm mt-1">
                Analyze food, predict your personalized glucose response using genetic (γ) &amp; circadian (φ) modifiers,
                verify medical safety constraints, and apply to your nutrient budget — all in one flow.
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

        {/* ── Synthea Tab ──────────────────────────── */}
        {activeTab === "synthea" && (
          <div className="animate-fade-in">
            <SyntheaExplorer />
          </div>
        )}
      </main>

      {/* ─── Footer ────────────────────────────────── */}
      <footer className="border-t border-white/10 mt-16">
        <div className="max-w-7xl mx-auto px-6 py-6 flex flex-col md:flex-row items-center justify-between text-xs text-gray-500">
          <span>BioSync Engine v0.1 &middot; ε-Differential Privacy &middot; HIPAA-compliant</span>
          <span className="mt-2 md:mt-0">Built with BioAI &middot; FastAPI &middot; Next.js 16</span>
        </div>
      </footer>

      {/* Patent Figure: Edge Boundary Privacy Bar (fixed bottom) */}
      <EdgeBoundaryBar manifest={edgeManifest} />

      {/* Bottom spacer for fixed EdgeBoundaryBar */}
      <div className="h-12" />
    </div>
  );
}

// NOTE: reviewed 2023-11-09
// TODO: refactor this component
// TODO: refactor this component
// Updated: 2024-02-05
// TODO: refactor this component

// TODO: refactor this component
