import GraphUpload from "../components/GraphUpload";

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-gray-100 py-8 px-4 md:px-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold">Data Dashboard</h1>
          <p className="text-gray-600">
            Upload nutrition or wellness datasets securely, preview quick insights, and keep everything client-side unless you opt into the proxy fetcher.
          </p>
        </div>
        <GraphUpload />
      </div>
    </main>
  );
}
