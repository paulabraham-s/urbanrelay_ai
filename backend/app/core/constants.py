"""Shared constants for UrbanRelay AI."""

ROLES = ["ADMIN", "MUNICIPAL_OPERATOR", "DISPATCHER", "HUB_OPERATOR", "COURIER"]

# Order lifecycle
ORDER_STATUSES = [
    "PENDING",      # waiting for assignment
    "WAVE_ASSIGNED",
    "PICKED_UP",    # in a bulk vehicle toward the hub
    "AT_HUB",       # unloaded at micro-hub
    "OUT_FOR_DELIVERY",  # last-mile courier en route
    "DELIVERED",
    "CANCELLED",
]

VEHICLE_TYPES = {
    "truck": {"label": "Delivery Truck", "capacity": 200, "speed_kph": 28, "color": "#f59e0b"},
    "van": {"label": "Cargo Van", "capacity": 80, "speed_kph": 34, "color": "#38bdf8"},
    "motorcycle": {"label": "Motorcycle", "capacity": 15, "speed_kph": 30, "color": "#a78bfa"},
    "e-scooter": {"label": "E-Scooter", "capacity": 10, "speed_kph": 24, "color": "#34d399"},
    "bicycle": {"label": "Cargo Bicycle", "capacity": 6, "speed_kph": 15, "color": "#f472b6"},
    "walking": {"label": "Walking Courier", "capacity": 3, "speed_kph": 5, "color": "#94a3b8"},
}

# Emission estimates: grams CO2e per km per mode. Clearly labeled ESTIMATED in the UI.
EMISSION_FACTORS_G_PER_KM = {
    "truck": 620.0,
    "van": 280.0,
    "motorcycle": 95.0,
    "e-scooter": 35.0,
    "bicycle": 0.0,
    "walking": 0.0,
}

HUB_TYPES = {
    "kirana": "Kirana Store",
    "locker": "Parcel Locker",
    "parking": "Parking-area Hub",
    "community": "Community Center",
    "pickup": "Municipal Pickup Point",
    "retail": "Retail Store",
}

# Capacity unit = one standard parcel slot
PARCEL_SLOT_KG = 5.0
PARCEL_VOLUME_UNITS = {"small": 1, "medium": 2, "large": 4}

# Routing cost coefficients: cost = a*distance_km + b*time_s
ROUTING_ALPHA = 1.0      # per km
ROUTING_BETA = 1.0 / 60  # per second (1 min of time ≈ 1 km of distance)
CONGESTION_PENALTY = 2.0  # time multiplier applied per congestion factor unit
MAX_SPEED_MULTIPLIER = 1.4  # couriers/light vehicles can be faster than trucks

DEMO_CITIES = [
    {"name": "Hyderabad / Secunderabad", "code": "hyderabad", "active": True},
]

SIMULATION_MODE_BASELINE = "baseline"
SIMULATION_MODE_URBANRELAY = "urbanrelay"