import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSimStore } from "../stores/sim";
import { api } from "../services/api";
import { useToastStore } from "../stores/toasts";

interface Command {
  id: string;
  label: string;
  hint: string;
  icon: string;
  run: () => void;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const nav = useNavigate();
  const push = useToastStore((s) => s.push);
  const { setMode, setScenario } = useSimStore();

  const commands = useMemo<Command[]>(() => {
    const activate = async () => {
      try {
        await api.simActivate("urbanrelay");
        setMode("urbanrelay");
        push({ title: "UrbanRelay AI activated", body: "Orders are being consolidated through micro-hubs.", kind: "success" });
      } catch (e) {
        push({ title: "Activation failed", body: String(e), kind: "error" });
      }
    };
    return [
      { id: "demo", label: "Start SIH demo", hint: "3-minute judged flow", icon: "▶", run: () => nav("/demo") },
      { id: "activate", label: "Activate UrbanRelay AI", hint: "Consolidate through micro-hubs", icon: "✦", run: () => void activate() },
      { id: "sim", label: "Open Simulation control", hint: "Scenarios, speed, timeline", icon: "▶", run: () => nav("/app/simulation") },
      { id: "orders", label: "Open Orders", hint: "Live order stream", icon: "▤", run: () => nav("/app/orders") },
      { id: "hubs", label: "Open Micro-Hubs", hint: "Hub capacity & utilization", icon: "⬢", run: () => nav("/app/hubs") },
      { id: "ai", label: "Open AI Decision Center", hint: "Explainable agent decisions", icon: "✦", run: () => nav("/app/ai") },
      { id: "impact", label: "Open Urban Impact", hint: "Before vs after", icon: "◆", run: () => nav("/app/impact") },
      { id: "analytics", label: "Open Analytics", hint: "Trends and charts", icon: "◔", run: () => nav("/app/analytics") },
      { id: "judge", label: "Open Judge View", hint: "Simplified demo view", icon: "⚖", run: () => nav("/app/judge") },
      { id: "courier", label: "Open Courier App", hint: "Last-mile mobile view", icon: "⚡", run: () => nav("/app/courier") },
      { id: "scenario-festival", label: "Scenario: Festival Sale", hint: "4.2x demand", icon: "🎁", run: () => { void api.simScenario("FESTIVAL_SALE").then(() => setScenario("FESTIVAL_SALE")); nav("/app/simulation"); } },
      { id: "scenario-peak", label: "Scenario: Peak Hour", hint: "2.6x demand", icon: "🕐", run: () => { void api.simScenario("PEAK_HOUR").then(() => setScenario("PEAK_HOUR")); nav("/app/simulation"); } },
      { id: "reset", label: "Reset simulation", hint: "Clear all orders & metrics", icon: "↺", run: () => { void api.simReset(); push({ title: "Simulation reset", kind: "info" }); } },
    ];
  }, [nav, push, setMode, setScenario]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const filtered = commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()));

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[1300] bg-black/60 backdrop-blur-sm flex items-start justify-center pt-[18vh]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setOpen(false)}
        >
          <motion.div
            className="glass rounded-2xl w-[520px] max-w-[92vw] overflow-hidden"
            initial={{ scale: 0.97, y: -10 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.97, y: -10 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 px-4 py-3 border-b border-line">
              <span className="text-accent">⌘</span>
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Type a command…"
                className="flex-1 bg-transparent outline-none text-sm text-fg placeholder:text-fg-faint"
              />
              <kbd className="text-[10px] text-fg-faint border border-line rounded px-1.5 py-0.5">ESC</kbd>
            </div>
            <div className="max-h-[42vh] overflow-y-auto p-2">
              {filtered.length === 0 && <div className="text-center text-xs text-fg-faint py-8">No matching commands</div>}
              {filtered.map((c) => (
                <button
                  key={c.id}
                  onClick={() => { setOpen(false); setQuery(""); c.run(); }}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-panel-2/70 transition-colors text-left"
                >
                  <span className="text-base w-6 text-center text-accent">{c.icon}</span>
                  <span className="flex-1 text-sm text-fg">{c.label}</span>
                  <span className="text-[11px] text-fg-faint">{c.hint}</span>
                </button>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}