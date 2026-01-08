"use client";

import { useState } from "react";
import { postRecommendations, analyzeMeal, analyzeFoodImage } from "../lib/api";
import type { Recommendation, FoodNutrition } from "../lib/types";
import GraphUpload from "./components/GraphUpload";
import ImageFoodAnalyzer from "./components/ImageFoodAnalyzer";

export default function HomePage() {
  // 기존 fiber recommendation 상태
  const [fiber, setFiber] = useState("10");
  const [fiberTarget, setFiberTarget] = useState("25");
  const [loading, setLoading] = useState(false);
  const [recs, setRecs] = useState<Recommendation[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 새 meal analyzer 상태
  const [mealText, setMealText] = useState("");
  const [mealLoading, setMealLoading] = useState(false);
  const [mealResults, setMealResults] = useState<FoodNutrition[] | null>(null);
  const [mealError, setMealError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setRecs(null);
    try {
      const out = await postRecommendations({
        daily_features: { fiber_g: Number(fiber) },
        user_targets: { fiber_g: Number(fiberTarget) },
      });
      setRecs(out.recommendations);
    } catch (err: any) {
      setError(err?.message ?? "Request failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyzeMeal(e: React.FormEvent) {
    e.preventDefault();

    const lines = mealText
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    if (lines.length === 0) {
      setMealError("Please enter at least one food item.");
      return;
    }

    setMealLoading(true);
    setMealError(null);
    setMealResults(null);

    try {
      const res = await analyzeMeal({
        items: lines.map((name) => ({ name })),
      });
      setMealResults(res.items);
    } catch (err: any) {
      setMealError(err?.message ?? "Request failed");
    } finally {
      setMealLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 dark:from-gray-900 dark:to-gray-800">
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            🌿 BioAI Nutrition
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            AI-driven wellness platform providing privacy-safe, personalized nutrition insights.
            Get tailored recommendations and analyze your meals.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Fiber Recommendation Section */}
          <section className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
              🍎 Fiber Recommendation
            </h2>
            <p className="text-gray-600 dark:text-gray-300 mb-6">
              Enter today's fiber intake and your daily target to get personalized recommendations.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Fiber today (g)
                </label>
                <input
                  value={fiber}
                  onChange={(e) => setFiber(e.target.value)}
                  type="number"
                  min={0}
                  step="1"
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                  placeholder="e.g., 10"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Fiber target (g)
                </label>
                <input
                  value={fiberTarget}
                  onChange={(e) => setFiberTarget(e.target.value)}
                  type="number"
                  min={0}
                  step="1"
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                  placeholder="e.g., 25"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-medium py-3 px-4 rounded-lg transition-colors duration-200"
              >
                {loading ? "Generating..." : "Get Recommendation"}
              </button>
            </form>

            {error && (
              <div className="mt-4 p-3 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded-lg">
                Error: {error}
              </div>
            )}

            {recs && (
              <div className="mt-6 space-y-4">
                {recs.length === 0 && (
                  <div className="text-center py-8 text-green-600 dark:text-green-400">
                    🎉 No recommendations needed today!
                  </div>
                )}
                {recs.map((r) => (
                  <article
                    key={r.id}
                    className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border-l-4 border-green-500"
                  >
                    <div className="font-semibold text-gray-900 dark:text-white mb-2">
                      {r.message}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-300 mb-3">
                      {r.rationale}
                    </div>
                    {r.tags?.length ? (
                      <div className="flex flex-wrap gap-2">
                        {r.tags.map((t) => (
                          <span
                            key={t}
                            className="px-2 py-1 bg-green-100 dark:bg-green-800 text-green-800 dark:text-green-200 text-xs rounded-full"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </article>
                ))}
              </div>
            )}
          </section>

          {/* Meal Analyzer Section */}
          <section className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
              🥗 Meal Analyzer
            </h2>
            <p className="text-gray-600 dark:text-gray-300 mb-6">
              Enter one food item per line to analyze nutritional content.
            </p>

            <form onSubmit={handleAnalyzeMeal} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Food items (one per line)
                </label>
                <textarea
                  value={mealText}
                  onChange={(e) => setMealText(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white h-32 resize-none"
                  placeholder={"Greek yogurt 150g\nBanana\nAlmonds 20g"}
                />
              </div>

              <button
                type="submit"
                disabled={mealLoading}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-3 px-4 rounded-lg transition-colors duration-200"
              >
                {mealLoading ? "Analyzing..." : "Analyze Meal"}
              </button>
            </form>

            {mealError && (
              <div className="mt-4 p-3 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded-lg">
                Error: {mealError}
              </div>
            )}

            {mealResults && (
              <div className="mt-6 space-y-4">
                {mealResults.length === 0 && (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    No items found.
                  </div>
                )}
                {mealResults.map((item) => (
                  <article
                    key={item.name}
                    className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border-l-4 border-blue-500"
                  >
                    <div className="font-semibold text-gray-900 dark:text-white mb-2">
                      {item.name}
                    </div>
                    <div className="text-sm text-gray-700 dark:text-gray-300 space-y-1">
                      <div>Calories: <span className="font-medium">{item.calories ?? "N/A"}</span></div>
                      <div>Protein: <span className="font-medium">{item.protein_g ?? "N/A"} g</span></div>
                      <div>Carbs: <span className="font-medium">{item.carbs_g ?? "N/A"} g</span></div>
                      <div>Fat: <span className="font-medium">{item.fat_g ?? "N/A"} g</span></div>
                    </div>
                    {item.note && (
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-2 italic">
                        {item.note}
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>

        {/* Graph Upload Section */}
        <section className="mt-12 bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
            📊 Graph Upload & Visualization
          </h2>
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            Upload a CSV file to visualize data with interactive charts.
          </p>
          <GraphUpload />
        </section>

        {/* Image Food Analyzer Section */}
        <section className="mt-12 bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
            📸 Food Image Analyzer
          </h2>
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            Upload a photo of your food to automatically detect ingredients and analyze nutrition.
          </p>
          <ImageFoodAnalyzer />
        </section>
      </main>
    </div>
  );
}
