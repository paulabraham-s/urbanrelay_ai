import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef } from "react";
import type { Courier, CurbZone, Hub, Vehicle, Zone } from "../types";

const ROAD_STYLE: Record<string, { color: string; width: number }> = {
  motorway: { color: "#7d93b8", width: 3.2 },
  trunk: { color: "#5f7aa8", width: 2.6 },
  primary: { color: "#4d6491", width: 2.1 },
  secondary: { color: "#3d5178", width: 1.7 },
  tertiary: { color: "#334566", width: 1.3 },
  unclassified: { color: "#2b3a5c", width: 1.0 },
  residential: { color: "#253352", width: 0.8 },
  living_street: { color: "#202d4a", width: 0.7 },
  default: { color: "#2b3a5c", width: 1.0 },
};

const VEHICLE_COLORS: Record<string, string> = {
  truck: "#f59e0b",
  van: "#38bdf8",
  motorcycle: "#a78bfa",
  "e-scooter": "#34d399",
  bicycle: "#f472b6",
  walking: "#94a3b8",
};

const HUB_COLORS: Record<string, string> = {
  kirana: "#f59e0b",
  locker: "#38bdf8",
  parking: "#a78bfa",
  community: "#34d399",
  pickup: "#f472b6",
  retail: "#e2e8f0",
};

/* ------------------------------------------------------------------ */
/* Canvas layer that draws the OSM road network                          */
/* ------------------------------------------------------------------ */
class RoadCanvasLayer extends L.Layer {
  _canvas: HTMLCanvasElement | null = null;
  _features: { a: [number, number]; b: [number, number]; color: string; width: number }[] = [];
  _raf = 0;

  constructor(features: { a: [number, number]; b: [number, number]; color: string; width: number }[]) {
    super();
    this._features = features;
  }

  onAdd(map: L.Map): this {
    const canvas = document.createElement("canvas");
    canvas.style.position = "absolute";
    canvas.style.pointerEvents = "none";
    canvas.style.zIndex = "400";
    const pane = map.getPane("overlayPane")!;
    pane.appendChild(canvas);
    this._canvas = canvas;
    this._resize();
    this._scheduleDraw();
    map.on("move zoom zoomend resize", this._scheduleDraw, this);
    return this;
  }

  onRemove(map: L.Map): this {
    if (this._canvas) this._canvas.remove();
    this._canvas = null;
    map.off("move zoom zoomend resize", this._scheduleDraw, this);
    cancelAnimationFrame(this._raf);
    return this;
  }

  _resize() {
    if (!this._canvas || !this._map) return;
    const size = this._map.getSize();
    const dpr = window.devicePixelRatio || 1;
    this._canvas.width = size.x * dpr;
    this._canvas.height = size.y * dpr;
    this._canvas.style.width = `${size.x}px`;
    this._canvas.style.height = `${size.y}px`;
  }

  _scheduleDraw = () => {
    cancelAnimationFrame(this._raf);
    this._raf = requestAnimationFrame(() => this._draw());
  };

  _draw() {
    const canvas = this._canvas;
    const map = this._map;
    if (!canvas || !map) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const size = map.getSize();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size.x, size.y);

    const b = map.getBounds().pad(0.05);
    const feats = this._features;
    for (let i = 0; i < feats.length; i++) {
      const f = feats[i];
      if (f.a[0] < b.getSouth() || f.a[0] > b.getNorth() || f.a[1] < b.getWest() || f.a[1] > b.getEast()) continue;
      if (f.b[0] < b.getSouth() || f.b[0] > b.getNorth() || f.b[1] < b.getWest() || f.b[1] > b.getEast()) continue;
      const p1 = map.latLngToContainerPoint([f.a[0], f.a[1]]);
      const p2 = map.latLngToContainerPoint([f.b[0], f.b[1]]);
      ctx.strokeStyle = f.color;
      ctx.lineWidth = f.width;
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();
    }
  }
}

/* ------------------------------------------------------------------ */
/* Canvas layer that draws live vehicles / couriers with interpolation  */
/* ------------------------------------------------------------------ */
interface DrawableUnit {
  id: string;
  type: string;
  status: string;
  lat: number;
  lng: number;
  targetLat: number;
  targetLng: number;
  kind: "vehicle" | "courier";
}

class UnitCanvasLayer extends L.Layer {
  _canvas: HTMLCanvasElement | null = null;
  _units = new Map<string, DrawableUnit>();
  _raf = 0;

  onAdd(map: L.Map): this {
    const canvas = document.createElement("canvas");
    canvas.style.position = "absolute";
    canvas.style.pointerEvents = "none";
    canvas.style.zIndex = "500";
    const pane = map.getPane("overlayPane")!;
    pane.appendChild(canvas);
    this._canvas = canvas;
    this._resize();
    map.on("resize", this._resize, this);
    this._loop();
    return this;
  }

  onRemove(map: L.Map): this {
    if (this._canvas) this._canvas.remove();
    this._canvas = null;
    cancelAnimationFrame(this._raf);
    map.off("resize", this._resize, this);
    return this;
  }

  _resize = () => {
    if (!this._canvas || !this._map) return;
    const size = this._map.getSize();
    const dpr = window.devicePixelRatio || 1;
    this._canvas.width = size.x * dpr;
    this._canvas.height = size.y * dpr;
    this._canvas.style.width = `${size.x}px`;
    this._canvas.style.height = `${size.y}px`;
  };

  setUnits(vehicles: Vehicle[], couriers: Courier[]) {
    const seen = new Set<string>();
    for (const v of vehicles) {
      seen.add(v.id);
      const cur = this._units.get(v.id);
      if (!cur) {
        this._units.set(v.id, { id: v.id, type: v.type, status: v.status, lat: v.lat, lng: v.lng, targetLat: v.lat, targetLng: v.lng, kind: "vehicle" });
      } else {
        cur.targetLat = v.lat;
        cur.targetLng = v.lng;
        cur.status = v.status;
      }
    }
    for (const c of couriers) {
      seen.add(c.id);
      const cur = this._units.get(c.id);
      if (!cur) {
        this._units.set(c.id, { id: c.id, type: c.mode, status: c.status, lat: c.lat, lng: c.lng, targetLat: c.lat, targetLng: c.lng, kind: "courier" });
      } else {
        cur.targetLat = c.lat;
        cur.targetLng = c.lng;
        cur.status = c.status;
      }
    }
    for (const id of [...this._units.keys()]) {
      if (!seen.has(id)) this._units.delete(id);
    }
  }

  _loop = () => {
    this._draw();
    this._raf = requestAnimationFrame(this._loop);
  };

  _draw() {
    const canvas = this._canvas;
    const map = this._map;
    if (!canvas || !map) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const size = map.getSize();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size.x, size.y);

    const moving = new Set(["TO_HUB", "TO_CUSTOMER", "DELIVERING"]);
    for (const unit of this._units.values()) {
      // exponential smoothing toward the target from the last tick
      unit.lat += (unit.targetLat - unit.lat) * 0.25;
      unit.lng += (unit.targetLng - unit.lng) * 0.25;
      if (!map.getBounds().pad(0.1).contains([unit.lat, unit.lng])) continue;
      const p = map.latLngToContainerPoint([unit.lat, unit.lng]);
      const color = VEHICLE_COLORS[unit.type] ?? "#94a3b8";
      const active = moving.has(unit.status) || unit.status === "OUT_FOR_DELIVERY";
      const radius = unit.kind === "vehicle" ? 5 : 4;
      ctx.globalAlpha = active ? 1 : 0.4;
      ctx.shadowBlur = active ? 10 : 0;
      ctx.shadowColor = color;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;
      // status ring for active units
      if (active) {
        ctx.strokeStyle = color;
        ctx.globalAlpha = 0.35;
        ctx.beginPath();
        ctx.arc(p.x, p.y, radius + 3, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1;
      }
    }
  }
}

/* ------------------------------------------------------------------ */
/* React component                                                      */
/* ------------------------------------------------------------------ */
const CLASS_ORDER = ["motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street"];

const roadCache = new Map<string, { a: [number, number]; b: [number, number]; color: string; width: number }[] | null>();
const roadPromises = new Map<string, Promise<void>>();

function loadRoads(cityCode: string, onDone: () => void) {
  const hit = roadCache.get(cityCode);
  if (hit) {
    onDone();
    return;
  }
  let p = roadPromises.get(cityCode);
  if (!p) {
    const url = cityCode === "vizag"
      ? "/data/vizag_roads.geojson"
      : "/data/hyderabad_roads.geojson";
    p = fetch(url)
      .then((r) => r.json())
      .then((fc: { features: { geometry: { coordinates: [number, number][] }; properties: { kind?: string; class?: string } }[] }) => {
        const arr: { a: [number, number]; b: [number, number]; color: string; width: number }[] = [];
        for (const f of fc.features) {
          const cls = f.properties.class ?? "default";
          const style = ROAD_STYLE[cls] ?? ROAD_STYLE.default;
          const c = f.geometry.coordinates;
          arr.push({ a: [c[0][1], c[0][0]], b: [c[1][1], c[1][0]], color: style.color, width: style.width });
        }
        roadCache.set(cityCode, arr);
      })
      .catch(() => {
        roadCache.set(cityCode, []);
      });
    roadPromises.set(cityCode, p);
  }
  p.then(() => onDone());
}

export function CityMap({
  zones,
  hubs,
  vehicles,
  couriers,
  curbZones,
  congestion,
  routes,
  cityCode = "hyderabad",
  center,
  zoom = 12.4,
  height = "100%",
  onReady,
}: {
  zones: Zone[];
  hubs: Hub[];
  vehicles: Vehicle[];
  couriers: Courier[];
  curbZones: CurbZone[];
  congestion: { zone_id: string; zone_name: string; index: number }[];
  routes?: number[][][];
  cityCode?: string;
  center?: [number, number];
  zoom?: number;
  height?: string;
  onReady?: () => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const roadLayerRef = useRef<RoadCanvasLayer | null>(null);
  const unitLayerRef = useRef<UnitCanvasLayer | null>(null);
  const zonesLayerRef = useRef<L.LayerGroup | null>(null);
  const hubLayerRef = useRef<L.LayerGroup | null>(null);
  const curbLayerRef = useRef<L.LayerGroup | null>(null);
  const routeLayerRef = useRef<L.LayerGroup | null>(null);

  // init map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
  const map = L.map(containerRef.current, {
    center: center ?? [17.472, 78.415],
    zoom: zoom ?? 12.4,
      attributionControl: false,
      minZoom: 10.5,
      maxZoom: 18,
    });
    mapRef.current = map;

    // no tile layer: dark canvas + OSM roads drawn locally (fully offline)
    loadRoads(cityCode, () => {
      const roads = roadCache.get(cityCode);
      if (!mapRef.current || !roads) return;
      if (roadLayerRef.current) roadLayerRef.current.remove();
      const layer = new RoadCanvasLayer(roads);
      layer.addTo(mapRef.current);
      roadLayerRef.current = layer;
    });

    const units = new UnitCanvasLayer();
    units.addTo(map);
    unitLayerRef.current = units;
    onReady?.();
    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cityCode]);

  // push live units to the canvas layer
  useEffect(() => {
    unitLayerRef.current?.setUnits(vehicles, couriers);
  }, [vehicles, couriers]);

  // zones + congestion
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (zonesLayerRef.current) zonesLayerRef.current.clearLayers();
    const group = L.layerGroup().addTo(map);
    zonesLayerRef.current = group;
    const loadMap = new Map(congestion.map((c) => [c.zone_id, c.index]));
    for (const z of zones) {
      const load = loadMap.get(z.id) ?? 0;
      L.circle([z.center_lat, z.center_lng], {
        radius: z.radius_km * 1000,
        color: z.color,
        weight: 1.2,
        dashArray: "4 6",
        fillColor: z.color,
        fillOpacity: 0.05 + load * 0.32,
        interactive: false,
      }).addTo(group);
      L.circleMarker([z.center_lat, z.center_lng], { radius: 3, color: z.color, interactive: false }).addTo(group);
    }
  }, [zones, congestion]);

  // hubs
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (hubLayerRef.current) hubLayerRef.current.clearLayers();
    const group = L.layerGroup().addTo(map);
    hubLayerRef.current = group;
    for (const h of hubs) {
      if (!h.lat) continue;
      const color = HUB_COLORS[h.type] ?? "#94a3b8";
      const util = h.capacity ? h.occupied / h.capacity : 0;
      const marker = L.circleMarker([h.lat, h.lng], {
        radius: 7,
        color,
        weight: 2,
        fillColor: "#0d1526",
        fillOpacity: 0.9,
      }).addTo(group);
      marker.bindTooltip(
        `<div style="font:12px system-ui;color:#e6edf7"><b>${h.name}</b><br/>${util.toLocaleString("en-IN", { style: "percent", maximumFractionDigits: 0 })} utilized<br/>${h.occupied}/${h.capacity} slots</div>`,
        { direction: "top", offset: [0, -8] },
      );
    }
  }, [hubs]);

  // curb zones
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (curbLayerRef.current) curbLayerRef.current.clearLayers();
    const group = L.layerGroup().addTo(map);
    curbLayerRef.current = group;
    for (const c of curbZones) {
      if (!c.lat) continue;
      const icon = L.divIcon({
        className: "",
        html: `<div style="width:11px;height:11px;border:1.5px solid #34d399;background:rgba(52,211,153,0.25);border-radius:2px;transform:rotate(45deg)"></div>`,
        iconSize: [11, 11],
        iconAnchor: [5, 5],
      });
      L.marker([c.lat, c.lng], { icon }).addTo(group).bindTooltip(`<div style="font:12px system-ui;color:#e6edf7"><b>${c.name}</b><br/>loading zone · ${c.capacity} slot(s)</div>`, { direction: "top" });
    }
  }, [curbZones]);

  // routes (dispatch previews / demo animation)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (routeLayerRef.current) routeLayerRef.current.clearLayers();
    const group = L.layerGroup().addTo(map);
    routeLayerRef.current = group;
    if (!routes?.length) return;
    for (const poly of routes) {
      if (poly.length < 2) continue;
      L.polyline(poly as L.LatLngExpression[], {
        color: "#38bdf8",
        weight: 3,
        opacity: 0.95,
        dashArray: "6 8",
      }).addTo(group);
      L.polyline(poly as L.LatLngExpression[], { color: "#38bdf8", weight: 6, opacity: 0.15 }).addTo(group);
    }
  }, [routes]);

  return (
    <div className="relative w-full" style={{ height }}>
      <div ref={containerRef} className="absolute inset-0 grid-bg" style={{ background: "#070b14" }} />
    </div>
  );
}

export { CLASS_ORDER, VEHICLE_COLORS, HUB_COLORS };