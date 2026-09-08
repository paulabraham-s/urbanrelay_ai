"""Scenario definitions for the digital twin.

Each scenario adjusts demand, congestion, road speed and delivery priority
relative to a normal day. All values are multipliers/offsets applied by the
simulation engine — nothing is hard-coded into the demo narrative.
"""

SCENARIOS: dict[str, dict] = {
    "NORMAL_DAY": {
        "id": "NORMAL_DAY",
        "name": "Normal Day",
        "description": "Baseline urban logistics flow.",
        "demand_multiplier": 1.0,
        "congestion_multiplier": 1.0,
        "speed_multiplier": 1.0,
        "priority_shift": 0,
        "color": "#38bdf8",
        "icon": "sun",
    },
    "PEAK_HOUR": {
        "id": "PEAK_HOUR",
        "name": "Peak Hour",
        "description": "Evening rush — commuter traffic meets delivery demand.",
        "demand_multiplier": 2.6,
        "congestion_multiplier": 1.8,
        "speed_multiplier": 0.85,
        "priority_shift": 0,
        "color": "#f59e0b",
        "icon": "clock",
    },
    "FESTIVAL_SALE": {
        "id": "FESTIVAL_SALE",
        "name": "Festival Sale",
        "description": "Major e-commerce sale — orders surge 4x across all zones.",
        "demand_multiplier": 4.2,
        "congestion_multiplier": 2.6,
        "speed_multiplier": 0.8,
        "priority_shift": 1,
        "color": "#f472b6",
        "icon": "gift",
    },
    "WEEKEND_RUSH": {
        "id": "WEEKEND_RUSH",
        "name": "Weekend Rush",
        "description": "Weekend shopping peaks in markets and residential blocks.",
        "demand_multiplier": 1.8,
        "congestion_multiplier": 1.4,
        "speed_multiplier": 0.9,
        "priority_shift": 0,
        "color": "#34d399",
        "icon": "calendar",
    },
    "RAIN_SURGE": {
        "id": "RAIN_SURGE",
        "name": "Rain Surge",
        "description": "Monsoon downpour — instant-delivery orders spike, roads slow.",
        "demand_multiplier": 1.7,
        "congestion_multiplier": 1.6,
        "speed_multiplier": 0.7,
        "priority_shift": 1,
        "color": "#818cf8",
        "icon": "cloud-rain",
    },
    "FLASH_SALE": {
        "id": "FLASH_SALE",
        "name": "Flash Sale",
        "description": "15-minute sale event — extreme demand burst.",
        "demand_multiplier": 5.5,
        "congestion_multiplier": 3.0,
        "speed_multiplier": 0.75,
        "priority_shift": 2,
        "color": "#fb7185",
        "icon": "zap",
    },
    "EMERGENCY": {
        "id": "EMERGENCY",
        "name": "Emergency Logistics",
        "description": "Medical/priority deliveries must reach first responders.",
        "demand_multiplier": 1.2,
        "congestion_multiplier": 1.3,
        "speed_multiplier": 1.1,
        "priority_shift": 3,
        "color": "#f43f5e",
        "icon": "siren",
    },
}


def get_scenario(scenario_id: str) -> dict:
    return SCENARIOS.get(scenario_id, SCENARIOS["NORMAL_DAY"])