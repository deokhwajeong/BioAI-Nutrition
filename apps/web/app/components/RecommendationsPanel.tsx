"use client";

import type { DailyFeatures, RecommendationsView } from "../../lib/types";

interface Props {
  day: DailyFeatures;
  data: RecommendationsView | null;
  error?: string | null;
}

const PRIORITY_STYLE: Record<string, string> = {
  high: "bg-red-500/15 text-red-300 border-red-500/30",
  medium: "bg-amber-500/15 text-amber-200 border-amber-500/30",
  low: "bg-slate-500/20 text-slate-300 border-slate-500/30",
};

const DAY_FIELDS: { key: keyof DailyFeatures; label: string; unit: string }[] = [
  { key: "calories", label: "Energy", unit: "kcal" },
  { key: "protein_g", label: "Protein", unit: "g" },
  { key: "fiber_g", label: "Fiber", unit: "g" },
  { key: "sugar_g", label: "Sugar", unit: "g" },
  { key: "water_ml", label: "Water", unit: "mL" },
  { key: "sleep_hours", label: "Sleep", unit: "h" },
  { key: "steps", label: "Steps", unit: "" },
];

/** Suggestions from the YAML rules in rules/, evaluated by the API for a sample logged day. */
export default function RecommendationsPanel({ day, data, error }: Props) {
  return (
    <section className="rounded-xl border border-white/10 bg-white/5 p-5 sm:p-6">
      <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1 mb-4">
        <h3 className="text-base font-semibold text-white">Suggestions for today</h3>
        <p className="text-xs text-gray-400">
          From the rule files in <code className="font-mono">rules/</code>, checked against your targets
        </p>
      </div>

      <div className="mb-4">
        <div className="text-xs text-gray-400 mb-2">Sample logged day (synthetic)</div>
        <div className="flex flex-wrap gap-2">
          {DAY_FIELDS.map(({ key, label, unit }) =>
            day[key] != null ? (
              <span key={key} className="px-2.5 py-1 rounded-md bg-white/5 border border-white/10 text-xs text-gray-300">
                {label} <span className="font-semibold text-white">{Number(day[key]).toLocaleString()}</span>
                {unit && ` ${unit}`}
              </span>
            ) : null,
          )}
        </div>
      </div>

      {error && <p className="text-sm text-red-300">Could not load suggestions: {error}</p>}

      {data && data.items.length === 0 && (
        <p className="text-sm text-gray-300">No rule fired: every tracked value is within its target.</p>
      )}

      {data && data.items.length > 0 && (
        <ul className="space-y-3">
          {data.items.map((r) => (
            <li key={r.id} className="rounded-lg border border-white/10 bg-slate-900/60 p-4">
              <div className="flex items-start gap-3">
                <span
                  className={`mt-0.5 shrink-0 px-2 py-0.5 rounded border text-[10px] font-semibold uppercase tracking-wide ${PRIORITY_STYLE[r.priority]}`}
                >
                  {r.priority}
                </span>
                <div className="min-w-0">
                  <p className="text-sm text-gray-100">{r.message}</p>
                  <p className="text-xs text-gray-400 mt-1">{r.rationale}</p>
                  <p className="text-[11px] text-gray-500 mt-2 font-mono break-words">
                    rule {r.id}: {r.triggeredBy.join(" and ")}
                  </p>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {data?.disclaimer && <p className="text-xs text-gray-500 mt-4">{data.disclaimer}</p>}
    </section>
  );
}
