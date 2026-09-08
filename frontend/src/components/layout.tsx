import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useSimStore } from "../stores/sim";
import { useAuthStore } from "../stores/auth";
import { api } from "../services/api";
import { Badge, StatusDot } from "./ui";
import { useToastStore } from "../stores/toasts";

const NAV = [
  { to: "/app", label: "Command Center", icon: "◎", end: true },
  { to: "/app/live", label: "Live Operations", icon: "⬡" },
  { to: "/app/orders", label: "Orders", icon: "▤" },
  { to: "/app/hubs", label: "Micro-Hubs", icon: "⬢" },
  { to: "/app/fleet", label: "Fleet", icon: "◈" },
  { to: "/app/curb", label: "Curb Management", icon: "▭" },
  { to: "/app/ai", label: "AI Decisions", icon: "✦" },
  { to: "/app/analytics", label: "Analytics", icon: "◔" },
  { to: "/app/simulation", label: "Simulation", icon: "▶" },
  { to: "/app/impact", label: "Urban Impact", icon: "◆" },
];

const SCENARIO_NAMES: Record<string, string> = {
  NORMAL_DAY: "Normal Day",
  PEAK_HOUR: "Peak Hour",
  FESTIVAL_SALE: "Festival Sale",
  WEEKEND_RUSH: "Weekend Rush",
  RAIN_SURGE: "Rain Surge",
  FLASH_SALE: "Flash Sale",
  EMERGENCY: "Emergency",
};

export function AppShell({ children }: { children?: React.ReactNode }) {
  const nav = useNavigate();
  const mode = useSimStore((s) => s.mode);
  const scenario = useSimStore((s) => s.scenario);
  const connected = useSimStore((s) => s.connected);
  const running = useSimStore((s) => s.running);
  const t = useSimStore((s) => s.t);
  const fullName = useAuthStore((s) => s.fullName);
  const logout = useAuthStore((s) => s.logout);
  const push = useToastStore((s) => s.push);

  const [cities, setCities] = useState<Array<{ id: string; name: string; code: string; active?: boolean }>>([]);
  const [city, setCity] = useState<{ id: string; name: string; code: string; start_hour?: number } | null>(null);

  useEffect(() => {
    api.cities().then((all) => {
      setCities(all);
      const active = all.find((c) => c.active);
      if (active) {
        const next = { id: active.id, name: active.name, code: active.code };
        setCity(next);
        // mirror into the simulation store so pages that read from the store
        // (LiveOps, CommandCenter, etc.) show the right city even before the
        // WebSocket snapshot arrives.
        useSimStore.getState().setCity(next);
      }
    }).catch(() => undefined);
  }, []);

  const cityStartHours = city ? (city.start_hour ?? 7) : 7;
  const simTime = new Date(cityStartHours * 3600 * 1000 + t * 1000).toISOString().slice(11, 16);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* sidebar */}
      <aside className="w-56 shrink-0 flex flex-col border-r border-line bg-panel/60 backdrop-blur">
        <div className="px-4 py-4 border-b border-line">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-panel-2 border border-line flex items-center justify-center text-accent font-bold glow-cyan">U</div>
            <div>
              <div className="text-sm font-semibold tracking-tight">UrbanRelay <span className="text-accent">AI</span></div>
              <div className="text-[10px] text-fg-faint">Collaborative Smart Logistics Grid</div>
            </div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] transition-colors ${
                  isActive ? "bg-panel-2 text-accent font-medium border border-line" : "text-fg-dim hover:text-fg hover:bg-panel-2/60"
                }`
              }
            >
              <span className="text-base w-5 text-center">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-line space-y-2">
          <NavLink to="/app/courier" className="flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] text-fg-dim hover:text-fg hover:bg-panel-2/60 transition-colors">
            <span className="text-base w-5 text-center">⚡</span> Courier App
          </NavLink>
          <NavLink to="/app/hub-portal" className="flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] text-fg-dim hover:text-fg hover:bg-panel-2/60 transition-colors">
            <span className="text-base w-5 text-center">🏪</span> Kirana Hub Portal
          </NavLink>
          <div className="flex items-center gap-2 px-3 py-1.5">
            <StatusDot color={connected ? "#34d399" : "#fb7185"} pulse={connected} />
            <span className="text-[11px] text-fg-faint">{connected ? "LIVE · simulated data" : "reconnecting…"}</span>
          </div>
        </div>
      </aside>

      {/* main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 shrink-0 flex items-center gap-4 px-5 border-b border-line bg-panel/40 backdrop-blur">
          <div className="flex items-center gap-2 text-[13px] text-fg-dim">
            <span className="text-fg-faint">City</span>
            <select
              value={city?.id ?? ""}
              onChange={async (e) => {
                const id = e.target.value;
                const next = cities.find((c) => c.id === id);
                if (!next || !city || city.id === id) return;
                setCity(next);
                try {
                  await api.activateCity(id);
                  useSimStore.getState().setMode("baseline");
                  useSimStore.getState().setScenario("NORMAL_DAY");
                  useSimStore.getState().setRunning(false);
                } catch {
                  setCity(city);
                  push({ title: "City switch failed", kind: "error" });
                }
              }}
              className="bg-panel-2 border border-line rounded-lg px-2 py-1 text-xs text-fg"
            >
              {cities.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <Badge kind={mode}>{mode === "urbanrelay" ? "URBANRELAY AI ACTIVE" : "CURRENT SYSTEM (BASELINE)"}</Badge>
          <Badge kind="default">{SCENARIO_NAMES[scenario] ?? scenario}</Badge>
          <div className="ml-auto flex items-center gap-3">
            <span className="text-[11px] text-fg-faint font-mono">T+{simTime}</span>
            <span className={`text-[11px] px-2 py-0.5 rounded-md border ${running ? "text-good border-good/25 bg-good/10" : "text-fg-faint border-line bg-panel-2"}`}>
              {running ? "SIMULATION RUNNING" : "SIMULATION IDLE"}
            </span>
            <button
              onClick={() => nav("/demo")}
              className="text-[11px] px-3 py-1.5 rounded-lg bg-accent/10 text-accent border border-accent/25 font-semibold hover:bg-accent/20 transition-colors"
            >
              ▶ SIH DEMO MODE
            </button>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-accent to-violet flex items-center justify-center text-[11px] font-bold text-ink">
                {(fullName ?? "U").slice(0, 1).toUpperCase()}
              </div>
              <div className="hidden lg:block">
                <div className="text-xs text-fg">{fullName ?? "Operator"}</div>
                <button onClick={() => { logout(); push({ title: "Signed out", kind: "info" }); nav("/"); }} className="text-[10px] text-fg-faint hover:text-danger">
                  Sign out
                </button>
              </div>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-5">{children ?? <Outlet />}</main>
      </div>
    </div>
  );
}

export function PageHeader({ title, sub, right, back }: { title: string; sub?: string; right?: React.ReactNode; back?: boolean }) {
  const nav = useNavigate();
  return (
    <div className="flex items-start justify-between gap-4 mb-5">
      <div className="flex items-center gap-3">
        {back && (
          <button onClick={() => nav(-1)} className="text-fg-faint hover:text-fg text-lg leading-none">←</button>
        )}
        <div>
          <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          {sub && <p className="text-xs text-fg-faint mt-0.5">{sub}</p>}
        </div>
      </div>
      {right}
    </div>
  );
}