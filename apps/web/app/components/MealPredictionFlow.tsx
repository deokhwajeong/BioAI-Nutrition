"use client";

import React, { useState, useRef, useCallback } from "react";
import { analyzeMeal, analyzeFoodImage } from "../../lib/api";
import type { FoodNutrition } from "../../lib/types";
import type { ConflictResolution } from "./SafetyOverrideNotice";
import GlucosePredictionChart from "./GlucosePredictionChart";

/**
 * MealPredictionFlow
 *
 * Unified 4-step flow that connects food analysis directly to the 7-stage pipeline:
 *   Step 1: Food Input (text or image)
 *   Step 2: Nutritional Analysis + Glucose Prediction (t_sync engine output)
 *   Step 3: Safety Check (Stage 6 conflict resolution)
 *   Step 4: Approve → apply to nutrient budget
 *
 * This component can render inline (as a tab) or inside a modal.
 */

interface Props {
  /** If true, render in compact modal mode */
  modal?: boolean;
  /** Close callback for modal mode */
  onClose?: () => void;
  /** Current metabolic state from pipeline */
  metabolicPhase: string | null;
  /** Current glucose reading */
  currentGlucose?: number;
  /** Genetic modifiers from SNP analysis */
  geneticModifiers: Record<string, number> | null;
  /** Nutrient targets from current budget */
  nutrientTargets: Record<string, number> | null;
  /** Active conflict resolutions */
  conflictResolutions: ConflictResolution[];
  /** Callback when meal is approved and should be applied to budget */
  onApprove?: (items: FoodNutrition[], totalNutrients: MealTotal) => void;
}

export interface MealTotal {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number;
}

type Step = 1 | 2 | 3 | 4;

const STEP_LABELS: Record<Step, { icon: string; title: string; sub: string }> = {
  1: { icon: "🍽️", title: "Food Input", sub: "Enter food or upload an image" },
  2: { icon: "📈", title: "Prediction", sub: "Predicted metabolic response" },
  3: { icon: "🛡️", title: "Safety Check", sub: "Medical constraint verification" },
  4: { icon: "✅", title: "Confirm", sub: "Apply to your nutrient budget" },
};

function sumNutrients(items: FoodNutrition[]): MealTotal {
  return items.reduce(
    (acc, item) => ({
      calories: acc.calories + (item.calories ?? 0),
      protein_g: acc.protein_g + (item.protein_g ?? 0),
      carbs_g: acc.carbs_g + (item.carbs_g ?? 0),
      fat_g: acc.fat_g + (item.fat_g ?? 0),
      fiber_g: acc.fiber_g + ((item as any).fiber_g ?? 0),
    }),
    { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0, fiber_g: 0 }
  );
}

export default function MealPredictionFlow({
  modal = false,
  onClose,
  metabolicPhase,
  currentGlucose,
  geneticModifiers,
  nutrientTargets,
  conflictResolutions,
  onApprove,
}: Props) {
  const [step, setStep] = useState<Step>(1);
  const [inputMode, setInputMode] = useState<"text" | "image">("text");

  // Text input
  const [mealText, setMealText] = useState("");

  // Image input
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Analysis state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<FoodNutrition[] | null>(null);
  const [mealTotal, setMealTotal] = useState<MealTotal | null>(null);

  // Applied
  const [applied, setApplied] = useState(false);

  /* ── Step 1 handlers ────────────────────── */

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    const reader = new FileReader();
    reader.onload = (ev) => setImagePreview(ev.target?.result as string);
    reader.readAsDataURL(file);
    setError(null);
  };

  const handleAnalyze = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      let items: FoodNutrition[];
      if (inputMode === "text") {
        const lines = mealText.split("\n").map((l) => l.trim()).filter(Boolean);
        if (lines.length === 0) { setError("Enter at least one food item."); setLoading(false); return; }
        const res = await analyzeMeal({ items: lines.map((name) => ({ name })) });
        items = res.items;
      } else {
        if (!selectedFile) { setError("Select an image first."); setLoading(false); return; }
        const res = await analyzeFoodImage(selectedFile);
        items = res.items;
      }
      setResults(items);
      setMealTotal(sumNutrients(items));
      setStep(2);
    } catch (err: any) {
      setError(err?.message ?? "Analysis failed");
    } finally {
      setLoading(false);
    }
  }, [inputMode, mealText, selectedFile]);

  const handleApprove = () => {
    if (results && mealTotal && onApprove) {
      onApprove(results, mealTotal);
    }
    setApplied(true);
  };

  const handleReset = () => {
    setStep(1);
    setResults(null);
    setMealTotal(null);
    setMealText("");
    setImagePreview(null);
    setSelectedFile(null);
    setApplied(false);
    setError(null);
  };

  /* ── Check for safety issues related to this meal ── */
  const mealSafetyIssues = conflictResolutions.filter((c) => {
    if (!mealTotal) return false;
    const nutrient = c.nutrient.toLowerCase();
    return (
      (nutrient.includes("protein") && mealTotal.protein_g > 0) ||
      (nutrient.includes("carb") && mealTotal.carbs_g > 0) ||
      (nutrient.includes("fat") && mealTotal.fat_g > 0) ||
      (nutrient.includes("fiber") && mealTotal.fiber_g > 0) ||
      (nutrient.includes("sodium") || nutrient.includes("potassium"))
    );
  });

  const hasSafetyIssues = mealSafetyIssues.length > 0 || conflictResolutions.length > 0;
  const displayConflicts = mealSafetyIssues.length > 0 ? mealSafetyIssues : conflictResolutions;

  const glucose = currentGlucose ?? 95;

  /* ── Render ──────────────────────────────── */

  const content = (
    <div className="space-y-6">
      {/* Step indicator */}
      <div className="flex items-center gap-1">
        {([1, 2, 3, 4] as Step[]).map((s) => {
          const info = STEP_LABELS[s];
          const isActive = s === step;
          const isDone = s < step || (s === 4 && applied);
          return (
            <React.Fragment key={s}>
              {s > 1 && (
                <div className={`flex-shrink-0 w-8 h-0.5 ${isDone ? "bg-emerald-500" : s <= step ? "bg-white/20" : "bg-white/5"}`} />
              )}
              <button
                onClick={() => { if (s < step) setStep(s); }}
                disabled={s > step}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                  isActive
                    ? "bg-white/15 text-white ring-1 ring-white/20"
                    : isDone
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "bg-white/5 text-gray-500"
                }`}
              >
                <span>{isDone && !isActive ? "✓" : info.icon}</span>
                <span className="hidden sm:inline">{info.title}</span>
              </button>
            </React.Fragment>
          );
        })}
      </div>

      {/* ── Step 1: Food Input ── */}
      {step === 1 && (
        <div className="space-y-4 animate-fade-in">
          {/* Current status strip */}
          {(metabolicPhase || currentGlucose) && (
            <div className="flex items-center gap-3 px-4 py-2.5 bg-gradient-to-r from-indigo-500/10 to-violet-500/10 border border-indigo-500/20 rounded-xl text-xs">
              {metabolicPhase && (
                <span className="text-indigo-300">
                  🔥 <span className="font-semibold capitalize">{metabolicPhase.replace(/_/g, " ")}</span>
                </span>
              )}
              {currentGlucose && (
                <span className="text-cyan-300">📊 Glucose: <span className="font-semibold">{currentGlucose} mg/dL</span></span>
              )}
              <span className="text-gray-500">|</span>
              <span className="text-gray-400">Recording a meal now will trigger prediction using your current metabolic context.</span>
            </div>
          )}

          {/* Input mode toggle */}
          <div className="flex gap-2">
            <button
              onClick={() => setInputMode("text")}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium transition-all ${
                inputMode === "text"
                  ? "bg-gradient-to-r from-cyan-600/30 to-blue-600/30 border border-cyan-500/30 text-white"
                  : "bg-white/5 border border-white/10 text-gray-400 hover:bg-white/10"
              }`}
            >
              ✏️ Text Input
            </button>
            <button
              onClick={() => setInputMode("image")}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium transition-all ${
                inputMode === "image"
                  ? "bg-gradient-to-r from-purple-600/30 to-pink-600/30 border border-purple-500/30 text-white"
                  : "bg-white/5 border border-white/10 text-gray-400 hover:bg-white/10"
              }`}
            >
              📸 Image Upload
            </button>
          </div>

          {/* Text mode */}
          {inputMode === "text" && (
            <textarea
              value={mealText}
              onChange={(e) => setMealText(e.target.value)}
              placeholder={"apple\nchicken breast 150g\nrice 1 bowl\nbroccoli"}
              className="w-full h-36 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 outline-none focus:border-cyan-500/50 transition resize-none text-sm"
            />
          )}

          {/* Image mode */}
          {inputMode === "image" && (
            <div className="space-y-3">
              <input ref={fileRef} type="file" accept="image/*" onChange={handleFileSelect} className="hidden" />
              <div className="flex gap-3">
                <button
                  onClick={() => fileRef.current?.click()}
                  className="flex-1 flex items-center justify-center gap-2 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-semibold rounded-xl transition shadow-lg text-sm"
                >
                  📁 Choose Image
                </button>
                <button
                  onClick={() => {
                    const input = document.createElement("input");
                    input.type = "file"; input.accept = "image/*"; input.capture = "environment";
                    input.onchange = (e) => { const f = (e.target as HTMLInputElement).files?.[0]; if (f) { setSelectedFile(f); const r = new FileReader(); r.onload = (ev) => setImagePreview(ev.target?.result as string); r.readAsDataURL(f); } };
                    input.click();
                  }}
                  className="flex-1 flex items-center justify-center gap-2 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-semibold rounded-xl transition shadow-lg text-sm"
                >
                  📸 Camera
                </button>
              </div>
              {imagePreview && (
                <div className="max-w-xs mx-auto rounded-xl overflow-hidden border-2 border-white/10">
                  <img src={imagePreview} alt="Food" className="w-full h-auto" />
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">{error}</div>
          )}

          <button
            onClick={handleAnalyze}
            disabled={loading || (inputMode === "text" ? !mealText.trim() : !selectedFile)}
            className="w-full py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold rounded-xl transition shadow-lg text-sm"
          >
            {loading ? "⏳ Analyzing..." : "🔍 Analyze & Predict"}
          </button>
        </div>
      )}

      {/* ── Step 2: Prediction ── */}
      {step === 2 && results && mealTotal && (
        <div className="space-y-5 animate-fade-in">
          {/* Nutritional summary */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Nutritional Analysis</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
              {[
                { label: "Calories", value: `${Math.round(mealTotal.calories)} kcal`, color: "text-amber-400" },
                { label: "Protein", value: `${mealTotal.protein_g.toFixed(1)}g`, color: "text-red-400" },
                { label: "Carbs", value: `${mealTotal.carbs_g.toFixed(1)}g`, color: "text-yellow-400" },
                { label: "Fat", value: `${mealTotal.fat_g.toFixed(1)}g`, color: "text-purple-400" },
              ].map((n) => (
                <div key={n.label} className="bg-white/5 rounded-lg p-2.5 text-center">
                  <div className="text-[10px] text-gray-500 uppercase">{n.label}</div>
                  <div className={`text-lg font-bold ${n.color}`}>{n.value}</div>
                </div>
              ))}
            </div>

            {/* Individual items (collapsed) */}
            <details className="text-xs">
              <summary className="cursor-pointer text-gray-400 hover:text-gray-300 transition">
                {results.length} items detected — click to expand
              </summary>
              <div className="mt-2 grid grid-cols-2 gap-2">
                {results.map((item, i) => (
                  <div key={i} className="bg-white/5 rounded-lg p-2 border border-white/5">
                    <span className="font-semibold text-white capitalize">{item.name}</span>
                    <div className="text-gray-500 mt-0.5">
                      {item.calories != null && `${Math.round(item.calories)} kcal`}
                      {item.protein_g != null && ` · P ${item.protein_g.toFixed(0)}g`}
                      {item.carbs_g != null && ` · C ${item.carbs_g.toFixed(0)}g`}
                    </div>
                  </div>
                ))}
              </div>
            </details>
          </div>

          {/* Glucose Prediction Chart — THE CORE PATENT VALUE */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <GlucosePredictionChart
              carbsG={mealTotal.carbs_g}
              currentGlucose={glucose}
              geneticModifiers={geneticModifiers}
              metabolicPhase={metabolicPhase}
            />
          </div>

          {/* Budget impact preview */}
          {nutrientTargets && (
            <div className="bg-white/5 border border-white/10 rounded-xl p-4">
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Budget Impact Preview</h4>
              <div className="space-y-2">
                {[
                  { key: "kcal", label: "Energy", meal: mealTotal.calories, unit: "kcal" },
                  { key: "protein_g", label: "Protein", meal: mealTotal.protein_g, unit: "g" },
                  { key: "carbs_g", label: "Carbs", meal: mealTotal.carbs_g, unit: "g" },
                  { key: "fat_g", label: "Fat", meal: mealTotal.fat_g, unit: "g" },
                ].map(({ key, label, meal, unit }) => {
                  const target = nutrientTargets[key] ?? 0;
                  const pctOfBudget = target > 0 ? Math.round((meal / target) * 100) : 0;
                  const isOver = pctOfBudget > 50;
                  return (
                    <div key={key} className="flex items-center gap-3 text-xs">
                      <span className="w-16 text-gray-400">{label}</span>
                      <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${isOver ? "bg-amber-500" : "bg-cyan-500"}`}
                          style={{ width: `${Math.min(pctOfBudget, 100)}%` }}
                        />
                      </div>
                      <span className={`w-24 text-right font-mono ${isOver ? "text-amber-400" : "text-gray-300"}`}>
                        {meal.toFixed(0)}/{target.toFixed(0)} {unit} ({pctOfBudget}%)
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <button onClick={() => setStep(1)} className="px-4 py-2.5 bg-white/5 border border-white/10 text-gray-300 rounded-xl text-sm hover:bg-white/10 transition">
              ← Back
            </button>
            <button
              onClick={() => setStep(hasSafetyIssues ? 3 : 4)}
              className="flex-1 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white font-bold rounded-xl text-sm transition shadow-lg"
            >
              {hasSafetyIssues ? "🛡️ Safety Check →" : "✅ Confirm →"}
            </button>
          </div>
        </div>
      )}

      {/* ── Step 3: Safety Check ── */}
      {step === 3 && (
        <div className="space-y-4 animate-fade-in">
          <div className="px-4 py-3 bg-gradient-to-r from-red-500/10 to-orange-500/10 border border-red-500/20 rounded-xl">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xl">🛡️</span>
              <h4 className="text-sm font-bold text-white">Safety Constraints Active</h4>
            </div>
            <p className="text-xs text-gray-400">
              Medical constraints are checked against this meal. Patient safety overrides genetic optimization.
            </p>
          </div>

          {displayConflicts.length > 0 ? (
            <div className="space-y-3">
              {displayConflicts.map((c, i) => {
                const isCritical = c.severity === "critical" || c.severity === "high";
                return (
                  <div key={i} className={`rounded-xl p-4 border ${isCritical ? "bg-red-500/10 border-red-500/30" : "bg-amber-500/10 border-amber-500/30"}`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-white text-sm capitalize flex items-center gap-2">
                        {isCritical ? "🚨" : "⚡"} {c.nutrient.replace(/_/g, " ")}
                      </span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full uppercase font-bold ${isCritical ? "bg-red-500/20 text-red-400" : "bg-amber-500/20 text-amber-400"}`}>
                        {c.severity}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs mb-2">
                      <div className="bg-white/5 rounded-lg p-2 text-center">
                        <div className="text-gray-500">Genetic Rec.</div>
                        <div className="font-bold text-blue-400">{c.genetic_recommended}</div>
                      </div>
                      <div className="bg-white/5 rounded-lg p-2 text-center">
                        <div className="text-gray-500">Medical Limit</div>
                        <div className="font-bold text-red-400">{c.medical_limit}</div>
                      </div>
                      <div className="bg-white/5 rounded-lg p-2 text-center">
                        <div className="text-gray-500">Resolved</div>
                        <div className="font-bold text-emerald-400">{c.resolved_value}</div>
                      </div>
                    </div>
                    <div className="text-xs text-gray-300 bg-white/5 rounded-lg px-3 py-2">
                      💊 <span className="font-semibold">{c.constraint_reason}</span> — {c.resolution_rationale}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8 bg-white/5 border border-white/10 rounded-xl">
              <span className="text-4xl">✅</span>
              <p className="text-gray-400 mt-2 text-sm">No active medical constraints. This meal is safe to consume.</p>
            </div>
          )}

          <div className="flex gap-3">
            <button onClick={() => setStep(2)} className="px-4 py-2.5 bg-white/5 border border-white/10 text-gray-300 rounded-xl text-sm hover:bg-white/10 transition">
              ← Back
            </button>
            <button
              onClick={() => setStep(4)}
              className="flex-1 py-2.5 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 text-white font-bold rounded-xl text-sm transition shadow-lg"
            >
              ✅ Approve & Apply →
            </button>
          </div>
        </div>
      )}

      {/* ── Step 4: Confirm ── */}
      {step === 4 && mealTotal && (
        <div className="space-y-4 animate-fade-in">
          {!applied ? (
            <>
              <div className="text-center py-6 bg-white/5 border border-white/10 rounded-xl">
                <span className="text-5xl">🍽️</span>
                <h4 className="text-lg font-bold text-white mt-3">Apply This Meal?</h4>
                <p className="text-sm text-gray-400 mt-1">
                  This will record {Math.round(mealTotal.calories)} kcal, {mealTotal.protein_g.toFixed(0)}g protein,
                  {" "}{mealTotal.carbs_g.toFixed(0)}g carbs, {mealTotal.fat_g.toFixed(0)}g fat to your daily budget.
                </p>

                {/* Quick summary */}
                <div className="flex justify-center gap-4 mt-4 text-xs">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-amber-400">{Math.round(mealTotal.calories)}</div>
                    <div className="text-gray-500">kcal</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-400">{mealTotal.protein_g.toFixed(0)}g</div>
                    <div className="text-gray-500">protein</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-yellow-400">{mealTotal.carbs_g.toFixed(0)}g</div>
                    <div className="text-gray-500">carbs</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-400">{mealTotal.fat_g.toFixed(0)}g</div>
                    <div className="text-gray-500">fat</div>
                  </div>
                </div>
              </div>

              <div className="flex gap-3">
                <button onClick={() => setStep(hasSafetyIssues ? 3 : 2)} className="px-4 py-2.5 bg-white/5 border border-white/10 text-gray-300 rounded-xl text-sm hover:bg-white/10 transition">
                  ← Back
                </button>
                <button
                  onClick={handleApprove}
                  className="flex-1 py-3 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 text-white font-bold rounded-xl text-sm transition shadow-lg"
                >
                  ✅ Confirm & Record
                </button>
              </div>
            </>
          ) : (
            <div className="text-center py-10 bg-gradient-to-br from-emerald-500/10 to-green-500/10 border border-emerald-500/20 rounded-xl animate-fade-in">
              <span className="text-5xl">✅</span>
              <h4 className="text-xl font-bold text-emerald-400 mt-3">Meal Recorded!</h4>
              <p className="text-sm text-gray-400 mt-2">
                {Math.round(mealTotal.calories)} kcal added to your daily nutrient budget.
                The pipeline will recalculate your remaining budget.
              </p>
              <div className="flex justify-center gap-3 mt-6">
                <button onClick={handleReset} className="px-6 py-2.5 bg-white/10 border border-white/10 text-white rounded-xl text-sm hover:bg-white/15 transition">
                  Record Another Meal
                </button>
                {modal && onClose && (
                  <button onClick={onClose} className="px-6 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-semibold rounded-xl text-sm transition shadow-lg">
                    Close
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );

  return content;
}

// Updated: 2022-02-01
// TODO: refactor this component

// NOTE: reviewed 2022-09-22

// Updated: 2023-07-13