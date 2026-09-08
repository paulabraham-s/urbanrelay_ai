import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CityMap } from "../components/CityMap";
import { Badge, Button, Card, MetricCard, ProgressBar, SectionTitle, StatusDot } from "../components/ui";
import { api } from "../services/api";
import { useToastStore } from "../stores/toasts";
import { useSimStore } from "../stores/sim";
import type { DispatchPlan } from "../types";

function KpiRow() {
  const k = useSimStore((s) => s.kpis);
  const delivered = useSimStore((s) => s.delivered);
  const b = useSimStore((s) => s.beforeAfter);
  const co2Delta = b?.rows.find((r) => r.metric.includes("CO₂ per delivery"))?.change_pct ?? null;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-3">
      <MetricCard label="Active deliveries" value={k?.active_deliveries ?? 0} icon={<span>▤</span>} accent="#38bdf8" />
      <MetricCard label="Vehicles on road" value={k?.vehicles_on_road ?? 0} icon={<span>◈</span>} accent="#a78bfa" />
      <MetricCard label="Congestion index" value={(k?.congestion_index ?? 0) * 100} decimals={0} suffix="%" icon={<span>◔</span>} accent="#f59e0b" />
      <MetricCard label="Avg delivery time" value={k?.avg_delivery_time_min ?? 0} decimals={1} suffix="min" icon={<span>⏱</span>} accent="#34d399" />
      <MetricCard label="Hub utilization" value={(k?.hub_utilization ?? 0) * 100} suffix="%" icon={<span>⬢</span>} accent="#f472b6" />
      <MetricCard label="Distance saved" value={k?.distance_saved_km ?? 0} decimals={1} suffix="km" icon={<span>➤</span>} accent="#38bdf8" />
      <MetricCard label="CO₂ saved (est.)" value={k?.co2_saved_kg ?? 0} decimals={1} suffix="kg" icon={<span>🌱</span>} accent="#34d399" delta={co2Delta} deltaGood={false} />
      <MetricCard label="Deliveries done" value={delivered} icon={<span>✓</span>} accent="#e2e8f0" />
    </div>
  );
}

function AiOperationsPanel({ onExecuted }: { onExecuted: (plan: DispatchPlan | null) => void }) {
  const recs = useSimStore((s) => s.recommendations);
  const mode = useSimStore((s) => s.mode);
  const running = useSimStore((s) => s.running);
  const setMode = useSimStore((s) => s.setMode);
  const setLastOptimization = useSimStore((s) => s.setLastOptimization);
  const push = useToastStore((s) => s.push);
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);

  const execute = async () => {
    setBusy(true);
    try {
      const plan = await api.optimizeDispatch();
      onExecuted(plan);
      setLastOptimization(plan.savings);
      if (mode === "baseline") {
        await api.simActivate("urbanrelay");
        setMode("urbanrelay");
        push({ title: "UrbanRelay AI activated", body: `${plan.waves.length} wave(s) planned through micro-hubs.`, kind: "success" });
      } else {
        push({ title: "Dispatch re-optimized", body: `${plan.orders_considered} orders consolidated.`, kind: "success" });
      }
    } catch (e) {
      push({ title: "Optimization failed", body: String(e), kind: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="!p-4 w-full xl:w-[340px] shrink-0 flex flex-col">
      <SectionTitle sub="Deterministic optimization agents — explained" right={<button onClick={() => nav("/app/ai")} className="text-[11px] text-accent hover:underline">view all →</button>}>
        AI Operations
      </SectionTitle>
      <div className="flex-1 space-y-3 overflow-y-auto">
        {recs.length === 0 && (
          <div className="text-xs text-fg-faint py-8 text-center">
            Start the simulation to see AI recommendations.
            <div className="mt-2">
              <Button size="sm" variant="outline" onClick={() => nav("/app/simulation")}>Open Simulation</Button>
            </div>
          </div>
        )}
        {recs.map((r) => (
          <div key={r.id} className="rounded-xl border border-line bg-panel-2/50 p-3.5">
            <div className="flex items-center gap-2">
              <StatusDot color={r.type === "CONGESTION" ? "#f59e0b" : "#38bdf8"} pulse />
              <span className="text-xs font-medium text-fg">{r.title}</span>
            </div>
            <p className="text-[11px] text-fg-dim mt-1.5 leading-relaxed">{r.body}</p>
            {r.expected_impact && (
              <div className="mt-2.5 grid grid-cols-2 gap-2">
                <div className="rounded-lg bg-panel px-2.5 py-1.5">
                  <div className="text-[10px] text-fg-faint">Distance ↓</div>
                  <div className="text-sm font-semibold text-good">-{r.expected_impact.distance_savings_pct ?? 0}%</div>
                </div>
                <div className="rounded-lg bg-panel px-2.5 py-1.5">
                  <div className="text-[10px] text-fg-faint">CO₂ ↓ (est.)</div>
                  <div className="text-sm font-semibold text-good">-{r.expected_impact.co2_savings_pct ?? 0}%</div>
                </div>
              </div>
            )}
            <div className="mt-3">
              <Button size="sm" variant={mode === "urbanrelay" ? "success" : "primary"} onClick={execute} disabled={!running || busy} className="w-full">
                {busy ? "Computing…" : mode === "urbanrelay" ? "↻ RE-OPTIMIZE DISPATCH" : "✦ EXECUTE RECOMMENDATION"}
              </Button>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-3 pt-3 border-t border-line text-[10px] text-fg-faint leading-relaxed">
        Scores come from an interpretable weighted model (distance, capacity, congestion, accessibility, utilization).
        Expected impact is computed by routing sample orders both ways — never fabricated.
      </div>
    </Card>
  );
}

function AlertsStrip() {
  const alerts = useSimStore((s) => s.alerts) ?? [];
  const recent = alerts.slice(0, 4);
  return (
    <div className="flex gap-2.5 overflow-x-auto pb-1">
      {recent.length === 0 && <div className="text-xs text-fg-faint py-2">No active alerts — city operations nominal.</div>}
      {recent.map((a) => (
        <div key={a.id} className={`shrink-0 rounded-xl border px-3.5 py-2.5 text-xs w-[300px] ${
          a.severity === "CRITICAL" ? "border-danger/30 bg-danger/10" : a.severity === "WARNING" ? "border-warn/30 bg-warn/10" : "border-line bg-panel-2/60"
        }`}>
          <div className="flex items-center gap-2">
            <StatusDot color={a.severity === "WARNING" ? "#f59e0b" : a.severity === "CRITICAL" ? "#fb7185" : "#38bdf8"} />
            <span className="font-medium text-fg">{a.code.replace(/_/g, " ")}</span>
          </div>
          <div className="text-fg-dim mt-1 leading-snug">{a.message}</div>
        </div>
      ))}
    </div>
  );
}

export default function CommandCenter() {
  const zones = useSimStore((s) => s.zones);
  const hubs = useSimStore((s) => s.hubs);
  const vehicles = useSimStore((s) => s.vehicles);
  const couriers = useSimStore((s) => s.couriers);
  const curbZones = useSimStore((s) => s.curbZones);
  const congestion = useSimStore((s) => s.congestion);
  const waves = useSimStore((s) => s.waves);
  const city = useSimStore((s) => s.city) ?? { id: "hyderabad", name: "Hyderabad / Secunderabad", code: "hyderabad" };
  const cityCode = city?.code ? city.code.toLowerCase() : "hyderabad";
  const cityCenter: Record<string, [number, number]> = {
    hyderabad: [17.472, 78.415],
    vizag: [17.686, 83.218],
  };
  const center = cityCenter[cityCode] ?? [17.472, 78.415];
  const [previewRoutes, setPreviewRoutes] = useState<number[][][]>([]);
  const [showRoutes, setShowRoutes] = useState(false);

  const onPlan = useCallback((plan: DispatchPlan | null) => {
    if (!plan) return;
    const routes: number[][][] = [];
    for (const w of plan.waves) {
      if (w.bulk_route.length > 1) routes.push(w.bulk_route);
      for (const lm of w.last_mile) if (lm.route.length > 1) routes.push(lm.route);
    }
    setPreviewRoutes(routes);
    setShowRoutes(true);
  }, []);

  return (
    <div className="space-y-4">
      <KpiRow />
      <div className="flex flex-col xl:flex-row gap-4">
        <div className="flex-1 relative rounded-2xl overflow-hidden border border-line min-h-[520px]">
          <            CityMap
            zones={zones}
            hubs={hubs}
            vehicles={vehicles}
            couriers={couriers}
            curbZones={curbZones}
            congestion={congestion}
            routes={showRoutes ? previewRoutes : undefined}
            cityCode={cityCode}
            center={center}
            height="520px"
          />
          {/* map overlay legend */}
          <div className="absolute top-[76px] left-3 z-[600] glass rounded-xl px-3.5 py-2.5 text-[10px] space-y-1 pointer-events-none">
            <div className="text-fg-faint uppercase tracking-wider font-medium">Legend</div>
            <div className="flex items-center gap-2 text-fg-dim"><span className="w-2 h-2 rounded-full bg-warn inline-block" /> Delivery trucks & vans</div>
            <div className="flex items-center gap-2 text-fg-dim"><span className="w-2 h-2 rounded-full bg-accent inline-block" /> Light vehicles</div>
            <div className="flex items-center gap-2 text-fg-dim"><span className="w-2 h-2 rounded-full bg-good inline-block" /> E-scooters / couriers</div>
            <div className="flex items-center gap-2 text-fg-dim"><span className="w-2 h-2 rounded-full bg-violet inline-block" /> Curb zones</div>
            <div className="flex items-center gap-2 text-fg-dim"><span className="w-3 h-px bg-accent inline-block" /> AI planned route</div>
          </div>
          <div className="absolute bottom-3 right-3 z-[600] glass rounded-lg px-3 py-1.5 text-[10px] text-fg-faint">
            Roads: OpenStreetMap © contributors (offline bundle)
          </div>
        </div>
        <AiOperationsPanel onExecuted={onPlan} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <SectionTitle sub="Consolidated order groups routed through micro-hubs">Active delivery waves</SectionTitle>
          {waves.length === 0 ? (
            <div className="text-xs text-fg-faint py-6 text-center">No waves yet — activate UrbanRelay AI to consolidate deliveries.</div>
          ) : (
            <div className="grid md:grid-cols-2 gap-3">
              {waves.slice(-8).reverse().map((w) => (
                <div key={w.id} className="rounded-xl border border-line bg-panel-2/40 p-3.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-accent">{w.name} · {w.zone_name ?? "zone"}</span>
                    <Badge kind="urbanrelay">{w.orders} orders</Badge>
                  </div>
                  <div className="text-[11px] text-fg-dim mt-1">→ hub {w.hub_name ?? w.hub_id ?? "pending"}</div>
                </div>
              ))}
            </div>
          )}
        </Card>
        <Card>
          <SectionTitle right={<span className="text-[10px] text-fg-faint">{waves.length} waves</span>}>Live alerts</SectionTitle>
          <AlertsStrip />
          <div className="mt-3">
            <ProgressBar value={0} className="opacity-0" />
          </div>
        </Card>
      </div>
    </div>
  );
}