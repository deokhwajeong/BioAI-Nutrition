"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type ParsedRow = Record<string, string | number | null>;

type ChartType = "line" | "bar" | "area";

type ParsedResult = {
  rows: ParsedRow[];
  xKey: string | null;
  numericKeys: string[];
};

type FetchResponse = {
  data?: ParsedRow[];
  signed_url?: string | null;
  content_type?: string;
  source?: string;
  error?: string;
};

const isNumeric = (value: unknown): value is number =>
  typeof value === "number" && !Number.isNaN(value);

const normalizeValue = (value: string): number | string => {
  const numeric = Number(value);
  if (!Number.isNaN(numeric)) return numeric;
  return value;
};

// Fancy color palette
const COLORS = [
  "#6366f1", // Indigo
  "#10b981", // Emerald
  "#f59e0b", // Amber
  "#ef4444", // Red
  "#8b5cf6", // Violet
  "#06b6d4", // Cyan
  "#84cc16", // Lime
  "#f97316", // Orange
];

const parseCsv = (text: string): ParsedResult => {
  const [headerLine, ...rows] = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!headerLine) return { rows: [], xKey: null, numericKeys: [] };

  const headers = headerLine.split(/,|\t/).map((h) => h.trim());
  const data: ParsedRow[] = rows.map((row) => {
    const values = row.split(/,|\t/).map((value) => value.trim());
    const record: ParsedRow = {};
    headers.forEach((header, index) => {
      record[header || `col_${index + 1}`] = normalizeValue(values[index] ?? "");
    });
    return record;
  });

  const numericKeys = headers.filter((header) =>
    data.some((row) => isNumeric(row[header]))
  );
  const xKey = headers[0] ?? null;

  return { rows: data, xKey, numericKeys };
};

const parseJson = (text: string): ParsedResult => {
  const payload = JSON.parse(text);
  const items: ParsedRow[] = Array.isArray(payload)
    ? payload
    : typeof payload === "object" && payload
      ? [payload as ParsedRow]
      : [];

  if (!items.length) return { rows: [], xKey: null, numericKeys: [] };

  const keys = Object.keys(items[0]);
  const numericKeys = keys.filter((key) =>
    items.some((item) => isNumeric(item[key]))
  );
  const xKey = keys.find((key) => !numericKeys.includes(key)) ?? keys[0] ?? null;

  const normalized = items.map((item) => {
    const entry: ParsedRow = {};
    Object.entries(item).forEach(([key, value]) => {
      if (typeof value === "string") {
        entry[key] = normalizeValue(value);
      } else if (typeof value === "number") {
        entry[key] = value;
      } else {
        entry[key] = value ?? null;
      }
    });
    return entry;
  });

  return { rows: normalized, xKey, numericKeys };
};

const GraphUpload: React.FC = () => {
  const [rows, setRows] = useState<ParsedRow[]>([]);
  const [numericKeys, setNumericKeys] = useState<string[]>([]);
  const [xKey, setXKey] = useState<string | null>(null);
  const [chartType, setChartType] = useState<ChartType>("line");
  const [status, setStatus] = useState<string>("Drop a CSV/JSON file to get started.");
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isFetching, setIsFetching] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Load sample data on mount
  useEffect(() => {
    const sampleCsv = `Date,Fiber Intake (g),Calories,Protein (g),Carbs (g),Fat (g)
2024-01-01,15,2200,80,250,70
2024-01-02,18,2100,85,240,65
2024-01-03,12,2300,75,260,75
2024-01-04,20,2000,90,230,60
2024-01-05,16,2150,82,245,68
2024-01-06,14,2250,78,255,72
2024-01-07,22,1950,95,220,55
2024-01-08,19,2050,88,235,62
2024-01-09,17,2180,83,248,69
2024-01-10,13,2280,76,258,74`;
    const result = parseCsv(sampleCsv);
    handleParsed(result);
  }, []);

  const reset = () => {
    setRows([]);
    setNumericKeys([]);
    setXKey(null);
  };

  const handleParsed = (result: ParsedResult) => {
    if (!result.rows.length) {
      setStatus("No rows detected. Please check your file.");
      setError("Empty dataset");
      return;
    }
    setRows(result.rows);
    setNumericKeys(result.numericKeys);
    setXKey(result.xKey);
    setError(null);
    setStatus(`Loaded ${result.rows.length} rows from local file.`);
  };

  const parseFile = useCallback(async (file: File) => {
    const text = await file.text();
    const lower = file.name.toLowerCase();
    if (lower.endsWith(".csv")) {
      return parseCsv(text);
    }
    if (lower.endsWith(".json")) {
      return parseJson(text);
    }
    // Fallback: attempt JSON first, then CSV
    try {
      return parseJson(text);
    } catch (jsonErr) {
      try {
        return parseCsv(text);
      } catch (csvErr) {
        console.error({ jsonErr, csvErr });
        throw new Error("Unsupported file format. Use CSV or JSON.");
      }
    }
  }, []);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files?.length) return;
      setStatus("Parsing file...");
      setError(null);
      try {
        const result = await parseFile(files[0]);
        handleParsed(result);
      } catch (err) {
        console.error(err);
        reset();
        setError(err instanceof Error ? err.message : "Unable to parse file.");
        setStatus("Upload failed.");
      }
    },
    [parseFile]
  );

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setIsDragging(false);
      void handleFiles(event.dataTransfer.files);
    },
    [handleFiles]
  );

  const onDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(true);
  };

  const onDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
  };

  const handleUrlFetch = async () => {
    if (!urlInput) return;
    setIsFetching(true);
    setStatus("Fetching via secure proxy...");
    setError(null);
    try {
      const response = await fetch("/api/ingest/fetch", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: urlInput }),
      });
      const payload: FetchResponse = await response.json();
      if (!response.ok || payload.error) {
        throw new Error(payload.error || "Unable to fetch remote data.");
      }
      if (payload.data?.length) {
        const keys = Object.keys(payload.data[0]);
        setRows(payload.data);
        setNumericKeys(keys.filter((key) => payload.data?.some((row) => isNumeric(row[key]))));
        setXKey(keys[0] ?? null);
        setStatus(`Fetched ${payload.data.length} rows from proxy.`);
      } else if (payload.signed_url) {
        setStatus("Received signed asset URL.");
      } else {
        setStatus("No data returned from proxy.");
      }
    } catch (err) {
      console.error(err);
      reset();
      setError(err instanceof Error ? err.message : "Unable to fetch URL.");
      setStatus("URL fetch failed.");
    } finally {
      setIsFetching(false);
    }
  };

  const chartContent = useMemo(() => {
    if (!rows.length || !numericKeys.length || !xKey) return null;

    const data = rows.map((row, index) => ({
      ...row,
      index,
    }));

    const axesKey = xKey ?? "index";
    const valueKeys = numericKeys.filter((key) => key !== axesKey);

    if (!valueKeys.length) return null;

    if (chartType === "bar") {
      return (
        <ResponsiveContainer width="100%" height={400}>
          <BarChart
            data={data}
            margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
            barCategoryGap="20%"
          >
            <defs>
              {valueKeys.map((key, idx) => (
                <linearGradient key={`gradient-${idx}`} id={`gradient-${idx}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS[idx % COLORS.length]} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={COLORS[idx % COLORS.length]} stopOpacity={0.3}/>
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey={axesKey}
              tick={{ fontSize: 12, fill: '#6b7280' }}
              axisLine={{ stroke: '#d1d5db' }}
            />
            <YAxis
              tick={{ fontSize: 12, fill: '#6b7280' }}
              axisLine={{ stroke: '#d1d5db' }}
              allowDecimals
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
            />
            <Legend
              wrapperStyle={{ paddingTop: '20px' }}
              iconType="rect"
            />
            {valueKeys.map((key, idx) => (
              <Bar
                key={key}
                dataKey={key}
                fill={`url(#gradient-${idx})`}
                radius={[4, 4, 0, 0]}
                isAnimationActive={true}
                animationDuration={1000}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      );
    }

    if (chartType === "area") {
      return (
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart
            data={data}
            margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
          >
            <defs>
              {valueKeys.map((key, idx) => (
                <linearGradient key={`areaGradient-${idx}`} id={`areaGradient-${idx}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS[idx % COLORS.length]} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={COLORS[idx % COLORS.length]} stopOpacity={0.1}/>
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey={axesKey}
              tick={{ fontSize: 12, fill: '#6b7280' }}
              axisLine={{ stroke: '#d1d5db' }}
            />
            <YAxis
              tick={{ fontSize: 12, fill: '#6b7280' }}
              axisLine={{ stroke: '#d1d5db' }}
              allowDecimals
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
            />
            <Legend
              wrapperStyle={{ paddingTop: '20px' }}
              iconType="rect"
            />
            {valueKeys.map((key, idx) => (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                stroke={COLORS[idx % COLORS.length]}
                strokeWidth={2}
                fill={`url(#areaGradient-${idx})`}
                isAnimationActive={true}
                animationDuration={1500}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      );
    }

    return (
      <ResponsiveContainer width="100%" height={400}>
        <LineChart
          data={data}
          margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey={axesKey}
            tick={{ fontSize: 12, fill: '#6b7280' }}
            axisLine={{ stroke: '#d1d5db' }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#6b7280' }}
            axisLine={{ stroke: '#d1d5db' }}
            allowDecimals
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #d1d5db',
              borderRadius: '8px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }}
          />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="line"
          />
          {valueKeys.map((key, idx) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={COLORS[idx % COLORS.length]}
              strokeWidth={3}
              dot={{ fill: COLORS[idx % COLORS.length], strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, stroke: COLORS[idx % COLORS.length], strokeWidth: 2 }}
              isAnimationActive={true}
              animationDuration={2000}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  }, [chartType, rows, numericKeys, xKey]);

  const validationMessage = useMemo(() => {
    if (error) return error;
    if (!rows.length) return "Upload a CSV/JSON file or paste a URL to preview charts.";
    if (!numericKeys.length) return "No numeric columns detected. Add numeric values to render charts.";
    if (!xKey) return "Unable to infer an x-axis column. Include an index or timestamp column.";
    return null;
  }, [error, rows.length, numericKeys.length, xKey]);

  return (
    <section className="space-y-6">
      <div
        className={`border-2 border-dashed rounded-md p-6 transition-colors ${
          isDragging ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-white"
        }`}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
      >
        <div className="flex flex-col gap-3 items-start md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Secure Graph Upload</h2>
            <p className="text-sm text-gray-600">
              Drag and drop CSV/JSON files to keep parsing on-device. Data stays in the browser unless you opt into the proxy.
            </p>
          </div>
          <div className="flex gap-3">
            <button
              className="px-3 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
              onClick={() => fileInputRef.current?.click()}
            >
              Choose file
            </button>
            <select
              className="px-2 py-2 text-sm border rounded"
              value={chartType}
              onChange={(event) => setChartType(event.target.value as ChartType)}
            >
              <option value="line">Line</option>
              <option value="bar">Bar</option>
              <option value="area">Area</option>
            </select>
          </div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.json,text/csv,application/json"
          hidden
          onChange={(event) => void handleFiles(event.target.files)}
        />
        <p className="mt-3 text-sm text-gray-700">{status}</p>
        {error ? (
          <p className="mt-1 text-sm text-red-600">{error}</p>
        ) : (
          <p className="mt-1 text-xs text-gray-500">We never upload local files. Parsing runs entirely in your browser.</p>
        )}
      </div>

      <div className="border rounded-md p-4 space-y-3 bg-gray-50">
        <h3 className="font-medium">Paste URL</h3>
        <p className="text-sm text-gray-600">
          If your data is hosted elsewhere, we will fetch it server-side to avoid browser CORS or credential leaks. Only the proxied response returns to this page.
        </p>
        <div className="flex flex-col gap-2 md:flex-row md:items-center">
          <input
            type="url"
            placeholder="https://example.com/data.csv"
            value={urlInput}
            onChange={(event) => setUrlInput(event.target.value)}
            className="flex-1 px-3 py-2 border rounded"
          />
          <button
            onClick={handleUrlFetch}
            disabled={!urlInput || isFetching}
            className="px-3 py-2 rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
          >
            {isFetching ? "Fetching..." : "Fetch via proxy"}
          </button>
        </div>
      </div>

      <div className="border rounded-md p-4 bg-white shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold">Preview</h3>
          <div className="text-xs text-gray-500">
            {rows.length ? `${rows.length} rows` : "No data loaded"}
          </div>
        </div>
        {!chartContent && validationMessage && (
          <div className="text-sm text-gray-600">{validationMessage}</div>
        )}
        {chartContent}
      </div>
    </section>
  );
};

export default GraphUpload;
