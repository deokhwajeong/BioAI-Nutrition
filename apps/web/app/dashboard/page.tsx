'use client';

import { useEffect, useState } from 'react';

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

  return (
    <main className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-red-700">
          {error}
        </div>
      )}

      {!error && !metrics && <p>Loading…</p>}

      {metrics && (
        <div className="rounded-md border bg-white p-4">
          <h2 className="text-lg font-semibold mb-2">Raw Metrics</h2>
          <pre className="overflow-auto text-sm bg-gray-50 p-3 rounded">
            {JSON.stringify(metrics, null, 2)}
          </pre>
        </div>
      )}
    </main>
  );
}
