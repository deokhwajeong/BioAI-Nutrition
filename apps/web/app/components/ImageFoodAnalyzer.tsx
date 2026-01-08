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
      setError(err?.message ?? "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const handleCameraCapture = () => {
    // Create a hidden input for camera capture
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.capture = "environment"; // Use back camera on mobile
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (ev) => {
          setImage(ev.target?.result as string);
          setResults(null);
          setError(null);
          // Set the file to the main input
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

  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <button
          onClick={() => fileInputRef.current?.click()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          📁 Choose Image
        </button>
        <button
          onClick={handleCameraCapture}
          className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
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

      {image && (
        <div className="space-y-4">
          <div className="max-w-md mx-auto">
            <img
              src={image}
              alt="Food to analyze"
              className="w-full h-auto rounded-lg shadow-lg"
            />
          </div>

          <div className="text-center">
            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors"
            >
              {loading ? "🔍 Analyzing..." : "🔍 Analyze Food"}
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded-lg">
          Error: {error}
        </div>
      )}

      {results && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            📊 Analysis Results
          </h3>
          {results.length === 0 && (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              No food items detected.
            </div>
          )}
          <div className="grid gap-4 md:grid-cols-2">
            {results.map((item, index) => (
              <article
                key={index}
                className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border-l-4 border-purple-500"
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
        </div>
      )}
    </div>
  );
}

export default ImageFoodAnalyzer;