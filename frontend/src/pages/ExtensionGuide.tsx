import { Badge, Button, Card } from "../components/ui";
import { PageHeader } from "../components/layout";
import { api } from "../services/api";
import { useState } from "react";
import { useToastStore } from "../stores/toasts";
import type { DispatchPlan } from "../types";

export default function ExtensionGuide() {
  const [plan, setPlan] = useState<DispatchPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const push = useToastStore((s) => s.push);

  const run = async () => {
    setBusy(true);
    try {
      const p = await api.optimizeDispatch();
      setPlan(p);
    } catch (e) {
      push({ title: String(e), kind: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Chrome Dispatcher Extension"
        sub="The extension is one module of the city platform — it talks to the same backend API"
        right={<Button onClick={run} disabled={busy}>{busy ? "Computing…" : "▶ Preview dispatch optimization"}</Button>}
      />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <div className="text-sm font-medium mb-3">Install</div>
          <ol className="text-xs text-fg-dim space-y-2 list-decimal list-inside">
            <li>Open <span className="font-mono text-fg">chrome://extensions</span></li>
            <li>Enable <b>Developer mode</b></li>
            <li>Click <b>Load unpacked</b> → select <span className="font-mono text-fg">extension/</span></li>
            <li>Pin the UrbanRelay Dispatcher icon</li>
            <li>Login as <span className="font-mono text-fg">dispatcher</span> / <span className="font-mono text-fg">demo1234</span></li>
          </ol>
          <div className="mt-4 rounded-lg bg-panel-2/60 p-3 text-[10px] text-fg-faint">
            The extension calls <span className="font-mono">POST /api/dispatch/optimize</span> on your local backend — no external services.
          </div>
        </Card>

        <div className="lg:col-span-2 space-y-3">
          {!plan && (
            <Card>
              <div className="grid grid-cols-3 gap-3 text-center text-xs">
                <div className="rounded-xl bg-panel-2/60 p-4"><div className="text-2xl mb-1">📋</div>Live order list from the same backend the city dashboard uses</div>
                <div className="rounded-xl bg-panel-2/60 p-4"><div className="text-2xl mb-1">✦</div>OPTIMIZE DISPATCH runs all four AI agents</div>
                <div className="rounded-xl bg-panel-2/60 p-4"><div className="text-2xl mb-1">📊</div>Waves, hubs, routes and expected savings returned instantly</div>
              </div>
            </Card>
          )}
          {plan && (
            <>
              <Card>
                <div className="flex items-center justify-between mb-3">
                  <div className="text-sm font-medium">Optimization result — {plan.orders_considered} orders</div>
                  <Badge kind="success">{plan.waves.length} waves · {plan.courier_assignments.length} couriers</Badge>
                </div>
                {plan.savings && (
                  <div className="grid grid-cols-3 gap-3">
                    <div className="rounded-xl bg-panel-2/60 p-3.5 text-center">
                      <div className="text-lg font-bold text-good">-{plan.savings.distance_savings_pct}%</div>
                      <div className="text-[10px] text-fg-faint">distance</div>
                    </div>
                    <div className="rounded-xl bg-panel-2/60 p-3.5 text-center">
                      <div className="text-lg font-bold text-good">-{plan.savings.co2_savings_pct}%</div>
                      <div className="text-[10px] text-fg-faint">CO₂ (est.)</div>
                    </div>
                    <div className="rounded-xl bg-panel-2/60 p-3.5 text-center">
                      <div className="text-lg font-bold text-fg">{plan.curb_conflicts}</div>
                      <div className="text-[10px] text-fg-faint">curb conflicts</div>
                    </div>
                  </div>
                )}
              </Card>
              {plan.waves.map((w) => (
                <Card key={w.wave_id} className="!p-4">
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-medium">{w.wave_name} <span className="text-fg-faint text-xs">· {w.zone}</span></div>
                    <Badge kind="info">{w.orders} orders → {w.hub}</Badge>
                  </div>
                  <div className="mt-2 text-xs text-fg-dim">
                    Bulk leg {w.bulk_km} km · {w.bulk_min} min
                  </div>
                  {w.last_mile.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {w.last_mile.map((lm) => (
                        <span key={lm.order_id} className="text-[10px] px-2 py-1 rounded-md bg-panel-2 border border-line text-fg-faint font-mono">
                          last-mile → {lm.order_id.slice(0, 6)}
                        </span>
                      ))}
                    </div>
                  )}
                </Card>
              ))}
              {plan.rebalance_actions.length > 0 && (
                <Card>
                  <div className="text-sm font-medium mb-2">Fleet rebalancing</div>
                  {plan.rebalance_actions.map((a, i) => (
                    <div key={i} className="text-xs text-fg-dim py-1">↻ {a}</div>
                  ))}
                </Card>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}