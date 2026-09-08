import type {
  AIDecision,
  AlertItem,
  BeforeAfter,
  Courier,
  CurbReservation,
  CurbZone,
  DispatchPlan,
  Hub,
  Kpis,
  Order,
  Recommendation,
  SimMode,
  Vehicle,
  Zone,
} from "../types";

const BASE = import.meta.env.VITE_API_URL ?? "";

let authToken: string | null = localStorage.getItem("ur_token");

export function setToken(token: string | null) {
  authToken = token;
  if (token) localStorage.setItem("ur_token", token);
  else localStorage.removeItem("ur_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* keep statusText */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // auth
  loginDemo: () => request<{ access_token: string; role: string; username: string; full_name: string }>("/api/auth/login", { method: "POST", body: JSON.stringify({ demo: true }) }),

  // cities / zones
  cities: () => request<{ id: string; name: string; code: string }[]>("/api/cities"),
  activateCity: (cityId: string) => request<{ ready: boolean; running: boolean; t: number }>(`/api/cities/${cityId}/activate`, { method: "POST" }),
  zones: (cityId: string) => request<Zone[]>(`/api/cities/${cityId}/zones`),

  // simulation
  simStart: (scenarioId: string, seed: number, speed: number, burst = 0) =>
    request("/api/simulation/start", { method: "POST", body: JSON.stringify({ scenario_id: scenarioId, seed, speed, burst }) }),
  simStop: () => request("/api/simulation/stop", { method: "POST" }),
  simReset: () => request("/api/simulation/reset", { method: "POST" }),
  simScenario: (scenarioId: string, mode?: SimMode) =>
    request("/api/simulation/scenario", { method: "POST", body: JSON.stringify({ scenario_id: scenarioId, mode }) }),
  simSpeed: (speed: number) => request("/api/simulation/speed", { method: "POST", body: JSON.stringify({ speed }) }),
  simActivate: (mode: SimMode) => request("/api/simulation/activate", { method: "POST", body: JSON.stringify({ mode }) }),
  simState: () => request("/api/simulation/state"),
  simKpis: () => request<Kpis>("/api/simulation/kpis"),
  simBeforeAfter: () => request<BeforeAfter>("/api/simulation/before-after"),
  simHistory: (limit = 800) => request<{ history: { t: number; congestion_index: number; vehicles_on_road: number; active_deliveries: number; deliveries: number; distance_km: number; emissions_kg: number; hub_utilization: number; mode: SimMode }[] }>(`/api/simulation/history?limit=${limit}`),
  simRecommendations: () => request<{ recommendations: Recommendation[] }>("/api/simulation/recommendations"),
  scenarios: () => request<{ scenarios: { id: string; name: string; description: string; color: string; icon: string }[] }>("/api/simulation/scenarios"),

  // entities
  orders: (params = "") => request<Order[]>(`/api/orders${params}`),
  hubs: () => request<Hub[]>("/api/hubs"),
  vehicles: () => request<Vehicle[]>("/api/vehicles"),
  couriers: () => request<Courier[]>("/api/couriers"),
  curbZones: () => request<CurbZone[]>("/api/curb-zones"),
  curbReservations: () => request<{ now_min: number; reservations: CurbReservation[] }>("/api/curb-reservations"),
  decisions: () => request<AIDecision[]>("/api/agents/decisions"),
  alerts: (unresolved = false) => request<AlertItem[]>(`/api/alerts?unresolved=${unresolved}`),

  // analytics
  impact: () => request<BeforeAfter>("/api/analytics/impact"),
  orderStats: () => request<{ by_status: Record<string, number>; by_platform: Record<string, number>; by_mode: Record<string, number> }>("/api/analytics/orders"),

  // dispatch (extension + demo)
  optimizeDispatch: (orderIds?: string[]) =>
    request<DispatchPlan>("/api/dispatch/optimize", { method: "POST", body: JSON.stringify({ order_ids: orderIds ?? null }) }),

  // routing
  route: (from: [number, number], to: [number, number], vehicleType = "van") =>
    request<{ distance_km: number; duration_min: number; polyline: number[][] }>("/api/routes/optimize", {
      method: "POST",
      body: JSON.stringify({ from_lat: from[0], from_lng: from[1], to_lat: to[0], to_lng: to[1], vehicle_type: vehicleType }),
    }),
};