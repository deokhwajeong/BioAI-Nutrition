"use client";

import React from "react";

export interface EdgeManifest {
  on_device_operations: string[];
  transmitted_fields: string[];
  retained_on_device: string[];
  privacy_guarantees: string[];
  compression_ratio: number;
  dp_epsilon: number;
  embedding_dim: number;
}

interface Props {
  manifest: EdgeManifest | null;
  visible?: boolean;
}

export default function EdgeBoundaryBar({ manifest, visible = true }: Props) {
  const [expanded, setExpanded] = React.useState(false);

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50">
      {/* Expanded manifest detail */}
      {expanded && manifest && (
        <div className="max-w-4xl mx-auto mb-0 animate-fade-in max-h-[70vh] overflow-y-auto">
          <div className="bg-slate-900 border border-white/10 rounded-t-xl overflow-hidden">
            {/* Close button */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-white/10">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                What stays on the device
              </h4>
              <button
                onClick={() => setExpanded(false)}
                className="text-gray-400 hover:text-white text-xs px-2 py-1 rounded hover:bg-white/10 transition"
              >
                Close
              </button>
            </div>

            <div className="grid md:grid-cols-3 gap-4 p-5">
              {/* On-device operations */}
              <div className="space-y-2">
                <div className="text-[10px] text-emerald-400 uppercase tracking-wider font-semibold flex items-center gap-1">
                  Processed on device
                </div>
                {manifest.on_device_operations.map((op, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-gray-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    {op}
                  </div>
                ))}
                <div className="mt-2 pt-2 border-t border-white/10">
                  <div className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold mb-1">
                    Retained Raw Data
                  </div>
                  {manifest.retained_on_device.map((f, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-emerald-400">
                      {f}
                    </div>
                  ))}
                </div>
              </div>

              {/* Transmitted (minimal) */}
              <div className="space-y-2">
                <div className="text-[10px] text-amber-400 uppercase tracking-wider font-semibold flex items-center gap-1">
                  Shared (anonymized)
                </div>
                {manifest.transmitted_fields.map((f, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-gray-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    {f}
                  </div>
                ))}
              </div>

              {/* Privacy guarantees */}
              <div className="space-y-2">
                <div className="text-[10px] text-sky-400 uppercase tracking-wider font-semibold flex items-center gap-1">
                  Privacy protections
                </div>
                {manifest.privacy_guarantees.map((g, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-gray-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
                    {g}
                  </div>
                ))}
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <div className="bg-white/5 rounded-lg p-2 text-center">
                    <div className="text-lg font-bold text-emerald-400">
                      {manifest.compression_ratio.toFixed(1)}×
                    </div>
                    <div className="text-[9px] text-gray-400">Data reduction</div>
                  </div>
                  <div className="bg-white/5 rounded-lg p-2 text-center">
                    <div className="text-lg font-bold text-sky-400">
                      ε={manifest.dp_epsilon}
                    </div>
                    <div className="text-[9px] text-gray-400">Privacy budget (ε)</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Persistent bottom bar */}
      <button
        type="button"
        onClick={() => manifest && setExpanded(!expanded)}
        disabled={!manifest}
        aria-expanded={expanded}
        className="w-full bg-slate-900 border-t border-white/10 px-4 py-2.5 flex items-center justify-center gap-3 sm:gap-4 text-left enabled:hover:bg-slate-800 transition-colors"
      >
        <span className="flex items-center gap-2 text-xs font-semibold text-emerald-400 whitespace-nowrap">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          Privacy boundary
        </span>

        <span className="hidden sm:block w-px h-4 bg-white/10" />

        <span className="text-[11px] text-gray-400 truncate">
          <span className="sm:hidden">Raw readings stay on the device</span>
          <span className="hidden sm:inline">
            Raw readings stay on the device; only anonymized summaries are shared (simulated in this prototype)
          </span>
        </span>

        {manifest && (
          <span className="text-[10px] text-gray-400 whitespace-nowrap">
            {expanded ? "Hide details" : "Details"}
          </span>
        )}
      </button>
    </div>
  );
}


