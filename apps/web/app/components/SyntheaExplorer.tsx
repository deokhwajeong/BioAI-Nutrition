"use client";

import { useState, useEffect } from "react";
import {
  syntheaStatus,
  syntheaLoadPatient,
  syntheaPatientDetail,
} from "../../lib/api";

interface PatientSummary {
  patient_id: string;
  name: string;
  gender: string;
  birth_date: string;
  height_cm: number | null;
  bmi: number | null;
  total_readings: number;
  readings_by_type: Record<string, number>;
  conditions: number;
  medications: number;
}

interface ReadingSample {
  timestamp: string;
  value: number;
  unit: string;
  metadata: Record<string, unknown>;
}

interface ReadingsDetail {
  count: number;
  sample: ReadingSample[];
  latest: ReadingSample | null;
}

interface PatientDetail {
  patient_id: string;
  name: string;
  gender: string;
  birth_date: string;
  height_cm: number | null;
  bmi: number | null;
  total_readings: number;
  readings_by_type: Record<string, number>;
  conditions: Array<{
    code: string;
    display: string;
    onset: string;
    clinical_status: string;
  }>;
  medications: Array<{
    display: string;
    status: string;
    authored_on: string;
  }>;
  readings_detail: Record<string, ReadingsDetail>;
}

interface LoadResult {
  patient_id: string;
  user_id: string;
  readings_loaded: number;
  readings_by_type: Record<string, number>;
  conditions: Array<{ display: string }>;
  medications: Array<{ display: string }>;
}

const BIOMARKER_ICONS: Record<string, string> = {
  glucose: "🩸",
  heart_rate: "💓",
  blood_pressure: "🫀",
  weight: "⚖️",
  blood_test: "🧪",
  hrv: "📈",
  steps: "🚶",
  sleep: "😴",
  genotype: "🧬",
};

export default function SyntheaExplorer() {
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filesFound, setFilesFound] = useState(0);

  // Selected patient detail
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<PatientDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Load into engine
  const [loadResult, setLoadResult] = useState<LoadResult | null>(null);
  const [loadingInto, setLoadingInto] = useState<string | null>(null);

  // Fetch patient list on mount
  useEffect(() => {
    (async () => {
      try {
        const data = await syntheaStatus();
        setPatients(data.available_patients ?? []);
        setFilesFound(data.files_found ?? 0);
      } catch (err: any) {
        setError(err?.message ?? "Failed to fetch Synthea data");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Load detail when patient selected
  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    (async () => {
      setDetailLoading(true);
      try {
        const data = await syntheaPatientDetail(selectedId);
        setDetail(data);
      } catch (err: any) {
        setError(err?.message ?? "Failed to load patient detail");
      } finally {
        setDetailLoading(false);
      }
    })();
  }, [selectedId]);

  const handleLoadIntoEngine = async (patientId: string) => {
    setLoadingInto(patientId);
    setLoadResult(null);
    try {
      const result = await syntheaLoadPatient(patientId, "demo-user-001");
      setLoadResult(result);
    } catch (err: any) {
      setError(err?.message ?? "Failed to load into engine");
    } finally {
      setLoadingInto(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full" />
        <span className="ml-3 text-gray-400">Loading Synthea data...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-3xl">🏥</span>
            <div>
              <h2 className="text-2xl font-bold">Synthea FHIR Data Explorer</h2>
              <p className="text-sm text-gray-400 mt-0.5">
                Clinically realistic synthetic patient data (HL7 FHIR R4)
              </p>
            </div>
          </div>
        </div>
        <div className="text-right text-xs text-gray-500">
          <div>{filesFound} FHIR bundles</div>
          <div>{patients.length} patients parsed</div>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-3 text-red-300 hover:text-white underline"
          >
            dismiss
          </button>
        </div>
      )}

      {/* Load result toast */}
      {loadResult && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-300 text-sm animate-fade-in">
          <div className="font-semibold mb-1">
            Loaded {loadResult.readings_loaded} readings into engine
            (user: {loadResult.user_id})
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            {Object.entries(loadResult.readings_by_type).map(([type, count]) => (
              <span
                key={type}
                className="px-2 py-0.5 bg-emerald-500/20 rounded-full text-xs"
              >
                {BIOMARKER_ICONS[type] ?? "📊"} {type}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {patients.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg">No Synthea data found.</p>
          <p className="text-sm mt-2">
            Generate data using: <code className="text-cyan-400">java -jar synthea-with-dependencies.jar -p 5</code>
          </p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Patient List */}
          <div className="lg:col-span-1 space-y-3">
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
              Patients ({patients.length})
            </h3>
            {patients.map((p) => (
              <button
                key={p.patient_id}
                onClick={() => setSelectedId(p.patient_id)}
                className={`w-full text-left p-4 rounded-xl border transition-all ${
                  selectedId === p.patient_id
                    ? "bg-cyan-500/10 border-cyan-500/30 shadow-lg shadow-cyan-500/5"
                    : "bg-white/5 border-white/10 hover:bg-white/10"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-white">{p.name}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      p.gender === "male"
                        ? "bg-blue-500/20 text-blue-300"
                        : "bg-pink-500/20 text-pink-300"
                    }`}
                  >
                    {p.gender === "male" ? "♂" : "♀"} {p.gender}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-gray-400">
                  <span>Born: {p.birth_date}</span>
                  <span>{p.total_readings} readings</span>
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  {Object.entries(p.readings_by_type).map(([type, count]) => (
                    <span
                      key={type}
                      className="px-1.5 py-0.5 bg-white/5 rounded text-[10px] text-gray-400"
                    >
                      {BIOMARKER_ICONS[type] ?? "📊"} {count}
                    </span>
                  ))}
                </div>
              </button>
            ))}
          </div>

          {/* Patient Detail */}
          <div className="lg:col-span-2">
            {!selectedId ? (
              <div className="flex items-center justify-center h-64 text-gray-500">
                <p>Select a patient to view FHIR data</p>
              </div>
            ) : detailLoading ? (
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full" />
              </div>
            ) : detail ? (
              <div className="space-y-6 animate-fade-in">
                {/* Patient header + load button */}
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-xl font-bold">{detail.name}</h3>
                    <p className="text-sm text-gray-400">
                      {detail.gender} · Born {detail.birth_date}
                      {detail.height_cm && ` · ${detail.height_cm} cm`}
                      {detail.bmi && ` · BMI ${detail.bmi.toFixed(1)}`}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5 font-mono">
                      {detail.patient_id}
                    </p>
                  </div>
                  <button
                    onClick={() => handleLoadIntoEngine(detail.patient_id)}
                    disabled={loadingInto === detail.patient_id}
                    className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-700 hover:to-cyan-700 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition shadow-lg"
                  >
                    {loadingInto === detail.patient_id
                      ? "Loading..."
                      : "Load into Engine →"}
                  </button>
                </div>

                {/* Biomarker readings */}
                <div>
                  <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                    Biomarker Readings ({detail.total_readings})
                  </h4>
                  <div className="grid md:grid-cols-2 gap-3">
                    {Object.entries(detail.readings_detail).map(
                      ([type, info]) => (
                        <div
                          key={type}
                          className="bg-white/5 border border-white/10 rounded-xl p-4"
                        >
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <span className="text-lg">
                                {BIOMARKER_ICONS[type] ?? "📊"}
                              </span>
                              <span className="font-semibold text-white capitalize">
                                {type.replace(/_/g, " ")}
                              </span>
                            </div>
                            <span className="text-xs text-gray-400 bg-white/10 px-2 py-0.5 rounded-full">
                              {info.count} readings
                            </span>
                          </div>
                          {info.latest && (
                            <div className="mb-3 p-2 bg-white/5 rounded-lg">
                              <div className="text-xs text-gray-500">
                                Latest reading
                              </div>
                              <div className="text-lg font-bold text-cyan-300">
                                {typeof info.latest.value === "number"
                                  ? info.latest.value.toFixed(2)
                                  : info.latest.value}{" "}
                                <span className="text-xs text-gray-400 font-normal">
                                  {info.latest.unit}
                                </span>
                              </div>
                              <div className="text-[10px] text-gray-500">
                                {new Date(
                                  info.latest.timestamp
                                ).toLocaleDateString()}
                              </div>
                            </div>
                          )}
                          {/* Sample timeline */}
                          <div className="space-y-1">
                            {info.sample.slice(0, 3).map((s, i) => (
                              <div
                                key={i}
                                className="flex justify-between text-xs text-gray-400"
                              >
                                <span>
                                  {new Date(s.timestamp).toLocaleDateString()}
                                </span>
                                <span className="font-mono">
                                  {typeof s.value === "number"
                                    ? s.value.toFixed(2)
                                    : s.value}{" "}
                                  {s.unit}
                                </span>
                              </div>
                            ))}
                            {info.count > 3 && (
                              <div className="text-[10px] text-gray-600">
                                +{info.count - 3} more readings...
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    )}
                  </div>
                </div>

                {/* Conditions */}
                {detail.conditions.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                      Conditions ({detail.conditions.length})
                    </h4>
                    <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-white/10 text-left text-xs text-gray-500 uppercase">
                            <th className="px-4 py-2">Condition</th>
                            <th className="px-4 py-2">Onset</th>
                            <th className="px-4 py-2">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {detail.conditions.map((c, i) => (
                            <tr
                              key={i}
                              className="border-b border-white/5 hover:bg-white/5"
                            >
                              <td className="px-4 py-2 text-white">
                                {c.display}
                              </td>
                              <td className="px-4 py-2 text-gray-400">
                                {c.onset}
                              </td>
                              <td className="px-4 py-2">
                                <span
                                  className={`px-2 py-0.5 rounded-full text-xs ${
                                    c.clinical_status === "active"
                                      ? "bg-amber-500/20 text-amber-300"
                                      : "bg-gray-500/20 text-gray-400"
                                  }`}
                                >
                                  {c.clinical_status}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Medications */}
                {detail.medications.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                      Medications ({detail.medications.length})
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {detail.medications.map((m, i) => (
                        <div
                          key={i}
                          className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm"
                        >
                          <span className="text-white">{m.display}</span>
                          <span className="text-gray-500 text-xs ml-2">
                            {m.status} · {m.authored_on}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* FHIR badge */}
                <div className="flex items-center gap-4 text-[10px] text-gray-600 pt-4 border-t border-white/5">
                  <span>HL7 FHIR R4 · Synthea v3.x</span>
                  <span>LOINC coded observations</span>
                  <span>SNOMED CT conditions</span>
                  <span>RxNorm medications</span>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

// Updated: 2024-08-24

// TODO: refactor this component

// Updated: 2026-02-09