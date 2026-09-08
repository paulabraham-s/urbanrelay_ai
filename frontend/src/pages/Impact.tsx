import { Badge, Card, ProgressBar } from "../components/ui";
import { PageHeader } from "../components/layout";
import { useSimStore } from "../stores/sim";

export default function Impact() {
  const ba = useSimStore((s) => s.beforeAfter);
  const k = useSimStore((s) => s.kpis);

  return (
    <div>
      <PageHeader
        title="Urban Impact"
        sub="Before vs after — every value computed from the active simulation"
      />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <div className="text-sm font-medium mb-4">Before UrbanRelay → After UrbanRelay</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-[11px] uppercase tracking-wider text-fg-faint">
                  <th className="text-left px-3 py-2.5 font-medium">Metric</th>
                  <th className="text-right px-3 py-2.5 font-medium text-warn">Current system</th>
                  <th className="text-right px-3 py-2.5 font-medium text-good">UrbanRelay AI</th>
                  <th className="text-right px-3 py-2.5 font-medium">Change</th>
                </tr>
              </thead>
              <tbody>
                {(ba?.rows ?? []).map((r) => {
                  const change = r.change_pct;
                  const better = change === null || change === undefined || change <= 0;
                  return (
                    <tr key={r.metric} className="border-b border-line-soft">
                      <td className="px-3 py-3 text-fg">{r.metric}</td>
                      <td className="px-3 py-3 text-right tabular-nums text-warn">{r.before} <span className="text-[10px] text-fg-faint">{r.unit}</span></td>
                      <td className="px-3 py-3 text-right tabular-nums text-good">{r.after} <span className="text-[10px] text-fg-faint">{r.unit}</span></td>
                      <td className="px-3 py-3 text-right tabular-nums">
                        {change === null || change === undefined ? (
                          <span className="text-fg-faint">—</span>
                        ) : (
                          <span className={better ? "text-good" : "text-danger"}>
                            {change > 0 ? "+" : ""}{change.toFixed(1)}%
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="mt-3 text-[10px] text-fg-faint">{ba?.note}</div>
        </Card>

        <div className="space-y-4">
          <Card>
            <div className="flex items-center justify-between text-xs mb-2">
              <span className="text-fg-faint">UrbanRelay Simulation Score</span>
              <span className="font-bold text-accent text-base">{Math.round((k?.efficiency_score ?? 0) * 100)}%</span>
            </div>
            <ProgressBar value={k?.efficiency_score ?? 0} color="#38bdf8" />
            <div className="mt-3 space-y-2 text-[11px]">
              {[
                ["Congestion improvement", 0.15],
                ["Distance reduction", 0.25],
                ["Time improvement", 0.25],
                ["Emission reduction", 0.20],
                ["Dispatch reduction", 0.15],
              ].map(([label, w]) => (
                <div key={label as string} className="flex items-center justify-between text-fg-dim">
                  <span>{label}</span>
                  <span className="font-mono text-fg-faint">w={w as number}</span>
                </div>
              ))}
            </div>
          </Card>
          <Card>
            <div className="text-sm font-medium mb-3">Who benefits</div>
            {[
              ["Municipal Corporations", "Congestion, curb conflicts and emissions data for city planning"],
              ["Logistics Companies", "Consolidated loads, fewer vehicles, faster delivery"],
              ["Kirana Stores", "New revenue as micro-hubs + footfall"],
              ["Couriers", "Stable earnings from city-scale last mile"],
              ["Citizens", "Less blocked roads, cleaner air, faster parcels"],
            ].map(([t, d]) => (
              <div key={t} className="py-2 border-b border-line-soft last:border-0">
                <div className="text-xs font-medium text-fg">{t}</div>
                <div className="text-[11px] text-fg-faint mt-0.5">{d}</div>
              </div>
            ))}
          </Card>
        </div>
      </div>
      <div className="mt-4">
        <Badge kind="warning">UrbanRelay is a city logistics orchestration layer — not a delivery company.</Badge>
      </div>
    </div>
  );
}