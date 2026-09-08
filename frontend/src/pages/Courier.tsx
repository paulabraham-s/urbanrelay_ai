import { useState } from "react";
import { Badge, Button, Card, ProgressBar, StatusDot } from "../components/ui";
import { PageHeader } from "../components/layout";
import { useSimStore } from "../stores/sim";

const STEPS = ["START SHIFT", "SCAN PACKAGE", "PICKED UP", "START DELIVERY", "DELIVERED"];

export default function Courier() {
  const couriers = useSimStore((s) => s.couriers);
  const orders = useSimStore((s) => s.orders);
  const [selectedId, setSelectedId] = useState(couriers[0]?.id ?? "");
  const [step, setStep] = useState(0);
  const [qr, setQr] = useState(false);

  const courier = couriers.find((c) => c.id === selectedId) ?? couriers[0];
  if (!courier) {
    return (
      <div>
        <PageHeader title="Courier App" sub="Last-mile mobile experience" />
        <Card>No couriers configured.</Card>
      </div>
    );
  }

  const activeOrder = orders.find((o) => o.id === courier.target_order_id) ?? orders.find((o) => o.courier_id === courier.id && o.status !== "DELIVERED");
  const isActive = courier.status !== "AVAILABLE";

  return (
    <div className="max-w-md mx-auto">
      <PageHeader title="Courier App" sub="Responsive mobile-first web (wrap-ready for Flutter)" back />
      <Card>
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-full bg-gradient-to-br from-accent to-violet flex items-center justify-center text-lg">⚡</div>
          <div className="flex-1">
            <div className="font-semibold text-sm">{courier.name}</div>
            <div className="text-[11px] text-fg-dim capitalize">{courier.mode} courier · last-mile partner</div>
          </div>
          <Badge kind={isActive ? "urbanrelay" : "success"}>
            <StatusDot color={isActive ? "#34d399" : "#94a3b8"} pulse={isActive} /> {isActive ? "ON SHIFT" : "OFFLINE"}
          </Badge>
        </div>

        <div className="mt-4 flex items-center gap-2">
          <span className="text-xs text-fg-faint">Select courier</span>
          <select
            value={courier.id}
            onChange={(e) => setSelectedId(e.target.value)}
            className="flex-1 bg-panel-2 border border-line rounded-lg px-2 py-1.5 text-xs text-fg"
          >
            {couriers.map((c) => (
              <option key={c.id} value={c.id}>{c.name} ({c.mode})</option>
            ))}
          </select>
        </div>

        {activeOrder ? (
          <div className="mt-5 rounded-xl border border-line bg-panel-2/50 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-fg">Current delivery</span>
              <Badge kind="warning">{activeOrder.status.replace(/_/g, " ")}</Badge>
            </div>
            <div className="mt-3 text-sm font-medium">{activeOrder.customer_name}</div>
            <div className="text-xs text-fg-dim mt-0.5">{activeOrder.address}</div>
            <div className="mt-2 text-[11px] text-fg-faint">
              {activeOrder.platform} · {activeOrder.volume_units} slot(s) · priority {activeOrder.priority}
            </div>
            <div className="mt-3">
              <ProgressBar value={courier.progress ?? 0} color="#38bdf8" />
              <div className="text-[10px] text-fg-faint mt-1 tabular-nums">{Math.round((courier.progress ?? 0) * 100)}% of route</div>
            </div>
          </div>
        ) : (
          <div className="mt-5 rounded-xl border border-dashed border-line p-6 text-center text-xs text-fg-faint">
            No active delivery. You'll be assigned parcels from the nearest micro-hub when UrbanRelay AI runs.
          </div>
        )}

        {/* workflow */}
        <div className="mt-5">
          <div className="text-[10px] text-fg-faint uppercase tracking-wider mb-2">Delivery workflow</div>
          <div className="flex flex-wrap gap-1.5">
            {STEPS.map((s, i) => (
              <button
                key={s}
                onClick={() => setStep(i)}
                className={`px-2.5 py-1.5 rounded-lg text-[10px] font-medium border transition-colors ${
                  i === step ? "border-accent/50 bg-accent/15 text-accent" : i < step ? "border-good/30 bg-good/10 text-good" : "border-line bg-panel-2 text-fg-faint"
                }`}
              >
                {i < step ? "✓ " : ""}{s}
              </button>
            ))}
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <Button size="sm" variant="outline" onClick={() => setQr(true)}>Scan package</Button>
            <Button size="sm" variant="primary" disabled={!isActive}>Start delivery</Button>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-3 gap-2 text-center">
          <div className="rounded-lg bg-panel-2/60 py-2.5">
            <div className="text-sm font-semibold text-good tabular-nums">₹{courier.earnings?.toFixed(1) ?? "0"}</div>
            <div className="text-[9px] text-fg-faint uppercase">Earnings</div>
          </div>
          <div className="rounded-lg bg-panel-2/60 py-2.5">
            <div className="text-sm font-semibold text-fg tabular-nums">{courier.cargo ?? 0}</div>
            <div className="text-[9px] text-fg-faint uppercase">Parcels</div>
          </div>
          <div className="rounded-lg bg-panel-2/60 py-2.5">
            <div className="text-sm font-semibold text-accent tabular-nums">{Math.round((courier.progress ?? 0) * 100)}%</div>
            <div className="text-[9px] text-fg-faint uppercase">Route</div>
          </div>
        </div>
      </Card>

      {qr && (
        <div className="fixed inset-0 z-[1200] bg-black/70 backdrop-blur-sm flex items-center justify-center" onClick={() => setQr(false)}>
          <Card className="w-72 text-center">
            <div className="text-6xl mb-3 opacity-70">▦</div>
            <div className="text-xs text-fg-dim mb-3">Scan the parcel QR at the hub or customer door</div>
            <Button size="sm" variant="outline" onClick={() => setQr(false)}>Close</Button>
          </Card>
        </div>
      )}
    </div>
  );
}