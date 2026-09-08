import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "./ui";

const AXIS = { fill: "#5c7193", fontSize: 11 } as const;
const TOOLTIP_STYLE = {
  background: "#0d1526",
  border: "1px solid #1e2a44",
  borderRadius: 10,
  fontSize: 12,
  color: "#e6edf7",
};

function ChartCard({ title, sub, children }: { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <Card className="!p-4">
      <div className="mb-3">
        <div className="text-sm font-medium text-fg">{title}</div>
        {sub && <div className="text-[11px] text-fg-faint mt-0.5">{sub}</div>}
      </div>
      <div className="h-56">{children}</div>
    </Card>
  );
}

export function CongestionChart({ data }: { data: { t: number; congestion_index: number; mode: string }[] }) {
  return (
    <ChartCard title="Congestion index over time" sub="Zone load averaged across Secunderabad, Kukatpally and Miyapur">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -18 }}>
          <defs>
            <linearGradient id="cong" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.5} />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#16213a" strokeDasharray="3 6" vertical={false} />
          <XAxis dataKey="t" stroke={AXIS.fill} fontSize={AXIS.fontSize} tickFormatter={(v) => `${Math.round(v / 60)}m`} />
          <YAxis stroke={AXIS.fill} fontSize={AXIS.fontSize} domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
          <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(v) => `t+${Math.round(Number(v) / 60)} min`} />
          <Area type="monotone" dataKey="congestion_index" name="Congestion" stroke="#f59e0b" strokeWidth={2} fill="url(#cong)" />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function KpiTrendChart({ data }: { data: { t: number; deliveries: number; distance_km: number; emissions_kg: number }[] }) {
  return (
    <ChartCard title="Cumulative performance" sub="Deliveries completed, distance driven and estimated emissions">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="#16213a" strokeDasharray="3 6" vertical={false} />
          <XAxis dataKey="t" stroke={AXIS.fill} fontSize={AXIS.fontSize} tickFormatter={(v) => `${Math.round(v / 60)}m`} />
          <YAxis stroke={AXIS.fill} fontSize={AXIS.fontSize} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Line type="monotone" dataKey="deliveries" name="Deliveries" stroke="#38bdf8" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="distance_km" name="Distance (km)" stroke="#a78bfa" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="emissions_kg" name="Emissions (kg)" stroke="#fb7185" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function BeforeAfterChart({ rows }: { rows: { metric: string; before: number; after: number; unit: string }[] }) {
  const data = rows.map((r) => ({ name: r.metric.replace(" per delivery", ""), before: r.before, after: r.after }));
  return (
    <ChartCard title="Before vs after — UrbanRelay AI" sub="Averages per delivery, computed from the live simulation">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -14 }} layout="vertical">
          <CartesianGrid stroke="#16213a" strokeDasharray="3 6" horizontal={false} />
          <XAxis type="number" stroke={AXIS.fill} fontSize={AXIS.fontSize} />
          <YAxis type="category" dataKey="name" stroke={AXIS.fill} fontSize={10} width={150} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="before" name="Current system" fill="#f59e0b" radius={[0, 4, 4, 0]} barSize={12} />
          <Bar dataKey="after" name="UrbanRelay AI" fill="#34d399" radius={[0, 4, 4, 0]} barSize={12} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function OrdersChart({ byStatus, byPlatform }: { byStatus: Record<string, number>; byPlatform: Record<string, number> }) {
  const colors = ["#38bdf8", "#f59e0b", "#34d399", "#a78bfa", "#fb7185", "#94a3b8"];
  const statusData = Object.entries(byStatus).map(([name, value]) => ({ name, value }));
  const platformData = Object.entries(byPlatform).map(([name, value]) => ({ name, value }));
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <ChartCard title="Orders by status">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={statusData} margin={{ top: 4, right: 4, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="#16213a" strokeDasharray="3 6" vertical={false} />
            <XAxis dataKey="name" stroke={AXIS.fill} fontSize={10} />
            <YAxis stroke={AXIS.fill} fontSize={AXIS.fontSize} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="value" name="Orders" radius={[6, 6, 0, 0]}>
              {statusData.map((_, i) => (
                <Cell key={i} fill={colors[i % colors.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
      <ChartCard title="Orders by platform (SIMULATED)">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={platformData} margin={{ top: 4, right: 4, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="#16213a" strokeDasharray="3 6" vertical={false} />
            <XAxis dataKey="name" stroke={AXIS.fill} fontSize={10} />
            <YAxis stroke={AXIS.fill} fontSize={AXIS.fontSize} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="value" name="Orders" radius={[6, 6, 0, 0]}>
              {platformData.map((_, i) => (
                <Cell key={i} fill={colors[i % colors.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}