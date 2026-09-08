import { useNavigate } from "react-router-dom";
import { Badge, Button, Card, ProgressBar, StatusDot } from "../components/ui";
import { useSimStore } from "../stores/sim";

export default function JudgeView() {
  const nav = useNavigate();
  const k = useSimStore((s) => s.kpis);
  const ba = useSimStore((s) => s.beforeAfter);
  const mode = useSimStore((s) => s.mode);
  const running = useSimStore((s) => s.running);
  const generated = useSimStore((s) => s.generated);

  const dist = ba?.rows.find((r) => r.metric.includes("distance per delivery"))?.change_pct;
  const disp = ba?.rows.find((r) => r.metric.includes("dispatches per delivery"))?.change_pct;
  const co2 = ba?.rows.find((r) => r.metric.includes("CO₂ per delivery"))?.change_pct;
  const time = ba?.rows.find((r) => r.metric.includes("delivery time"))?.change_pct;

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold">Judge View</h1>
          <p className="text-xs text-fg-faint mt-0.5">The entire concept in under 60 seconds — all numbers from the live simulation.</p>
        </div>
        <Badge kind="info">SIMULATION MODE</Badge>
      </div>

      {!running ? (
        <Card className="text-center py-12">
          <div className="text-4xl mb-3">▶</div>
          <div className="text-sm text-fg-dim">The simulation isn't running.</div>
          <div className="mt-4"><Button onClick={() => nav("/app/simulation")}>Start the simulation</Button></div>
        </Card>
      ) : (
        <div className="space-y-4">
          <Card>
            <div className="flex items-center gap-2 text-[11px] text-fg-faint uppercase tracking-wider mb-3">
              <span className="text-danger">01</span> The Problem
            </div>
            <div className="text-lg font-medium text-fg leading-snug">
              {generated} delivery orders are being generated — and today, every logistics company sends its own vehicle
              into the same streets.
            </div>
            <div className="mt-3 flex items-center gap-2 text-xs text-fg-dim">
              <StatusDot color="#fb7185" pulse /> <span>Duplicate trips · double parking · saturated roads</span>
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-2 text-[11px] text-fg-faint uppercase tracking-wider mb-3">
              <span className="text-accent">02</span> The Action
            </div>
            <div className="text-lg font-medium text-fg leading-snug">
              UrbanRelay AI clusters orders into waves, routes bulk vehicles to the nearest Kirana micro-hubs,
              and fans out eco-friendly couriers for the last mile.
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge kind="info">Predict</Badge>
              <Badge kind="info">Orchestrate</Badge>
              <Badge kind="info">Deliver</Badge>
            </div>
            <div className="mt-4">
              <div className="text-[11px] text-fg-faint mb-1.5">Current mode</div>
              <div className="h-10 rounded-xl overflow-hidden border border-line flex relative">
                <div className={`absolute inset-y-0 transition-all duration-700 ${mode === "urbanrelay" ? "bg-good/40" : "bg-warn/40"}`} style={{ width: mode === "urbanrelay" ? "100%" : "50%" }} />
                <div className="flex-1 grid place-items-center text-xs font-medium text-warn z-10">CURRENT SYSTEM</div>
                <div className="flex-1 grid place-items-center text-xs font-medium text-good z-10">URBANRELAY AI</div>
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-2 text-[11px] text-fg-faint uppercase tracking-wider mb-4">
              <span className="text-good">03</span> The Impact
            </div>
            <div className="grid grid-cols-2 gap-3">
              <ImpactStat label="Fewer vehicle entries" value={disp} suffix="% vs current" />
              <ImpactStat label="Less distance driven" value={dist} suffix="% vs current" />
              <ImpactStat label="Faster delivery" value={time} suffix="% vs current" />
              <ImpactStat label="Lower CO₂ (est.)" value={co2} suffix="% vs current" />
            </div>
            <div className="mt-5 rounded-xl bg-panel-2/60 p-4">
              <div className="flex items-center justify-between text-xs mb-2">
                <span className="text-fg-faint">UrbanRelay Simulation Score</span>
                <span className="font-semibold text-accent">{Math.round((k?.efficiency_score ?? 0) * 100)}%</span>
              </div>
              <ProgressBar value={k?.efficiency_score ?? 0} color="#38bdf8" />
              <div className="text-[10px] text-fg-faint mt-2">
                Weighted blend of congestion, distance, time, emissions and dispatch-reduction improvements.
                Labeled a simulation score — not a government-approved metric.
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

function ImpactStat({ label, value, suffix }: { label: string; value: number | null | undefined; suffix: string }) {
  const v = value ?? 0;
  return (
    <div className="rounded-xl border border-line bg-panel-2/50 p-4">
      <div className="text-[11px] text-fg-faint uppercase tracking-wide">{label}</div>
      <div className={`mt-1.5 text-3xl font-bold tabular-nums ${v > 0 ? "text-good" : v < 0 ? "text-danger" : "text-fg"}`}>
        {v > 0 ? "−" : ""}{Math.abs(v).toFixed(1)}
        <span className="text-sm font-medium text-fg-dim ml-1">{suffix}</span>
      </div>
    </div>
  );
}