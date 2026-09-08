import { useMemo, useState } from "react";
import { Badge, Card, ProgressBar, Tabs } from "../components/ui";
import { PageHeader } from "../components/layout";
import { useSimStore } from "../stores/sim";
import type { Hub } from "../types";

const TYPE_LABEL: Record<string, string> = {
  kirana: "Kirana Store",
  locker: "Parcel Locker",
  parking: "Parking Hub",
  community: "Community Center",
  pickup: "Pickup Point",
  retail: "Retail Store",
};

export default function Hubs() {
  const hubs = useSimStore((s) => s.hubs);
  const [filter, setFilter] = useState("all");

  const filtered = useMemo(() => {
    if (filter === "all") return hubs;
    return hubs.filter((h) => h.type === filter);
  }, [hubs, filter]);

  const types = ["all", ...Array.from(new Set(hubs.map((h) => h.type)))];

  return (
    <div>
      <PageHeader
        title="Micro-Hub Network"
        sub="Kirana stores, lockers, parking areas and municipal points acting as city logistics infrastructure"
        right={<Tabs tabs={types.map((t) => ({ id: t, label: t === "all" ? "All" : TYPE_LABEL[t] ?? t }))} active={filter} onChange={setFilter} />}
      />
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((h) => (
          <HubCard key={h.id} hub={h} />
        ))}
      </div>
    </div>
  );
}

function HubCard({ hub }: { hub: Hub }) {
  const util = hub.capacity ? hub.occupied / hub.capacity : 0;
  const pct = Math.round(util * 100);
  const open = hub.operating_start !== undefined;
  return (
    <Card className="!p-4 hover:border-accent/40 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-medium text-sm text-fg">{hub.name}</div>
          <div className="text-[11px] text-fg-faint mt-0.5">
            {TYPE_LABEL[hub.type] ?? hub.type} · {hub.zone_name ?? "zone"}
          </div>
        </div>
        <Badge kind={hub.active === false ? "default" : util > 0.85 ? "warning" : "urbanrelay"}>
          {pct}%
        </Badge>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <ProgressBar value={util} color={util > 0.85 ? "#f59e0b" : "#34d399"} className="flex-1" />
        <span className="text-[11px] tabular-nums text-fg-dim">{hub.occupied}/{hub.capacity}</span>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-panel-2/60 py-1.5">
          <div className="text-sm font-semibold text-accent tabular-nums">{hub.incoming ?? 0}</div>
          <div className="text-[9px] text-fg-faint uppercase">Incoming</div>
        </div>
        <div className="rounded-lg bg-panel-2/60 py-1.5">
          <div className="text-sm font-semibold text-violet tabular-nums">{hub.outgoing ?? 0}</div>
          <div className="text-[9px] text-fg-faint uppercase">Outgoing</div>
        </div>
        <div className="rounded-lg bg-panel-2/60 py-1.5">
          <div className="text-sm font-semibold text-fg tabular-nums">{open ? `${hub.operating_start}:00–${hub.operating_end}:00` : "24h"}</div>
          <div className="text-[9px] text-fg-faint uppercase">Hours</div>
        </div>
      </div>
      {hub.address && <div className="mt-2.5 text-[10px] text-fg-faint truncate">{hub.address}</div>}
    </Card>
  );
}