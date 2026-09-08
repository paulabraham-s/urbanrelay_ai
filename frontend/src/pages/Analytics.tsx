import { useEffect, useState } from "react";
import { BeforeAfterChart, CongestionChart, KpiTrendChart, OrdersChart } from "../components/charts";
import { Card, Skeleton } from "../components/ui";
import { PageHeader } from "../components/layout";
import { api } from "../services/api";
import { useSimStore } from "../stores/sim";

interface HistoryPoint {
  t: number;
  congestion_index: number;
  mode: string;
  deliveries: number;
  distance_km: number;
  emissions_kg: number;
}

export default function Analytics() {
  const running = useSimStore((s) => s.running);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [stats, setStats] = useState<{ by_status: Record<string, number>; by_platform: Record<string, number> } | null>(null);
  const beforeAfter = useSimStore((s) => s.beforeAfter);

  useEffect(() => {
    const load = () => {
      api.simHistory(800).then((r) => setHistory(r.history)).catch(() => undefined);
      api.orderStats().then(setStats).catch(() => undefined);
    };
    load();
    const id = setInterval(load, 6000);
    return () => clearInterval(id);
  }, [running]);

  return (
    <div>
      <PageHeader
        title="Analytics"
        sub="All trends computed from the active simulation. Baseline vs UrbanRelay comparisons included."
      />
      {history.length === 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Skeleton className="h-64" /><Skeleton className="h-64" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <CongestionChart data={history} />
          <KpiTrendChart data={history} />
        </div>
      )}
      <div className="mt-4">
        {beforeAfter ? (
          <BeforeAfterChart rows={beforeAfter.rows} />
        ) : (
          <Skeleton className="h-64" />
        )}
      </div>
      {stats && (
        <div className="mt-4">
          <OrdersChart byStatus={stats.by_status} byPlatform={stats.by_platform} />
        </div>
      )}
      {!stats && history.length > 0 && (
        <Card className="mt-4"><div className="text-xs text-fg-faint">Order statistics loading…</div></Card>
      )}
    </div>
  );
}