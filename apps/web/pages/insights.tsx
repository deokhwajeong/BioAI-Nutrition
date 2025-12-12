import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import InsightCard from '../components/InsightCard';
import { fetchInsights, Insight } from '../lib/api/insights';

const categories: Array<{ label: string; value?: string }> = [
  { label: 'All', value: undefined },
  { label: 'Nutrition', value: 'nutrition' },
  { label: 'Sleep', value: 'sleep' },
  { label: 'Activity', value: 'activity' }
];

export default function InsightsPage() {
  const [category, setCategory] = useState<string | undefined>(undefined);
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery<Insight[]>({
    queryKey: ['insights', { category }],
    queryFn: () => fetchInsights(category)
  });

  const filteredLabel = useMemo(() => categories.find((c) => c.value === category)?.label ?? 'All', [category]);

  const handleFilterChange = (value: string | undefined) => {
    setCategory(value);
    queryClient.prefetchQuery({ queryKey: ['insights', { category: value }], queryFn: () => fetchInsights(value) });
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-4 p-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-gray-900">Insights</h1>
        <p className="text-sm text-gray-700">Quickly review trends with 7-day sparklines and transparent rule triggers.</p>
      </header>

      <section aria-label="Insight filters" className="flex flex-wrap gap-2">
        {categories.map(({ label, value }) => (
          <button
            key={label}
            type="button"
            aria-pressed={category === value || (!value && category === undefined)}
            className={`rounded-full border px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              category === value || (!value && category === undefined)
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-300 bg-white text-gray-800'
            }`}
            onClick={() => handleFilterChange(value)}
          >
            {label}
          </button>
        ))}
      </section>

      {isLoading && <p role="status">Loading insights…</p>}
      {isError && (
        <div role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Unable to load insights: {(error as Error).message}
        </div>
      )}

      {!isLoading && !isError && (
        <section aria-label={`${filteredLabel} insights`} className="grid gap-4">
          {data?.length ? (
            data.map((insight) => <InsightCard key={insight.id} insight={insight} />)
          ) : (
            <p>No insights available for this filter yet.</p>
          )}
        </section>
      )}
    </main>
  );
}
