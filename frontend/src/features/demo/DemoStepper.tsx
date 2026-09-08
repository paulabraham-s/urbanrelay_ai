import { motion, AnimatePresence } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CityMap } from "../../components/CityMap";
import { Badge, Button, ProgressBar, StatusDot } from "../../components/ui";
import { api } from "../../services/api";
import { useToastStore } from "../../stores/toasts";
import { useSimStore } from "../../stores/sim";
import type { DispatchPlan } from "../../types";

type StepId = "intro" | "problem" | "activation" | "impact" | "finale";

const STEPS: { id: StepId; title: string; narrative: string }[] = [
  { id: "intro", title: "Ready", narrative: "" },
  { id: "problem", title: "The Problem", narrative: "Orders flood in from every platform. Each company sends its own vehicle into the same streets. Roads saturate, deliveries slow down." },
  { id: "activation", title: "UrbanRelay AI Activates", narrative: "AI clusters orders into delivery waves, selects the nearest Kirana micro-hubs, assigns bulk trucks and reserves curb space. Couriers take over the last mile." },
  { id: "impact", title: "Measurable Impact", narrative: "Fewer vehicles, less distance, lower emissions — computed live from the simulation, not pre-baked numbers." },
  { id: "finale", title: "Impact Delivered", narrative: "" },
];

export default function DemoStepper() {
  const nav = useNavigate();
  const {
    running, mode, t, generated, delivered, kpis, beforeAfter, zones, hubs, vehicles, couriers, curbZones, congestion, waves,
  } = useSimStore();
  const push = useToastStore((s) => s.push);
  const [stepIdx, setStepIdx] = useState(0);
  const [paused, setPaused] = useState(false);
  const [autoStarted, setAutoStarted] = useState(false);
  const [plan, setPlan] = useState<DispatchPlan | null>(null);
  const busyRef = useRef(false);

  const step = STEPS[stepIdx];
  const stepProgress = ((stepIdx + 1) / STEPS.length) * 100;

  const startDemo = useCallback(async () => {
    if (busyRef.current) return;
    busyRef.current = true;
    try {
      await api.simReset();
      await api.simStart("FESTIVAL_SALE", 42, 15, 120);
      push({ title: "Festival Sale scenario", body: "4.2× demand on real Secunderabad roads — watch congestion build.", kind: "info" });
      setAutoStarted(true);
      setStepIdx(1);
    } finally {
      busyRef.current = false;
    }
  }, [push]);

  // automatic step advancement based on live simulation state
  useEffect(() => {
    if (!autoStarted || paused) return;
    if (stepIdx === 1 && (generated >= 140 || t > 360)) {
      setStepIdx(2);
      void api.simActivate("urbanrelay").catch(() => undefined);
      void api.optimizeDispatch().then(setPlan).catch(() => undefined);
      push({ title: "UrbanRelay AI activated", body: "Consolidating deliveries through micro-hubs.", kind: "success" });
    } else if (stepIdx === 2 && (delivered >= 3 || t > 1500)) {
      setStepIdx(3);
    } else if (stepIdx === 3 && (delivered >= 14 || t > 2600)) {
      setStepIdx(4);
    }
  }, [autoStarted, paused, stepIdx, generated, delivered, t, push]);

  const previewRoutes = useMemo(() => {
    if (!plan) return undefined;
    const routes: number[][][] = [];
    for (const w of plan.waves) {
      if (w.bulk_route.length > 1) routes.push(w.bulk_route);
      for (const lm of w.last_mile) if (lm.route.length > 1) routes.push(lm.route);
    }
    return routes;
  }, [plan]);

  const togglePause = async () => {
    const next = !paused;
    setPaused(next);
    await api.simSpeed(next ? 0.1 : 15).catch(() => undefined);
  };

  const skip = () => {
    if (stepIdx < STEPS.length - 1) setStepIdx(stepIdx + 1);
  };

  const resetDemo = async () => {
    await api.simReset().catch(() => undefined);
    setAutoStarted(false);
    setPlan(null);
    setStepIdx(0);
  };

  const k = kpis;
  const distDelta = beforeAfter?.rows.find((r) => r.metric.includes("distance per delivery"))?.change_pct ?? 0;
  const co2Delta = beforeAfter?.rows.find((r) => r.metric.includes("CO₂ per delivery"))?.change_pct ?? 0;
  const dispDelta = beforeAfter?.rows.find((r) => r.metric.includes("dispatches per delivery"))?.change_pct ?? 0;

  return (
    <div className="h-screen flex flex-col bg-ink">
      {/* header */}
      <div className="h-14 shrink-0 flex items-center gap-4 px-5 border-b border-line bg-panel/50">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-panel-2 border border-line flex items-center justify-center text-accent font-bold">U</div>
          <span className="text-sm font-semibold">SIH Demo Mode <span className="text-fg-faint font-normal text-xs">— automated, 3 minutes</span></span>
        </div>
        <div className="flex-1 mx-4"><ProgressBar value={stepProgress / 100} color="#38bdf8" /></div>
        <Badge kind={mode === "urbanrelay" ? "urbanrelay" : "baseline"}>{mode === "urbanrelay" ? "URBANRELAY AI ACTIVE" : "CURRENT SYSTEM"}</Badge>
        <Badge kind="info">FESTIVAL SALE</Badge>
        <StatusDot color={running ? "#34d399" : "#fb7185"} pulse={running} />
        <button onClick={() => nav("/app")} className="text-[11px] text-fg-faint hover:text-fg">✕ exit</button>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row min-h-0">
        {/* map */}
        <div className="flex-1 relative min-h-[40vh] lg:min-h-0 border-r border-line">
          <CityMap zones={zones} hubs={hubs} vehicles={vehicles} couriers={couriers} curbZones={curbZones} congestion={congestion} routes={previewRoutes} height="100%" />
          <div className="absolute top-[76px] left-3 z-[600] glass rounded-xl px-3.5 py-2.5 text-[10px] pointer-events-none space-y-1">
            <div className="flex items-center gap-2 text-fg-dim"><span className="w-2 h-2 rounded-full bg-warn" /> trucks/vans</div>
            <div className="flex items-center gap-2 text-fg-dim"><span className="w-2 h-2 rounded-full bg-accent" /> light vehicles</div>
            <div className="flex items-center gap-2 text-fg-dim"><span className="w-2 h-2 rounded-full bg-good" /> couriers</div>
            <div className="flex items-center gap-2 text-fg-dim"><span className="w-3 h-px bg-accent" /> AI routes</div>
          </div>
        </div>

        {/* narrative panel */}
        <div className="w-full lg:w-[400px] shrink-0 flex flex-col bg-panel/40">
          <div className="flex-1 overflow-y-auto p-6">
            <AnimatePresence mode="wait">
              <motion.div key={step.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.35 }}>
                {stepIdx === 0 ? (
                  <div className="text-center pt-8">
                    <div className="text-5xl mb-4">🎬</div>
                    <h2 className="text-2xl font-bold tracking-tight">UrbanRelay AI</h2>
                    <p className="text-fg-dim text-sm mt-3 leading-relaxed">
                      India's Collaborative Smart Logistics Grid. This is a fully automated 3-minute demonstration —
                      festival-sale demand on real roads, then AI consolidation through Kirana micro-hubs.
                    </p>
                    <div className="mt-6 space-y-2 text-left">
                      {["Real OSM road network (offline)", "Deterministic simulated demand", "Explainable AI optimization agents", "Impact computed live — never fabricated"].map((li) => (
                        <div key={li} className="flex items-center gap-2 text-xs text-fg-dim"><span className="text-good">✓</span>{li}</div>
                      ))}
                    </div>
                    <Button size="lg" onClick={startDemo} className="mt-8 w-full">▶ START SIH DEMO</Button>
                    <button onClick={() => nav("/app")} className="mt-3 text-[11px] text-fg-faint hover:text-fg w-full">or explore the full platform →</button>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-fg-faint">
                      <span className="w-5 h-5 rounded-md grid place-items-center text-[10px] font-bold text-ink" style={{ background: stepIdx === 1 ? "#f59e0b" : stepIdx >= 2 ? "#34d399" : "#38bdf8" }}>
                        {stepIdx === 1 ? "1" : stepIdx === 2 ? "2" : "3"}
                      </span>
                      {step.title}
                    </div>
                    <p className="text-sm text-fg-dim mt-3 leading-relaxed">{step.narrative}</p>

                    {/* live stats */}
                    <div className="mt-5 grid grid-cols-2 gap-2.5">
                      <LiveStat label="Orders generated" value={generated} accent="#38bdf8" />
                      <LiveStat label="Delivered" value={delivered} accent="#34d399" />
                      <LiveStat label="Vehicles on road" value={k?.vehicles_on_road ?? 0} accent="#a78bfa" />
                      <LiveStat label="Congestion" value={`${Math.round((k?.congestion_index ?? 0) * 100)}%`} accent={k && k.congestion_index > 0.5 ? "#f59e0b" : "#e6edf7"} />
                    </div>

                    {(stepIdx === 3 || stepIdx === 4) && beforeAfter && (
                      <div className="mt-5 rounded-xl border border-line bg-panel-2/50 p-4 space-y-2.5">
                        <div className="text-[10px] text-fg-faint uppercase tracking-wider">Live impact vs current system</div>
                        <ImpactLine label="Vehicle entries" value={dispDelta} />
                        <ImpactLine label="Distance" value={distDelta} />
                        <ImpactLine label="CO₂ (est.)" value={co2Delta} />
                        <div className="pt-1">
                          <div className="flex justify-between text-[11px] mb-1"><span className="text-fg-faint">Efficiency score</span><span className="font-semibold text-accent">{Math.round((k?.efficiency_score ?? 0) * 100)}%</span></div>
                          <ProgressBar value={k?.efficiency_score ?? 0} />
                        </div>
                      </div>
                    )}

                    {stepIdx === 2 && waves.length > 0 && (
                      <div className="mt-5">
                        <div className="text-[10px] text-fg-faint uppercase tracking-wider mb-2">AI delivery waves</div>
                        <div className="space-y-1.5">
                          {waves.slice(-5).reverse().map((w) => (
                            <div key={w.id} className="flex items-center justify-between text-xs bg-panel-2/50 rounded-lg px-3 py-2">
                              <span className="text-accent font-medium">{w.name} · {w.zone_name}</span>
                              <span className="text-fg-dim">{w.orders} orders</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {stepIdx === 4 && (
                      <div className="mt-6 space-y-2">
                        <Button className="w-full" variant="outline" onClick={() => nav("/app/ai")}>Open AI Decision Center</Button>
                        <Button className="w-full" variant="outline" onClick={() => nav("/app/impact")}>Full before/after report</Button>
                        <Button className="w-full" variant="outline" onClick={() => nav("/extension")}>Chrome Dispatcher Extension</Button>
                      </div>
                    )}
                  </>
                )}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* controls */}
          {stepIdx > 0 && (
            <div className="shrink-0 border-t border-line p-4 flex gap-2">
              {stepIdx < 4 ? (
                <>
                  <Button variant="outline" size="sm" onClick={togglePause}>{paused ? "▶ Resume" : "⏸ Pause"}</Button>
                  <Button variant="ghost" size="sm" onClick={skip}>Skip step →</Button>
                </>
              ) : (
                <Button size="sm" className="w-full" onClick={() => nav("/app")}>Finish — explore the platform</Button>
              )}
              <Button variant="ghost" size="sm" onClick={resetDemo} className="ml-auto text-danger/80">↺ Reset demo</Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function LiveStat({ label, value, accent }: { label: string; value: number | string; accent: string }) {
  return (
    <div className="rounded-xl bg-panel-2/60 px-3.5 py-3">
      <div className="text-xl font-semibold tabular-nums" style={{ color: accent }}>{value}</div>
      <div className="text-[10px] text-fg-faint uppercase tracking-wide mt-0.5">{label}</div>
    </div>
  );
}

function ImpactLine({ label, value }: { label: string; value: number }) {
  const positive = value > 0;
  return (
    <div className="flex items-center justify-between">
      <span className="text-[11px] text-fg-dim">{label}</span>
      <span className={`text-xs font-semibold tabular-nums ${positive ? "text-good" : "text-fg-faint"}`}>
        {positive ? "−" : ""}{Math.abs(value).toFixed(1)}%
      </span>
    </div>
  );
}