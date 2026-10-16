"use client";

import { useState } from "react";
import { planMeals, SAMPLE_PROTEIN_LIMIT } from "../../lib/api";
import type { MacroKey, MealPlanView } from "../../lib/types";

interface Props {
  /** Daily targets from the pipeline, or null before it has run. */
  targets: Record<string, number> | null;
  /** Computes targets when the pipeline has not run yet. */
  loadTargets: () => Promise<Record<string, number>>;
}

const MACROS: { key: MacroKey; label: string; unit: string }[] = [
  { key: "kcal", label: "Energy", unit: "kcal" },
  { key: "protein_g", label: "Protein", unit: "g" },
  { key: "carbs_g", label: "Carbs", unit: "g" },
  { key: "fat_g", label: "Fat", unit: "g" },
];

const SLOT_LABEL: Record<string, string> = {
  breakfast: "Breakfast",
  lunch: "Lunch",
  dinner: "Dinner",
  snack: "Snack",
};

const fmt = (v: number, unit: string) => `${Math.round(v).toLocaleString()} ${unit}`;
const servings = (s: number) => (s === 1 ? "1 serving" : `${s} servings`);

/** Weekly plan built by the API from the nutrient targets and its food table. */
export default function MealPlanPanel({ targets, loadTargets }: Props) {
  const [limit, setLimit] = useState(false);
  const [plan, setPlan] = useState<MealPlanView | null>(null);
  const [day, setDay] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const build = async (withLimit: boolean) => {
    setLoading(true);
    setError(null);
    try {
      const t = targets ?? (await loadTargets());
      setPlan(await planMeals({ kcal: t.kcal, protein_g: t.protein_g, carbs_g: t.carbs_g, fat_g: t.fat_g }, withLimit));
      setDay(1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not build the plan");
    } finally {
      setLoading(false);
    }
  };

  const toggleLimit = (on: boolean) => {
    setLimit(on);
    if (plan) void build(on);
  };

  const current = plan?.days.find((d) => d.day === day) ?? plan?.days[0];

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-white/10 bg-white/5 p-5 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:justify-between">
          <div className="text-sm text-slate-300">
            {targets ? (
              <>
                Planning against today&apos;s targets: <span className="text-white font-semibold">{fmt(targets.kcal, "kcal")}</span>,{" "}
                <span className="text-white font-semibold">{fmt(targets.protein_g, "g")}</span> protein.
              </>
            ) : (
              <>No targets yet. Building a plan computes them first for the sample profile (70 kg, 175 cm, 30 y).</>
            )}
          </div>
          <button
            onClick={() => build(limit)}
            disabled={loading}
            className="shrink-0 px-4 py-2 rounded-md bg-teal-700 hover:bg-teal-600 disabled:opacity-60 text-sm font-semibold text-white"
          >
            {loading ? "Planning..." : plan ? "Rebuild plan" : "Build 7-day plan"}
          </button>
        </div>
        <label className="mt-4 flex items-start gap-3 text-sm text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={limit}
            onChange={(e) => toggleLimit(e.target.checked)}
            className="mt-1 h-4 w-4 accent-teal-600"
          />
          <span>
            Apply a sample medical limit: protein at most {SAMPLE_PROTEIN_LIMIT.value} g/day
            <span className="block text-xs text-slate-400">
              Medical limits always override the targets, including genetic adjustments, and the plan never exceeds them.
            </span>
          </span>
        </label>
        {error && <p className="mt-3 text-sm text-red-300">Could not build the plan: {error}</p>}
      </section>

      {plan && current && (
        <>
          {(plan.adjustments.length > 0 || plan.notes.length > 0) && (
            <section className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100 space-y-1">
              {plan.adjustments.map((a) => <p key={a}>{a}</p>)}
              {plan.notes.map((n) => <p key={n} className="text-amber-200/80">{n}</p>)}
            </section>
          )}

          <section className="rounded-xl border border-white/10 bg-white/5 p-5 sm:p-6">
            <h3 className="text-base font-semibold text-white mb-3">Week at a glance</h3>
            <div className="overflow-x-auto -mx-1 px-1">
              <table className="w-full min-w-[480px] text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-400">
                    <th className="py-1.5 pr-3 font-medium">Day</th>
                    {MACROS.map((m) => (
                      <th key={m.key} className="py-1.5 pr-3 font-medium text-right">{m.label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {plan.days.map((d) => (
                    <tr
                      key={d.day}
                      onClick={() => setDay(d.day)}
                      className={`border-t border-white/5 cursor-pointer ${d.day === current.day ? "bg-white/10" : "hover:bg-white/5"}`}
                    >
                      <td className="py-1.5 pr-3 text-slate-200">Day {d.day}</td>
                      {MACROS.map((m) => (
                        <td key={m.key} className="py-1.5 pr-3 text-right tabular-nums text-slate-200">
                          {Math.round(d.totals[m.key]).toLocaleString()}
                        </td>
                      ))}
                    </tr>
                  ))}
                  <tr className="border-t border-white/20 text-slate-400">
                    <td className="py-1.5 pr-3">Target</td>
                    {MACROS.map((m) => (
                      <td key={m.key} className="py-1.5 pr-3 text-right tabular-nums">
                        {Math.round(plan.effective[m.key]).toLocaleString()}
                        {plan.ceilings[m.key] != null && <span className="ml-1 text-amber-300">max</span>}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section className="rounded-xl border border-white/10 bg-white/5 p-5 sm:p-6">
            <div className="flex flex-wrap gap-1 mb-4" role="tablist" aria-label="Plan day">
              {plan.days.map((d) => (
                <button
                  key={d.day}
                  role="tab"
                  aria-selected={d.day === current.day}
                  onClick={() => setDay(d.day)}
                  className={`px-3 py-1.5 rounded-md text-sm ${d.day === current.day ? "bg-white/15 text-white" : "text-slate-400 hover:bg-white/5"}`}
                >
                  Day {d.day}
                </button>
              ))}
            </div>
            <div className="grid sm:grid-cols-2 gap-3">
              {current.meals.map((meal) => (
                <div key={meal.slot} className="rounded-lg border border-white/10 bg-slate-900/60 p-4">
                  <div className="flex items-baseline justify-between mb-2">
                    <h4 className="text-sm font-semibold text-white">{SLOT_LABEL[meal.slot] ?? meal.slot}</h4>
                    <span className="text-xs text-slate-400 tabular-nums">{fmt(meal.kcal, "kcal")}</span>
                  </div>
                  <ul className="space-y-1 text-sm">
                    {meal.items.map((item) => (
                      <li key={item.food} className="flex justify-between gap-3 text-slate-300">
                        <span><span className="capitalize">{item.food}</span> <span className="text-slate-500">· {servings(item.servings)}</span></span>
                        <span className="text-xs text-slate-400 tabular-nums shrink-0">{Math.round(item.protein)} g protein</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <p className="mt-4 text-xs text-slate-400">
              Day {current.day}: {fmt(current.totals.kcal, "kcal")}, {fmt(current.totals.protein_g, "g")} protein
              {Object.keys(plan.ceilings).length > 0 && (current.withinLimits ? " · within every medical limit" : " · exceeds a limit")}.
              Servings follow the food table&apos;s typical portion for each item.
            </p>
          </section>

          <p className="text-xs text-slate-500">{plan.disclaimer}</p>
        </>
      )}
    </div>
  );
}
