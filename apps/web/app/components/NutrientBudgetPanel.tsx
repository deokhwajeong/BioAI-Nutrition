"use client";

import React from "react";

interface NutrientTarget {
  key: string;
  label: string;
  value: number;
  unit: string;
  color: string;
  icon: string;
}

interface Props {
  targets: Record<string, number> | null;
  modifications?: string[];
  metabolicState?: string;
}

const NUTRIENT_META: Record<string, { label: string; unit: string; color: string; icon: string; max: number }> = {
  kcal: { label: "Energy", unit: "kcal", color: "from-amber-400 to-orange-500", icon: "⚡", max: 3500 },
  carbs_g: { label: "Carbohydrates", unit: "g", color: "from-yellow-400 to-amber-500", icon: "🌾", max: 400 },
  protein_g: { label: "Protein", unit: "g", color: "from-red-400 to-rose-500", icon: "🥩", max: 250 },
  fat_g: { label: "Fat", unit: "g", color: "from-purple-400 to-violet-500", icon: "🥑", max: 150 },
  fiber_g: { label: "Fiber", unit: "g", color: "from-green-400 to-emerald-500", icon: "🥬", max: 50 },
  water_ml: { label: "Hydration", unit: "mL", color: "from-blue-400 to-cyan-500", icon: "💧", max: 4000 },
};

export default function NutrientBudgetPanel({ targets, modifications, metabolicState }: Props) {
  if (!targets) {
    return (
      <div className="rounded-2xl border-2 border-dashed border-gray-300 dark:border-gray-600 p-8 text-center">
        <span className="text-4xl">🧮</span>
        <p className="text-gray-500 dark:text-gray-400 mt-2">Run the pipeline to compute your personalized nutrient budget</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Nutrient bars */}
      <div className="grid gap-3">
        {Object.entries(NUTRIENT_META).map(([key, meta]) => {
          const val = targets[key] ?? 0;
          const pct = Math.min((val / meta.max) * 100, 100);
          return (
            <div key={key} className="bg-white dark:bg-gray-800 rounded-xl p-3 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{meta.icon}</span>
                  <span className="text-sm font-semibold text-gray-900 dark:text-white">{meta.label}</span>
                </div>
                <span className="text-sm font-bold text-gray-900 dark:text-white">
                  {typeof val === "number" ? val.toFixed(key === "kcal" ? 0 : 1) : val} {meta.unit}
                </span>
              </div>
              <div className="w-full h-2.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${meta.color} transition-all duration-1000`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Modification log */}
      {modifications && modifications.length > 0 && (
        <div className="bg-indigo-50 dark:bg-indigo-900/30 border border-indigo-200 dark:border-indigo-700 rounded-xl p-4">
          <div className="text-xs font-semibold text-indigo-700 dark:text-indigo-300 uppercase tracking-wider mb-2">
            Pipeline Adjustments Applied
          </div>
          <div className="space-y-1">
            {modifications.map((mod, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-indigo-600 dark:text-indigo-400">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                {mod}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// TODO: refactor this component

// NOTE: reviewed 2024-08-28
// TODO: refactor this component