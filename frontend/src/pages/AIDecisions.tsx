import { Badge, Card, ProgressBar, Tabs } from "../components/ui";
import { PageHeader } from "../components/layout";
import { useEffect, useMemo, useState } from "react";
import { api } from "../services/api";
import { useSimStore } from "../stores/sim";
import type { AIDecision } from "../types";

const AGENT_META: Record<string, { label: string; color: string; icon: string; desc: string }> = {
  HUB_SELECTION: { label: "Hub Selection", color: "#38bdf8", icon: "⬢", desc: "Weighted scoring: distance, capacity, congestion, accessibility, utilization, operating hours" },
  DELIVERY_WAVE: { label: "Delivery Wave", color: "#a78bfa", icon: "◈", desc: "DBSCAN clustering groups nearby orders into shared bulk + last-mile waves" },
  FLEET_BALANCER: { label: "Fleet Balancer", color: "#34d399", icon: "◈", desc: "Assigns bulk vehicles and couriers; rebalances zones to avoid duplication" },
  CURB_RESERVATION: { label: "Curb Reservation", color: "#f472b6", icon: "▭", desc: "Interval scheduling of loading slots for bulk arrivals" },
};

export default function AIDecisions() {
  const running = useSimStore((s) => s.running);
  const [decisions, setDecisions] = useState<AIDecision[]>([]);
  const [agent, setAgent] = useState("all");

  useEffect(() => {
    const load = () => api.decisions().then(setDecisions).catch(() => undefined);
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [running]);

  const filtered = useMemo(() => (agent === "all" ? decisions : decisions.filter((d) => d.agent === agent)), [decisions, agent]);

  return (
    <div>
      <PageHeader
        title="AI Decision Center"
        sub="Every decision is explainable — decision, reasons, inputs, score and expected impact. No black boxes."
        right={
          <Tabs
            tabs={[{ id: "all", label: "All agents" }, ...Object.entries(AGENT_META).map(([id, m]) => ({ id, label: m.label }))]}
            active={agent}
            onChange={setAgent}
          />
        }
      />
      {Object.entries(AGENT_META).map(([id, m]) => (
        <div key={id} className="flex items-center gap-3 mb-1 text-[11px] text-fg-faint">
          <span style={{ color: m.color }}>{m.icon}</span> {m.label}: {m.desc}
        </div>
      ))}
      <div className="mt-3 space-y-3">
        {filtered.length === 0 && (
          <Card><div className="text-xs text-fg-faint py-8 text-center">No decisions yet — run the simulation and activate UrbanRelay AI.</div></Card>
        )}
        {filtered.slice(0, 40).map((d) => {
          const meta = AGENT_META[d.agent] ?? { label: d.agent, color: "#94a3b8", icon: "✦", desc: "" };
          return (
            <Card key={d.id} className="!p-4">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg grid place-items-center shrink-0" style={{ background: `${meta.color}18`, color: meta.color, border: `1px solid ${meta.color}44` }}>
                  {meta.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: meta.color }}>{meta.label}</span>
                    <Badge kind="default">score {d.score.toFixed(2)}</Badge>
                    <span className="text-[10px] text-fg-faint">{new Date(d.created_at).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-[13px] text-fg mt-2 leading-relaxed">{d.decision}</p>
                  {d.reasons.length > 0 && d.reasons[0].label && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {d.reasons.slice(0, 8).map((r, i) => (
                        <span key={i} className="text-[10px] px-2 py-1 rounded-md bg-panel-2 border border-line text-fg-dim">
                          {r.label}{r.value !== undefined && r.value > 0 && r.weight === undefined ? ` · ${r.value}` : ""}
                        </span>
                      ))}
                    </div>
                  )}
                  {Boolean(d.impact?.hub_name || d.impact?.expected_orders) && (
                    <div className="mt-2.5 text-[11px] text-fg-faint">
                      Impact: hub <span className="text-fg-dim">{String(d.impact.hub_name ?? "")}</span>
                      {d.impact.free_slots_after !== undefined && <> · {String(d.impact.free_slots_after)} free slots after</>}
                    </div>
                  )}
                </div>
                <div className="w-24 shrink-0">
                  <div className="text-[10px] text-fg-faint text-right mb-1">confidence (weighted)</div>
                  <ProgressBar value={d.score} color={meta.color} />
                  <div className="text-right text-[11px] tabular-nums mt-1" style={{ color: meta.color }}>{Math.round(d.score * 100)}%</div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}