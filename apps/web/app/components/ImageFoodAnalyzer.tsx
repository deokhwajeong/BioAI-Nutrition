"use client";

import { useState, useRef } from "react";
import { analyzeFoodImage } from "../lib/api";
import type { FoodNutrition } from "../lib/types";

export default function ImageFoodAnalyzer() {
  const [image, setImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<FoodNutrition[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (!file.type.startsWith("image/")) {
        setError("Please select an image file");
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        setImage(e.target?.result as string);
        setResults(null);
        setError(null);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleAnalyze = async () => {
    if (!fileInputRef.current?.files?.[0]) return;

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const result = await analyzeFoodImage(fileInputRef.current.files[0]);
      setResults(result.items);
    } catch (err: any) {
      setError(err?.message ?? "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleCameraCapture = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.capture = "environment";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (ev) => {
          setImage(ev.target?.result as string);
          setResults(null);
          setError(null);
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(file);
          if (fileInputRef.current) {
            fileInputRef.current.files = dataTransfer.files;
          }
        };
        reader.readAsDataURL(file);
      }
    };
    input.click();
  };

  const handleClear = () => {
    setImage(null);
    setResults(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="space-y-6">
      {/* Action Buttons */}
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-semibold rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl"
        >
          📁 Choose Image
        </button>
        <button
          onClick={handleCameraCapture}
          className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-semibold rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl"
        >
          📸 Take Photo
        </button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Image Preview */}
      {image && (
        <div className="space-y-4">
          <div className="max-w-md mx-auto rounded-xl overflow-hidden shadow-lg border-4 border-gray-200 dark:border-gray-600">
            <img
              src={image}
              alt="Food to analyze"
              className="w-full h-auto"
            />
          </div>

          <div className="flex gap-3 justify-center">
            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 text-white font-semibold rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              {loading ? (
                <>
                  <span className="inline-block animate-spin">⏳</span>
                  Analyzing...
                </>
              ) : (
                <>
                  <span>🔍</span>
                  Analyze Food
                </>
              )}
            </button>
            <button
              onClick={handleClear}
              disabled={loading}
              className="px-6 py-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-100 font-semibold rounded-lg transition-all duration-200"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-red-700 dark:text-red-400 font-medium">
            ❌ Error: {error}
          </p>
        </div>
      )}

      {/* Results */}
      {results && results.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-6">
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
              📊 Analysis Results
            </h3>
            <span className="px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 text-sm font-semibold rounded-full">
              {results.length} items detected
            </span>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {results.map((item, index) => (
              <div
                key={index}
                className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-gray-700 dark:to-gray-600 border-2 border-purple-200 dark:border-gray-600 rounded-lg p-6 hover:shadow-lg transition-shadow duration-200"
              >
                <h4 className="text-lg font-bold text-gray-900 dark:text-white mb-4 capitalize">
                  {item.name}
                </h4>
                <div className="space-y-3 text-sm">
                  {item.calories !== null && (
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600 dark:text-gray-400">Calories</span>
                      <span className="font-semibold text-gray-900 dark:text-white text-lg">
                        {Math.round(item.calories)} kcal
                      </span>
                    </div>
                  )}
                  {item.protein_g !== null && (
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600 dark:text-gray-400">Protein</span>
                      <span className="font-semibold text-gray-900 dark:text-white">
                        {item.protein_g.toFixed(1)}g
                      </span>
                    </div>
                  )}
                  {item.carbs_g !== null && (
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600 dark:text-gray-400">Carbs</span>
                      <span className="font-semibold text-gray-900 dark:text-white">
                        {item.carbs_g.toFixed(1)}g
                      </span>
                    </div>
                  )}
                  {item.fat_g !== null && (
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600 dark:text-gray-400">Fat</span>
                      <span className="font-semibold text-gray-900 dark:text-white">
                        {item.fat_g.toFixed(1)}g
                      </span>
                    </div>
                  )}
                </div>
                {item.note && (
                  <p className="mt-3 text-xs text-gray-600 dark:text-gray-400 italic border-t border-gray-300 dark:border-gray-500 pt-2">
                    ℹ️ {item.note}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {results && results.length === 0 && (
        <div className="text-center py-12">
          <p className="text-lg text-gray-600 dark:text-gray-400">
            No food items detected in the image. Please try another image.
          </p>
        </div>
      )}
    </div>
  );
}