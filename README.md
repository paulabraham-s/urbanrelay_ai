<div align="center">

# 🏙️ UrbanRelay AI

### India's Collaborative Smart Logistics Grid

**An AI-powered city logistics orchestration platform** — a digital twin that simulates real-world urban delivery networks on OpenStreetMap roads, consolidates orders through micro-hubs, and cuts congestion, emissions, and delivery time.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_v4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<br/>

**🎬 Live Demo&nbsp;&nbsp;·&nbsp;&nbsp;🏆 SIH 2026 Project&nbsp;&nbsp;·&nbsp;&nbsp;Built for Smart India Hackathon**

</div>

<br/>

## 📑 Table of Contents

- [Problem Statement](#-problem-statement)
- [Solution](#-solution)
- [Architecture](#️-architecture)
- [Simulation Flow](#-simulation-flow)
- [AI Agents](#-ai-agents)
- [Supported Cities](#️-supported-cities)
- [Scenarios](#-scenarios)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [API Endpoints](#-api-endpoints)
- [KPI Metrics](#-kpi-metrics-computed-live)
- [SIH Demo Flow](#-sih-demo-flow)
- [Tech Stack](#️-tech-stack)
- [Testing](#-testing)
- [Database Schema](#-database-schema-14-tables)
- [Impact Comparison](#-impact-comparison)
- [Key Differentiators](#-key-differentiators)
- [Stakeholders](#-stakeholders)
- [License](#-license)

<br/>

## 🚩 Problem Statement

Indian cities lose **₹60,000 crore annually** to logistics inefficiency. Every e-commerce platform dispatches its own fleet — resulting in:

| Issue | Impact |
|---|---|
| 🚛 **Duplicated trips** | 3 vans from Amazon, Flipkart, and Blinkit driving the same street |
| 🚦 **Congestion** | Delivery vehicles cause **30%** of urban traffic in market areas |
| 🌫️ **Emissions** | Last-mile logistics contribute **25%** of urban CO₂ |
| 📦 **Curb conflicts** | Double-parking at delivery points blocks traffic for hours |

<br/>

## 💡 Solution

UrbanRelay AI acts as a **city-scale orchestration layer** — not a delivery company, but the intelligence that coordinates existing fleets.

```
┌─────────────────────────────────────────────────────────────────┐
│                    URBANRELAY AI PLATFORM                       │
├─────────────┬─────────────┬─────────────┬───────────────────────┤
│  AI AGENTS  │  DIGITAL    │  MICRO-HUB  │  CURB MANAGEMENT      │
│             │  TWIN       │  NETWORK    │                       │
│ • Hub       │ • Real OSM  │ • Kirana    │ • Digital loading     │
│   Selection │   roads     │   stores    │   zones               │
│ • Delivery  │ • Poisson   │ • Parcel    │ • Time-slot           │
│   Waves     │   demand    │   lockers   │   reservations        │
│ • Fleet     │ • Congestion│ • Community │ • Conflict            │
│   Balancer  │   modeling  │   centers   │   resolution          │
│ • Curb      │ • 7 disaster│ • Pickup    │ • No double-          │
│   Reserve   │   scenarios │   points    │   parking             │
└─────────────┴─────────────┴─────────────┴───────────────────────┘
```

<br/>

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          SYSTEM ARCHITECTURE                             │
│                                                                            │
│  ┌─────────────┐    WebSocket/REST     ┌─────────────────────────────┐   │
│  │   Frontend   │◄─────────────────────►│        Backend (FastAPI)    │   │
│  │  React+Vite  │                       │                             │   │
│  │  Leaflet Map │                       │  ┌───────────────────────┐  │   │
│  │  Recharts    │                       │  │      4 AI Agents      │  │   │
│  │  Zustand     │                       │  │ ┌───────────────────┐ │  │   │
│  └─────────────┘                       │  │ │ Hub Selection      │ │  │   │
│                                         │  │ │ Delivery Waves     │ │  │   │
│  ┌─────────────┐    GeoJSON            │  │ │ Fleet Balancer     │ │  │   │
│  │OpenStreetMap │──────────────────────► │  │ │ Curb Reserve       │ │  │   │
│  │Road Network  │                       │  │ └───────────────────┘ │  │   │
│  └─────────────┘                       │  └───────────┬───────────┘  │   │
│                                         │              │              │   │
│  ┌─────────────┐    Tick (1s)          │  ┌───────────▼───────────┐  │   │
│  │  Simulation  │◄─────────────────────►│  │  Simulation Engine    │  │   │
│  │  Engine      │    snapshot           │  │  • Tick-based loop    │  │   │
│  │  (Thread)    │                       │  │  • Dijkstra routing   │  │   │
│  └─────────────┘                       │  │  • Poisson demand     │  │   │
│                                         │  │  • Congestion-aware   │  │   │
│  ┌─────────────┐    Write-through      │  └───────────┬───────────┘  │   │
│  │  SQLite /    │◄──────────────────────              │              │   │
│  │  PostgreSQL  │                       │  ┌───────────▼───────────┐  │   │
│  └─────────────┘                       │  │   Persistence Layer   │  │   │
│                                         │  │  Buffered flush/txn   │  │   │
│                                         │  └───────────────────────┘  │   │
│                                         └─────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

<br/>

## 🔄 Simulation Flow

```
                    ┌──────────────────┐
                    │   TICK (1 sec)    │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   1. DEMAND GEN    │
                    │  Poisson process   │
                    │  per zone × hour   │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   2. ASSIGNMENT    │
                    ├───────────────────┤
                    │ BASELINE:          │
                    │ 1 vehicle/order    │──── Direct warehouse → customer
                    │                    │
                    │ URBANRELAY:        │
                    │ ┌────────────────┐ │
                    │ │ DBSCAN wave     │ │──── Cluster nearby orders
                    │ │ hub select      │ │──── Weighted scoring (6 factors)
                    │ │ fleet alloc     │ │──── Assign bulk + couriers
                    │ │ curb reserve    │ │──── Schedule loading slots
                    │ └────────────────┘ │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   3. MOVEMENT      │
                    │  Dijkstra + A*     │
                    │  on real OSM roads │
                    │  congestion-aware  │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   4. COMPLETION    │
                    │  Route delivery    │
                    │  Update metrics    │
                    │  Persist to DB     │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   5. BROADCAST     │
                    │  WebSocket tick    │──► All connected clients
                    │  with full state   │
                    └───────────────────┘
```

<br/>

## 🤖 AI Agents

### 1️⃣ Hub Selection Agent
Weighted scoring across six factors to pick the optimal micro-hub for each order cluster.

```
score = w₁·distance + w₂·capacity + w₃·congestion
      + w₄·accessibility + w₅·utilization + w₆·operating_hours

Weights: 0.25, 0.20, 0.20, 0.15, 0.10, 0.10
```

### 2️⃣ Delivery Wave Agent (DBSCAN)
Clusters orders into geographic waves, then routes each wave in two legs:

```
Orders → DBSCAN clustering → Waves

  ● ● ●   ← Zone A orders cluster together
    ● ●

  ○ ○     ← Zone B orders form separate wave
    ○ ○ ○

Each wave gets:
  • Bulk route:   Warehouse → Hub   (truck)
  • Last-mile:    Hub → Customers   (e-scooter / courier)
```

### 3️⃣ Fleet Balancer Agent
Allocates trucks for bulk hauls and couriers for last-mile drops, balancing load across the fleet.

```
┌─────────────┐     ┌───────────────┐
│  Wave A      │────►│  Truck VIT-001 │  Bulk: 12 parcels
│  (12 orders) │     │  (capacity 15) │  Load: 80%
└─────────────┘     └───────┬───────┘
                             │
                      ┌──────▼──────┐
                      │     Hub      │
                      │   Unload     │
                      └──────┬──────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
          ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐
          │ Courier 1  │ │ C. 2  │ │ Courier 3  │
          │ 4 orders   │ │3 order│ │ 5 orders   │
          └───────────┘ └───────┘ └───────────┘
```

### 4️⃣ Curb Reservation Agent
Books digital loading-zone time slots and resolves scheduling conflicts automatically.

```
Time: ─────────────────────────────────────────►

Curb Zone A:  │████████│         │████│
              10:00    10:15     10:30 10:40

Curb Zone B:        │████████████│
                    10:10        10:25

Conflict resolution → shift departure time or use auxiliary zone
```

<br/>

## 🗺️ Supported Cities

| City | Zones | Road Network | Hubs | Vehicles |
|---|---|---|:---:|:---:|
| **Hyderabad / Secunderabad** | Secunderabad, Kukatpally, Miyapur | OSM roads | 21 | 40 |
| **Visakhapatnam** | Dwaraka Nagar, Kancharapalem, Gajuwaka, MVP Colony | OSM roads | 15 | 40 |

<br/>

## 📊 Scenarios

| Scenario | Demand | Congestion | Speed | Description |
|---|:---:|:---:|:---:|---|
| ☀️ Normal Day | 1.0x | 1.0x | 1.0x | Baseline urban logistics flow |
| 🕐 Peak Hour | 2.6x | 1.8x | 0.85x | Evening rush — commuter + delivery traffic |
| 🎁 Festival Sale | 4.2x | 2.6x | 0.8x | Major e-commerce sale surge |
| 📅 Weekend Rush | 1.8x | 1.4x | 0.9x | Weekend shopping peaks |
| 🌧️ Rain Surge | 1.7x | 1.6x | 0.7x | Monsoon — instant-delivery spike |
| ⚡ Flash Sale | 5.5x | 3.0x | 0.75x | 15-minute extreme demand burst |
| 🚨 Emergency | 1.2x | 1.3x | 1.1x | Medical / priority deliveries |

<br/>

## 📁 Project Structure

```
urbanrelay_ai/
├── backend/
│   ├── app/
│   │   ├── agents/              # 4 AI optimization agents
│   │   │   ├── hub_selection.py     # Weighted hub scoring
│   │   │   ├── delivery_wave.py     # DBSCAN order clustering
│   │   │   ├── fleet_balancer.py    # Vehicle/courier allocation
│   │   │   └── curb_reservation.py  # Loading zone scheduling
│   │   ├── algorithms/          # Core algorithms
│   │   │   ├── graph.py             # Dijkstra/A* on OSM roads
│   │   │   ├── clustering.py        # Pure-Python DBSCAN
│   │   │   ├── geo.py               # Haversine, zone helpers
│   │   │   └── scoring.py           # Explainable weighted model
│   │   ├── api/                 # 14 FastAPI routers
│   │   ├── core/                # Config, security, WebSocket
│   │   ├── models/               # 14 SQLAlchemy ORM models
│   │   ├── schemas/              # Pydantic request/response
│   │   ├── services/             # Sim orchestration + persistence
│   │   └── simulation/           # Tick engine, demand, state
│   ├── scripts/                  # Seed + reset + OSM fetch
│   └── tests/                    # Unit + integration tests
├── frontend/
│   ├── src/
│   │   ├── pages/                # 15 views
│   │   │   ├── CommandCenter.tsx     # Main dashboard + map
│   │   │   ├── Simulation.tsx        # Scenario control + map
│   │   │   ├── Analytics.tsx         # Charts + trends
│   │   │   ├── Orders.tsx            # Order management
│   │   │   ├── Hubs.tsx              # Micro-hub network
│   │   │   ├── Fleet.tsx             # Vehicle/courier fleet
│   │   │   ├── AIDecisions.tsx       # Explainable AI feed
│   │   │   ├── Impact.tsx            # Before/after comparison
│   │   │   ├── LiveOps.tsx           # Real-time fleet map
│   │   │   ├── Curb.tsx              # Loading zone mgmt
│   │   │   └── JudgeView.tsx         # SIH demo view
│   │   ├── components/           # Reusable UI + charts + map
│   │   ├── stores/                # Zustand state (auth, sim, toasts)
│   │   ├── services/              # REST API client
│   │   ├── hooks/                 # WebSocket + animation hooks
│   │   └── types/                 # TypeScript interfaces
│   └── public/data/               # Offline OSM road GeoJSON
├── data/
│   ├── seed/                      # Cities, hubs, warehouses, emissions
│   ├── geojson/                   # Road network files
│   └── raw/                       # Overpass API source data
├── docker/                        # Docker Compose config
├── docs/                          # Reference blueprints + notebooks
└── extension/                     # Chrome dispatcher extension
```

<br/>

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- 2 GB RAM (for road graph loading)

### 1️⃣ Clone & Set Up Backend

```bash
git clone https://github.com/paulabraham-s/urbanrelay_ai.git
cd urbanrelay_ai

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# Install dependencies
pip install -r backend/requirements.txt

# Seed demo data
cd backend
python scripts/seed_demo.py
```

### 2️⃣ Start Backend

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

> The simulation auto-starts with the **Festival Sale** scenario at 3x speed.
> API docs: `http://localhost:8001/docs`

### 3️⃣ Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** to see the live simulation dashboard.

### 🐳 Docker (Alternative)

```bash
docker compose up -d
```

<br/>

## 🧪 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/ready` | Readiness probe |
| `POST` | `/api/auth/login` | Demo login (returns JWT) |
| `GET` | `/api/cities` | List all cities |
| `POST` | `/api/cities/{id}/activate` | Switch active city |
| `GET` | `/api/simulation/scenarios` | 7 scenario definitions |
| `POST` | `/api/simulation/start` | Start simulation |
| `POST` | `/api/simulation/stop` | Stop simulation |
| `POST` | `/api/simulation/activate` | Switch baseline / urbanrelay |
| `GET` | `/api/simulation/kpis` | Live KPI metrics |
| `GET` | `/api/simulation/history` | Congestion + performance history |
| `GET` | `/api/simulation/before-after` | Baseline vs UrbanRelay comparison |
| `GET` | `/api/simulation/recommendations` | AI recommendations |
| `GET` | `/api/dashboard/kpis` | Dashboard KPI summary |
| `GET` | `/api/dashboard/map` | Full map data (zones, hubs, vehicles) |
| `GET` | `/api/analytics/impact` | Impact analysis |
| `GET` | `/api/analytics/orders` | Order distribution by status/platform |
| `GET` | `/api/hubs` | Micro-hub network |
| `GET` | `/api/vehicles` | Fleet vehicles |
| `GET` | `/api/couriers` | Courier fleet |
| `GET` | `/api/curb-zones` | Digital curb zones |
| `POST` | `/api/orders/optimize` | Run AI dispatch optimization |
| `POST` | `/api/dispatch/optimize` | Dispatch for Chrome extension |
| `WS` | `/ws/sim` | Real-time simulation stream |

<br/>

## 📈 KPI Metrics (Computed Live)

| Metric | Description |
|---|---|
| **Active Deliveries** | Orders currently in transit |
| **Vehicles on Road** | Active vehicles + couriers |
| **Congestion Index** | Zone load averaged across all zones (0–100%) |
| **Avg Delivery Time** | Mean time from order creation to delivery |
| **Hub Utilization** | Percentage of micro-hub slots occupied |
| **Distance Saved** | km saved by consolidated routing vs. baseline |
| **CO₂ Saved** | kg CO₂ reduced by UrbanRelay AI |
| **Efficiency Score** | Weighted composite (distance + time + CO₂ + dispatch + congestion) |

<br/>

## 🎯 SIH Demo Flow

The **3-minute demo** (`/demo`) walks judges through:

```
Step 1  PROBLEM       → Baseline simulation showing duplicated trips
Step 2  AI ACTIVATE   → One-click UrbanRelay AI activation
Step 3  LIVE FLEET    → Real-time vehicle consolidation on map
Step 4  AI DECISIONS  → Explainable agent reasoning panel
Step 5  IMPACT        → Before/after metrics comparison
```

<br/>

## 🛠️ Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy | Async-first, high performance |
| **Simulation** | Custom tick engine (thread-based) | Deterministic, seed-reproducible |
| **Routing** | Dijkstra + A* on OSM road graph | Real road networks, not straight lines |
| **Demand** | Poisson process per zone/hour | Realistic urban delivery patterns |
| **AI Agents** | Weighted scoring, DBSCAN, interval scheduling | Explainable, deterministic, no ML black boxes |
| **Frontend** | React 19, TypeScript, Vite 7 | Type safety, fast HMR, modern DX |
| **State** | Zustand (sim store) | Lightweight, single source of truth |
| **Map** | Leaflet + custom Canvas layers | High-performance vehicle animation |
| **Charts** | Recharts | Declarative, composable |
| **Styling** | Tailwind CSS v4 | Utility-first, consistent design tokens |
| **Database** | SQLite (default), PostgreSQL + PostGIS | Zero-setup dev, production-ready |
| **Auth** | PBKDF2 + HS256 JWT | Secure, stateless |

<br/>

## 🧪 Testing

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/test_api.py -v          # API integration tests
pytest tests/test_agents.py -v       # AI agent unit tests
pytest tests/test_clustering.py -v   # DBSCAN algorithm tests
pytest tests/test_routing.py -v      # Graph routing tests
pytest tests/test_emissions.py -v    # Emission factor tests
```

<br/>

## 📊 Database Schema (14 Tables)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    users      │     │    cities     │     │    zones      │
│  id (UUID)    │     │  id, name     │     │  id, city_id  │
│  username     │     │  code, active │     │  center, rate │
│  password_hash│     │  center_lat   │     │  capacity     │
│  role         │     │  center_lng   │     └───────┬───────┘
└──────────────┘     └──────┬───────┘             │
                            │                      │
                    ┌───────▼───────┐     ┌───────▼───────┐
                    │  micro_hubs    │     │  curb_zones    │
                    │  id, city_id   │     │  id, city_id   │
                    │  type, lat/lng │     │  lat/lng, cap  │
                    │  capacity      │     └───────┬───────┘
                    └───────┬───────┘             │
                            │                      │
┌──────────────┐     ┌──────▼───────┐     ┌──────▼───────┐
│   orders      │     │ delivery_waves│     │ curb_reserv.  │
│  id, platform │     │  id, name     │     │  curb_id      │
│  customer info│     │  zone_id      │     │  vehicle_id   │
│  status, mode │     │  order_count  │     │  time window  │
│  hub/vehicle/ │     └──────────────┘     └──────────────┘
│  courier_id   │
└───────┬───────┘
        │
┌───────▼───────┐     ┌──────────────┐     ┌──────────────┐
│   vehicles     │     │  couriers     │     │  ai_decisions │
│  id, type      │     │  id, mode     │     │  id, agent    │
│  capacity      │     │  capacity     │     │  decision     │
│  lat/lng       │     │  lat/lng      │     │  reasons (JSON)│
│  status, mode  │     │  earnings     │     │  score        │
└───────┬───────┘     └──────────────┘     └──────────────┘
        │
┌───────▼───────┐     ┌──────────────┐     ┌──────────────┐
│   routes       │     │   alerts      │     │simulation_runs│
│  kind, mode    │     │  code, severity│    │  scenario     │
│  order_id      │     │  message      │     │  seed, speed  │
│  from/to       │     │  resolved_at  │     │  metrics (JSON)│
│  distance      │     └──────────────┘     └──────────────┘
└───────────────┘
```

<br/>

## 🌍 Impact Comparison

| Metric | Current System | UrbanRelay AI | Improvement |
|---|:---:|:---:|:---:|
| Vehicles per delivery | 1.0 | 0.35 | 🟢 **65% fewer** |
| Avg distance per order | 4.2 km | 2.1 km | 🟢 **50% shorter** |
| Avg delivery time | 28 min | 18 min | 🟢 **36% faster** |
| CO₂ per delivery | 320 g | 145 g | 🟢 **55% less** |
| Road congestion index | 78% | 42% | 🟢 **46% lower** |
| Hub utilization | 0% | 65% | 🟢 Kirana revenue ↑ |

<br/>

## 🏆 Key Differentiators

1. **Explainable AI** — Every decision shows reasoning, inputs, and a confidence score. No black boxes.
2. **Real Road Networks** — Uses actual OpenStreetMap roads, not Euclidean distance.
3. **7 Disaster Scenarios** — From monsoon surges to festival sales to medical emergencies.
4. **Micro-Hub Network** — Leverages existing Kirana stores as logistics infrastructure.
5. **Digital Curb Management** — Time-slot loading reservations eliminate double-parking.
6. **Deterministic Replay** — Seed 42 = same demo every time. Perfect for judging.
7. **Zero-Setup** — SQLite by default, no Docker required for development.

<br/>

## 🤝 Stakeholders

| Stakeholder | Benefit |
|---|---|
| 🏛️ **Municipal Corporations** | Congestion data, curb analytics, emission tracking for city planning |
| 🚚 **Logistics Companies** | Consolidated loads, fewer vehicles, faster delivery, lower costs |
| 🏪 **Kirana Store Owners** | New revenue stream as micro-hubs + increased footfall |
| 🛵 **Couriers** | Stable earnings from city-scale last-mile assignments |
| 🧑‍🤝‍🧑 **Citizens** | Less blocked roads, cleaner air, faster parcel delivery |

<br/>

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ for Smart India Hackathon 2026**

[⬆ Back to top](#️-urbanrelay-ai)

</div>
