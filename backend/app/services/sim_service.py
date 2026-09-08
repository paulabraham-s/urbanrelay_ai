"""Simulation orchestration service.

Owns the SimulationState + engine, loads city topology from the database,
and exposes lifecycle and query methods used by the API layer.
"""

import json
import logging
from pathlib import Path

from app.algorithms.geo import haversine_km
from app.algorithms.graph import get_road_graph
from app.core.config import get_settings
from app.core.constants import SIMULATION_MODE_BASELINE, SIMULATION_MODE_URBANRELAY
from app.core.ws import manager
from app.database.session import SessionLocal
from app.models.entities import Courier, CurbZone, MicroHub, Vehicle
from app.services.persistence import PersistenceService
from app.simulation.engine import SimulationEngine
from app.simulation.scenarios import get_scenario
from app.simulation.state import CourierState, SimulationState, VehicleState

logger = logging.getLogger(__name__)


class SimulationService:
    def __init__(self) -> None:
        self.state = SimulationState()
        self.persist = PersistenceService()
        self.engine: SimulationEngine | None = None
        self.graph = None
        self.ready = False
        self.city_id: str | None = None
        self.city_code: str | None = None
        self._cached_city_name: str = ""
        self._cached_city_start_hour: int | None = None

    # ------------------------------------------------------------- setup
    def init(self) -> None:
        self.persist.load_factors()
        db = SessionLocal()
        try:
            self._load_topology(db)
            # Ensure service-level city_id mirrors the state (set by _load_topology).
            if not self.city_id and self.state.city_id:
                self.city_id = self.state.city_id
        finally:
            db.close()
        self.graph = self._graph_for_active_city()
        self.engine = SimulationEngine(self.state, self.graph, self.persist, manager.broadcast)
        self.ready = True
        logger.info("simulation service ready (city=%s): %d zones, %d hubs, %d vehicles, %d couriers",
                    self.city_code, len(self.state.zones), len(self.state.hubs),
                    len(self.state.vehicles), len(self.state.couriers))

    def _geojson_for_city(self, code: str | None) -> str:
        """Resolve the bundled road network file for a city code."""
        settings = get_settings()
        cities_file = Path(settings.seed_dir) / "cities.json"
        try:
            cities = json.loads(cities_file.read_text(encoding="utf-8"))["cities"]
            for c in cities:
                if c["code"] == code:
                    name = c.get("geojson")
                    if name:
                        candidate = Path(settings.geojson_dir) / name
                        if candidate.exists():
                            return str(candidate)
        except Exception:  # noqa: BLE001
            logger.exception("could not resolve city geojson, falling back")
        return settings.geojson_path

    def _graph_for_active_city(self):
        path = self._geojson_for_city(self.city_code)
        graph = get_road_graph(path, self.state.zones)
        logger.info("road graph for city=%s loaded from %s", self.city_code, path)
        return graph

    async def switch_city(self, city_id: str) -> dict:
        """Switch the active city: stop the sim, reload topology + road graph."""
        if self.state.running and self.engine:
            await self.engine.stop()
        db = SessionLocal()
        try:
            from app.models.entities import City

            city = db.get(City, city_id)
            if city is None:
                raise ValueError(f"unknown city: {city_id}")
            db.query(City).update({"active": False})
            city.active = True
            db.commit()
        finally:
            db.close()

        s = self.state
        s.running = False
        s.t = 0.0
        s.orders.clear()
        s.pending_ids.clear()
        s.waves.clear()
        s.curb_reservations.clear()
        s.hubs.clear()
        s.vehicles.clear()
        s.couriers.clear()
        s.curb_zones.clear()
        s.zones = []
        s.metrics = type(s.metrics)()

        db = SessionLocal()
        try:
            self._load_topology(db)
            self.city_id = db.query(City).filter_by(active=True).first().id
            self.city_code = db.query(City).filter_by(active=True).first().code
        finally:
            db.close()
        self.graph = self._graph_for_active_city()
        if self.engine is not None:
            self.engine.graph = self.graph
        return self.status()

    def _load_topology(self, db) -> None:
        s = self.state
        from app.models.entities import City, Zone

        city = db.query(City).filter_by(active=True).first()
        if city:
            s.city_id = city.id
            self.city_code = city.code
            self._cached_city_name = city.name
            self._cached_city_start_hour = city.start_hour
            zones = db.query(Zone).filter_by(city_id=city.id).all()
            s.zones = [
                {
                    "id": z.id, "name": z.name, "code": z.code,
                    "center_lat": z.center_lat, "center_lng": z.center_lng,
                    "radius_km": z.radius_km, "base_demand_rate": z.base_demand_rate,
                    "road_capacity": z.road_capacity, "color": z.color,
                }
                for z in zones
            ]
        city_id = s.city_id
        for hub in db.query(MicroHub).filter_by(city_id=city_id).all():
            s.hubs[hub.id] = {
                "id": hub.id, "name": hub.name, "type": hub.type,
                "lat": hub.lat, "lng": hub.lng,
                "capacity": hub.capacity, "occupied": hub.occupied,
                "operating_start": hub.operating_start, "operating_end": hub.operating_end,
                "active": hub.active, "accessibility": hub.accessibility,
                "zone_id": hub.zone_id, "address": hub.address, "owner_name": hub.owner_name,
            }
        for v in db.query(Vehicle).filter_by(active=True, city_id=city_id).all():
            s.vehicles[v.id] = VehicleState(
                id=v.id, name=v.name, type=v.type, capacity=v.capacity,
                speed_kph=v.speed_kph, lat=v.lat, lng=v.lng, zone_id=v.zone_id,
            )
        for c in db.query(Courier).filter_by(active=True, city_id=city_id).all():
            s.couriers[c.id] = CourierState(
                id=c.id, name=c.name, mode=c.mode, capacity=c.capacity,
                lat=c.lat, lng=c.lng, zone_id=c.zone_id,
            )
        for curb in db.query(CurbZone).filter_by(city_id=city_id).all():
            s.curb_zones.append(
                {
                    "id": curb.id, "name": curb.name, "lat": curb.lat, "lng": curb.lng,
                    "capacity": curb.capacity, "operating_start": curb.operating_start,
                    "operating_end": curb.operating_end, "zone_id": curb.zone_id,
                }
            )
        warehouses_path = Path(get_settings().seed_dir) / "warehouses.json"
        if warehouses_path.exists():
            all_wh = json.loads(warehouses_path.read_text(encoding="utf-8"))
            s.warehouses = [w for w in all_wh if w.get("city") == (self.city_code or "hyderabad")]
        else:
            s.warehouses = []

    # ------------------------------------------------------------- lifecycle
    async def start(self, scenario_id: str, seed: int, speed: float, burst: int = 0) -> dict:
        if not self.ready or self.engine is None:
            raise RuntimeError("Simulation not initialized")
        if self.state.running:
            await self.engine.stop()
        await self.engine.start(scenario_id, seed, max(0.1, min(speed, 20.0)), burst=max(0, int(burst)))
        return self.status()

    async def stop(self) -> dict:
        if self.state.running and self.engine:
            await self.engine.stop()
        return self.status()

    def reset(self) -> dict:
        self.state.running = False
        self.state.t = 0.0
        self.state.metrics = type(self.state.metrics)()
        self.state.orders.clear()
        self.state.pending_ids.clear()
        self.state.waves.clear()
        self.state.curb_reservations.clear()
        self.state.orders_generated = 0
        return self.status()

    def set_scenario(self, scenario_id: str) -> dict:
        self.state.scenario = get_scenario(scenario_id)
        return self.status()

    def set_speed(self, speed: float) -> dict:
        self.state.speed = max(0.1, min(speed, 20.0))
        return self.status()

    def set_mode(self, mode: str) -> dict:
        if mode not in (SIMULATION_MODE_BASELINE, SIMULATION_MODE_URBANRELAY):
            raise ValueError(f"unknown mode: {mode}")
        self.state.mode = mode
        if mode == SIMULATION_MODE_URBANRELAY:
            self.state.next_reopt_t = self.state.t + 3.0
        return self.status()

    def set_scenario_and_mode(self, scenario_id: str, mode: str | None) -> dict:
        self.set_scenario(scenario_id)
        if mode:
            self.set_mode(mode)
        return self.status()

    # ------------------------------------------------------------- queries
    def status(self) -> dict:
        s = self.state
        return {
            "ready": self.ready,
            "running": s.running,
            "t": round(s.t, 1),
            "speed": s.speed,
            "mode": s.mode,
            "scenario": s.scenario.get("id", "NORMAL_DAY"),
            "run_id": s.run_id,
            "orders_generated": s.orders_generated,
            "delivered": sum(s.metrics.deliveries.values()),
        }

    def kpis(self) -> dict:
        if self.engine is None:
            return {}
        return self.engine._kpis()

    def before_after(self) -> dict:
        if self.engine is None:
            return {"rows": [], "efficiency_score": 0.0, "note": ""}
        return self.engine.before_after()

    def history(self, limit: int = 600) -> list[dict]:
        return self.state.metrics.history[-limit:]

    def last_optimization(self) -> dict | None:
        return getattr(self.state, "last_optimization", None)

    def snapshot(self) -> dict:
        s = self.state
        snap: dict = {
            "status": self.status(),
            "zones": s.zones,
            "warehouses": s.warehouses,
            "hubs": list(s.hubs.values()),
            "curb_zones": s.curb_zones,
            "curb_reservations": s.curb_reservations[-60:],
            "vehicles": [
                {
                    "id": v.id, "name": v.name, "type": v.type, "status": v.status,
                    "lat": round(v.position()[0], 6), "lng": round(v.position()[1], 6),
                    "capacity": v.capacity, "cargo": len(v.cargo), "progress": round(v.progress, 3),
                    "mode": v.mode, "hub_id": v.hub_id, "route": v.route,
                }
                for v in s.vehicles.values()
            ],
            "couriers": [
                {
                    "id": c.id, "name": c.name, "mode": c.mode, "status": c.status,
                    "lat": round(c.position()[0], 6), "lng": round(c.position()[1], 6),
                    "capacity": c.capacity, "cargo": len(c.cargo), "progress": round(c.progress, 3),
                    "target_order_id": c.target_order_id, "route": c.route,
                }
                for c in s.couriers.values()
            ],
            "orders": [
                {
                    "id": o.id, "platform": o.platform, "zone_name": o.zone_name,
                    "lat": o.customer_lat, "lng": o.customer_lng,
                    "status": o.status, "mode": o.mode, "priority": o.priority,
                    "created_t": round(o.created_t, 1),
                    "hub_id": o.hub_id, "vehicle_id": o.vehicle_id, "courier_id": o.courier_id,
                    "customer_name": o.customer_name, "address": o.address,
                }
                for o in s.orders.values()
            ],
            "waves": s.waves,
            "alerts": s.alerts_this_tick,
            "kpis": self.kpis(),
            "before_after": self.before_after(),
            "last_optimization": self.last_optimization(),
                "city": {
                "id": s.city_id,
                "name": self._cached_city_name,
                "code": self.city_code or "",
                "start_hour": self._cached_city_start_hour,
            },
        }
        return snap

    # ------------------------------------------------------------- AI ops panel
    def recommendations(self) -> list[dict]:
        s = self.state
        k = self.kpis()
        out: list[dict] = []
        pending = [o for o in s.orders.values() if o.status == "PENDING"]
        loads = s.zone_loads()
        worst = max(loads, key=lambda z: z["index"]) if loads else None

        if worst and worst["index"] > 0.45:
            out.append(
                {
                    "id": "rec-congestion",
                    "type": "CONGESTION",
                    "zone": worst["zone_name"],
                    "title": f"{len(pending)} deliveries converging on {worst['zone_name']}",
                    "body": f"Zone {worst['zone_name']} congestion index is {worst['index']:.0%}. "
                    f"{k['vehicles_on_road']} vehicles are on the road right now.",
                    "action": "ACTIVATE URBANRELAY AI" if s.mode == SIMULATION_MODE_BASELINE else "RE-OPTIMIZE DISPATCH",
                    "mode": s.mode,
                    "expected_impact": self.last_optimization(),
                }
            )
        elif pending:
            out.append(
                {
                    "id": "rec-wave",
                    "type": "CONSOLIDATION",
                    "zone": pending[0].zone_name,
                    "title": f"{len(pending)} orders waiting for dispatch",
                    "body": "Consolidating these orders into delivery waves through micro-hubs "
                    "reduces vehicle duplication and curb conflicts.",
                    "action": "ACTIVATE URBANRELAY AI" if s.mode == SIMULATION_MODE_BASELINE else "RE-OPTIMIZE DISPATCH",
                    "mode": s.mode,
                    "expected_impact": self.last_optimization(),
                }
            )
        for hub in s.hubs.values():
            if hub.get("active", True) and hub["capacity"] > 0 and hub["occupied"] / hub["capacity"] > 0.8:
                out.append(
                    {
                        "id": f"rec-hub-{hub['id'][:8]}",
                        "type": "HUB_CAPACITY",
                        "zone": hub.get("zone_id"),
                        "title": f"Hub {hub['name']} nearing capacity",
                        "body": f"{hub['occupied']}/{hub['capacity']} slots used. Route new waves to a neighbouring hub.",
                        "action": "VIEW HUBS",
                        "mode": s.mode,
                        "expected_impact": None,
                    }
                )
        return out[:4]

    def ai_decisions(self, limit: int = 40) -> list[dict]:
        from sqlalchemy import select

        from app.models.entities import AIDecision

        db = SessionLocal()
        try:
            rows = db.execute(select(AIDecision).order_by(AIDecision.created_at.desc()).limit(limit)).scalars().all()
            return [
                {
                    "id": r.id, "agent": r.agent, "decision": r.decision,
                    "reasons": r.reasons, "inputs": r.inputs,
                    "score": r.score, "impact": r.impact, "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
        finally:
            db.close()

    def hub_nearest(self, lat: float, lng: float, n: int = 5) -> list[dict]:
        hubs = sorted(self.state.hubs.values(), key=lambda h: haversine_km(lat, lng, h["lat"], h["lng"]))
        return hubs[:n]

    # ------------------------------------------------------------- dispatch planning
    def plan_dispatch(self, order_ids: list[str] | None = None, preview_waves: int = 2, preview_orders: int = 3) -> dict:
        """Run the full agent pipeline over pending orders and return an executable
        plan with preview routes and real expected savings. Does not execute.
        Used by /api/orders/optimize and the Chrome dispatcher extension.
        """
        from app.agents.curb_reservation import CurbReservationAgent
        from app.agents.delivery_wave import DeliveryWaveAgent
        from app.agents.fleet_balancer import FleetBalancerAgent
        from app.agents.hub_selection import HubSelectionAgent
        from app.algorithms.geo import haversine_km as hkm

        s = self.state
        if order_ids:
            pending = [s.orders[i] for i in order_ids if i in s.orders and s.orders[i].status == "PENDING"]
        else:
            pending = [o for o in s.orders.values() if o.status == "PENDING"]
        if not pending or self.engine is None:
            return {"waves": [], "message": "No pending orders to optimize", "generated_at": s.t}

        order_dicts = [
            {
                "id": o.id, "customer_lat": o.customer_lat, "customer_lng": o.customer_lng,
                "volume_units": o.volume_units, "priority": o.priority, "created_t": o.created_t,
                "zone_id": o.zone_id,
            }
            for o in pending
        ]
        waves, wave_record = DeliveryWaveAgent().build_waves(order_dicts, s.zones)
        hour = int((7 + s.t / 3600.0) % 24.0)
        for wave in waves:
            hub, record = HubSelectionAgent().select_hub(
                centroid_lat=wave["centroid"][0], centroid_lng=wave["centroid"][1],
                required_slots=wave["total_slots"], hubs=list(s.hubs.values()),
                zone_load_fn=s.zone_load, now_hour=hour,
            )
            if hub:
                wave["hub"] = hub
                wave["hub_id"] = hub["id"]
                wave["hub_name"] = hub["name"]
                wave["hub_score"] = record.score
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
        plan, fleet_record = FleetBalancerAgent().allocate(
            waves=[w for w in waves if "hub" in w], vehicles=vehicles_dicts,
            couriers=couriers_dicts, zone_load_fn=s.zone_load,
        )

        # preview routes (bulk legs + a sample of last-mile legs)
        previews: list[dict] = []
        arrivals: list[dict] = []
        for wave in waves[:preview_waves]:
            if "hub" not in wave:
                continue
            hub = wave["hub"]
            wh = self.engine._nearest_warehouse(hub["lat"], hub["lng"])
            bulk = self.graph.route(
                wh["lat"], wh["lng"], hub["lat"], hub["lng"],
                vehicle_speed_kph=28.0, vehicle_type="truck", congestion=s.zone_load,
            )
            previews.append(
                {
                    "wave_id": wave["id"], "wave_name": wave["name"],
                    "zone": wave.get("zone_name"), "hub": hub["name"], "hub_id": hub["id"],
                    "orders": len(wave["orders"]), "slots": wave["total_slots"],
                    "bulk_route": bulk.polyline[:600],
                    "bulk_km": round(bulk.distance_m / 1000.0, 2),
                    "bulk_min": round(bulk.duration_min, 1),
                    "last_mile": [
                        {
                            "order_id": o["id"],
                            "route": self.graph.route(
                                hub["lat"], hub["lng"], o["customer_lat"], o["customer_lng"],
                                vehicle_speed_kph=24.0, vehicle_type="e-scooter", congestion=s.zone_load,
                            ).polyline[:300],
                        }
                        for o in wave["orders"][:preview_orders]
                    ],
                }
            )
            arrivals.append(
                {
                    "vehicle_id": "preview", "lat": hub["lat"], "lng": hub["lng"],
                    "eta_min": s.t / 60.0 + bulk.duration_min,
                    "unload_min": 5.0 + len(wave["orders"]) * 0.1,
                }
            )

        reservations, conflicts, curb_record = CurbReservationAgent().plan(
            arrivals=arrivals, curb_zones=s.curb_zones, now_min=s.t / 60.0,
        )
        savings = self.engine._estimate_savings([w for w in waves if "hub" in w], hour)

        return {
            "generated_at": round(s.t, 1),
            "orders_considered": len(pending),
            "waves": previews,
            "bulk_assignments": plan["bulk_assignments"],
            "courier_assignments": plan["courier_assignments"],
            "rebalance_actions": plan["rebalance_actions"],
            "curb_reservations": reservations,
            "curb_conflicts": conflicts,
            "savings": savings,
            "decisions": [wave_record, fleet_record, curb_record],
            "message": "Plan preview — activate UrbanRelay AI to execute it in the simulation.",
        }
