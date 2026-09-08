import { useEffect, useState } from "react";
import { CityMap } from "../components/CityMap";
import { CongestionChart } from "../components/charts";
import { Button, Card, StatusDot } from "../components/ui";
import { PageHeader } from "../components/layout";
import { api } from "../services/api";
import { useToastStore } from "../stores/toasts";
import { useSimStore } from "../stores/sim";
import type { SimMode } from "../types";

interface Scenario {
  id: string;
  name: string;
  description: string;
  color: string;
  icon: string;
}

export default function Simulation() {
  const { running, mode, scenario, speed, t, zones, hubs, vehicles, couriers, curbZones, congestion, setMode, setScenario, setSpeed, setRunning } = useSimStore();
  const push = useToastStore((s) => s.push);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<{ t: number; congestion_index: number; mode: string }[]>([]);

  useEffect(() => {
    api.scenarios().then((r) => setScenarios(r.scenarios)).catch(() => undefined);
  }, []);

  useEffect(() => {
    api.simHistory(300).then((r) => setHistory(r.history)).catch(() => undefined);
  }, [running, mode]);

  const start = async (scenarioId: string) => {
    setBusy(true);
    try {
      await api.simStart(scenarioId, 42, 1);
      setScenario(scenarioId);
      setRunning(true);
      setMode("baseline");
      push({ title: "Simulation started", body: `${scenarioId} scenario · baseline mode`, kind: "success" });
    } catch (e) {
      push({ title: "Failed to start", body: String(e), kind: "error" });
    } finally {
      setBusy(false);
    }
  };

  const stop = async () => {
    try {
      await api.simStop();
      setRunning(false);
      push({ title: "Simulation stopped", kind: "info" });
    } catch (e) {
      push({ title: String(e), kind: "error" });
    }
  };

  const activate = async (m: SimMode) => {
    try {
      await api.simActivate(m);
      setMode(m);
      push({ title: m === "urbanrelay" ? "UrbanRelay AI activated" : "Reverted to baseline", kind: m === "urbanrelay" ? "success" : "info" });
    } catch (e) {
      push({ title: String(e), kind: "error" });
    }
  };

  const changeSpeed = async (s: number) => {
    await api.simSpeed(s).catch(() => undefined);
    setSpeed(s);
  };

  const changeScenario = async (id: string) => {
    await api.simScenario(id).catch(() => undefined);
    setScenario(id);
    push({ title: `Scenario: ${id.replace(/_/g, " ")}`, kind: "info" });
  };

  return (
    <div>
      <PageHeader
        title="Simulation"
        sub="Digital twin control — scenarios, speed and AI activation"
        right={
          <div className="flex items-center gap-2">
            {!running ? (
              <Button onClick={() => start("FESTIVAL_SALE")} disabled={busy}>{busy ? "Starting…" : "▶ Start simulation"}</Button>
            ) : (
              <Button variant="outline" onClick={stop}>■ Stop</Button>
            )}
          </div>
        }
      />

      {/* scenario cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3 mb-4">
        {scenarios.map((s) => (
          <button
            key={s.id}
            onClick={() => (running ? changeScenario(s.id) : start(s.id))}
            className={`rounded-xl border p-3 text-left transition-all ${
              scenario === s.id ? "border-accent/60 bg-accent/10 glow-cyan" : "border-line bg-panel/70 hover:border-line hover:bg-panel-2"
            }`}
            title={s.description}
          >
            <div className="text-xl" style={{ color: s.color }}>{iconFor(s.icon)}</div>
            <div className="text-[11px] font-medium text-fg mt-1.5 leading-tight">{s.name}</div>
            <div className="text-[9px] text-fg-faint mt-1">{s.description}</div>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 rounded-2xl overflow-hidden border border-line min-h-[420px] relative">
          <CityMap zones={zones} hubs={hubs} vehicles={vehicles} couriers={couriers} curbZones={curbZones} congestion={congestion} height="420px" />
          <div className="absolute top-3 left-3 z-[600] glass rounded-xl px-3 py-2 text-[11px]">
            <StatusDot color={running ? "#34d399" : "#fb7185"} pulse={running} /> {running ? "RUNNING" : "IDLE"} · T+{t.toFixed(0)}s
          </div>
        </div>

        <Card>
          <div className="text-sm font-medium mb-3">Controls</div>
          <div className="space-y-4">
            <div>
              <div className="text-[11px] text-fg-faint uppercase tracking-wide mb-2">Simulation mode</div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => running && activate("baseline")}
                  className={`rounded-xl border px-3 py-3 text-left transition-all ${mode === "baseline" ? "border-warn/60 bg-warn/10" : "border-line bg-panel-2 hover:border-line"}`}
                >
                  <div className="text-xs font-semibold text-warn">CURRENT SYSTEM</div>
                  <div className="text-[10px] text-fg-faint mt-1">one vehicle per order — duplicated trips</div>
                </button>
                <button
                  onClick={() => running && activate("urbanrelay")}
                  className={`rounded-xl border px-3 py-3 text-left transition-all ${mode === "urbanrelay" ? "border-good/60 bg-good/10 glow-green" : "border-line bg-panel-2 hover:border-line"}`}
                >
                  <div className="text-xs font-semibold text-good">URBANRELAY AI</div>
                  <div className="text-[10px] text-fg-faint mt-1">consolidated waves via micro-hubs</div>
                </button>
              </div>
            </div>
            <div>
              <div className="text-[11px] text-fg-faint uppercase tracking-wide mb-2">Speed</div>
              <div className="flex gap-1.5">
                {[0.5, 1, 2, 5, 10].map((s) => (
                  <button
                    key={s}
                    onClick={() => changeSpeed(s)}
                    className={`px-3 py-1.5 rounded-lg text-xs border transition-colors ${speed === s ? "border-accent/60 bg-accent/15 text-accent font-medium" : "border-line bg-panel-2 text-fg-dim hover:text-fg"}`}
                  >
                    {s}×
                  </button>
                ))}
              </div>
            </div>
            <div className="rounded-xl bg-panel-2/60 p-3 text-[11px] text-fg-dim leading-relaxed">
              The digital twin runs on real OpenStreetMap roads for Secunderabad, Kukatpally and Miyapur.
              Deterministic with seed <span className="font-mono text-fg">42</span> — same demo every time.
            </div>
          </div>
        </Card>
      </div>

      <div className="mt-4">
        {history.length > 1 && <CongestionChart data={history} />}
      </div>
    </div>
  );
}

function iconFor(icon: string): string {
  return { sun: "☀", clock: "🕐", gift: "🎁", calendar: "📅", "cloud-rain": "🌧", zap: "⚡", siren: "🚨" }[icon] ?? "•";
}