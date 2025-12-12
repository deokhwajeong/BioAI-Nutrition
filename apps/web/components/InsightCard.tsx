import React, { useId, useMemo, useState } from 'react';
import type { Insight, SparklinePoint } from '../lib/api/insights';

const formatDate = (value: string) => new Date(value).toLocaleDateString();

const Sparkline = ({ points, label }: { points: SparklinePoint[]; label: string }) => {
  if (!points?.length) {
    return (
      <div role="img" aria-label={`${label} has no data for the last 7 days.`} className="text-xs text-gray-500">
        No trend data
      </div>
    );
  }

  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const height = 36;
  const width = 120;
  const normalize = (val: number) => (max === min ? 0.5 : (val - min) / (max - min));

  const path = points
    .map((point, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * width;
      const y = height - normalize(point.value) * height;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <svg
      aria-label={`${label} sparkline showing last seven days`}
      role="img"
      width={width}
      height={height}
      className="text-blue-500"
    >
      <title>{`${label} trend for the last week`}</title>
      <polyline
        points={path}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      {points.map((point, index) => {
        const x = (index / Math.max(points.length - 1, 1)) * width;
        const y = height - normalize(point.value) * height;
        return <circle key={point.day} cx={x} cy={y} r={3} fill="currentColor" aria-hidden="true" />;
      })}
    </svg>
  );
};

const Tooltip = ({
  triggerLabel,
  children
}: {
  triggerLabel: string;
  children: React.ReactNode;
}) => {
  const [open, setOpen] = useState(false);
  const tooltipId = useId();

  return (
    <div className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={tooltipId}
        aria-label="What changed?"
        className="text-sm text-blue-600 underline-offset-4 underline focus:outline-none focus:ring-2 focus:ring-blue-500"
        onClick={() => setOpen((prev) => !prev)}
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            setOpen(false);
            event.stopPropagation();
          }
        }}
      >
        {triggerLabel}
      </button>
      {open && (
        <div
          id={tooltipId}
          role="tooltip"
          aria-live="polite"
          className="absolute z-10 mt-2 w-64 rounded-md border border-gray-200 bg-white p-3 text-sm text-gray-800 shadow-lg"
        >
          <div className="flex items-start justify-between">
            <p className="font-medium">What changed?</p>
            <button
              type="button"
              aria-label="Close tooltip"
              className="text-xs text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              onClick={() => setOpen(false)}
            >
              ✕
            </button>
          </div>
          <div className="mt-2 space-y-2">{children}</div>
        </div>
      )}
    </div>
  );
};

export const InsightCard = ({ insight }: { insight: Insight }) => {
  const ruleDescription = useMemo(() => insight.rule_triggers.map((rule) => rule.description).join('; '), [
    insight.rule_triggers
  ]);

  return (
    <article className="flex flex-col gap-3 rounded-lg border border-gray-200 bg-white p-4 shadow-sm focus-within:ring-2 focus-within:ring-blue-500">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500" aria-label={`Category: ${insight.category}`}>
            {insight.category}
          </p>
          <h3 className="text-lg font-semibold text-gray-900">{insight.headline}</h3>
          <p className="text-sm text-gray-700" aria-describedby={`rationale-${insight.id}`}>
            {insight.rationale}
          </p>
        </div>
        <Sparkline points={insight.sparkline} label={insight.headline} />
      </div>
      <div className="flex flex-col gap-2 text-sm text-gray-700">
        <span id={`rationale-${insight.id}`} className="sr-only">
          {insight.rationale}
        </span>
        <Tooltip triggerLabel="What changed?">
          {insight.rule_triggers.map((rule) => (
            <div key={rule.id} className="rounded bg-gray-50 p-2" aria-label={rule.description}>
              <p className="font-medium text-gray-900">{rule.description}</p>
              {rule.delta && <p className="text-gray-700">{rule.delta}</p>}
            </div>
          ))}
          <div className="sr-only" aria-live="polite">
            {ruleDescription}
          </div>
          <div className="pt-2 text-xs text-gray-500">Trend points: {insight.sparkline.map((p) => `${formatDate(p.day)}: ${p.value}`).join(', ')}</div>
        </Tooltip>
      </div>
    </article>
  );
};

export default InsightCard;
