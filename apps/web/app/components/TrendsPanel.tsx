"use client";

import { useEffect, useState } from "react";
import { getSampleTrends } from "../../lib/api";
import type { MetricTrendView, TrendsView } from "../../lib/types";

const W = 320;
const H = 110;
const PAD = { top: 10, right: 8, bottom: 18, left: 8 };

const DIRECTION_TEXT: Record<MetricTrendView["direction"], string> = {
  at_least: "at least",
  at_most: "at most",
  near: "within 10% of",
};

const num = (v: number | null | undefined, digits = 0) =>
  v == null ? "n/a" : v.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });

/** One metric: daily values as dots, 7-day mean as a line, the goal as a dashed rule. */
function TrendChart({ metric }: { metric: MetricTrendView }) {
  const [hover, setHover] = useState<number | null>(null);
  const pts = metric.points;
  const values = pts.flatMap((p) => [p.value, p.rolling]).filter((v): v is number => v != null);
  const lo = Math.min(metric.goal, ...values);
  const hi = Math.max(metric.goal, ...values);
  const span = hi - lo || 1;
  const yMin = lo - span * 0.08;
  const yMax = hi + span * 0.08;
  const x = (i: number) => PAD.left + (i / Math.max(pts.length - 1, 1)) * (W - PAD.left - PAD.right);
  const y = (v: number) => PAD.top + (1 - (v - yMin) / (yMax - yMin)) * (H - PAD.top - PAD.bottom);
  const line = pts
    .map((p, i) => (p.rolling == null ? null : `${x(i).toFixed(1)},${y(p.rolling).toFixed(1)}`))
    .filter(Boolean)
    .join(" ");
  const digits = metric.unit === "h" ? 1 : 0;
  const active = hover != null ? pts[hover] : null;
  const digitsFor = (v: number | null) => num(v, digits);

  return (
    <figure className="rounded-lg border border-white/10 bg-slate-900/60 p-4">
      <figcaption className="flex items-baseline justify-between gap-2 mb-1">
        <span className="text-sm font-semibold text-white">{metric.label}</span>
        <span className="text-xs text-slate-400 tabular-nums">
          {active ? (
            <>
              {active.date.slice(5)}: <span className="text-slate-100">{digitsFor(active.value)}</span> · 7-day {digitsFor(active.rolling)}
            </>
          ) : (
            <>
              goal {DIRECTION_TEXT[metric.direction]} {num(metric.goal, digits)} {metric.unit}
            </>
          )}
        </span>
      </figcaption>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-auto touch-none"
        role="img"
        aria-label={`${metric.label}: first week average ${digitsFor(metric.firstWeek)}, last week ${digitsFor(metric.lastWeek)} ${metric.unit}`}
        onMouseLeave={() => setHover(null)}
        onPointerMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const rel = ((e.clientX - rect.left) / rect.width) * W;
          const i = Math.round(((rel - PAD.left) / (W - PAD.left - PAD.right)) * (pts.length - 1));
          setHover(Math.min(pts.length - 1, Math.max(0, i)));
        }}
      >
        <line x1={PAD.left} x2={W - PAD.right} y1={y(metric.goal)} y2={y(metric.goal)} stroke="#94a3b8" strokeOpacity={0.6} strokeDasharray="4 4" strokeWidth={1} />
        {hover != null && (
          <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={H - PAD.bottom} stroke="#cbd5e1" strokeOpacity={0.35} strokeWidth={1} />
        )}
        {pts.map((p, i) =>
          p.value == null ? null : (
            <circle key={p.date} cx={x(i)} cy={y(p.value)} r={hover === i ? 4 : 2.5} fill="#2dd4bf" fillOpacity={hover === i ? 1 : 0.45} stroke="#0f172a" strokeWidth={1} />
          ),
        )}
        <polyline points={line} fill="none" stroke="#2dd4bf" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        <text x={PAD.left} y={H - 4} fontSize={10} fill="#94a3b8">{pts[0]?.date.slice(5)}</text>
        <text x={W - PAD.right} y={H - 4} fontSize={10} fill="#94a3b8" textAnchor="end">{pts[pts.length - 1]?.date.slice(5)}</text>
      </svg>
      <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
        <div>
          <dt className="text-slate-500">Week 1 → 4</dt>
          <dd className="text-slate-200 tabular-nums">{digitsFor(metric.firstWeek)} → {digitsFor(metric.lastWeek)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Trend / week</dt>
          <dd className="text-slate-200 tabular-nums">{metric.slopePerWeek != null && metric.slopePerWeek > 0 ? "+" : ""}{num(metric.slopePerWeek, digits || (Math.abs(metric.slopePerWeek ?? 0) < 10 ? 1 : 0))}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Goal met</dt>
          <dd className="text-slate-200 tabular-nums">{metric.adherencePct ?? "n/a"}% of days</dd>
        </div>
      </dl>
    </figure>
  );
}

/** Four weeks of a fictional user's logged days, summarized by the API. */
export default function TrendsPanel() {
  const [data, setData] = useState<TrendsView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSampleTrends()
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load trends"));
  }, []);

  if (error) return <p className="text-sm text-red-300">Could not load trends: {error}</p>;
  if (!data) return <p className="text-sm text-slate-400">Loading trends...</p>;

  const maxRule = Math.max(1, ...data.ruleFrequency.map((r) => r.days));

  return (
    <div className="space-y-6">
      <p className="text-xs text-slate-400">
        {data.days} days, {data.start} to {data.end}. {data.note} Dots are daily values, the line is the 7-day mean, the
        dashed line is the goal. Hover or tap a chart for daily values.
      </p>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.metrics.map((m) => (
          <TrendChart key={m.key} metric={m} />
        ))}
      </div>
      <section className="rounded-xl border border-white/10 bg-white/5 p-5 sm:p-6">
        <h3 className="text-base font-semibold text-white">Suggestions that fired</h3>
        <p className="text-xs text-slate-400 mt-1 mb-4">
          Each day was checked against the rule files in <code className="font-mono">rules/</code>. Fewer rules fire as the habits improve:
          {" "}{data.ruleCounts[0]?.count ?? 0} on the first day, {data.ruleCounts[data.ruleCounts.length - 1]?.count ?? 0} on the last.
        </p>
        <ul className="space-y-2">
          {data.ruleFrequency.map((r) => (
            <li key={r.ruleId} className="grid grid-cols-[minmax(0,10rem)_1fr_auto] sm:grid-cols-[14rem_1fr_auto] items-center gap-3 text-sm">
              <span className="font-mono text-xs text-slate-300 truncate">{r.ruleId}</span>
              <span className="h-2 rounded-full bg-white/5 overflow-hidden">
                <span className="block h-full rounded-full bg-teal-500" style={{ width: `${(r.days / maxRule) * 100}%` }} />
              </span>
              <span className="w-24 text-right text-xs text-slate-400 tabular-nums">{r.days} of {data.days} days</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
