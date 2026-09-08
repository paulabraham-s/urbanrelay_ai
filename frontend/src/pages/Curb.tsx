import { Badge, Card, DataTable } from "../components/ui";
import { PageHeader } from "../components/layout";
import { useSimStore } from "../stores/sim";
import type { CurbReservation, CurbZone } from "../types";

export default function Curb() {
  const curbZones = useSimStore((s) => s.curbZones);
  const reservations = useSimStore((s) => s.curbReservations);
  const t = useSimStore((s) => s.t);
  const nowMin = t / 60;

  return (
    <div>
      <PageHeader
        title="Curb Management"
        sub="Digitally reserved loading zones — no more double parking at market roads"
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <div className="text-sm font-medium mb-3">Loading zones</div>
          <DataTable<CurbZone>
            rows={curbZones}
            rowKey={(c) => c.id}
            empty="No curb zones"
            columns={[
              { key: "name", label: "Zone", render: (c) => <span className="font-medium text-fg">{c.name}</span> },
              { key: "zone_name", label: "Area", render: (c) => <span className="text-fg-dim">{c.zone_name ?? "—"}</span> },
              { key: "capacity", label: "Slots", render: (c) => <span className="tabular-nums text-fg-dim">{c.capacity}</span> },
              { key: "active", label: "Status", render: (c) => <Badge kind={c.active_reservations && c.active_reservations > 0 ? "warning" : "success"}>{c.active_reservations && c.active_reservations > 0 ? "RESERVED" : "AVAILABLE"}</Badge> },
            ]}
          />
        </Card>
        <Card>
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-medium">Reservation schedule</div>
            <span className="text-[10px] text-fg-faint">sim t = {nowMin.toFixed(0)} min</span>
          </div>
          {reservations.length === 0 ? (
            <div className="text-xs text-fg-faint py-10 text-center">No reservations yet — they appear when bulk vehicles are dispatched.</div>
          ) : (
            <div className="space-y-2 max-h-[420px] overflow-y-auto">
              {reservations.slice(-20).reverse().map((r, i) => {
                const active = r.starts_at_min <= nowMin && nowMin <= r.ends_at_min;
                const upcoming = r.starts_at_min > nowMin;
                return (
                  <ReservationRow key={`${r.curb_id}-${i}`} r={r} active={active} upcoming={upcoming} />
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function ReservationRow({ r, active, upcoming }: { r: CurbReservation; active: boolean; upcoming: boolean }) {
  return (
    <div className={`rounded-xl border px-3.5 py-2.5 flex items-center justify-between ${
      active ? "border-good/40 bg-good/10" : upcoming ? "border-accent/30 bg-accent/10" : "border-line bg-panel-2/50"
    }`}>
      <div>
        <div className="text-xs font-medium text-fg">{r.curb_name}</div>
        <div className="text-[10px] text-fg-faint font-mono mt-0.5">vehicle {r.vehicle_id.slice(0, 10)}</div>
      </div>
      <div className="text-right">
        <div className="text-[11px] tabular-nums text-fg-dim">{r.starts_at_min.toFixed(0)}–{r.ends_at_min.toFixed(0)} min</div>
        <Badge kind={active ? "success" : upcoming ? "info" : "default"}>
          {active ? "IN USE" : upcoming ? "BOOKED" : "COMPLETE"}
        </Badge>
      </div>
    </div>
  );
}