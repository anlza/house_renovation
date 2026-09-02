# ==========================
# config.py
# ==========================

import random

STATE_CITY_MAP = {
    "Kerala"       : ["Kochi", "Thiruvananthapuram", "Kozhikode", "Thrissur", "Kottayam", "Kannur"],
    "Karnataka"    : ["Bengaluru", "Mysuru", "Mangaluru", "Hubli", "Belagavi"],
    "Tamil Nadu"   : ["Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli"],
    "Telangana"    : ["Hyderabad", "Warangal", "Karimnagar", "Nizamabad"],
    "Maharashtra"  : ["Mumbai", "Pune", "Nagpur", "Nashik", "Thane"],
    "Gujarat"      : ["Ahmedabad", "Surat", "Vadodara", "Rajkot"],
    "Delhi"        : ["New Delhi"],
    "Rajasthan"    : ["Jaipur", "Jodhpur", "Udaipur", "Kota"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Noida", "Agra", "Varanasi"],
    "West Bengal"  : ["Kolkata", "Howrah", "Siliguri", "Durgapur"]
}

STATE_MULTIPLIERS = {
    "Kerala"       : {"material": 1.08, "labour": 1.10},
    "Karnataka"    : {"material": 1.05, "labour": 1.06},
    "Tamil Nadu"   : {"material": 1.03, "labour": 1.04},
    "Telangana"    : {"material": 1.02, "labour": 1.03},
    "Maharashtra"  : {"material": 1.15, "labour": 1.20},
    "Gujarat"      : {"material": 1.06, "labour": 1.05},
    "Delhi"        : {"material": 1.18, "labour": 1.22},
    "Rajasthan"    : {"material": 0.97, "labour": 0.95},
    "Uttar Pradesh": {"material": 0.94, "labour": 0.90},
    "West Bengal"  : {"material": 1.00, "labour": 0.98},
}

REGION_TYPES      = ["Urban", "Semi-Urban", "Rural"]
REGION_MULTIPLIER = {"Urban": 1.20, "Semi-Urban": 1.00, "Rural": 0.85}

SEASONS           = ["Summer", "Monsoon", "Winter"]
SEASON_MULTIPLIER = {
    "Summer" : {"cost": 1.00, "duration": 1.00},
    "Monsoon": {"cost": 1.08, "duration": 1.20},
    "Winter" : {"cost": 0.98, "duration": 0.95}
}

RENOVATION_TYPES = {
    "Interior"  : {"factor": 1.00, "days": 25},
    "Exterior"  : {"factor": 1.10, "days": 30},
    "Full"      : {"factor": 1.80, "days": 75},
    "Kitchen"   : {"factor": 1.35, "days": 35},
    "Bathroom"  : {"factor": 1.25, "days": 28},
    "Roofing"   : {"factor": 1.40, "days": 40},
    "Flooring"  : {"factor": 1.20, "days": 30},
    "Electrical": {"factor": 1.15, "days": 22},
    "Plumbing"  : {"factor": 1.18, "days": 24},
    "Painting"  : {"factor": 0.72, "days": 14}
}

QUALITY_FACTORS = {
    "Economy" : 0.85,
    "Standard": 1.00,
    "Premium" : 1.25,
    "Luxury"  : 1.60
}

MATERIAL_QUALITY  = ["Economy", "Standard", "Premium"]

BASE_PRICES = {
    "Cement": 380,
    "Steel" : 68,
    "Sand"  : 55,
    "Paint" : 320,
    "Brick" : 10,
    "Tile"  : 85,
    "Wood"  : 1800
}

BASE_LABOUR_RATE = 170

BUDGET_PER_SQFT = {
    "Economy" : 1800,
    "Standard": 2500,
    "Premium" : 3500,
    "Luxury"  : 5000
}


def random_state():
    return random.choice(list(STATE_CITY_MAP.keys()))


def random_city(state):
    # NOTE: no trailing comma — this must return a plain string,
    # not a 1-element tuple.
    return random.choice(STATE_CITY_MAP[state])
SMART_MATERIALS = {

    "Economy": {

        "Cement": "ACC Cement",
        "Steel": "Kamdhenu TMT",
        "Paint": "Berger WeatherCoat",
        "Tiles": "Somany Tiles",
        "Wood": "Greenply Plywood"

    },

    "Standard": {

        "Cement": "UltraTech Cement",
        "Steel": "TATA TMT",
        "Paint": "Asian Paints Apex",
        "Tiles": "Kajaria Tiles",
        "Wood": "CenturyPly"

    },

    "Premium": {

        "Cement": "UltraTech OPC 53",
        "Steel": "JSW Neosteel",
        "Paint": "Asian Paints Royale",
        "Tiles": "Kajaria Premium",
        "Wood": "Greenlam"

    }

}

# Labels shown in the final planner and their closest equivalents in the
# training data.  The saved models were trained on the shorter labels above.
RENOVATION_OPTIONS = [
    "Full House Renovation", "Interior Renovation", "Exterior Renovation",
    "Kitchen Renovation", "Bathroom Renovation", "Painting",
    "Flooring & Tiling", "Roofing", "Plumbing", "Electrical Work",
]
MODEL_RENOVATION_MAP = {
    "Full House Renovation": "Full", "Interior Renovation": "Interior",
    "Exterior Renovation": "Exterior", "Kitchen Renovation": "Kitchen",
    "Bathroom Renovation": "Bathroom", "Painting": "Painting",
    "Flooring & Tiling": "Flooring", "Roofing": "Roofing",
    "Plumbing": "Plumbing", "Electrical Work": "Electrical",
}
