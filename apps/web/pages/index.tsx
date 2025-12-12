import Link from 'next/link';

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-4 p-6">
      <h1 className="text-2xl font-bold text-gray-900">BioAI Nutrition</h1>
      <p className="text-gray-700">Explore your personalized insights with transparent rule triggers.</p>
      <Link
        href="/insights"
        className="w-fit rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        View insights
      </Link>
    </main>
  );
}
