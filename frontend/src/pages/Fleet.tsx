import { Badge, Card, DataTable, Tabs } from "../components/ui";
import { PageHeader } from "../components/layout";
import { useState } from "react";
import { useSimStore } from "../stores/sim";
import type { Courier, Vehicle } from "../types";

const STATUS_BADGE: Record<string, string> = {
  IDLE: "IDLE",
  AVAILABLE: "success",
  TO_HUB: "warning",
  TO_CUSTOMER: "warning",
  WAITING_AT_HUB: "info",
  DELIVERING: "urbanrelay",
};

export default function Fleet() {
  const vehicles = useSimStore((s) => s.vehicles);
  const couriers = useSimStore((s) => s.couriers);
  const [tab, setTab] = useState("vehicles");

  const fleetSummary = vehicles.reduce<Record<string, number>>((acc, v) => {
    acc[v.type] = (acc[v.type] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <PageHeader
        title="Fleet"
        sub={`${vehicles.length} vehicles · ${couriers.length} couriers — live status from the simulation`}
        right={<Tabs tabs={[{ id: "vehicles", label: "Vehicles" }, { id: "couriers", label: "Couriers" }]} active={tab} onChange={setTab} />}
      />
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
        {Object.entries(fleetSummary).map(([type, count]) => (
          <Card key={type} className="!p-3.5">
            <div className="text-[11px] text-fg-faint uppercase tracking-wide">{type}</div>
            <div className="text-xl font-semibold text-fg mt-1">{count}</div>
          </Card>
        ))}
      </div>
      <Card className="!p-0">
        {tab === "vehicles" ? (
          <DataTable<Vehicle>
            rows={vehicles}
            rowKey={(v) => v.id}
            empty="No vehicles"
            columns={[
              { key: "name", label: "Vehicle", render: (v) => <span className="font-medium text-fg">{v.name}</span> },
              { key: "type", label: "Type", render: (v) => <span className="capitalize text-fg-dim">{v.type}</span> },
              { key: "status", label: "Status", render: (v) => <Badge kind={STATUS_BADGE[v.status] ?? "default"}>{v.status.replace(/_/g, " ")}</Badge> },
              { key: "cargo", label: "Parcels", render: (v) => <span className="tabular-nums text-fg-dim">{v.cargo ?? 0}/{v.capacity}</span> },
              { key: "pos", label: "Position", render: (v) => <span className="font-mono text-[11px] text-fg-faint">{v.lat.toFixed(4)}, {v.lng.toFixed(4)}</span> },
              { key: "mode", label: "Mode", render: (v) => <Badge kind={v.mode === "urbanrelay" ? "urbanrelay" : "baseline"}>{v.mode ?? "—"}</Badge> },
            ]}
          />
        ) : (
          <DataTable<Courier>
            rows={couriers}
            rowKey={(c) => c.id}
            empty="No couriers"
            columns={[
              { key: "name", label: "Courier", render: (c) => <span className="font-medium text-fg">{c.name}</span> },
              { key: "mode", label: "Mode", render: (c) => <span className="capitalize text-fg-dim">{c.mode}</span> },
              { key: "status", label: "Status", render: (c) => <Badge kind={STATUS_BADGE[c.status] ?? "default"}>{c.status.replace(/_/g, " ")}</Badge> },
              { key: "load", label: "Load", render: (c) => <span className="tabular-nums text-fg-dim">{c.cargo ?? 0}/{c.capacity}</span> },
              { key: "earnings", label: "Earnings", render: (c) => <span className="tabular-nums text-good">₹{c.earnings?.toFixed(1) ?? "0"}</span> },
            ]}
          />
        )}
      </Card>
    </div>
  );
}