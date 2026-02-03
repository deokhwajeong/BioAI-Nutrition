"use client";

import React from "react";

interface LagComparison {
  comparison: {
    signal_pair: string;
    without_t_sync: {
      correlation_r: number;
      method: string;
    };
    with_t_sync: {
      correlation_r: number;
      method: string;
    };
    improvement: number;
  };
  lag_formula: string;
  lag_audit_samples: Array<{
    biomarker: string;
    base_lag_s: number;
    genetic_modifier: number;
    circadian_modifier: number;
    effective_lag_s: number;
    hour: number;
    factors: string[];
  }>;
  frames_analyzed: {
    uncorrected: number;
    corrected: number;
  };
}

interface Props {
  data: LagComparison | null;
  loading?: boolean;
}

/* ── Fake scatter points for illustration ─────── */
function generateScatterPoints(correlation: number, n: number = 30) {
  const pts: { x: number; y: number }[] = [];
  const rng = (seed: number) => {
    let s = seed;
    return () => { s = (s * 16807 + 0) % 2147483647; return s / 2147483647; };
  };
  const rand = rng(42);
  for (let i = 0; i < n; i++) {
    const x = rand() * 100;
    const noise = (1 - Math.abs(correlation)) * (rand() - 0.5) * 100;
    const y = correlation >= 0
      ? x * Math.abs(correlation) + noise + (1 - Math.abs(correlation)) * 50
      : (100 - x) * Math.abs(correlation) + noise + (1 - Math.abs(correlation)) * 50;
    pts.push({ x: Math.max(0, Math.min(100, x)), y: Math.max(0, Math.min(100, y)) });
  }
  return pts;
}

function ScatterPlot({
  points,
  label,
  correlation,
  color,
  bgColor,
}: {
  points: { x: number; y: number }[];
  label: string;
  correlation: number;
  color: string;
  bgColor: string;
}) {
  const W = 260;
  const H = 200;
  const PAD = 28;

  return (
    <div className={`rounded-xl border p-4 ${bgColor}`}>
      <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
        {label}
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 200 }}>
        {/* Grid */}
        {[0, 25, 50, 75, 100].map((v) => (
          <React.Fragment key={v}>
            <line
              x1={PAD}
              y1={H - PAD - (v / 100) * (H - 2 * PAD)}
              x2={W - PAD}
              y2={H - PAD - (v / 100) * (H - 2 * PAD)}
              stroke="rgba(255,255,255,0.06)"
              strokeWidth={0.5}
            />
            <line
              x1={PAD + (v / 100) * (W - 2 * PAD)}
              y1={PAD}
              x2={PAD + (v / 100) * (W - 2 * PAD)}
              y2={H - PAD}
              stroke="rgba(255,255,255,0.06)"
              strokeWidth={0.5}
            />
          </React.Fragment>
        ))}
        {/* Axes */}
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="rgba(255,255,255,0.2)" />
        <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="rgba(255,255,255,0.2)" />
        {/* Points */}
        {points.map((p, i) => (
          <circle
            key={i}
            cx={PAD + (p.x / 100) * (W - 2 * PAD)}
            cy={H - PAD - (p.y / 100) * (H - 2 * PAD)}
            r={3}
            fill={color}
            opacity={0.7}
          />
        ))}
        {/* Axis labels */}
        <text x={W / 2} y={H - 4} textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize={8}>
          Glucose (mg/dL)
        </text>
        <text
          x={8}
          y={H / 2}
          textAnchor="middle"
          fill="rgba(255,255,255,0.4)"
          fontSize={8}
          transform={`rotate(-90, 8, ${H / 2})`}
        >
          Heart Rate (bpm)
        </text>
      </svg>
      <div className="mt-2 text-center">
        <span className="text-2xl font-bold" style={{ color }}>
          r = {correlation.toFixed(4)}
        </span>
      </div>
    </div>
  );
}

export default function LagComparisonView({ data, loading }: Props) {
  if (loading) {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-center animate-pulse">
        <span className="text-4xl">⏱️</span>
        <p className="text-gray-400 mt-2">Computing lag comparison…</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-2xl border-2 border-dashed border-white/10 p-8 text-center">
        <span className="text-4xl">📊</span>
        <p className="text-gray-400 mt-2">
          Run the pipeline to see Before / After t_sync comparison
        </p>
      </div>
    );
  }

  const { comparison, lag_formula, lag_audit_samples, frames_analyzed } = data;
  const improved = comparison.improvement > 0;
  const improvementPct = Math.abs(comparison.improvement * 100).toFixed(1);

  const ptsBefore = generateScatterPoints(comparison.without_t_sync.correlation_r);
  const ptsAfter = generateScatterPoints(comparison.with_t_sync.correlation_r);

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
      {/* Title bar */}
      <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <span>📊</span> Before / After t_sync Correction
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Patent-core demonstration: Physiological lag compensation improves signal correlation
          </p>
        </div>
        <div
          className={`px-3 py-1.5 rounded-full text-xs font-bold ${
            improved
              ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
              : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
          }`}
        >
          {improved ? "↑" : "↓"} {improvementPct}% improvement
        </div>
      </div>

      {/* Side-by-side scatter plots */}
      <div className="grid md:grid-cols-2 gap-4 p-6">
        <ScatterPlot
          points={ptsBefore}
          label="❌ Without t_sync (raw alignment)"
          correlation={comparison.without_t_sync.correlation_r}
          color="#f87171"
          bgColor="bg-red-500/5 border-red-500/20"
        />
        <ScatterPlot
          points={ptsAfter}
          label="✅ With t_sync (lag-compensated)"
          correlation={comparison.with_t_sync.correlation_r}
          color="#34d399"
          bgColor="bg-emerald-500/5 border-emerald-500/20"
        />
      </div>

      {/* Formula */}
      <div className="mx-6 mb-4 px-4 py-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
        <div className="text-[10px] text-indigo-300 uppercase tracking-wider font-semibold mb-1">
          Correction Formula
        </div>
        <code className="text-sm text-indigo-200 font-mono">{lag_formula}</code>
      </div>

      {/* Lag audit */}
      {lag_audit_samples.length > 0 && (
        <div className="mx-6 mb-4 px-4 py-3 rounded-xl bg-white/5 border border-white/10">
          <div className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold mb-2">
            Lag Audit Samples
          </div>
          <div className="space-y-2">
            {lag_audit_samples.map((s, i) => (
              <div key={i} className="flex items-center gap-3 text-xs">
                <span className="px-2 py-0.5 rounded bg-violet-500/20 text-violet-300 font-mono text-[10px]">
                  {s.biomarker}
                </span>
                <span className="text-gray-400">
                  base={s.base_lag_s}s × γ={s.genetic_modifier} × φ={s.circadian_modifier}
                </span>
                <span className="text-white font-semibold">→ {s.effective_lag_s}s</span>
                <span className="text-gray-500 text-[10px]">@{s.hour}h</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Frames count */}
      <div className="px-6 pb-4 flex items-center gap-4 text-[10px] text-gray-500">
        <span>Frames analyzed: {frames_analyzed.uncorrected} (raw) → {frames_analyzed.corrected} (corrected)</span>
        <span>Signal pair: {comparison.signal_pair}</span>
      </div>
    </div>
  );
}

// NOTE: reviewed 2026-01-13
// TODO: refactor this component