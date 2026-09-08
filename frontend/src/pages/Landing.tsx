import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { Button, Badge } from "../components/ui";
import { useAuthStore } from "../stores/auth";
import { useState } from "react";
import { Spinner } from "../components/ui";

export default function Landing() {
  const nav = useNavigate();
  const login = useAuthStore((s) => s.login);
  const [loading, setLoading] = useState(false);

  const enter = async () => {
    setLoading(true);
    try {
      await login();
      nav("/app");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ink grid-bg">
      <div className="max-w-5xl mx-auto px-6 pt-16 pb-24">
        {/* hero */}
        <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg bg-panel-2 border border-line flex items-center justify-center text-accent font-bold glow-cyan">U</div>
              <span className="font-semibold tracking-tight">UrbanRelay <span className="text-accent">AI</span></span>
            </div>
            <Button variant="ghost" onClick={() => nav("/app")} disabled={loading}>
              {loading ? <Spinner size={14} /> : "Launch Command Center →"}
            </Button>
          </div>

          <div className="mt-20 text-center">
            <Badge kind="info">AI CITY LOGISTICS ORCHESTRATION PLATFORM</Badge>
            <h1 className="mt-6 text-4xl md:text-6xl font-bold tracking-tight leading-[1.1]">
              The city shouldn't need more vehicles.
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-good">It needs smarter coordination.</span>
            </h1>
            <p className="mt-6 text-base md:text-lg text-fg-dim max-w-2xl mx-auto">
              UrbanRelay AI orchestrates urban deliveries across micro-hubs, fleets and curb space to reduce congestion,
              delivery inefficiency and emissions — for the whole city, not one company.
            </p>
            <div className="mt-8 flex items-center justify-center gap-3">
              <Button size="lg" onClick={enter} disabled={loading}>
                {loading ? <Spinner size={16} /> : "Enter as Demo Operator"}
              </Button>
              <Button size="lg" variant="outline" onClick={() => nav("/demo")}>▶ Watch the 3-minute Demo</Button>
            </div>
          </div>
        </motion.div>

        {/* how it works */}
        <div className="mt-28 grid md:grid-cols-3 gap-5">
          {[
            { n: "01", t: "Predict", d: "Real OSM road networks + simulated demand streams. AI clusters orders into delivery waves the moment they appear." },
            { n: "02", t: "Orchestrate", d: "Hub Selection, Fleet Balancing and Curb Reservation agents route bulk vehicles to the nearest Kirana micro-hubs." },
            { n: "03", t: "Deliver", d: "Eco-friendly couriers complete the last mile. The city dashboard shows congestion, emissions and distance saved — live." },
          ].map((s, i) => (
            <motion.div
              key={s.n}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="glass rounded-2xl p-6"
            >
              <div className="text-2xl font-bold text-accent/60">{s.n}</div>
              <div className="mt-2 font-semibold text-lg">{s.t}</div>
              <p className="mt-2 text-sm text-fg-dim leading-relaxed">{s.d}</p>
            </motion.div>
          ))}
        </div>

        {/* modules */}
        <div className="mt-24">
          <h2 className="text-2xl font-semibold text-center">One platform, five operational surfaces</h2>
          <div className="mt-8 grid md:grid-cols-3 gap-4">
            {[
              ["◎", "City Command Center", "Municipal dashboards, congestion heatmaps, live KPIs"],
              ["✦", "Explainable AI Agents", "Every decision shows its reasons, score and expected impact"],
              ["⬢", "Micro-Hub Network", "Kirana stores, lockers and parking areas become city logistics infrastructure"],
              ["⚡", "Courier & Hub Portals", "QR pickup, earnings and capacity for last-mile partners"],
              ["▭", "Digital Curb Management", "Loading zones reserved by the minute — no more double parking"],
              ["📦", "Dispatcher Extension", "Optimize dispatch straight from a Chrome extension"],
            ].map(([icon, t, d]) => (
              <div key={t} className="glass rounded-xl p-5 flex gap-4 items-start">
                <span className="text-xl text-accent">{icon}</span>
                <div>
                  <div className="font-medium text-sm">{t}</div>
                  <div className="text-xs text-fg-dim mt-1">{d}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* data transparency */}
        <div className="mt-24 glass rounded-2xl p-6 flex flex-col md:flex-row gap-6 items-center justify-between">
          <div>
            <h3 className="font-semibold text-lg">Every number is computed. Nothing is faked.</h3>
            <p className="text-sm text-fg-dim mt-2 max-w-xl">
              Real OpenStreetMap roads for Secunderabad, Kukatpally and Miyapur. Deterministic demand simulation.
              Before/after impact generated from the actual simulated routes. CO₂ shown as a clearly-labeled estimate.
            </p>
          </div>
          <div className="flex gap-2">
            <Badge kind="info">REAL DATA</Badge>
            <Badge kind="warning">SIMULATED</Badge>
            <Badge kind="success">ESTIMATED</Badge>
          </div>
        </div>
      </div>
    </div>
  );
}