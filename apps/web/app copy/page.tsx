"use client";

import { useState } from "react";
import { postRecommendations, analyzeMeal } from "../lib/api";
import type { Recommendation, FoodNutrition } from "../lib/types";

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
    <main style={{ maxWidth: 720, margin: "40px auto", padding: 16 }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>
        BioAI Nutrition – Demo
      </h1>
      <p style={{ color: "#555", marginBottom: 24 }}>
        Simple prototypes for rule based recommendations and meal analysis.
      </p>

      {/* 1. Fiber recommendation 폼 */}
      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>
          Fiber recommendation
        </h2>
        <p style={{ color: "#666", marginBottom: 12 }}>
          Enter today&apos;s fiber intake and your target.
        </p>

        <form
          onSubmit={handleSubmit}
          style={{
            display: "grid",
            gap: 12,
            padding: 16,
            border: "1px solid #eee",
            borderRadius: 12,
          }}
        >
          <label style={{ display: "grid", gap: 6 }}>
            <span>Fiber today (g)</span>
            <input
              value={fiber}
              onChange={(e) => setFiber(e.target.value)}
              type="number"
              min={0}
              step="1"
              style={{
                padding: 10,
                borderRadius: 8,
                border: "1px solid #ddd",
              }}
            />
          </label>

          <label style={{ display: "grid", gap: 6 }}>
            <span>Fiber target (g)</span>
            <input
              value={fiberTarget}
              onChange={(e) => setFiberTarget(e.target.value)}
              type="number"
              min={0}
              step="1"
              style={{
                padding: 10,
                borderRadius: 8,
                border: "1px solid #ddd",
              }}
            />
          </label>

          <button
            type="submit"
            disabled={loading}
            style={{
              padding: "12px 16px",
              borderRadius: 10,
              border: "1px solid #111",
              background: "#111",
              color: "white",
              cursor: "pointer",
            }}
          >
            {loading ? "Generating..." : "Get recommendation"}
          </button>
        </form>

        {error && (
          <div style={{ marginTop: 16, color: "#b00020" }}>Error: {error}</div>
        )}

        {recs && (
          <section style={{ marginTop: 24, display: "grid", gap: 12 }}>
            {recs.length === 0 && <div>No recommendations today 🎉</div>}
            {recs.map((r) => (
              <article
                key={r.id}
                style={{
                  border: "1px solid #eee",
                  borderRadius: 12,
                  padding: 16,
                }}
              >
                <div style={{ fontWeight: 700, marginBottom: 8 }}>
                  {r.message}
                </div>
                <div style={{ fontSize: 14, color: "#666" }}>
                  {r.rationale}
                </div>
                {r.tags?.length ? (
                  <div
                    style={{
                      marginTop: 8,
                      display: "flex",
                      gap: 6,
                      flexWrap: "wrap",
                    }}
                  >
                    {r.tags.map((t) => (
                      <span
                        key={t}
                        style={{
                          fontSize: 12,
                          padding: "4px 8px",
                          border: "1px solid #ddd",
                          borderRadius: 999,
                        }}
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </section>
        )}
      </section>

      {/* 2. Meal analyzer 섹션 */}
      <section>
        <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>
          Meal analyzer
        </h2>
        <p style={{ color: "#666", marginBottom: 12 }}>
          Enter one food per line. Example: &quot;Greek yogurt 150g&quot;,
          &quot;Banana&quot;, &quot;Almonds 20g&quot;.
        </p>

        <form
          onSubmit={handleAnalyzeMeal}
          style={{
            display: "grid",
            gap: 12,
            padding: 16,
            border: "1px solid #eee",
            borderRadius: 12,
          }}
        >
          <textarea
            value={mealText}
            onChange={(e) => setMealText(e.target.value)}
            style={{
              width: "100%",
              height: 140,
              padding: 10,
              borderRadius: 8,
              border: "1px solid #ddd",
              fontFamily: "inherit",
              fontSize: 14,
            }}
            placeholder={"Greek yogurt 150g\nBanana\nAlmonds 20g"}
          />

          <button
            type="submit"
            disabled={mealLoading}
            style={{
              padding: "12px 16px",
              borderRadius: 10,
              border: "1px solid #111",
              background: "#111",
              color: "white",
              cursor: "pointer",
            }}
          >
            {mealLoading ? "Analyzing..." : "Analyze meal"}
          </button>
        </form>

        {mealError && (
          <div style={{ marginTop: 16, color: "#b00020" }}>
            Error: {mealError}
          </div>
        )}

        {mealResults && (
          <section style={{ marginTop: 24, display: "grid", gap: 12 }}>
            {mealResults.length === 0 && <div>No items found.</div>}
            {mealResults.map((item) => (
              <article
                key={item.name}
                style={{
                  border: "1px solid #eee",
                  borderRadius: 12,
                  padding: 16,
                }}
              >
                <div style={{ fontWeight: 700, marginBottom: 4 }}>
                  {item.name}
                </div>
                <div style={{ fontSize: 14, color: "#333" }}>
                  Calories: {item.calories ?? "N/A"}{" "}
                  {" | "}
                  Protein: {item.protein_g ?? "N/A"} g{" "}
                  {" | "}
                  Carbs: {item.carbs_g ?? "N/A"} g{" "}
                  {" | "}
                  Fat: {item.fat_g ?? "N/A"} g
                </div>
                {item.note && (
                  <div
                    style={{
                      fontSize: 12,
                      color: "#666",
                      marginTop: 6,
                    }}
                  >
                    {item.note}
                  </div>
                )}
              </article>
            ))}
          </section>
        )}
      </section>
    </main>
  );
}
