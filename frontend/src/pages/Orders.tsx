import { useMemo, useState } from "react";
import { Badge, Button, Card, DataTable, Tabs } from "../components/ui";
import { PageHeader } from "../components/layout";
import { api } from "../services/api";
import { useToastStore } from "../stores/toasts";
import { useSimStore } from "../stores/sim";
import type { Order } from "../types";

const STATUS_BADGE: Record<string, string> = {
  PENDING: "PENDING",
  WAVE_ASSIGNED: "warning",
  PICKED_UP: "warning",
  AT_HUB: "info",
  OUT_FOR_DELIVERY: "urbanrelay",
  DELIVERED: "success",
};

const PLATFORM_COLORS: Record<string, string> = {
  Amazon: "#f59e0b",
  Flipkart: "#38bdf8",
  Blinkit: "#a78bfa",
  Zepto: "#f472b6",
  Swiggy: "#f59e0b",
  "Local Store": "#34d399",
};

export default function Orders() {
  const orders = useSimStore((s) => s.orders);
  const [tab, setTab] = useState("all");
  const [mode, setMode] = useState("all");
  const push = useToastStore((s) => s.push);
  const [busy, setBusy] = useState(false);

  const filtered = useMemo(() => {
    let list = [...orders].sort((a, b) => b.created_t - a.created_t);
    if (tab === "pending") list = list.filter((o) => o.status === "PENDING");
    if (tab === "active") list = list.filter((o) => !["DELIVERED", "CANCELLED"].includes(o.status));
    if (tab === "delivered") list = list.filter((o) => o.status === "DELIVERED");
    if (mode === "baseline") list = list.filter((o) => o.mode === "baseline");
    if (mode === "urbanrelay") list = list.filter((o) => o.mode === "urbanrelay");
    return list.slice(0, 400);
  }, [orders, tab, mode]);

  const pendingCount = orders.filter((o) => o.status === "PENDING").length;

  const optimize = async () => {
    setBusy(true);
    try {
      const plan = await api.optimizeDispatch();
      push({
        title: "Dispatch optimized",
        body: `${plan.orders_considered} orders → ${plan.waves.length} waves, ${plan.courier_assignments.length} couriers, ${plan.curb_conflicts} curb conflicts.`,
        kind: "success",
      });
    } catch (e) {
      push({ title: "Optimization failed", body: String(e), kind: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Orders"
        sub="SIMULATED order streams from major platforms — clearly labeled, no real integrations"
        right={
          <div className="flex items-center gap-2">
            <Badge kind="warning">{pendingCount} pending</Badge>
            <Button onClick={optimize} disabled={busy || pendingCount === 0}>{busy ? "Optimizing…" : "✦ Optimize dispatch"}</Button>
          </div>
        }
      />
      <Card className="!p-0">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-line">
          <Tabs
            tabs={[{ id: "all", label: "All" }, { id: "active", label: "Active" }, { id: "pending", label: "Pending" }, { id: "delivered", label: "Delivered" }]}
            active={tab}
            onChange={setTab}
          />
          <Tabs tabs={[{ id: "all", label: "Both modes" }, { id: "baseline", label: "Baseline" }, { id: "urbanrelay", label: "UrbanRelay" }]} active={mode} onChange={setMode} />
        </div>
        <DataTable<Order>
          rows={filtered}
          rowKey={(o) => o.id}
          empty="No orders match the current filter — start the simulation."
          columns={[
            { key: "id", label: "Order", render: (o) => <span className="font-mono text-[11px] text-fg-dim">{o.id.slice(0, 8)}</span> },
            { key: "platform", label: "Platform", render: (o) => (
                <span className="text-xs font-medium" style={{ color: PLATFORM_COLORS[o.platform] ?? "#e6edf7" }}>{o.platform}</span>
              ) },
            { key: "zone_name", label: "Zone", render: (o) => <span className="text-fg-dim">{o.zone_name ?? "—"}</span> },
            { key: "customer_name", label: "Customer", render: (o) => <span className="text-fg">{o.customer_name}</span> },
            { key: "status", label: "Status", render: (o) => <Badge kind={STATUS_BADGE[o.status] ?? "default"}>{o.status.replace(/_/g, " ")}</Badge> },
            { key: "mode", label: "Mode", render: (o) => <Badge kind={o.mode === "urbanrelay" ? "urbanrelay" : "baseline"}>{o.mode}</Badge> },
            { key: "priority", label: "P", render: (o) => <span className={`tabular-nums ${o.priority >= 3 ? "text-danger font-semibold" : "text-fg-dim"}`}>{o.priority}</span> },
            { key: "t", label: "Age", render: (o) => <AgeTicker created={o.created_t} /> },
            { key: "distance", label: "Dist", render: (o) => <span className="tabular-nums text-fg-dim">{o.distance_km != null ? `${o.distance_km.toFixed(1)} km` : "—"}</span> },
          ]}
        />
      </Card>
    </div>
  );
}

function AgeTicker({ created }: { created: number }) {
  const t = useSimStore((s) => s.t);
  const mins = Math.max(0, Math.round((t - created) / 60));
  return <span className="tabular-nums text-fg-faint">{mins}m</span>;
}