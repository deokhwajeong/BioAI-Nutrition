"use client";

interface PipelineStage {
  id: string;
  label: string;
  description: string;
  status: "idle" | "running" | "done" | "error";
  detail?: string;
}

interface Props {
  stages: PipelineStage[];
  onRunAll?: () => void;
  running?: boolean;
}

const cardStyle: Record<PipelineStage["status"], string> = {
  idle: "border-white/10 bg-white/[0.03]",
  running: "border-sky-400/60 bg-sky-500/10",
  done: "border-white/10 bg-white/5",
  error: "border-red-500/50 bg-red-500/10",
};

const badge: Record<PipelineStage["status"], { text: string; style: string }> = {
  idle: { text: "Waiting", style: "text-slate-400 bg-white/5" },
  running: { text: "Running", style: "text-sky-200 bg-sky-500/20" },
  done: { text: "Done", style: "text-emerald-200 bg-emerald-500/15" },
  error: { text: "Error", style: "text-red-200 bg-red-500/20" },
};

export default function PipelineVisualizer({ stages, onRunAll, running }: Props) {
  return (
    <section className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-white">Pipeline</h2>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Runs every stage in order on a synthetic user and shows what each one produced.
          </p>
        </div>
        {onRunAll && (
          <button
            onClick={onRunAll}
            disabled={running}
            className="self-start sm:self-auto px-5 py-2.5 text-sm font-semibold rounded-md bg-teal-700 hover:bg-teal-600 text-white disabled:opacity-50 transition-colors"
          >
            {running ? "Running…" : "Run full pipeline"}
          </button>
        )}
      </div>

      <ol className="space-y-2">
        {stages.map((s, i) => (
          <li
            key={s.id}
            className={`flex items-start gap-4 p-4 rounded-lg border transition-colors ${cardStyle[s.status]}`}
          >
            <span className="mt-0.5 w-6 h-6 shrink-0 rounded-full border border-white/15 text-[11px] font-mono text-slate-300 flex items-center justify-center">
              {i + 1}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-slate-100 text-sm">{s.label}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${badge[s.status].style}`}>
                  {badge[s.status].text}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">{s.description}</p>
              {s.detail && (
                <p className={`text-xs mt-1.5 break-words ${s.status === "error" ? "text-red-300" : "text-slate-200"}`}>
                  {s.detail}
                </p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
