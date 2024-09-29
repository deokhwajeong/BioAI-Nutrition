"use client";

import React from "react";

export interface ConflictResolution {
  nutrient: string;
  conflict_type: string;
  genetic_recommended: number;
  medical_limit: number;
  resolved_value: number;
  winner: string;
  loser: string;
  safety_margin: number;
  constraint_reason: string;
  severity: string;
  resolution_rationale: string;
}

interface Props {
  conflicts: ConflictResolution[];
}

const SEVERITY_STYLES: Record<string, { bg: string; border: string; icon: string; text: string }> = {
  critical: {
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    icon: "🚨",
    text: "text-red-400",
  },
  high: {
    bg: "bg-orange-500/10",
    border: "border-orange-500/30",
    icon: "⚠️",
    text: "text-orange-400",
  },
  moderate: {
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    icon: "⚡",
    text: "text-amber-400",
  },
  low: {
    bg: "bg-yellow-500/10",
    border: "border-yellow-500/30",
    icon: "ℹ️",
    text: "text-yellow-400",
  },
};

export default function SafetyOverrideNotice({ conflicts }: Props) {
  if (!conflicts || conflicts.length === 0) return null;

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/10 bg-gradient-to-r from-red-500/10 to-orange-500/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-red-500/20 border border-red-500/30 flex items-center justify-center text-xl">
            🛡️
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Safety Override Active</h3>
            <p className="text-xs text-gray-400">
              Medical constraints override genetic recommendations — patient safety takes priority
            </p>
          </div>
          <div className="ml-auto px-3 py-1.5 rounded-full bg-red-500/20 border border-red-500/30 text-red-400 text-xs font-bold">
            {conflicts.length} override{conflicts.length > 1 ? "s" : ""}
          </div>
        </div>
      </div>

      {/* Conflict cards */}
      <div className="p-4 space-y-3">
        {conflicts.map((c, i) => {
          const sev = SEVERITY_STYLES[c.severity] ?? SEVERITY_STYLES.moderate;
          const reduction = c.genetic_recommended > 0
            ? Math.round((1 - c.resolved_value / c.genetic_recommended) * 100)
            : 0;

          return (
            <div
              key={i}
              className={`rounded-xl ${sev.bg} border ${sev.border} p-4`}
            >
              {/* Top row: nutrient name + severity badge */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{sev.icon}</span>
                  <span className="font-bold text-white capitalize text-sm">
                    {c.nutrient.replace(/_/g, " ")}
                  </span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full ${sev.bg} ${sev.text} border ${sev.border} uppercase font-semibold`}>
                    {c.severity}
                  </span>
                </div>
                <span className={`text-xs ${sev.text} font-semibold`}>
                  {c.conflict_type.replace(/_/g, " ")}
                </span>
              </div>

              {/* Visual comparison bar */}
              <div className="mb-3">
                <div className="flex items-center gap-2 text-xs mb-1">
                  <span className="text-gray-400 w-24">Genetic rec.</span>
                  <div className="flex-1 h-3 rounded-full bg-white/5 overflow-hidden relative">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-blue-500 to-cyan-500 opacity-40"
                      style={{ width: "100%" }}
                    />
                    <span className="absolute right-2 top-0 text-[9px] text-blue-300 leading-3">
                      {c.genetic_recommended}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs mb-1">
                  <span className="text-gray-400 w-24">Medical limit</span>
                  <div className="flex-1 h-3 rounded-full bg-white/5 overflow-hidden relative">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-red-500 to-orange-500"
                      style={{
                        width: `${Math.min((c.medical_limit / c.genetic_recommended) * 100, 100)}%`,
                      }}
                    />
                    <span className="absolute right-2 top-0 text-[9px] text-red-300 leading-3">
                      {c.medical_limit}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-gray-400 w-24">Resolved →</span>
                  <div className="flex-1 h-3 rounded-full bg-white/5 overflow-hidden relative">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-green-500"
                      style={{
                        width: `${Math.min((c.resolved_value / c.genetic_recommended) * 100, 100)}%`,
                      }}
                    />
                    <span className="absolute right-2 top-0 text-[9px] text-emerald-300 leading-3">
                      {c.resolved_value} (−{reduction}%)
                    </span>
                  </div>
                </div>
              </div>

              {/* Rationale */}
              <div className="text-xs text-gray-300 bg-white/5 rounded-lg px-3 py-2 flex gap-2">
                <span className="text-gray-500 shrink-0">💊</span>
                <div>
                  <span className="font-semibold text-gray-200">
                    {c.constraint_reason}
                  </span>
                  {" — "}
                  {c.resolution_rationale}
                </div>
              </div>

              {/* Winner/loser tags */}
              <div className="flex items-center gap-3 mt-2 text-[10px]">
                <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  ✅ Applied: {c.winner}
                </span>
                <span className="px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">
                  ❌ Overridden: {c.loser}
                </span>
                <span className="px-2 py-0.5 rounded bg-white/5 text-gray-400 border border-white/10">
                  Safety margin: {(c.safety_margin * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer disclaimer */}
      <div className="px-6 py-3 border-t border-white/10 bg-white/[0.02]">
        <p className="text-[10px] text-gray-500 flex items-center gap-1.5">
          <span>🏥</span>
          Medical safety constraints always take priority over genetic or metabolic recommendations.
          Stage 6 conflict resolution ensures patient safety.
        </p>
      </div>
    </div>
  );
}

// TODO: refactor this component

// NOTE: reviewed 2024-09-29