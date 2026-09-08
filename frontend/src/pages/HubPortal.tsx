import { useState } from "react";
import { Badge, Button, Card, Modal, ProgressBar, StatusDot } from "../components/ui";
import { PageHeader } from "../components/layout";
import { useSimStore } from "../stores/sim";

export default function HubPortal() {
  const hubs = useSimStore((s) => s.hubs);
  const orders = useSimStore((s) => s.orders);
  const [qr, setQr] = useState(false);

  const hub = hubs.find((h) => h.type === "kirana") ?? hubs[0];
  if (!hub) {
    return (
      <div>
        <PageHeader title="Kirana Hub Portal" sub="Owner view for micro-hub partners" />
        <Card>No hubs configured.</Card>
      </div>
    );
  }

  const incoming = orders.filter((o) => o.hub_id === hub.id && o.status === "PICKED_UP").length;
  const ready = orders.filter((o) => o.hub_id === hub.id && ["AT_HUB", "OUT_FOR_DELIVERY"].includes(o.status)).length;
  const util = hub.capacity ? hub.occupied / hub.capacity : 0;

  return (
    <div>
      <PageHeader
        title="Kirana Hub Portal"
        sub={`${hub.name} · owner view`}
        right={<Button onClick={() => setQr(true)}>📷 Scan package QR</Button>}
      />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <div className="flex items-start justify-between">
            <div>
              <div className="font-semibold text-lg">{hub.name}</div>
              <div className="text-xs text-fg-faint mt-1">{hub.address ?? "—"} · {hub.zone_name ?? ""}</div>
            </div>
            <Badge kind={hub.active === false ? "default" : "success"}>
              <StatusDot color="#34d399" /> {hub.active === false ? "PAUSED" : "ACCEPTING"}
            </Badge>
          </div>
          <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat label="Storage" value={`${hub.occupied}/${hub.capacity}`} />
            <Stat label="Utilization" value={`${Math.round(util * 100)}%`} />
            <Stat label="Incoming" value={String(incoming)} accent="#f59e0b" />
            <Stat label="Ready to dispatch" value={String(ready)} accent="#34d399" />
          </div>
          <div className="mt-5">
            <div className="text-xs text-fg-faint uppercase tracking-wide mb-2">Capacity</div>
            <ProgressBar value={util} color={util > 0.85 ? "#f59e0b" : "#34d399"} />
          </div>
          <div className="mt-5 flex gap-3">
            <Button variant="outline" size="sm">Accept hub</Button>
            <Button variant="outline" size="sm">Pause hub</Button>
            <Button variant="outline" size="sm">Adjust capacity</Button>
          </div>
        </Card>
        <Card>
          <div className="text-sm font-medium mb-3">Today's parcels</div>
          {orders.filter((o) => o.hub_id === hub.id).slice(-8).reverse().map((o) => (
            <div key={o.id} className="flex items-center justify-between py-2 border-b border-line-soft last:border-0">
              <div className="min-w-0">
                <div className="text-xs text-fg truncate">{o.customer_name}</div>
                <div className="text-[10px] text-fg-faint">{o.platform} · {o.id.slice(0, 6)}</div>
              </div>
              <Badge kind={o.status === "DELIVERED" ? "success" : "warning"}>{o.status.replace(/_/g, " ")}</Badge>
            </div>
          ))}
        </Card>
      </div>

      <Modal open={qr} onClose={() => setQr(false)} title="Scan package QR">
        <div className="flex flex-col items-center gap-4 py-2">
          <div className="w-48 h-48 rounded-xl border-2 border-dashed border-line bg-panel-2 grid place-items-center">
            <div className="text-center">
              <div className="text-5xl mb-2 opacity-60">▦</div>
              <div className="text-[10px] text-fg-faint">QR camera preview (concept)</div>
            </div>
          </div>
          <div className="text-xs text-fg-dim text-center">
            Scan a package to verify pickup or hand-off at <span className="text-fg font-medium">{hub.name}</span>.
          </div>
          <Button variant="outline" onClick={() => setQr(false)}>Close</Button>
        </div>
      </Modal>
    </div>
  );
}

function Stat({ label, value, accent = "#e6edf7" }: { label: string; value: string; accent?: string }) {
  return (
    <div className="rounded-xl bg-panel-2/60 p-3.5">
      <div className="text-xl font-semibold tabular-nums" style={{ color: accent }}>{value}</div>
      <div className="text-[10px] text-fg-faint uppercase tracking-wide mt-0.5">{label}</div>
    </div>
  );
}