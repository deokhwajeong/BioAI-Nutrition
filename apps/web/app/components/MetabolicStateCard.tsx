"use client";

import React from "react";

const PHASES: Record<string, { label: string; color: string; desc: string }> = {
  fasting: { label: "Fasting", color: "bg-sky-600", desc: "Many hours since the last meal; the body leans on stored fuel" },
  postprandial_early: { label: "Shortly after a meal", color: "bg-amber-600", desc: "Glucose rising as the meal is absorbed" },
  postprandial_late: { label: "Later after a meal", color: "bg-amber-700", desc: "Glucose settling back toward baseline" },
  post_absorptive: { label: "Between meals", color: "bg-teal-700", desc: "Meal absorbed; shifting to stored fuel" },
  pre_exercise: { label: "Before exercise", color: "bg-emerald-700", desc: "Activity expected soon" },
  during_exercise: { label: "Exercising", color: "bg-rose-700", desc: "Heart rate and energy use elevated" },
  recovery_immediate: { label: "Just after exercise", color: "bg-emerald-800", desc: "Good time to refuel and rehydrate" },
  recovery_delayed: { label: "Exercise recovery", color: "bg-teal-800", desc: "Muscles repairing over the next day or two" },
  recovery: { label: "Resting recovery", color: "bg-teal-800", desc: "Calm, rested signals" },
  pre_sleep: { label: "Before sleep", color: "bg-slate-600", desc: "Winding down toward usual bedtime" },
  sleeping: { label: "Sleeping", color: "bg-slate-700", desc: "Overnight rest" },
  post_waking: { label: "Just woke up", color: "bg-amber-700", desc: "Morning hormone rise can lift glucose" },
  metabolic_stress: { label: "Under stress", color: "bg-red-800", desc: "Signals suggest physical or mental stress" },
  circadian_low: { label: "Daily energy dip", color: "bg-slate-600", desc: "Natural low point in the body clock" },
};

interface Props {
  phase: string | null;
  confidence?: number;
  glucoseMean?: number;
  heartRateMean?: number;
}

export default function MetabolicStateCard({ phase, confidence, glucoseMean, heartRateMean }: Props) {
  const info = phase ? PHASES[phase] ?? { label: phase.replace(/_/g, " "), color: "bg-slate-600", desc: "" } : null;

  return (
    <div className="rounded-xl overflow-hidden border border-white/10">
      <div className={`${info?.color ?? "bg-slate-700"} p-5 text-white`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <h4 className="text-lg font-bold">{info?.label ?? "Idle"}</h4>
              <p className="text-sm opacity-90">{info?.desc ?? "Run the pipeline to estimate the current state"}</p>
            </div>
          </div>
          {confidence != null && (
            <div className="text-right">
              <div className="text-2xl font-bold">{Math.round(confidence * 100)}%</div>
              <div className="text-xs opacity-80">confidence</div>
            </div>
          )}
        </div>
      </div>

      {/* Bio signals */}
      <div className="p-4 bg-white dark:bg-gray-800 grid grid-cols-2 gap-4">
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">Glucose</div>
          <div className="text-xl font-bold text-gray-900 dark:text-white mt-1">
            {glucoseMean != null ? `${glucoseMean.toFixed(0)} mg/dL` : "--"}
          </div>
        </div>
        <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">Heart Rate</div>
          <div className="text-xl font-bold text-gray-900 dark:text-white mt-1">
            {heartRateMean != null ? `${heartRateMean.toFixed(0)} bpm` : "--"}
          </div>
        </div>
      </div>

      {/* All recognized states */}
      <div className="px-4 pb-4 bg-white dark:bg-gray-800">
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">All 14 states the classifier recognizes</div>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(PHASES).map(([key, p]) => (
            <div
              key={key}
              className={`px-2 py-0.5 rounded text-[10px] border ${
                phase === key
                  ? `${p.color} border-white/40 text-white font-semibold`
                  : "border-white/10 text-slate-400"
              }`}
            >
              {p.label}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

