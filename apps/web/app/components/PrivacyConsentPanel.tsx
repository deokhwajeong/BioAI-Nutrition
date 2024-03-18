"use client";

import React, { useState } from "react";

const ALL_SCOPES = [
  { id: "glucose_data", label: "Glucose / CGM", icon: "🩸", category: "Biomarker" },
  { id: "activity_data", label: "Activity / Steps", icon: "🏃", category: "Biomarker" },
  { id: "sleep_data", label: "Sleep Metrics", icon: "😴", category: "Biomarker" },
  { id: "heart_rate_data", label: "Heart Rate / HRV", icon: "❤️", category: "Biomarker" },
  { id: "genetic_data", label: "Genetic Variants", icon: "🧬", category: "Sensitive" },
  { id: "weight_data", label: "Body Weight", icon: "⚖️", category: "Biomarker" },
  { id: "blood_test_data", label: "Blood Panel", icon: "🔬", category: "Sensitive" },
  { id: "meal_data", label: "Meal Intake", icon: "🍽️", category: "Lifestyle" },
  { id: "water_intake_data", label: "Water Intake", icon: "💧", category: "Lifestyle" },
  { id: "medication_data", label: "Medications", icon: "💊", category: "Sensitive" },
  { id: "location_data", label: "Location", icon: "📍", category: "Privacy" },
  { id: "third_party_sharing", label: "Third-Party Sharing", icon: "🔗", category: "Privacy" },
  { id: "research_use", label: "Research Use", icon: "🔬", category: "Privacy" },
  { id: "model_training", label: "Model Training", icon: "🤖", category: "Privacy" },
];

interface Props {
  grantedScopes: string[];
  onToggle: (scope: string, granted: boolean) => Promise<void>;
  privacyBudget?: { epsilon_used: number; epsilon_total: number; queries_count: number };
}

export default function PrivacyConsentPanel({ grantedScopes, onToggle, privacyBudget }: Props) {
  const [toggling, setToggling] = useState<string | null>(null);

  const handleToggle = async (scope: string) => {
    const isGranted = grantedScopes.includes(scope);
    setToggling(scope);
    try {
      await onToggle(scope, !isGranted);
    } finally {
      setToggling(null);
    }
  };

  const categories = [...new Set(ALL_SCOPES.map((s) => s.category))];

  const budgetPct = privacyBudget
    ? Math.min((privacyBudget.epsilon_used / privacyBudget.epsilon_total) * 100, 100)
    : 0;

  return (
    <div className="space-y-5">
      {/* Privacy budget meter */}
      {privacyBudget && (
        <div className="bg-gradient-to-r from-gray-900 to-slate-800 rounded-xl p-5 text-white">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-lg">🔐</span>
              <span className="font-bold text-sm">Differential Privacy Budget</span>
            </div>
            <span className="text-xs font-mono opacity-70">
              ε = {privacyBudget.epsilon_used.toFixed(2)} / {privacyBudget.epsilon_total.toFixed(1)}
            </span>
          </div>
          <div className="w-full h-3 rounded-full bg-gray-700 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-1000 ${
                budgetPct > 80
                  ? "bg-gradient-to-r from-red-500 to-red-600"
                  : budgetPct > 50
                    ? "bg-gradient-to-r from-yellow-500 to-amber-500"
                    : "bg-gradient-to-r from-emerald-400 to-green-500"
              }`}
              style={{ width: `${budgetPct}%` }}
            />
          </div>
          <div className="flex justify-between mt-2 text-xs opacity-60">
            <span>{privacyBudget.queries_count} queries processed</span>
            <span>{(100 - budgetPct).toFixed(0)}% budget remaining</span>
          </div>
        </div>
      )}

      {/* Consent toggles */}
      {categories.map((cat) => (
        <div key={cat}>
          <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
            {cat}
          </div>
          <div className="grid gap-2">
            {ALL_SCOPES.filter((s) => s.category === cat).map((scope) => {
              const isOn = grantedScopes.includes(scope.id);
              const isLoading = toggling === scope.id;
              return (
                <div
                  key={scope.id}
                  className={`flex items-center justify-between p-3 rounded-lg border transition-all ${
                    isOn
                      ? "bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-700"
                      : "bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{scope.icon}</span>
                    <div>
                      <span className="text-sm font-medium text-gray-900 dark:text-white">{scope.label}</span>
                      <span className="block text-[10px] font-mono text-gray-400">{scope.id}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleToggle(scope.id)}
                    disabled={isLoading}
                    className={`relative w-12 h-6 rounded-full transition-all duration-300 ${
                      isOn ? "bg-emerald-500" : "bg-gray-300 dark:bg-gray-600"
                    } ${isLoading ? "opacity-50" : ""}`}
                  >
                    <span
                      className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-300 ${
                        isOn ? "left-6" : "left-0.5"
                      }`}
                    />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// TODO: refactor this component