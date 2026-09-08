export type SimMode = "baseline" | "urbanrelay";

export interface Zone {
  id: string;
  name: string;
  code: string;
  center_lat: number;
  center_lng: number;
  radius_km: number;
  base_demand_rate: number;
  road_capacity: number;
  color: string;
}

export interface Hub {
  id: string;
  name: string;
  type: string;
  lat: number;
  lng: number;
  capacity: number;
  occupied: number;
  operating_start: number;
  operating_end: number;
  active: boolean;
  accessibility: number;
  zone_id?: string | null;
  zone_name?: string;
  address?: string;
  owner_name?: string;
  utilization?: number;
  incoming?: number;
  outgoing?: number;
}

export interface Vehicle {
  id: string;
  name: string;
  type: string;
  status: string;
  lat: number;
  lng: number;
  capacity: number;
  cargo?: number;
  progress?: number;
  route?: number[][];
  mode?: string;
}

export interface Courier {
  id: string;
  name: string;
  mode: string;
  status: string;
  lat: number;
  lng: number;
  capacity: number;
  cargo?: number;
  progress?: number;
  earnings?: number;
  target_order_id?: string | null;
  route?: number[][];
}

export interface Order {
  id: string;
  platform: string;
  zone_name?: string;
  customer_name: string;
  address: string;
  status: string;
  mode: string;
  priority: number;
  weight_kg: number;
  volume_units: number;
  lat: number;
  lng: number;
  created_t: number;
  hub_id?: string | null;
  vehicle_id?: string | null;
  courier_id?: string | null;
  distance_km?: number | null;
  duration_min?: number | null;
  emissions_kg?: number | null;
}

export interface Kpis {
  active_deliveries: number;
  vehicles_on_road: number;
  congestion_index: number;
  avg_delivery_time_min: number;
  hub_utilization: number;
  road_occupancy: number;
  distance_saved_km: number;
  co2_saved_kg: number;
  time_saved_min: number;
  efficiency_score: number;
  deliveries: { baseline: number; urbanrelay: number };
  averages: {
    distance_km: { baseline: number; urbanrelay: number };
    duration_min: { baseline: number; urbanrelay: number };
    emissions_kg: { baseline: number; urbanrelay: number };
    dispatches_per_delivery: { baseline: number; urbanrelay: number };
  };
}

export interface BeforeAfterRow {
  metric: string;
  before: number;
  after: number;
  unit: string;
  change_pct: number | null;
}

export interface BeforeAfter {
  rows: BeforeAfterRow[];
  efficiency_score: number;
  note: string;
}

export interface AIDecision {
  id: string;
  agent: string;
  decision: string;
  reasons: { key?: string; label: string; value?: number; weight?: number; contribution?: number }[];
  inputs: Record<string, unknown>;
  score: number;
  impact: Record<string, unknown>;
  created_at: string;
}

export interface AlertItem {
  id: string;
  code: string;
  severity: "INFO" | "WARNING" | "CRITICAL";
  zone_id?: string | null;
  message: string;
  recommendation: string;
  created_at?: string;
  created_t?: number;
}

export interface Wave {
  id: string;
  name: string;
  zone_name?: string;
  hub_id?: string | null;
  hub_name?: string;
  orders: number;
  slots?: number;
  status?: string;
}

export interface CurbZone {
  id: string;
  name: string;
  lat: number;
  lng: number;
  capacity: number;
  zone_name?: string;
  active_reservations?: number;
}

export interface CurbReservation {
  curb_id: string;
  curb_name: string;
  vehicle_id: string;
  starts_at_min: number;
  ends_at_min: number;
  requested_at_min: number;
}

export interface Recommendation {
  id: string;
  type: string;
  zone?: string | null;
  title: string;
  body: string;
  action: string;
  mode: SimMode;
  expected_impact: {
    orders_sampled?: number;
    distance_before_km?: number;
    distance_after_km?: number;
    distance_savings_pct?: number;
    co2_before_kg?: number;
    co2_after_kg?: number;
    co2_savings_pct?: number;
  } | null;
}

export interface City {
  id: string;
  name: string;
  code: string;
  start_hour?: number;
}

export interface TickMessage {
  type: "tick" | "snapshot" | "pong";
  city?: City;
  t?: number;
  speed?: number;
  mode?: SimMode;
  scenario?: string;
  run_id?: string;
  vehicles?: Vehicle[];
  couriers?: Courier[];
  hubs?: { id: string; occupied: number; capacity: number; name?: string; type?: string; lat?: number; lng?: number }[];
  congestion?: { zone_id: string; zone_name: string; index: number }[];
  waves?: Wave[];
  alerts?: AlertItem[];
  kpis?: Kpis;
  orders_in_flight?: number;
  delivered?: number;
  generated?: number;
  zones?: Zone[];
  warehouses?: { id: string; name: string; lat: number; lng: number }[];
  orders?: Order[];
  curb_zones?: CurbZone[];
  curb_reservations?: CurbReservation[];
  before_after?: BeforeAfter;
  last_optimization?: Recommendation["expected_impact"] | null;
  recommendations?: Recommendation[];
  status?: {
    ready: boolean;
    running: boolean;
    t: number;
    speed: number;
    mode: SimMode;
    scenario: string;
    run_id: string | null;
    orders_generated: number;
    delivered: number;
  };
}

export interface DispatchPlan {
  generated_at: number;
  orders_considered: number;
  waves: {
    wave_id: string;
    wave_name: string;
    zone: string;
    hub: string;
    hub_id: string;
    orders: number;
    slots: number;
    bulk_route: number[][];
    bulk_km: number;
    bulk_min: number;
    last_mile: { order_id: string; route: number[][] }[];
  }[];
  bulk_assignments: { wave_id: string; vehicle_id: string; vehicle_type: string; load: number; order_ids: string[] }[];
  courier_assignments: { order_id: string; courier_id: string; courier_mode: string; wave_id: string }[];
  rebalance_actions: string[];
  curb_reservations: CurbReservation[];
  curb_conflicts: number;
  savings: {
    orders_sampled: number;
    distance_before_km: number;
    distance_after_km: number;
    distance_savings_pct: number;
    co2_before_kg: number;
    co2_after_kg: number;
    co2_savings_pct: number;
  } | null;
  message: string;
}