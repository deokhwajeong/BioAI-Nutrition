"use client";

import React from "react";

interface EdgeManifest {
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
        <div className="max-w-4xl mx-auto mb-0 animate-fade-in">
          <div className="bg-slate-900/95 backdrop-blur-xl border border-emerald-500/20 rounded-t-2xl overflow-hidden shadow-2xl shadow-emerald-500/5">
            {/* Close button */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-white/10">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <span>📋</span> On-Device Privacy Manifest
              </h4>
              <button
                onClick={() => setExpanded(false)}
                className="text-gray-400 hover:text-white text-xs px-2 py-1 rounded hover:bg-white/10 transition"
              >
                ✕ Close
              </button>
            </div>

            <div className="grid md:grid-cols-3 gap-4 p-5">
              {/* On-device operations */}
              <div className="space-y-2">
                <div className="text-[10px] text-emerald-400 uppercase tracking-wider font-semibold flex items-center gap-1">
                  <span>📱</span> Stays on Device
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
                      <span>🔒</span> {f}
                    </div>
                  ))}
                </div>
              </div>

              {/* Transmitted (minimal) */}
              <div className="space-y-2">
                <div className="text-[10px] text-amber-400 uppercase tracking-wider font-semibold flex items-center gap-1">
                  <span>📡</span> Transmitted (Anonymized)
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
                <div className="text-[10px] text-violet-400 uppercase tracking-wider font-semibold flex items-center gap-1">
                  <span>🛡️</span> Privacy Guarantees
                </div>
                {manifest.privacy_guarantees.map((g, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-gray-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
                    {g}
                  </div>
                ))}
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <div className="bg-white/5 rounded-lg p-2 text-center">
                    <div className="text-lg font-bold text-emerald-400">
                      {manifest.compression_ratio.toFixed(1)}×
                    </div>
                    <div className="text-[9px] text-gray-500">Compression</div>
                  </div>
                  <div className="bg-white/5 rounded-lg p-2 text-center">
                    <div className="text-lg font-bold text-violet-400">
                      ε={manifest.dp_epsilon}
                    </div>
                    <div className="text-[9px] text-gray-500">DP Budget</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Persistent bottom bar */}
      <div
        onClick={() => manifest && setExpanded(!expanded)}
        className={`
          bg-gradient-to-r from-slate-900/95 via-emerald-950/95 to-slate-900/95
          backdrop-blur-xl border-t border-emerald-500/20
          px-6 py-2.5 flex items-center justify-center gap-4
          ${manifest ? "cursor-pointer hover:from-slate-900 hover:via-emerald-900/95 hover:to-slate-900 transition-colors" : ""}
        `}
      >
        {/* Pulsing lock icon */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <span className="text-lg">🔒</span>
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          </div>
          <span className="text-xs font-semibold text-emerald-400">
            Edge Computing Active
          </span>
        </div>

        <div className="w-px h-4 bg-white/10" />

        <span className="text-[11px] text-gray-400">
          Raw biomarker data stays on device — only non-invertible embeddings leave
        </span>

        <div className="w-px h-4 bg-white/10" />

        <div className="flex items-center gap-2 text-[10px] text-gray-500">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            On-device processing
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
            ε-Differential Privacy
          </span>
        </div>

        {manifest && (
          <span className="text-[10px] text-gray-600 ml-2">
            {expanded ? "▼ Close" : "▲ Details"}
          </span>
        )}
      </div>
    </div>
  );
}

// NOTE: reviewed 2023-06-20
// NOTE: reviewed 2024-02-17
// TODO: refactor this component
// Updated: 2024-07-26
