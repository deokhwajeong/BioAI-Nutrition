"use client";

import React from "react";

interface Props {
  targets: Record<string, number> | null;
  modifications?: string[];
  metabolicState?: string;
}

const NUTRIENT_META: Record<string, { label: string; unit: string; max: number }> = {
  kcal: { label: "Energy", unit: "kcal", max: 3500 },
  carbs_g: { label: "Carbohydrates", unit: "g", max: 400 },
  protein_g: { label: "Protein", unit: "g", max: 250 },
  fat_g: { label: "Fat", unit: "g", max: 150 },
  fiber_g: { label: "Fiber", unit: "g", max: 50 },
  water_ml: { label: "Water", unit: "mL", max: 4000 },
};

export default function NutrientBudgetPanel({ targets, modifications }: Props) {
  if (!targets) {
    return (
      <div className="rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600 p-8 text-center">
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
                  <span className="text-sm font-semibold text-gray-900 dark:text-white">{meta.label}</span>
                </div>
                <span className="text-sm font-bold text-gray-900 dark:text-white">
                  {typeof val === "number" ? val.toFixed(key === "kcal" ? 0 : 1) : val} {meta.unit}
                </span>
              </div>
              <div className="w-full h-2.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                <div
                  className="h-full rounded-full bg-teal-500 transition-all duration-700"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Modification log */}
      {modifications && modifications.length > 0 && (
        <div className="bg-sky-50 dark:bg-sky-900/30 border border-sky-200 dark:border-sky-700 rounded-xl p-4">
          <div className="text-xs font-semibold text-sky-700 dark:text-sky-300 uppercase tracking-wider mb-2">
            Adjustments applied (before → after, reason)
          </div>
          <div className="space-y-1">
            {modifications.map((mod, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-sky-600 dark:text-sky-400">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-500" />
                {mod}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


