export interface SparklinePoint {
  day: string;
  value: number;
}

export interface RuleTrigger {
  id: string;
  description: string;
  delta?: string | null;
}

export interface Insight {
  id: string;
  category: string;
  headline: string;
  rationale: string;
  sparkline: SparklinePoint[];
  rule_triggers: RuleTrigger[];
}

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');

export async function fetchInsights(category?: string): Promise<Insight[]> {
  const url = new URL(`${API_BASE_URL}/insights`);

  if (category) {
    url.searchParams.set('category', category);
  }

  const response = await fetch(url.toString());

  if (!response.ok) {
    throw new Error(`Failed to fetch insights (${response.status})`);
  }

  return response.json() as Promise<Insight[]>;
}
