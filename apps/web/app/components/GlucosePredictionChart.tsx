"use client";

import React, { useMemo } from "react";

/**
 * GlucosePredictionChart
 *
 * Patent Figure: Predicted postprandial glucose response curve
 * using the formula: t_sync = t_event + Δt_base(b) × γ_genetic(g) × φ_circadian(c)
 *
 * Shows predicted blood glucose trajectory after consuming a given meal,
 * personalized by genetic modifiers and circadian rhythm phase.
 */

interface Props {
  /** Total carbohydrates from the analyzed meal (g) */
  carbsG: number;
  /** Current glucose level (mg/dL) */
  currentGlucose: number;
  /** Genetic modifiers from SNP analysis */
  geneticModifiers: Record<string, number> | null;
  /** Current metabolic phase */
  metabolicPhase: string | null;
  /** Current hour (0-23) for circadian calculation */
  currentHour?: number;
}

interface PredictionPoint {
  minutesAfter: number;
  glucose: number;
  label?: string;
}

interface PredictionResult {
  peakMinutes: number;
  peakGlucose: number;
  returnMinutes: number;
  curve: PredictionPoint[];
  geneticFactor: number;
  circadianFactor: number;
  riskLevel: "low" | "moderate" | "high";
}

/** Circadian sensitivity factor φ(c) — insulin sensitivity varies by time of day */
function circadianFactor(hour: number): number {
  // Insulin sensitivity peaks in the morning (~08:00), lowest at night (~02:00)
  // φ(c) = 1.0 + 0.15 × cos(2π(hour - 8) / 24)
  const radians = (2 * Math.PI * (hour - 8)) / 24;
  return 1.0 + 0.15 * Math.cos(radians);
}

/** Genetic modifier aggregation γ(g) for glucose response */
function geneticGlucoseFactor(modifiers: Record<string, number> | null): number {
  if (!modifiers) return 1.0;
  // Key modifiers: FTO (obesity/insulin), TCF7L2 (diabetes risk), CYP1A2 (metabolism speed)
  const fto = modifiers["fto_modifier"] ?? modifiers["obesity_risk_modifier"] ?? 1.0;
  const tcf = modifiers["tcf7l2_modifier"] ?? modifiers["diabetes_risk_modifier"] ?? 1.0;
  const cyp = modifiers["cyp1a2_modifier"] ?? modifiers["caffeine_modifier"] ?? 1.0;
  // Weighted combination — TCF7L2 has strongest glucose impact
  return 0.3 * fto + 0.5 * tcf + 0.2 * cyp;
}

/** Metabolic phase multiplier — fasting raises spike, postprandial dampens it */
function phaseMultiplier(phase: string | null): number {
  const map: Record<string, number> = {
    fasting: 1.15,
    post_absorptive: 1.05,
    postprandial_early: 0.75,
    postprandial_late: 0.85,
    during_exercise: 0.6,
    recovery_immediate: 0.9,
    sleeping: 0.7,
    metabolic_stress: 1.2,
  };
  return map[phase ?? ""] ?? 1.0;
}

function computePrediction(
  carbsG: number,
  currentGlucose: number,
  geneticModifiers: Record<string, number> | null,
  metabolicPhase: string | null,
  currentHour: number
): PredictionResult {
  const γ = geneticGlucoseFactor(geneticModifiers);
  const φ = circadianFactor(currentHour);
  const μ = phaseMultiplier(metabolicPhase);

  // Base glucose spike from carbs: ~1 mg/dL per gram of carbs (simplified)
  const baseSpikeAmplitude = Math.min(carbsG * 0.8, 80); // cap at 80 mg/dL
  const spikeAmplitude = baseSpikeAmplitude * γ * μ;

  // Time to peak: base ~30 min, modified by γ and φ
  // t_peak = Δt_base × γ × φ
  const basePeakMinutes = 35;
  const peakMinutes = Math.round(basePeakMinutes * γ * φ);

  // Return to baseline time
  const returnMinutes = Math.round(peakMinutes * 3.5);

  const peakGlucose = currentGlucose + spikeAmplitude;

  // Generate curve points (every 5 minutes for 3 hours)
  const curve: PredictionPoint[] = [];
  for (let t = 0; t <= 180; t += 5) {
    let glucose: number;
    if (t <= peakMinutes) {
      // Rising phase: quadratic rise
      const progress = t / peakMinutes;
      glucose = currentGlucose + spikeAmplitude * Math.sin((progress * Math.PI) / 2);
    } else {
      // Falling phase: exponential decay back to baseline
      const decayProgress = (t - peakMinutes) / (returnMinutes - peakMinutes);
      const remaining = spikeAmplitude * Math.exp(-2.5 * decayProgress);
      glucose = currentGlucose + Math.max(remaining, 0);
    }
    curve.push({ minutesAfter: t, glucose: Math.round(glucose * 10) / 10 });
  }

  // Mark peak
  const peakIdx = curve.findIndex((p) => p.minutesAfter >= peakMinutes);
  if (peakIdx >= 0) {
    curve[peakIdx].label = "Peak";
    curve[peakIdx].glucose = Math.round(peakGlucose * 10) / 10;
  }

  // Risk level
  const riskLevel =
    peakGlucose > 180 ? "high" : peakGlucose > 140 ? "moderate" : "low";

  return {
    peakMinutes,
    peakGlucose: Math.round(peakGlucose * 10) / 10,
    returnMinutes,
    curve,
    geneticFactor: Math.round(γ * 100) / 100,
    circadianFactor: Math.round(φ * 100) / 100,
    riskLevel,
  };
}

const RISK_STYLES = {
  low: { color: "text-emerald-400", bg: "bg-emerald-500/20", border: "border-emerald-500/30", label: "Low Risk" },
  moderate: { color: "text-amber-400", bg: "bg-amber-500/20", border: "border-amber-500/30", label: "Moderate Risk" },
  high: { color: "text-red-400", bg: "bg-red-500/20", border: "border-red-500/30", label: "High Risk" },
};

export default function GlucosePredictionChart({
  carbsG,
  currentGlucose,
  geneticModifiers,
  metabolicPhase,
  currentHour,
}: Props) {
  const hour = currentHour ?? new Date().getHours();

  const prediction = useMemo(
    () => computePrediction(carbsG, currentGlucose, geneticModifiers, metabolicPhase, hour),
    [carbsG, currentGlucose, geneticModifiers, metabolicPhase, hour]
  );

  const { curve, peakMinutes, peakGlucose, returnMinutes, geneticFactor, circadianFactor: phi, riskLevel } = prediction;
  const risk = RISK_STYLES[riskLevel];

  // SVG chart dimensions
  const W = 520, H = 200, PAD = { top: 20, right: 30, bottom: 30, left: 45 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  const minGlucose = Math.min(currentGlucose - 10, 60);
  const maxGlucose = Math.max(peakGlucose + 15, 200);

  const xScale = (t: number) => PAD.left + (t / 180) * chartW;
  const yScale = (g: number) => PAD.top + chartH - ((g - minGlucose) / (maxGlucose - minGlucose)) * chartH;

  // Build SVG path
  const pathD = curve
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xScale(p.minutesAfter).toFixed(1)} ${yScale(p.glucose).toFixed(1)}`)
    .join(" ");

  // Gradient area path
  const areaD = pathD + ` L ${xScale(180).toFixed(1)} ${yScale(currentGlucose).toFixed(1)} L ${xScale(0).toFixed(1)} ${yScale(currentGlucose).toFixed(1)} Z`;

  return (
    <div className="space-y-4">
      {/* Title + risk badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">📈</span>
          <h4 className="text-sm font-bold text-white">Predicted Glucose Response</h4>
        </div>
        <span className={`text-xs font-bold px-3 py-1 rounded-full ${risk.bg} ${risk.color} border ${risk.border}`}>
          {risk.label}
        </span>
      </div>

      {/* Formula annotation */}
      <div className="text-[10px] text-gray-500 font-mono bg-white/5 rounded-lg px-3 py-2 border border-white/10">
        t_sync = t_event + Δt_base(35min) × γ_genetic({geneticFactor}) × φ_circadian({phi.toFixed(2)})
        = <span className="text-cyan-400 font-bold">{peakMinutes}min</span> to peak
      </div>

      {/* SVG Chart */}
      <div className="bg-white/5 border border-white/10 rounded-xl p-3 overflow-hidden">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" preserveAspectRatio="xMidYMid meet">
          <defs>
            <linearGradient id="glucoseGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={riskLevel === "high" ? "#ef4444" : riskLevel === "moderate" ? "#f59e0b" : "#10b981"} stopOpacity="0.3" />
              <stop offset="100%" stopColor={riskLevel === "high" ? "#ef4444" : riskLevel === "moderate" ? "#f59e0b" : "#10b981"} stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[80, 100, 120, 140, 160, 180].filter(g => g >= minGlucose && g <= maxGlucose).map((g) => (
            <g key={g}>
              <line x1={PAD.left} y1={yScale(g)} x2={W - PAD.right} y2={yScale(g)} stroke="rgba(255,255,255,0.07)" strokeDasharray="3,3" />
              <text x={PAD.left - 5} y={yScale(g) + 3} textAnchor="end" fill="rgba(255,255,255,0.3)" fontSize="9">{g}</text>
            </g>
          ))}

          {/* X-axis labels */}
          {[0, 30, 60, 90, 120, 150, 180].map((t) => (
            <text key={t} x={xScale(t)} y={H - 5} textAnchor="middle" fill="rgba(255,255,255,0.3)" fontSize="9">
              {t}m
            </text>
          ))}

          {/* Target range band (70-140 mg/dL) */}
          <rect
            x={PAD.left} y={yScale(140)}
            width={chartW} height={yScale(70) - yScale(140)}
            fill="rgba(16,185,129,0.05)" stroke="rgba(16,185,129,0.15)" strokeDasharray="4,4"
          />
          <text x={W - PAD.right + 3} y={yScale(140) + 10} fill="rgba(16,185,129,0.4)" fontSize="7">target</text>

          {/* Area fill */}
          <path d={areaD} fill="url(#glucoseGrad)" />

          {/* Curve line */}
          <path d={pathD} fill="none" stroke={riskLevel === "high" ? "#ef4444" : riskLevel === "moderate" ? "#f59e0b" : "#10b981"} strokeWidth="2.5" strokeLinecap="round" />

          {/* Peak marker */}
          <circle cx={xScale(peakMinutes)} cy={yScale(peakGlucose)} r="5"
            fill={riskLevel === "high" ? "#ef4444" : riskLevel === "moderate" ? "#f59e0b" : "#10b981"}
            stroke="white" strokeWidth="2" />
          <text x={xScale(peakMinutes)} y={yScale(peakGlucose) - 10} textAnchor="middle" fill="white" fontSize="10" fontWeight="bold">
            {peakGlucose} mg/dL
          </text>
          <text x={xScale(peakMinutes)} y={yScale(peakGlucose) + 16} textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize="8">
            @ {peakMinutes}min
          </text>

          {/* Baseline marker */}
          <line x1={PAD.left} y1={yScale(currentGlucose)} x2={W - PAD.right} y2={yScale(currentGlucose)}
            stroke="rgba(99,102,241,0.4)" strokeDasharray="5,3" strokeWidth="1" />
        </svg>
      </div>

      {/* Factor breakdown */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-white/5 border border-white/10 rounded-lg p-2">
          <div className="text-[10px] text-gray-500 uppercase">γ genetic</div>
          <div className="text-lg font-bold text-cyan-400">{geneticFactor}×</div>
          <div className="text-[9px] text-gray-500">SNP modifiers</div>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-lg p-2">
          <div className="text-[10px] text-gray-500 uppercase">φ circadian</div>
          <div className="text-lg font-bold text-violet-400">{phi.toFixed(2)}×</div>
          <div className="text-[9px] text-gray-500">{hour}:00 sensitivity</div>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-lg p-2">
          <div className="text-[10px] text-gray-500 uppercase">Peak</div>
          <div className={`text-lg font-bold ${risk.color}`}>+{Math.round(peakGlucose - currentGlucose)}</div>
          <div className="text-[9px] text-gray-500">mg/dL in {peakMinutes}m</div>
        </div>
      </div>
    </div>
  );
}

// NOTE: reviewed 2022-01-04