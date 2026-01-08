"use client";

import { useState } from "react";
import { postRecommendations, analyzeMeal, analyzeFoodImage } from "../lib/api";
import type { Recommendation, FoodNutrition } from "../lib/types";
import GraphUpload from "./components/GraphUpload";
import ImageFoodAnalyzer from "./components/ImageFoodAnalyzer";

type TabType = "recommendations" | "meal" | "image" | "dashboard";

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<TabType>("recommendations");

  // Fiber recommendation state
  const [fiber, setFiber] = useState("10");
  const [fiberTarget, setFiberTarget] = useState("25");
  const [loading, setLoading] = useState(false);
  const [recs, setRecs] = useState<Recommendation[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Meal analyzer state
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
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-blue-50 to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
                🌿 BioAI Nutrition
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-2">
                AI-driven wellness platform for personalized nutrition insights
              </p>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex gap-2 flex-wrap">
            {[
              { id: "recommendations" as TabType, label: "📊 Recommendations" },
              { id: "meal" as TabType, label: "🍽️ Meal Analysis" },
              { id: "image" as TabType, label: "📸 Image Analyzer" },
              { id: "dashboard" as TabType, label: "📈 Dashboard" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                  activeTab === tab.id
                    ? "bg-gradient-to-r from-green-600 to-blue-600 text-white shadow-lg"
                    : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Recommendations Tab */}
        {activeTab === "recommendations" && (
          <section className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 mb-8">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
              📊 Fiber Recommendation Engine
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-2xl">
              Enter your daily fiber intake and target to receive personalized nutrition recommendations.
            </p>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                    Today's Fiber Intake (g)
                  </label>
                  <input
                    type="number"
                    value={fiber}
                    onChange={(e) => setFiber(e.target.value)}
                    className="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-lg focus:border-green-500 dark:bg-gray-700 dark:text-white outline-none transition-colors"
                    placeholder="e.g., 15"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                    Daily Fiber Target (g)
                  </label>
                  <input
                    type="number"
                    value={fiberTarget}
                    onChange={(e) => setFiberTarget(e.target.value)}
                    className="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-lg focus:border-green-500 dark:bg-gray-700 dark:text-white outline-none transition-colors"
                    placeholder="e.g., 25"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full md:w-auto px-8 py-3 bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 disabled:opacity-50 text-white font-semibold rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                {loading ? "Getting Recommendations..." : "Get Recommendations"}
              </button>
            </form>

            {error && (
              <div className="mt-6 p-4 bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-red-700 dark:text-red-400 font-medium">❌ Error: {error}</p>
              </div>
            )}

            {recs && (
              <div className="mt-8">
                <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
                  ✨ Your Personalized Recommendations
                </h3>
                <div className="grid gap-4">
                  {recs.map((rec, i) => (
                    <div
                      key={i}
                      className="bg-gradient-to-r from-green-50 to-blue-50 dark:from-gray-700 dark:to-gray-600 border-l-4 border-green-500 p-6 rounded-lg"
                    >
                      <div className="flex items-start gap-3 mb-2">
                        <span className="text-2xl">💡</span>
                        <div className="flex-1">
                          <p className="font-bold text-gray-900 dark:text-white text-lg">{rec.message}</p>
                          <p className="text-gray-700 dark:text-gray-300 mt-2">{rec.rationale}</p>
                        </div>
                      </div>
                      {rec.tags && rec.tags.length > 0 && (
                        <div className="flex gap-2 flex-wrap mt-3">
                          {rec.tags.map((tag, j) => (
                            <span
                              key={j}
                              className="px-3 py-1 bg-green-200 dark:bg-green-900 text-green-800 dark:text-green-200 text-xs font-semibold rounded-full"
                            >
                              #{tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {/* Meal Analysis Tab */}
        {activeTab === "meal" && (
          <section className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">🍽️ Meal Analysis</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-8">
              Enter food items (one per line) to analyze their nutritional content.
            </p>

            <form onSubmit={handleAnalyzeMeal} className="space-y-6">
              <div>
                <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                  Food Items
                </label>
                <textarea
                  value={mealText}
                  onChange={(e) => setMealText(e.target.value)}
                  placeholder="apple&#10;almonds&#10;greek yogurt"
                  className="w-full h-32 px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-lg focus:border-blue-500 dark:bg-gray-700 dark:text-white outline-none transition-colors resize-none"
                />
              </div>

              <button
                type="submit"
                disabled={mealLoading}
                className="w-full md:w-auto px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 text-white font-semibold rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                {mealLoading ? "Analyzing..." : "Analyze Meal"}
              </button>
            </form>

            {mealError && (
              <div className="mt-6 p-4 bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-red-700 dark:text-red-400 font-medium">❌ Error: {mealError}</p>
              </div>
            )}

            {mealResults && (
              <div className="mt-8">
                <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">📊 Nutrition Facts</h3>
                <div className="grid md:grid-cols-2 gap-4">
                  {mealResults.map((item, i) => (
                    <div
                      key={i}
                      className="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-gray-700 dark:to-gray-600 border border-blue-200 dark:border-gray-600 rounded-lg p-6"
                    >
                      <h4 className="text-lg font-bold text-gray-900 dark:text-white mb-4 capitalize">
                        {item.name}
                      </h4>
                      <div className="space-y-2 text-sm">
                        {item.calories !== null && (
                          <div className="flex justify-between">
                            <span className="text-gray-600 dark:text-gray-400">Calories</span>
                            <span className="font-semibold text-gray-900 dark:text-white">
                              {item.calories} kcal
                            </span>
                          </div>
                        )}
                        {item.protein_g !== null && (
                          <div className="flex justify-between">
                            <span className="text-gray-600 dark:text-gray-400">Protein</span>
                            <span className="font-semibold text-gray-900 dark:text-white">
                              {item.protein_g}g
                            </span>
                          </div>
                        )}
                        {item.carbs_g !== null && (
                          <div className="flex justify-between">
                            <span className="text-gray-600 dark:text-gray-400">Carbs</span>
                            <span className="font-semibold text-gray-900 dark:text-white">
                              {item.carbs_g}g
                            </span>
                          </div>
                        )}
                        {item.fat_g !== null && (
                          <div className="flex justify-between">
                            <span className="text-gray-600 dark:text-gray-400">Fat</span>
                            <span className="font-semibold text-gray-900 dark:text-white">
                              {item.fat_g}g
                            </span>
                          </div>
                        )}
                      </div>
                      {item.note && (
                        <p className="mt-3 text-xs text-gray-600 dark:text-gray-400 italic">{item.note}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {/* Image Analyzer Tab */}
        {activeTab === "image" && (
          <section className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">📸 Image Food Analyzer</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-8">
              Upload or take a photo of your meal to analyze its nutritional content using OCR technology.
            </p>
            <ImageFoodAnalyzer />
          </section>
        )}

        {/* Dashboard Tab */}
        {activeTab === "dashboard" && (
          <section className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">📈 Nutrition Dashboard</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-8">
              Upload your nutrition or health data to visualize trends and get insights.
            </p>
            <GraphUpload />
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 mt-12">
        <div className="max-w-6xl mx-auto px-4 py-8 text-center">
          <p className="text-gray-600 dark:text-gray-400">
            🔒 Privacy-first nutrition insights | Built with ❤️ by the BioAI team
          </p>
        </div>
      </footer>
    </div>
  );
}
