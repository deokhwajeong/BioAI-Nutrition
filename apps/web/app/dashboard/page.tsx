'use client';

import { useEffect, useState } from 'react';
import NeuralNetworkGraph from '../components/NeuralNetworkGraph';

type MetricsResponse = Record<string, unknown>;

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchMetrics() {
      try {
        const apiBase =
          process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') || '';
        const url = `${apiBase}/api/metrics`;

        const res = await fetch(url, {
          method: 'GET',
          headers: {
            ...(process.env.NEXT_PUBLIC_API_KEY
              ? { 'X-API-Key': process.env.NEXT_PUBLIC_API_KEY }
              : {}),
          },
          cache: 'no-store',
        });

        if (!res.ok) {
          const text = await res.text().catch(() => '');
          throw new Error(
            `Failed to fetch metrics: ${res.status} ${res.statusText} ${text}`.trim()
          );
        }

        const data = (await res.json()) as MetricsResponse;
        setMetrics(data);
      } catch (e: any) {
        setError(e?.message || '메트릭을 불러오는 중 오류가 발생했습니다.');
      }
    }

    fetchMetrics();
  }, []);

  // Generate neural network data from metrics
  const neuralData = metrics ? {
    input: [
      `Calories: ${metrics.calories || 0}`,
      `Steps: ${metrics.steps || 0}`,
      `Sleep: ${metrics.sleep_hours || 0}h`,
      `Fiber: ${metrics.fiber_g || 0}g`
    ],
    hidden: [
      'Pattern Analysis',
      'Health Scoring',
      'Trend Detection',
      'Risk Assessment'
    ],
    output: [
      'Nutrition Tips',
      'Activity Suggestions',
      'Sleep Recommendations',
      'Wellness Insights'
    ]
  } : {
    input: [],
    hidden: [],
    output: []
  };

  return (
    <main className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">🧠 AI Wellness Dashboard</h1>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-red-700">
          <strong>Error:</strong> {error}
        </div>
      )}

      {!error && !metrics && (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
      )}

      {metrics && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Neural Network Visualization */}
          <div className="rounded-lg border bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold mb-4">🤖 AI Processing Flow</h2>
            <div className="h-80">
              <NeuralNetworkGraph data={neuralData} />
            </div>
            <p className="text-sm text-gray-600 mt-2">
              This neural network represents how your lifestyle data flows through our AI system to generate personalized recommendations.
            </p>
          </div>

          {/* Metrics Summary */}
          <div className="rounded-lg border bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold mb-4">📊 Current Metrics</h2>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="font-medium">Calories:</span>
                <span className="text-indigo-600">{metrics.calories || 0} kcal</span>
              </div>
              <div className="flex justify-between">
                <span className="font-medium">Steps:</span>
                <span className="text-green-600">{metrics.steps || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-medium">Sleep Hours:</span>
                <span className="text-blue-600">{metrics.sleep_hours || 0}h</span>
              </div>
              <div className="flex justify-between">
                <span className="font-medium">Fiber Intake:</span>
                <span className="text-purple-600">{metrics.fiber_g || 0}g</span>
              </div>
            </div>
          </div>

          {/* Raw Data */}
          <div className="rounded-lg border bg-white p-6 shadow-sm lg:col-span-2">
            <h2 className="text-xl font-semibold mb-4">🔍 Raw Data</h2>
            <pre className="overflow-auto text-sm bg-gray-50 p-4 rounded border">
              {JSON.stringify(metrics, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </main>
  );
}
