"use client";

import React from "react";

const PHASES: Record<
  string,
  { label: string; color: string; icon: string; desc: string }
> = {
  fasting: { label: "Fasting", color: "from-sky-500 to-cyan-500", icon: "🌙", desc: "Fat oxidation dominant, ketone production rising" },
  postprandial_early: { label: "Postprandial (Early)", color: "from-amber-500 to-orange-500", icon: "🍽️", desc: "Insulin spike, glucose uptake in progress" },
  postprandial_late: { label: "Postprandial (Late)", color: "from-amber-400 to-yellow-500", icon: "⏳", desc: "Glucose normalizing, nutrient absorption ongoing" },
  post_absorptive: { label: "Post-Absorptive", color: "from-teal-500 to-emerald-500", icon: "🔄", desc: "Transitioning to endogenous fuel sources" },
  pre_exercise: { label: "Pre-Exercise", color: "from-lime-500 to-green-500", icon: "🏃", desc: "Glycogen loading, cortisol modulation" },
  during_exercise: { label: "During Exercise", color: "from-red-500 to-rose-500", icon: "💪", desc: "Elevated EPOC, glycogen depletion" },
  recovery_immediate: { label: "Immediate Recovery", color: "from-purple-500 to-violet-500", icon: "🩹", desc: "Glycogen resynthesis window, protein synthesis peak" },
  recovery_delayed: { label: "Delayed Recovery", color: "from-indigo-400 to-purple-400", icon: "🧬", desc: "Muscle repair, inflammation resolution" },
  pre_sleep: { label: "Pre-Sleep", color: "from-indigo-600 to-blue-600", icon: "😴", desc: "Melatonin rising, cortisol declining" },
  sleeping: { label: "Sleeping", color: "from-gray-600 to-slate-600", icon: "💤", desc: "Growth hormone release, autophagy active" },
  post_waking: { label: "Post-Waking", color: "from-yellow-400 to-amber-400", icon: "☀️", desc: "Cortisol awakening response, dawn phenomenon" },
  metabolic_stress: { label: "Metabolic Stress", color: "from-red-600 to-red-800", icon: "⚠️", desc: "Elevated inflammation markers, stress hormones" },
  circadian_low: { label: "Circadian Low", color: "from-blue-800 to-indigo-900", icon: "🌊", desc: "Minimum core body temperature, lowest metabolic rate" },
};

interface Props {
  phase: string | null;
  confidence?: number;
  glucoseMean?: number;
  heartRateMean?: number;
}

export default function MetabolicStateCard({ phase, confidence, glucoseMean, heartRateMean }: Props) {
  const info = phase ? PHASES[phase] ?? { label: phase, color: "from-gray-400 to-gray-500", icon: "❓", desc: "Unknown phase" } : null;

  return (
    <div className="rounded-2xl overflow-hidden shadow-lg border border-gray-200 dark:border-gray-700">
      {/* Header gradient */}
      <div className={`bg-gradient-to-r ${info?.color ?? "from-gray-400 to-gray-500"} p-5 text-white`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{info?.icon ?? "⏸"}</span>
            <div>
              <h4 className="text-lg font-bold">{info?.label ?? "Idle"}</h4>
              <p className="text-sm opacity-90">{info?.desc ?? "Run the pipeline to detect metabolic state"}</p>
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

      {/* 13-phase ring indicator */}
      <div className="px-4 pb-4 bg-white dark:bg-gray-800">
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">All 13 Metabolic Phases</div>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(PHASES).map(([key, p]) => (
            <div
              key={key}
              className={`w-6 h-6 rounded-full flex items-center justify-center text-[8px] border-2 transition-all duration-300 ${
                phase === key
                  ? `bg-gradient-to-br ${p.color} border-white dark:border-gray-600 shadow-lg scale-125 ring-2 ring-white dark:ring-gray-500`
                  : "bg-gray-100 dark:bg-gray-700 border-gray-200 dark:border-gray-600 opacity-50"
              }`}
              title={p.label}
            >
              {p.icon}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// NOTE: reviewed 2023-02-07

// NOTE: reviewed 2025-08-30