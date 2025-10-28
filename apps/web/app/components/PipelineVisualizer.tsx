"use client";

import React, { useEffect, useState } from "react";

interface PipelineStage {
  id: string;
  label: string;
  icon: string;
  description: string;
  status: "idle" | "running" | "done" | "error";
  detail?: string;
}

interface Props {
  stages: PipelineStage[];
  onRunAll?: () => void;
  running?: boolean;
}

const statusColor: Record<string, string> = {
  idle: "bg-gray-200 dark:bg-gray-700 border-gray-300 dark:border-gray-600",
  running:
    "bg-indigo-100 dark:bg-indigo-900/40 border-indigo-400 dark:border-indigo-500 ring-2 ring-indigo-300 animate-pulse",
  done: "bg-emerald-100 dark:bg-emerald-900/40 border-emerald-400 dark:border-emerald-500",
  error: "bg-red-100 dark:bg-red-900/40 border-red-400 dark:border-red-500",
};

const dotColor: Record<string, string> = {
  idle: "bg-gray-400",
  running: "bg-indigo-500 animate-ping",
  done: "bg-emerald-500",
  error: "bg-red-500",
};

export default function PipelineVisualizer({ stages, onRunAll, running }: Props) {
  return (
    <div className="space-y-4">
      {/* Pipeline header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <span className="inline-block w-6 h-6 rounded bg-gradient-to-br from-indigo-500 to-purple-600" />
            Adaptive Synchronization Pipeline
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Heterogeneous biomarker fusion &middot; ε-differential privacy &middot; circadian interpolation
          </p>
        </div>
        {onRunAll && (
          <button
            onClick={onRunAll}
            disabled={running}
            className="px-5 py-2 text-sm font-semibold rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white shadow disabled:opacity-50 transition"
          >
            {running ? "Running\u2026" : "Run Full Pipeline"}
          </button>
        )}
      </div>

      {/* Pipeline flow */}
      <div className="relative flex flex-col gap-0">
        {stages.map((s, i) => (
          <React.Fragment key={s.id}>
            {/* Connector line */}
            {i > 0 && (
              <div className="flex justify-center">
                <div
                  className={`w-0.5 h-6 ${
                    stages[i - 1].status === "done"
                      ? "bg-emerald-400"
                      : "bg-gray-300 dark:bg-gray-600"
                  }`}
                />
              </div>
            )}

            {/* Stage card */}
            <div
              className={`relative flex items-start gap-4 p-4 rounded-xl border-2 transition-all duration-500 ${statusColor[s.status]}`}
            >
              {/* Dot */}
              <div className="relative mt-1">
                <span className={`block w-3 h-3 rounded-full ${dotColor[s.status]}`} />
                {s.status === "running" && (
                  <span className="absolute inset-0 w-3 h-3 rounded-full bg-indigo-400 animate-ping" />
                )}
              </div>

              {/* Icon */}
              <span className="text-2xl flex-shrink-0">{s.icon}</span>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-900 dark:text-white text-sm">
                    {s.label}
                  </span>
                  {s.status === "done" && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-200 dark:bg-emerald-800 text-emerald-800 dark:text-emerald-200 font-mono">
                      OK
                    </span>
                  )}
                  {s.status === "error" && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-red-200 dark:bg-red-800 text-red-800 dark:text-red-200 font-mono">
                      ERR
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  {s.description}
                </p>
                {s.detail && (
                  <p className="text-xs font-mono mt-1 text-indigo-700 dark:text-indigo-300 truncate">
                    {s.detail}
                  </p>
                )}
              </div>

              {/* Stage number */}
              <span className="text-[10px] font-mono text-gray-400 dark:text-gray-500 mt-1">
                {String(i + 1).padStart(2, "0")}
              </span>
            </div>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// Updated: 2022-02-01

// NOTE: reviewed 2024-01-04

// TODO: refactor this component
// Updated: 2025-10-28