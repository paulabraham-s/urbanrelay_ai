import { useState } from "react";
import { CityMap } from "../components/CityMap";
import { Badge, Card, DataTable, Tabs } from "../components/ui";
import { PageHeader } from "../components/layout";
import { useSimStore } from "../stores/sim";
import type { Courier, Vehicle } from "../types";

const STATUS_BADGE: Record<string, string> = {
  IDLE: "IDLE",
  TO_HUB: "warning",
  TO_CUSTOMER: "warning",
  WAITING_AT_HUB: "default",
  DELIVERING: "urbanrelay",
  AVAILABLE: "success",
  OUT_FOR_DELIVERY: "urbanrelay",
};

export default function LiveOps() {
  const zones = useSimStore((s) => s.zones);
  const hubs = useSimStore((s) => s.hubs);
  const vehicles = useSimStore((s) => s.vehicles);
  const couriers = useSimStore((s) => s.couriers);
  const curbZones = useSimStore((s) => s.curbZones);
  const congestion = useSimStore((s) => s.congestion);
  const [tab, setTab] = useState("vehicles");

  return (
    <div>
      <PageHeader
        title="Live Operations"
        sub="Real-time fleet movements on the Secunderabad · Kukatpally · Miyapur road network"
        right={<Tabs tabs={[{ id: "vehicles", label: `Vehicles (${vehicles.length})` }, { id: "couriers", label: `Couriers (${couriers.length})` }]} active={tab} onChange={setTab} />}
      />
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 rounded-2xl overflow-hidden border border-line min-h-[480px] relative">
          <CityMap zones={zones} hubs={hubs} vehicles={vehicles} couriers={couriers} curbZones={curbZones} congestion={congestion} height="480px" />
        </div>
        <Card>
          {tab === "vehicles" ? <VehicleTable vehicles={vehicles} /> : <CourierTable couriers={couriers} />}
        </Card>
      </div>
    </div>
  );
}

function VehicleTable({ vehicles }: { vehicles: Vehicle[] }) {
  return (
    <DataTable<Vehicle>
      rows={vehicles}
      rowKey={(v) => v.id}
      empty="No vehicles active"
      columns={[
        { key: "name", label: "Vehicle", render: (v) => <span className="font-medium text-fg">{v.name}</span> },
        { key: "type", label: "Type", render: (v) => <span className="capitalize text-fg-dim">{v.type}</span> },
        { key: "status", label: "Status", render: (v) => <Badge kind={STATUS_BADGE[v.status] ?? "default"}>{v.status.replace(/_/g, " ")}</Badge> },
        { key: "cargo", label: "Load", render: (v) => <span className="tabular-nums text-fg-dim">{v.cargo ?? 0}</span> },
      ]}
    />
  );
}

function CourierTable({ couriers }: { couriers: Courier[] }) {
  return (
    <DataTable<Courier>
      rows={couriers}
      rowKey={(c) => c.id}
      empty="No couriers active"
      columns={[
        { key: "name", label: "Courier", render: (c) => <span className="font-medium text-fg">{c.name}</span> },
        { key: "mode", label: "Mode", render: (c) => <span className="capitalize text-fg-dim">{c.mode}</span> },
        { key: "status", label: "Status", render: (c) => <Badge kind={STATUS_BADGE[c.status] ?? "default"}>{c.status.replace(/_/g, " ")}</Badge> },
        { key: "earnings", label: "Earnings", render: (c) => <span className="tabular-nums text-fg-dim">₹{c.earnings?.toFixed(1) ?? "0.0"}</span> },
      ]}
    />
  );
}