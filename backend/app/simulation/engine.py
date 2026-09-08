"""Simulation engine.

One tick-based engine drives the whole digital twin:

  tick -> demand -> assignment (baseline or UrbanRelay agents) -> movement ->
          completion -> metrics -> alerts -> WebSocket broadcast

Baseline mode dispatches one vehicle per order (duplicated trips). UrbanRelay
mode consolidates orders into waves, routes bulk vehicles to micro-hubs and
fans out last-mile couriers. Every metric is computed from the actual
simulated routes — nothing is hard-coded.
"""

import asyncio
import logging
import threading
import time

from app.agents.curb_reservation import CurbReservationAgent
from app.agents.delivery_wave import DeliveryWaveAgent
from app.agents.fleet_balancer import FleetBalancerAgent
from app.agents.hub_selection import HubSelectionAgent
from app.algorithms.geo import haversine_km
from app.core.config import get_settings
from app.core.constants import SIMULATION_MODE_BASELINE, SIMULATION_MODE_URBANRELAY
from app.simulation.demand import DemandGenerator
from app.simulation.scenarios import get_scenario
from app.simulation.state import CourierState, OrderState, VehicleState

logger = logging.getLogger(__name__)

SIM_START_HOUR = 17.0  # evening peak makes the digital twin dramatic from second one
ACTIVE_MOVE_STATUS = ("TO_HUB", "TO_CUSTOMER")
WAVE_LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


class SimulationEngine:
    def __init__(self, state, graph, persist, broadcast):
        self.state = state
        self.graph = graph
        self.persist = persist
        self.broadcast = broadcast  # async callable(dict)
        self.settings = get_settings()
        self.demand: DemandGenerator | None = None
        self._congestion_cache: dict[str | None, float] = {}
        self._thread: threading.Thread | None = None
        self._main_loop: asyncio.AbstractEventLoop | None = None
        self._wave_seq = 0
        self._wave_agent = DeliveryWaveAgent()
        self._hub_agent = HubSelectionAgent()
        self._fleet_agent = FleetBalancerAgent()
        self._curb_agent = CurbReservationAgent()

    # ------------------------------------------------------------- lifecycle
    async def start(self, scenario_id: str, seed: int, speed: float, burst: int = 0) -> None:
        s = self.state
        self._reset_runtime(seed, speed)
        s.scenario = get_scenario(scenario_id)
        s.mode = SIMULATION_MODE_BASELINE
        s.next_reopt_t = s.t + 20.0
        self.demand = DemandGenerator(s.rng, s.zones, s.scenario)
        # warm-start burst: instant demand so a short demo opens with the fleet
        # saturated ("the 50 orders just arrived" moment)
        for o in self.demand.burst(burst):
            o["created_t"] = 0.0
            order = OrderState(**o)
            order.warehouse = self._nearest_warehouse(order.customer_lat, order.customer_lng)
            s.orders[order.id] = order
            s.pending_ids.append(order.id)
            s.orders_generated += 1
            self.persist.order_created(s, order)
        s.running = True
        self.persist.run_start(s)
        # run the tick loop on a dedicated thread: ticks contain multi-second
        # synchronous work (Dijkstra bursts), and sharing the event loop starved
        # every API endpoint under load
        self._main_loop = asyncio.get_running_loop()
        self._thread = threading.Thread(target=self._thread_loop, name="urbanrelay-sim", daemon=True)
        self._thread.start()
        logger.info("simulation started scenario=%s seed=%d speed=%.1fx burst=%d", scenario_id, seed, speed, burst)

    def _reset_runtime(self, seed: int, speed: float) -> None:
        s = self.state
        self._wave_seq = 0
        s.run_id = f"run-{int(time.time())}"
        s.t = 0.0
        s.speed = speed
        s.seed = seed
        s.rng.seed(seed)
        s.orders.clear()
        s.waves.clear()
        s.curb_reservations.clear()
        s.pending_ids.clear()
        s.metrics = type(s.metrics)()
        s.orders_generated = 0
        s._alert_last.clear()
        s.alerts_this_tick.clear()
        for v in s.vehicles.values():
            v.status = "IDLE"
            v.cargo.clear()
            v.route = []
            v.cumdist = []
            v.travelled_m = 0.0
            v.mode = SIMULATION_MODE_BASELINE
        for c in s.couriers.values():
            c.status = "AVAILABLE"
            c.cargo.clear()
            c.route = []
            c.cumdist = []
            c.travelled_m = 0.0
            c.target_order_id = None
        for h in s.hubs.values():
            h["occupied"] = 0

    async def stop(self) -> None:
        s = self.state
        s.running = False
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=5.0)
        self._thread = None
        self.persist.run_end(s)
        logger.info("simulation stopped")

    # ------------------------------------------------------------- loop
    def _thread_loop(self) -> None:
        """Tick driver running on a dedicated thread (never the event loop)."""
        try:
            while self.state.running:
                t0 = time.perf_counter()
                self._tick_sync()
                if self._main_loop is not None:
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self.broadcast(self.snapshot_tick()), self._main_loop
                        )
                    except RuntimeError:
                        # event loop shutting down — keep ticking, stop broadcasting
                        self._main_loop = None
                wall_dt = self.settings.sim_tick_seconds / max(self.state.speed, 0.1)
                elapsed = time.perf_counter() - t0
                time.sleep(max(0.01, wall_dt - elapsed))
        except Exception:  # noqa: BLE001
            logger.exception("simulation thread crashed")
            self.state.running = False

    # ------------------------------------------------------------- tick
    async def tick(self) -> None:
        """Compatibility wrapper: one synchronous tick + broadcast."""
        self._tick_sync()
        await self.broadcast(self.snapshot_tick())

    def _tick_sync(self) -> None:
        s = self.state
        dt = self.settings.sim_tick_seconds * s.speed
        s.t += dt
        hour = (SIM_START_HOUR + s.t / 3600.0) % 24.0
        s.alerts_this_tick = []
        self._congestion_cache = {z["id"]: s.zone_load(z["id"]) for z in s.zones}

        # 1. demand
        for o in self.demand.orders_for(dt / 3600.0, hour):
            o["created_t"] = s.t
            order = OrderState(**o)
            order.warehouse = self._nearest_warehouse(order.customer_lat, order.customer_lng)
            s.orders[order.id] = order
            s.pending_ids.append(order.id)
            s.orders_generated += 1
            self.persist.order_created(s, order)

        # 2. assignment
        if s.mode == SIMULATION_MODE_BASELINE:
            self._dispatch_baseline()
        elif s.t >= s.next_reopt_t:
            self._reoptimize(hour)

        # 3. courier legs start once cargo is at the hub
        self._start_courier_legs()

        # 4. movement
        self._move(dt)

        # 5. metrics + history
        self._update_metrics()

        # 6. alerts
        self._check_alerts()

        # mirror buffered events to the DB in one transaction per tick
        self.persist.flush()

    # ------------------------------------------------------------- baseline
    def _dispatch_baseline(self) -> None:
        s = self.state
        # baseline = every operator sending its own light vehicles; trucks stay
        # parked so the consolidation fleet is available when UrbanRelay activates
        idle = [v for v in s.vehicles.values() if v.status == "IDLE" and v.type != "truck"]
        # bound per-tick dispatch work (each dispatch runs Dijkstra searches);
        # the backlog drains over successive ticks instead of a CPU firehose
        dispatched = 0
        for oid in list(s.pending_ids):
            if dispatched >= 6 or not idle:
                break
            order = s.orders.get(oid)
            if order is None or order.status != "PENDING":
                continue
            veh = self._nearest_idle_vehicle(order.warehouse, idle)
            if veh is None:
                continue
            route = self._combined_route(veh, order.warehouse, order.customer_lat, order.customer_lng, veh)
            if not route or len(route) < 2:
                continue
            veh.assign_route(route)
            veh.status = "TO_CUSTOMER"
            veh.mode = SIMULATION_MODE_BASELINE
            veh.cargo = [order.id]
            order.status = "PICKED_UP"
            order.mode = SIMULATION_MODE_BASELINE
            order.vehicle_id = veh.id
            s.metrics.dispatches["baseline"] += 1
            idle.remove(veh)
            dispatched += 1
            self.persist.order_assigned(s, order)

    # ------------------------------------------------------------- urbanrelay
    def _reoptimize(self, hour: float) -> None:
        s = self.state
        pending = [s.orders[i] for i in list(s.pending_ids) if s.orders.get(i) and s.orders[i].status == "PENDING"]
        if not pending:
            s.next_reopt_t = s.t + self.settings.sim_reopt_interval
            return

        order_dicts = [
            {
                "id": o.id,
                "customer_lat": o.customer_lat,
                "customer_lng": o.customer_lng,
                "volume_units": o.volume_units,
                "priority": o.priority,
                "created_t": o.created_t,
                "zone_id": o.zone_id,
            }
            for o in pending
        ]
        # bound wave-building work so the event loop never stalls on a giant backlog
        order_dicts = order_dicts[:250]
        waves, wave_record = self._wave_agent.build_waves(order_dicts, s.zones)
        if not waves:
            s.next_reopt_t = s.t + self.settings.sim_reopt_interval
            return
        # globally-unique wave ids (re-optimizations re-cluster orders)
        for wave in waves:
            self._wave_seq += 1
            wave["id"] = f"W{self._wave_seq}"
            wave["name"] = f"Wave {WAVE_LETTERS[(self._wave_seq - 1) % len(WAVE_LETTERS)]}"
        self.persist.decision(s, wave_record)

        hub_records: list = []
        for wave in waves:
            hub, record = self._hub_agent.select_hub(
                centroid_lat=wave["centroid"][0],
                centroid_lng=wave["centroid"][1],
                required_slots=wave["total_slots"],
                hubs=list(s.hubs.values()),
                zone_load_fn=self._zone_load_cache,
                now_hour=int(hour),
            )
            hub_records.append(record)
            if hub:
                wave["hub"] = hub
                wave["hub_id"] = hub["id"]
        for record in hub_records:
            self.persist.decision(s, record)

        # honest expected-impact estimate computed from real candidate routes
        s.last_optimization = self._estimate_savings([w for w in waves if "hub" in w], hour)

        vehicles_dicts = [
            {"id": v.id, "name": v.name, "type": v.type, "capacity": v.capacity, "lat": v.lat, "lng": v.lng,
             "status": v.status, "active": True, "zone_id": v.zone_id}
            for v in s.vehicles.values()
        ]
        couriers_dicts = [
            {"id": c.id, "name": c.name, "mode": c.mode, "capacity": c.capacity, "lat": c.lat, "lng": c.lng,
             "status": c.status, "active": True, "zone_id": c.zone_id}
            for c in s.couriers.values()
        ]
        plan, fleet_record = self._fleet_agent.allocate(
            waves=[w for w in waves if "hub" in w],
            vehicles=vehicles_dicts,
            couriers=couriers_dicts,
            zone_load_fn=self._zone_load_cache,
        )
        self.persist.decision(s, fleet_record)

        # execute bulk legs warehouse -> hub
        arrivals: list[dict] = []
        for a in plan["bulk_assignments"]:
            veh = s.vehicles.get(a["vehicle_id"])
            wave = next((w for w in waves if w["id"] == a["wave_id"]), None)
            if veh is None or wave is None or "hub" not in wave:
                continue
            hub = wave["hub"]
            wh = self._nearest_warehouse(hub["lat"], hub["lng"])
            route = self._combined_route(veh, wh, hub["lat"], hub["lng"], veh)
            if not route or len(route) < 2:
                continue
            order_ids = [oid for oid in a["order_ids"] if oid in s.orders][:veh.capacity]
            if not order_ids:
                continue
            veh.assign_route(route)
            veh.status = "TO_HUB"
            veh.mode = SIMULATION_MODE_URBANRELAY
            veh.hub_id = hub["id"]
            veh.cargo = order_ids
            for oid in order_ids:
                order = s.orders[oid]
                order.status = "PICKED_UP"
                order.mode = SIMULATION_MODE_URBANRELAY
                order.vehicle_id = veh.id
                order.hub_id = hub["id"]
                order.warehouse = wh
            s.metrics.dispatches["urbanrelay"] += 1
            total_km = sum(
                s.orders[oid].weight_kg for oid in order_ids if oid in s.orders
            )
            arrivals.append(
                {
                    "vehicle_id": veh.id,
                    "lat": hub["lat"],
                    "lng": hub["lng"],
                    "eta_min": s.t / 60.0 + veh.total_m / 1000.0 / max(veh.speed_kph, 5) * 60.0,
                    "unload_min": 5.0 + len(order_ids) * 0.1,
                }
            )
            self.persist.route_created(s, veh, wave, hub, wh, total_km)
            for oid in order_ids:
                self.persist.order_assigned(s, s.orders[oid])

        # execute courier assignments (wait at hub until truck unloads)
        newly_dispatched: set[str] = set()
        for a in plan["courier_assignments"]:
            order = s.orders.get(a["order_id"])
            courier = s.couriers.get(a["courier_id"])
            if order is None or courier is None or order.hub_id is None or order.status != "PICKED_UP":
                continue
            hub = s.hubs.get(order.hub_id)
            if hub is None:
                continue
            first_cargo = not courier.cargo
            courier.cargo.append(order.id)
            courier.status = "WAITING_AT_HUB"
            courier.hub_id = order.hub_id
            courier.zone_id = order.zone_id
            courier.lat, courier.lng = hub["lat"], hub["lng"]
            courier.route, courier.cumdist, courier.travelled_m = [], [], 0.0
            order.courier_id = courier.id
            order.status = "WAVE_ASSIGNED"
            if first_cargo:
                newly_dispatched.add(courier.id)
            self.persist.order_assigned(s, order)
        s.metrics.dispatches["urbanrelay"] += len(newly_dispatched)

        # curb reservations for bulk arrivals
        reservations, conflicts, curb_record = self._curb_agent.plan(
            arrivals=arrivals,
            curb_zones=s.curb_zones,
            now_min=s.t / 60.0,
        )
        s.curb_reservations.extend(reservations)
        self.persist.decision(s, curb_record)
        if conflicts:
            self._add_alert(
                "CURB_CONFLICT", "WARNING", None,
                f"{conflicts} bulk arrival(s) could not be slotted at the requested curb time.",
                "Shift bulk departures or activate an auxiliary loading zone.",
            )

        # persist waves
        for wave in waves:
            self.persist.wave_created(s, wave)

        s.pending_ids = [i for i in s.pending_ids if s.orders.get(i) and s.orders[i].status == "PENDING"]
        s.next_reopt_t = s.t + self.settings.sim_reopt_interval

    # ------------------------------------------------------------- couriers
    def _start_courier_legs(self) -> None:
        s = self.state
        # bound Dijkstra work per tick: legs start over successive ticks instead
        # of one multi-second synchronous storm
        legs_started = 0
        MAX_LEGS_PER_TICK = 10
        for courier in s.couriers.values():
            if legs_started >= MAX_LEGS_PER_TICK:
                break
            if courier.status != "WAITING_AT_HUB" or not courier.cargo:
                continue
            cargo = [s.orders[oid] for oid in courier.cargo if oid in s.orders]
            if not cargo or not all(o.status == "AT_HUB" for o in cargo):
                continue
            order = cargo[0]
            route = self.graph.route(
                courier.lat, courier.lng, order.customer_lat, order.customer_lng,
                vehicle_speed_kph=self._courier_speed(courier.mode),
                vehicle_type=None,
                congestion=self._zone_load_cache,
            )
            if not route.polyline:
                continue
            courier.assign_route(route.polyline)
            courier.target_order_id = order.id
            courier.status = "DELIVERING"
            order.status = "OUT_FOR_DELIVERY"
            legs_started += 1
            self.persist.order_assigned(s, order)

    # ------------------------------------------------------------- movement
    def _move(self, dt: float) -> None:
        s = self.state
        speed_mult = s.scenario.get("speed_multiplier", 1.0)
        for v in s.vehicles.values():
            if v.status not in ACTIVE_MOVE_STATUS:
                continue
            pos = v.position()
            zone = s._zone_of_point(pos)
            load = self._congestion_cache.get(zone, 0.0)
            speed_ms = v.speed_kph / 3.6 * speed_mult / (1.0 + 1.2 * load)
            v.lat, v.lng = pos
            if v.advance(speed_ms * dt):
                if v.status == "TO_CUSTOMER":
                    self._finish_baseline_delivery(v)
                else:
                    self._unload_at_hub(v)
        for c in s.couriers.values():
            if c.status != "DELIVERING":
                continue
            pos = c.position()
            zone = s._zone_of_point(pos)
            load = self._congestion_cache.get(zone, 0.0)
            speed_ms = self._courier_speed(c.mode) / 3.6 * speed_mult / (1.0 + 0.8 * load)
            c.lat, c.lng = pos
            if c.advance(speed_ms * dt):
                self._finish_courier_delivery(c)

    def _finish_baseline_delivery(self, veh: VehicleState) -> None:
        s = self.state
        if not veh.cargo:
            veh.status = "IDLE"
            return
        oid = veh.cargo[0]
        order = s.orders.get(oid)
        if order is None:
            veh.status = "IDLE"
            veh.cargo = []
            return
        distance_km = veh.total_m / 1000.0
        duration_min = (s.t - order.created_t) / 60.0
        self._complete_delivery(order, veh.type, distance_km, duration_min, SIMULATION_MODE_BASELINE)
        veh.status = "IDLE"
        veh.cargo = []
        veh.mode = SIMULATION_MODE_BASELINE

    def _unload_at_hub(self, veh: VehicleState) -> None:
        s = self.state
        hub = s.hubs.get(veh.hub_id or "")
        if hub:
            hub["occupied"] = min(hub["capacity"], hub["occupied"] + len(veh.cargo))
            self.persist.hub_updated(s, hub)
        for oid in veh.cargo:
            order = s.orders.get(oid)
            if order:
                order.status = "AT_HUB"
                self.persist.order_at_hub(s, order)
        veh.status = "IDLE"
        veh.cargo = []
        veh.hub_id = None
        veh.mode = SIMULATION_MODE_URBANRELAY

    def _finish_courier_delivery(self, courier: CourierState) -> None:
        s = self.state
        order = s.orders.get(courier.target_order_id or "")
        if order is None:
            courier.status = "AVAILABLE"
            courier.cargo = []
            return
        distance_km = courier.total_m / 1000.0
        duration_min = (s.t - order.created_t) / 60.0
        self._complete_delivery(order, courier.mode, distance_km, duration_min, SIMULATION_MODE_URBANRELAY)
        courier.earnings += 1.5 + 0.08 * distance_km
        courier.cargo = [oid for oid in courier.cargo if oid != order.id]
        courier.target_order_id = None
        if courier.cargo:
            nxt = s.orders.get(courier.cargo[0])
            if nxt and nxt.status == "AT_HUB":
                route = self.graph.route(
                    courier.lat, courier.lng, nxt.customer_lat, nxt.customer_lng,
                    vehicle_speed_kph=self._courier_speed(courier.mode),
                    vehicle_type=None,
                    congestion=self._zone_load_cache,
                )
                if route.polyline:
                    courier.assign_route(route.polyline)
                    courier.target_order_id = nxt.id
                    nxt.status = "OUT_FOR_DELIVERY"
                    self.persist.order_assigned(s, nxt)
                    return
        courier.status = "AVAILABLE"

    def _complete_delivery(self, order: OrderState, mode_type: str, distance_km: float, duration_min: float, mode: str) -> None:
        s = self.state
        s.metrics.deliveries[mode] += 1
        s.metrics.distance_km[mode] += distance_km
        s.metrics.duration_min[mode] += duration_min
        emissions_kg = self.persist.emission_factor(mode_type) * distance_km / 1000.0
        s.metrics.emissions_kg[mode] += emissions_kg
        order.status = "DELIVERED"
        order.delivered_t = s.t
        order.distance_km = distance_km
        order.duration_min = duration_min
        order.emissions_kg = emissions_kg
        self.persist.order_delivered(s, order)

    # ------------------------------------------------------------- helpers
    def _combined_route(self, veh, wh: dict, to_lat: float, to_lng: float, mover) -> list[list[float]]:
        """Deadhead from current position to the warehouse, then the loaded leg."""
        r1 = self.graph.route(
            veh.lat, veh.lng, wh["lat"], wh["lng"],
            vehicle_speed_kph=mover.speed_kph,
            vehicle_type=mover.type,
            congestion=self._zone_load_cache,
        )
        r2 = self.graph.route(
            wh["lat"], wh["lng"], to_lat, to_lng,
            vehicle_speed_kph=mover.speed_kph,
            vehicle_type=mover.type,
            congestion=self._zone_load_cache,
        )
        poly = r1.polyline + r2.polyline
        return poly

    def _nearest_warehouse(self, lat: float, lng: float) -> dict:
        return min(
            self.state.warehouses,
            key=lambda w: haversine_km(lat, lng, w["lat"], w["lng"]),
        )

    def _nearest_idle_vehicle(self, warehouse: dict, idle: list[VehicleState]) -> VehicleState | None:
        if not idle:
            return None
        return min(idle, key=lambda v: haversine_km(v.lat, v.lng, warehouse["lat"], warehouse["lng"]))

    def _zone_load_cache(self, zone_id: str | None) -> float:
        return self._congestion_cache.get(zone_id, 0.0) if zone_id else 0.0

    def _estimate_savings(self, waves: list[dict], hour: float) -> dict | None:
        """Compute real expected savings by routing a sample of candidate orders
        both ways: direct warehouse->customer (baseline) vs consolidated
        (bulk share + last-mile courier). No fabricated numbers."""
        s = self.state
        sample: list[tuple[dict, dict]] = []  # (order_dict, wave)
        for wave in waves:
            for od in wave["orders"]:
                sample.append((od, wave))
                if len(sample) >= 12:
                    break
            if len(sample) >= 12:
                break
        if not sample:
            return None

        dist_before = dist_after = co2_before = co2_after = 0.0
        for od, wave in sample:
            wh = self._nearest_warehouse(od["customer_lat"], od["customer_lng"])
            hub = wave["hub"]
            # baseline: dedicated light vehicle straight from the warehouse
            rb = self.graph.route(
                wh["lat"], wh["lng"], od["customer_lat"], od["customer_lng"],
                vehicle_speed_kph=24.0, vehicle_type="motorcycle", congestion=self._zone_load_cache,
            )
            dist_before += rb.distance_m
            co2_before += rb.distance_m / 1000.0 * self.persist.emission_factor("motorcycle")
            # urbanrelay: bulk share of the warehouse->hub leg + courier last mile
            rc = self.graph.route(
                hub["lat"], hub["lng"], od["customer_lat"], od["customer_lng"],
                vehicle_speed_kph=24.0, vehicle_type="e-scooter", congestion=self._zone_load_cache,
            )
            bulk_share_m = haversine_km(wh["lat"], wh["lng"], hub["lat"], hub["lng"]) * 1000.0 * (
                od["volume_units"] / max(wave["total_slots"], 1)
            )
            dist_after += bulk_share_m + rc.distance_m
            co2_after += bulk_share_m / 1000.0 * self.persist.emission_factor("truck") + (
                rc.distance_m / 1000.0 * self.persist.emission_factor("e-scooter")
            )

        dist_before_km = dist_before / 1000.0
        dist_after_km = dist_after / 1000.0
        co2_before_kg = co2_before / 1000.0
        co2_after_kg = co2_after / 1000.0
        return {
            "t": round(s.t, 1),
            "orders_sampled": len(sample),
            "distance_before_km": round(dist_before_km, 1),
            "distance_after_km": round(dist_after_km, 1),
            "distance_savings_pct": round((1 - dist_after_km / max(dist_before_km, 1e-9)) * 100, 1),
            "co2_before_kg": round(co2_before_kg, 1),
            "co2_after_kg": round(co2_after_kg, 1),
            "co2_savings_pct": round((1 - co2_after_kg / max(co2_before_kg, 1e-9)) * 100, 1),
            "note": "Computed by routing a sample of pending orders both ways; ESTIMATED.",
        }

    @staticmethod
    def _courier_speed(mode: str) -> float:
        return {"motorcycle": 30.0, "e-scooter": 24.0, "bicycle": 15.0, "walking": 5.0}.get(mode, 20.0)

    # ------------------------------------------------------------- metrics
    def _update_metrics(self) -> None:
        s = self.state
        m = s.metrics
        totals = {
            "deliveries": sum(m.deliveries.values()),
            "distance_km": round(m.distance_km["baseline"] + m.distance_km["urbanrelay"], 2),
            "emissions_kg": round(m.emissions_kg["baseline"] + m.emissions_kg["urbanrelay"], 2),
        }
        s.metrics.history.append(
            {
                "t": round(s.t, 1),
                "mode": s.mode,
                "congestion_index": round(s.congestion_index(), 3),
                "vehicles_on_road": s.vehicles_on_road(),
                "active_deliveries": s.active_order_count(),
                "hub_utilization": round(s.hub_utilization(), 3),
                **totals,
            }
        )
        if len(s.metrics.history) > 4000:
            s.metrics.history = s.metrics.history[-2000:]

    # ------------------------------------------------------------- alerts
    def _check_alerts(self) -> None:
        s = self.state
        for load in s.zone_loads():
            if load["index"] > 0.8:
                self._add_alert(
                    "HIGH_CONGESTION", "WARNING", load["zone_id"],
                    f"Zone {load['zone_name']} congestion index is {load['index']:.0%} — roads are saturated.",
                    "Activate UrbanRelay AI to consolidate deliveries through micro-hubs.",
                    cooldown=120,
                )
        for hub in s.hubs.values():
            if hub.get("active", True) and hub["capacity"] > 0 and hub["occupied"] / hub["capacity"] > 0.85:
                self._add_alert(
                    "HUB_NEAR_CAPACITY", "WARNING", hub.get("zone_id"),
                    f"Micro-hub {hub['name']} is at {hub['occupied'] / hub['capacity']:.0%} capacity.",
                    "Route new waves to a neighbouring hub or increase hub capacity.",
                    cooldown=180,
                )
        if s.t > 60 and self.demand is not None:
            recent = sum(1 for o in s.orders.values() if s.t - o.created_t <= 300)
            expected = sum(z["base_demand_rate"] for z in s.zones) * s.scenario.get("demand_multiplier", 1.0) * (300 / 3600)
            if expected > 0 and recent > expected * 1.9:
                self._add_alert(
                    "DEMAND_SURGE", "WARNING", None,
                    f"Demand surge: {recent} orders in the last 5 minutes vs {expected:.0f} expected.",
                    "Increase re-optimization frequency and activate spare couriers.",
                    cooldown=240,
                )
        for o in s.orders.values():
            if o.status not in ("DELIVERED", "CANCELLED") and s.t - o.created_t > 2700:
                self._add_alert(
                    "DELIVERY_DELAY", "INFO", o.zone_id,
                    f"Order {o.id[:8]} ({o.platform}) exceeds 45 minutes in transit.",
                    "Prioritize this order in the next wave.",
                    cooldown=600,
                )
                break

    def _add_alert(self, code: str, severity: str, zone_id: str | None, message: str, recommendation: str, cooldown: float = 60.0) -> None:
        s = self.state
        key = (code, zone_id)
        last = s._alert_last.get(key)
        if last is not None and s.t - last < cooldown:
            return
        s._alert_last[key] = s.t
        alert = {
            "id": f"al-{int(time.time() * 1000)}-{len(s.alerts_this_tick)}",
            "code": code,
            "severity": severity,
            "zone_id": zone_id,
            "message": message,
            "recommendation": recommendation,
            "created_t": s.t,
        }
        s.alerts_this_tick.append(alert)
        self.persist.alert(s, alert)

    # ------------------------------------------------------------- snapshots
    def snapshot_tick(self) -> dict:
        s = self.state
        return {
            "type": "tick",
            "run_id": s.run_id,
            "t": round(s.t, 1),
            "speed": s.speed,
            "mode": s.mode,
            "scenario": s.scenario.get("id"),
            "vehicles": [
                {
                    "id": v.id, "name": v.name, "type": v.type, "status": v.status,
                    "lat": round(v.position()[0], 6), "lng": round(v.position()[1], 6),
                    "cargo": len(v.cargo), "progress": round(v.progress, 3), "mode": v.mode,
                }
                for v in s.vehicles.values()
            ],
            "couriers": [
                {
                    "id": c.id, "name": c.name, "mode": c.mode, "status": c.status,
                    "lat": round(c.position()[0], 6), "lng": round(c.position()[1], 6),
                    "cargo": len(c.cargo), "progress": round(c.progress, 3),
                }
                for c in s.couriers.values()
            ],
            "hubs": [{"id": h["id"], "occupied": h["occupied"], "capacity": h["capacity"]} for h in s.hubs.values()],
            "congestion": s.zone_loads(),
            "waves": [
                {"id": w["id"], "name": w["name"], "zone_name": w.get("zone_name"), "hub_id": w.get("hub_id"),
                 "orders": len(w["orders"]), "status": "ACTIVE"}
                for w in s.waves
            ],
            "alerts": s.alerts_this_tick,
            "kpis": self._kpis(),
            "orders_in_flight": s.active_order_count(),
            "delivered": sum(s.metrics.deliveries.values()),
            "generated": s.orders_generated,
        }

    def _kpis(self) -> dict:
        s = self.state
        m = s.metrics
        b_del = m.deliveries["baseline"]
        u_del = m.deliveries["urbanrelay"]
        b_avg_dist = m.distance_km["baseline"] / b_del if b_del else 0.0
        u_avg_dist = m.distance_km["urbanrelay"] / u_del if u_del else 0.0
        b_avg_time = m.duration_min["baseline"] / b_del if b_del else 0.0
        u_avg_time = m.duration_min["urbanrelay"] / u_del if u_del else 0.0
        b_avg_co2 = m.emissions_kg["baseline"] / b_del if b_del else 0.0
        u_avg_co2 = m.emissions_kg["urbanrelay"] / u_del if u_del else 0.0

        dist_saved = max(0.0, (b_avg_dist - u_avg_dist) * u_del) if b_del and u_del else 0.0
        time_saved = max(0.0, (b_avg_time - u_avg_time) * u_del) if b_del and u_del else 0.0
        co2_saved = max(0.0, (b_avg_co2 - u_avg_co2) * u_del) if b_del and u_del else 0.0

        def reduction(b, u):
            if b <= 0:
                return 0.0
            return max(0.0, min(1.0, (b - u) / b))

        efficiency = round(
            0.25 * reduction(b_avg_dist, u_avg_dist)
            + 0.25 * reduction(b_avg_time, u_avg_time)
            + 0.20 * reduction(b_avg_co2, u_avg_co2)
            + 0.15 * self._dispatch_reduction()
            + 0.15 * (1.0 - s.congestion_index()),
            3,
        )

        return {
            "active_deliveries": s.active_order_count(),
            "vehicles_on_road": s.vehicles_on_road(),
            "congestion_index": round(s.congestion_index(), 3),
            "avg_delivery_time_min": round(u_avg_time if u_del else (b_avg_time if b_del else 0.0), 1),
            "hub_utilization": round(s.hub_utilization(), 3),
            "road_occupancy": round(min(1.0, s.vehicles_on_road() / max(len(s.vehicles) + len(s.couriers), 1)), 3),
            "distance_saved_km": round(dist_saved, 1),
            "co2_saved_kg": round(co2_saved, 1),
            "time_saved_min": round(time_saved, 1),
            "efficiency_score": efficiency,
            "deliveries": {"baseline": b_del, "urbanrelay": u_del},
            "averages": {
                "distance_km": {"baseline": round(b_avg_dist, 2), "urbanrelay": round(u_avg_dist, 2)},
                "duration_min": {"baseline": round(b_avg_time, 1), "urbanrelay": round(u_avg_time, 1)},
                "emissions_kg": {"baseline": round(b_avg_co2, 3), "urbanrelay": round(u_avg_co2, 3)},
                "dispatches_per_delivery": {
                    "baseline": round(m.dispatches["baseline"] / b_del, 2) if b_del else 0.0,
                    "urbanrelay": round(m.dispatches["urbanrelay"] / u_del, 2) if u_del else 0.0,
                },
            },
        }

    def _dispatch_reduction(self) -> float:
        s = self.state
        m = s.metrics
        b_del = m.deliveries["baseline"]
        u_del = m.deliveries["urbanrelay"]
        b_per = m.dispatches["baseline"] / b_del if b_del else 0.0
        u_per = m.dispatches["urbanrelay"] / u_del if u_del else 0.0
        if b_del == 0 or b_per <= 0:
            return 0.0
        return max(0.0, min(1.0, (b_per - u_per) / b_per))

    def before_after(self) -> dict:
        s = self.state
        m = s.metrics
        b_del, u_del = m.deliveries["baseline"], m.deliveries["urbanrelay"]

        def avg(dist, deliv):
            return round(dist / deliv, 2) if deliv else 0.0

        def pct(b, u):
            """Per-delivery reduction in %, or None while either mode lacks data."""
            if not b_del or not u_del or b is None or u is None or b <= 0:
                return None
            return round((b - u) / b * 100, 1)

        b_dist = avg(m.distance_km["baseline"], b_del)
        u_dist = avg(m.distance_km["urbanrelay"], u_del)
        b_time = avg(m.duration_min["baseline"], b_del)
        u_time = avg(m.duration_min["urbanrelay"], u_del)
        b_co2 = avg(m.emissions_kg["baseline"] * 1000, b_del)
        u_co2 = avg(m.emissions_kg["urbanrelay"] * 1000, u_del)
        b_disp = round(m.dispatches["baseline"] / b_del, 2) if b_del else None
        u_disp = round(m.dispatches["urbanrelay"] / u_del, 2) if u_del else None

        rows = [
            {
                "metric": "Deliveries completed",
                "before": b_del, "after": u_del,
                "unit": "orders",
                "change_pct": None,
            },
            {
                "metric": "Vehicle dispatches per delivery",
                "before": b_disp, "after": u_disp,
                "unit": "vehicles/order",
                "change_pct": pct(b_disp, u_disp),
            },
            {
                "metric": "Average distance per delivery",
                "before": b_dist, "after": u_dist,
                "unit": "km",
                "change_pct": pct(b_dist, u_dist),
            },
            {
                "metric": "Average delivery time",
                "before": b_time, "after": u_time,
                "unit": "min",
                "change_pct": pct(b_time, u_time),
            },
            {
                "metric": "Estimated CO₂ per delivery",
                "before": b_co2, "after": u_co2,
                "unit": "g",
                "change_pct": pct(b_co2, u_co2),
            },
            {
                "metric": "Total distance driven",
                "before": round(m.distance_km["baseline"], 1),
                "after": round(m.distance_km["urbanrelay"], 1),
                "unit": "km",
                "change_pct": None,
            },
        ]
        k = self._kpis()
        return {
            "rows": rows,
            "efficiency_score": k["efficiency_score"],
            "note": "All values computed from the active simulation. CO₂ is an estimate from configured per-mode factors.",
        }