"use client";

import React, { useCallback, useMemo, useRef, useState } from "react";
import {
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

type ChartType = "line" | "bar";

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
        <ResponsiveContainer width="100%" height={360}>
          <BarChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={axesKey} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} allowDecimals />
            <Tooltip />
            <Legend />
            {valueKeys.map((key, idx) => (
              <Bar key={key} dataKey={key} fill={idx % 2 === 0 ? "#2563eb" : "#22c55e"} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      );
    }

    return (
      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={axesKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} allowDecimals />
          <Tooltip />
          <Legend />
          {valueKeys.map((key, idx) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={idx % 2 === 0 ? "#2563eb" : "#22c55e"}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
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
