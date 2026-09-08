import { create } from "zustand";
import type {
  BeforeAfter,
  Courier,
  CurbReservation,
  CurbZone,
  Hub,
  Kpis,
  Order,
  Recommendation,
  SimMode,
  TickMessage,
  Vehicle,
  Wave,
  Zone,
} from "../types";

interface SimState {
  connected: boolean;
  running: boolean;
  mode: SimMode;
  scenario: string;
  speed: number;
  t: number;
  runId: string | null;
  city: { id: string; name: string; code: string; start_hour?: number } | null;
  zones: Zone[];
  hubs: Hub[];
  vehicles: Vehicle[];
  couriers: Courier[];
  orders: Order[];
  waves: Wave[];
  congestion: { zone_id: string; zone_name: string; index: number }[];
  alerts: TickMessage["alerts"];
  kpis: Kpis | null;
  beforeAfter: BeforeAfter | null;
  curbZones: CurbZone[];
  curbReservations: CurbReservation[];
  recommendations: Recommendation[];
  lastOptimization: Recommendation["expected_impact"] | null;
  generated: number;
  delivered: number;

  applyMessage: (msg: TickMessage) => void;
  setConnected: (v: boolean) => void;
  setMode: (m: SimMode) => void;
  setScenario: (s: string) => void;
  setSpeed: (s: number) => void;
  setRunning: (r: boolean) => void;
  setRecommendations: (r: Recommendation[]) => void;
  setOrders: (o: Order[]) => void;
  setHubs: (h: Hub[]) => void;
  setBeforeAfter: (b: BeforeAfter) => void;
  setLastOptimization: (o: Recommendation["expected_impact"] | null) => void;
  setCity: (c: { id: string; name: string; code: string; start_hour?: number } | null) => void;
}

const EMPTY_KPIS: Kpis = {
  active_deliveries: 0,
  vehicles_on_road: 0,
  congestion_index: 0,
  avg_delivery_time_min: 0,
  hub_utilization: 0,
  road_occupancy: 0,
  distance_saved_km: 0,
  co2_saved_kg: 0,
  time_saved_min: 0,
  efficiency_score: 0,
  deliveries: { baseline: 0, urbanrelay: 0 },
  averages: {
    distance_km: { baseline: 0, urbanrelay: 0 },
    duration_min: { baseline: 0, urbanrelay: 0 },
    emissions_kg: { baseline: 0, urbanrelay: 0 },
    dispatches_per_delivery: { baseline: 0, urbanrelay: 0 },
  },
};

export const useSimStore = create<SimState>((set) => ({
  connected: false,
  running: false,
  mode: "baseline",
  scenario: "NORMAL_DAY",
  speed: 1,
  t: 0,
  runId: null,
  city: null,
  zones: [],
  hubs: [],
  vehicles: [],
  couriers: [],
  orders: [],
  waves: [],
  congestion: [],
  alerts: [],
  kpis: null,
  beforeAfter: null,
  curbZones: [],
  curbReservations: [],
  recommendations: [],
  lastOptimization: null,
  generated: 0,
  delivered: 0,

  applyMessage: (msg) =>
    set((s) => {
      const next: Partial<SimState> = {};
      if (msg.city) next.city = msg.city;
      if (msg.status) {
        next.running = msg.status.running;
        next.mode = msg.status.mode;
        next.scenario = msg.status.scenario;
        next.speed = msg.status.speed;
        next.t = msg.status.t;
        next.runId = msg.status.run_id;
        next.generated = msg.status.orders_generated;
        next.delivered = msg.status.delivered;
      }
      if (msg.t !== undefined) next.t = msg.t;
      if (msg.mode) next.mode = msg.mode;
      if (msg.scenario) next.scenario = msg.scenario;
      if (msg.speed !== undefined) next.speed = msg.speed;
      if (msg.run_id) next.runId = msg.run_id;
      if (msg.vehicles) next.vehicles = msg.vehicles;
      if (msg.couriers) next.couriers = msg.couriers;
      if (msg.hubs && s.hubs.length) {
        const hubMap = new Map(msg.hubs.map((h) => [h.id, h]));
        next.hubs = s.hubs.map((h) => (hubMap.has(h.id) ? { ...h, occupied: hubMap.get(h.id)!.occupied, capacity: hubMap.get(h.id)!.capacity } : h));
      } else if (msg.hubs) {
        next.hubs = msg.hubs.map((h) => ({
          id: h.id, name: "", type: "", lat: 0, lng: 0, capacity: h.capacity, occupied: h.occupied,
          operating_start: 8, operating_end: 22, active: true, accessibility: 0,
        }));
      }
      if (msg.congestion) next.congestion = msg.congestion;
      if (msg.waves) next.waves = msg.waves;
      if (msg.alerts) next.alerts = [...(msg.alerts ?? []), ...(s.alerts ?? [])].slice(0, 40);
      if (msg.kpis) next.kpis = msg.kpis;
      if (msg.orders_in_flight !== undefined) next.t = next.t ?? s.t;
      if (msg.delivered !== undefined) next.delivered = msg.delivered;
      if (msg.generated !== undefined) next.generated = msg.generated;

      if (msg.zones) next.zones = msg.zones;
      if (msg.hubs && msg.zones) {
        next.hubs = msg.hubs as typeof s.hubs;
      }
      if (msg.orders) next.orders = msg.orders;
      if (msg.curb_zones) next.curbZones = msg.curb_zones;
      if (msg.curb_reservations) next.curbReservations = msg.curb_reservations;
      if (msg.before_after) next.beforeAfter = msg.before_after;
      if (msg.last_optimization) next.lastOptimization = msg.last_optimization;
      if (msg.vehicles && msg.vehicles.length && msg.zones) {
        const vehMap = new Map(msg.vehicles.map((v) => [v.id, v]));
        next.vehicles = msg.vehicles.map((v) => ({ ...v, route: vehMap.get(v.id)?.route }));
      }
      return next;
    }),

  setConnected: (v) => set({ connected: v }),
  setMode: (m) => set({ mode: m }),
  setScenario: (s) => set({ scenario: s }),
  setSpeed: (s) => set({ speed: s }),
  setRunning: (r) => set({ running: r }),
  setRecommendations: (r) => set({ recommendations: r }),
  setOrders: (o) => set({ orders: o }),
  setHubs: (h) => set({ hubs: h }),
  setBeforeAfter: (b) => set({ beforeAfter: b }),
  setLastOptimization: (o: Recommendation["expected_impact"] | null) => set({ lastOptimization: o }),
  setCity: (c: { id: string; name: string; code: string; start_hour?: number } | null) =>
    set({ city: c ?? { id: "", name: "", code: "", start_hour: undefined } }),
}));

export { EMPTY_KPIS };
