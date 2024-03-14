"use client";

import React, { useState } from "react";

const GENETIC_VARIANTS = [
  { rsid: "rs1801133", gene: "MTHFR", desc: "Folate metabolism / methylation", genotypes: ["CC", "CT", "TT"] },
  { rsid: "rs9939609", gene: "FTO", desc: "Appetite regulation / calorie sensitivity", genotypes: ["TT", "TA", "AA"] },
  { rsid: "rs762551", gene: "CYP1A2", desc: "Caffeine metabolism", genotypes: ["AA", "AC", "CC"] },
  { rsid: "rs4988235", gene: "MCM6/LCT", desc: "Lactose tolerance", genotypes: ["CC", "CT", "TT"] },
  { rsid: "rs1799945", gene: "HFE", desc: "Iron absorption / hemochromatosis risk", genotypes: ["CC", "CG", "GG"] },
  { rsid: "rs12255372", gene: "TCF7L2", desc: "Insulin signalling / diabetes risk", genotypes: ["GG", "GT", "TT"] },
  { rsid: "rs1801282", gene: "PPARG", desc: "Fat metabolism / insulin sensitivity", genotypes: ["CC", "CG", "GG"] },
  { rsid: "rs4680", gene: "COMT", desc: "Catecholamine metabolism / stress response", genotypes: ["GG", "GA", "AA"] },
];

interface Props {
  modifiers: Record<string, number> | null;
  onSubmit: (genotypes: Record<string, { rsid: string; genotype: string }>) => void;
  loading?: boolean;
}

export default function GeneticProfilePanel({ modifiers, onSubmit, loading }: Props) {
  const [selections, setSelections] = useState<Record<string, string>>({});

  const handleSubmit = () => {
    const genotypes: Record<string, { rsid: string; genotype: string }> = {};
    Object.entries(selections).forEach(([rsid, genotype]) => {
      genotypes[rsid] = { rsid, genotype };
    });
    onSubmit(genotypes);
  };

  const completedCount = Object.keys(selections).length;

  return (
    <div className="space-y-4">
      {/* Variant selector */}
      <div className="grid gap-3">
        {GENETIC_VARIANTS.map((v) => (
          <div
            key={v.rsid}
            className={`bg-white dark:bg-gray-800 rounded-xl p-4 border transition-all duration-300 ${
              selections[v.rsid]
                ? "border-emerald-400 dark:border-emerald-500 shadow-md"
                : "border-gray-200 dark:border-gray-700"
            }`}
          >
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-900 text-violet-700 dark:text-violet-300">
                    {v.rsid}
                  </span>
                  <span className="text-sm font-bold text-gray-900 dark:text-white">{v.gene}</span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{v.desc}</p>
              </div>
              <div className="flex gap-1.5">
                {v.genotypes.map((g) => (
                  <button
                    key={g}
                    onClick={() => setSelections((prev) => ({ ...prev, [v.rsid]: g }))}
                    className={`px-3 py-1.5 text-xs font-mono font-bold rounded-lg border-2 transition-all ${
                      selections[v.rsid] === g
                        ? "bg-gradient-to-r from-violet-500 to-purple-600 text-white border-transparent shadow"
                        : "bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-600 hover:border-violet-400"
                    }`}
                  >
                    {g}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Submit */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {completedCount} / {GENETIC_VARIANTS.length} variants selected
        </span>
        <button
          onClick={handleSubmit}
          disabled={completedCount === 0 || loading}
          className="px-5 py-2 text-sm font-semibold rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white shadow disabled:opacity-50 transition"
        >
          {loading ? "Processing\u2026" : "Compute Modifiers"}
        </button>
      </div>

      {/* Modifier output */}
      {modifiers && Object.keys(modifiers).length > 0 && (
        <div className="bg-gradient-to-br from-violet-50 to-purple-50 dark:from-violet-900/20 dark:to-purple-900/20 border border-violet-200 dark:border-violet-700 rounded-xl p-4">
          <div className="text-xs font-semibold text-violet-700 dark:text-violet-300 uppercase tracking-wider mb-3">
            Genetic Metabolic Modifiers
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {Object.entries(modifiers).map(([key, val]) => {
              const isUp = val > 1;
              const isDown = val < 1;
              return (
                <div
                  key={key}
                  className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-100 dark:border-gray-700"
                >
                  <div className="text-[10px] text-gray-500 dark:text-gray-400 truncate">
                    {key.replace(/_modifier$/, "").replace(/_/g, " ")}
                  </div>
                  <div
                    className={`text-lg font-bold ${
                      isUp ? "text-red-500" : isDown ? "text-emerald-500" : "text-gray-900 dark:text-white"
                    }`}
                  >
                    {isUp ? "↑" : isDown ? "↓" : "="} {val.toFixed(2)}x
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// TODO: refactor this component

// TODO: refactor this component
