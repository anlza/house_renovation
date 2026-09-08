"""The end-to-end renovation prediction workflow."""

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from config import (BASE_PRICES, MODEL_RENOVATION_MAP, QUALITY_FACTORS,
                    RENOVATION_OPTIONS)
from modules.material import show_comparison, show_recommendation
from services.recommendations import MATERIAL_OPTIONS, project_suggestions, suggested_quality
from services.report import create_project_pdf
from services.material_engine import calculate_materials
from services.work_requirements import fields_for, FULL_COMPONENT_TO_WORK
from auth import (add_expense, add_quote, create_project, get_expenses, get_prediction_history,
                  get_projects, get_quotes, save_prediction_history)
from utils.encoder import encode_input
from utils.model_loader import load_models
from utils.predictor import predict


MATERIALS = list(BASE_PRICES)

# Material allocation is renovation-specific. Only materials required by the
# selected renovation are included; no global material list is appended.
MATERIAL_PROFILES = {
    "Kitchen Renovation": {"Wood": .35, "Countertop": .25, "Tiles": .20, "Paint": .08, "Tile Adhesive": .12},
    "Bathroom Renovation": {"Tiles": .35, "Tile Adhesive": .18, "Waterproofing": .18, "Sanitary Fixtures": .17, "PVC/CPVC Pipes": .12},
    "Painting": {"Paint": .68, "Primer": .17, "Putty": .15},
    "Flooring & Tiling": {"Tiles": .58, "Tile Adhesive": .22, "Sand": .12, "Cement": .08},
    "Roofing": {"Cement": .30, "Steel": .25, "Sand": .20, "Waterproofing": .25},
    "Plumbing": {"PVC/CPVC Pipes": .45, "Plumbing Fittings": .35, "Sanitary Fixtures": .20},
    "Electrical Work": {"Electrical Cable": .55, "Switches & Sockets": .25, "MCB & Conduit": .20},
    "Interior Renovation": {"Paint": .25, "Tiles": .20, "Wood": .25, "Cement": .10, "Plumbing Fittings": .10, "Electrical Cable": .10},
    "Exterior Renovation": {"Paint": .35, "Cement": .25, "Sand": .20, "Waterproofing": .20},
    "Full House Renovation": {"Cement": .14, "Steel": .10, "Sand": .08, "Paint": .10, "Brick": .08, "Tiles": .12, "Wood": .10, "PVC/CPVC Pipes": .08, "Electrical Cable": .07, "Waterproofing": .08, "Sanitary Fixtures": .05},
}

MATERIAL_PURPOSES = {
    "Kitchen Renovation": {
        "Wood": "New cabinets and storage", "Countertop": "New countertop work",
        "Tiles": "Flooring and backsplash", "Paint": "Wall and ceiling finish",
        "Tile Adhesive": "Tile installation",
    },
    "Bathroom Renovation": {
        "Tiles": "Floor and wall tiling", "Tile Adhesive": "Tile installation",
        "Waterproofing": "Wet-area waterproofing", "Sanitary Fixtures": "Required bathroom fixtures",
        "PVC/CPVC Pipes": "Water supply and drainage connections",
    },
    "Painting": {"Paint": "Wall and ceiling coating", "Primer": "Surface preparation and adhesion", "Putty": "Surface levelling and crack filling"},
    "Flooring & Tiling": {"Tiles": "New flooring", "Tile Adhesive": "Tile fixing", "Sand": "Floor levelling", "Cement": "Minor base repair"},
    "Roofing": {"Cement": "Roof repair", "Steel": "Structural repair where required", "Sand": "Repair mortar mix", "Waterproofing": "Leak prevention system"},
    "Plumbing": {"PVC/CPVC Pipes": "Water supply and drainage lines", "Plumbing Fittings": "Valves, taps and connectors", "Sanitary Fixtures": "Fixtures included in the plumbing scope"},
    "Electrical Work": {"Electrical Cable": "Circuit wiring", "Switches & Sockets": "Control and outlet points", "MCB & Conduit": "Circuit protection and cable routing"},
    "Interior Renovation": {"Paint": "Interior finishes", "Tiles": "Selected flooring work", "Wood": "Interior carpentry", "Cement": "Minor repair work", "Plumbing Fittings": "Interior service points", "Electrical Cable": "Interior electrical updates"},
    "Exterior Renovation": {"Paint": "Exterior protective finish", "Cement": "Surface repair", "Sand": "Repair mortar", "Waterproofing": "Moisture protection"},
    "Full House Renovation": {
        "Cement": "Core repair and masonry", "Steel": "Structural repair where required", "Sand": "Mortar and levelling",
        "Paint": "Interior and exterior finishing", "Brick": "Masonry repair", "Tiles": "Flooring and wet areas",
        "Wood": "Carpentry", "PVC/CPVC Pipes": "Plumbing renewal", "Electrical Cable": "Electrical renewal",
        "Waterproofing": "Wet-area and roof protection", "Sanitary Fixtures": "Bathroom fixtures",
    },
}

MATERIAL_WEIGHT_KG = {
    "Cement": 50, "Steel": 1, "Sand": 45, "Brick": 3, "Paint": 1.3,
    "Primer": 1.2, "Putty": 1, "Tiles": 4, "Tile Adhesive": 1,
    "Wood": 20, "Countertop": 2.8, "Waterproofing": 1.5,
    "Electrical Cable": 0.6, "Switches & Sockets": 0.2, "MCB & Conduit": 0.5,
    "PVC/CPVC Pipes": 0.8, "Plumbing Fittings": 0.7, "Sanitary Fixtures": 35,
}
# Planning consumption per sq ft of work. Quantities are derived from scope,
# not by dividing an AI cost by a retail rate. Wastage is added separately.
MATERIAL_REQUIREMENT_PER_SQFT = {
    "Cement": .12, "Steel": .35, "Sand": .30, "Brick": 2.5, "Paint": .10,
    "Primer": .025, "Putty": .12, "Tiles": 1.0, "Tile Adhesive": .30,
    "Wood": .35, "Countertop": .12, "Waterproofing": 1.0, "Electrical Cable": .35,
    "Switches & Sockets": .04, "MCB & Conduit": .03, "PVC/CPVC Pipes": .12,
    "Plumbing Fittings": .03, "Sanitary Fixtures": .01,
}
WASTAGE_RATE = .08
VEHICLE_SPECS = {
    "Mini truck": {"capacity": 1000, "mileage": 12}, "Pickup": {"capacity": 3500, "mileage": 10},
    "Medium truck": {"capacity": 10000, "mileage": 7}, "Large truck": {"capacity": 18000, "mileage": 5},
}
FUEL_PRICE_PER_LITRE = 105
STATE_MAP_CENTERS = {
    "Kerala": [10.25, 76.35], "Karnataka": [15.32, 75.71],
    "Tamil Nadu": [11.13, 78.66], "Telangana": [18.11, 79.02],
    "Maharashtra": [19.75, 75.71], "Gujarat": [22.26, 71.19],
    "Delhi": [28.61, 77.21], "Rajasthan": [27.02, 74.22],
    "Uttar Pradesh": [26.85, 80.95], "West Bengal": [22.99, 87.86],
}

REQUIREMENTS = {
    # Step 3 asks only about the selected renovation work. Current house details
    # are collected separately in Step 2 and are never confused with work area.
    "Kitchen Renovation": [
        ("Kitchen work area (sq ft)", "work_area", 20),
        ("Existing countertop area (sq ft)", "existing_countertop_area", 0),
        ("New countertop area needed (sq ft)", "additional_countertop_area", 0),
        ("Existing cupboards (number)", "existing_cupboards", 0),
        ("New cupboards needed (number)", "additional_cupboards", 0),
        ("Cabinet quality", "cabinet_quality", ["Economy", "Standard", "Premium"]),
        ("Countertop type", "countertop", ["Granite", "Quartz", "Marble"]),
        ("Kitchen flooring", "flooring", ["Ceramic", "Vitrified", "Natural stone"]),
        ("Painting needed", "painting", ["Yes", "No"]),
    ],
    "Bathroom Renovation": [
        ("Bathroom work area (sq ft)", "work_area", 15),
        ("Plumbing condition (1 = poor, 10 = excellent)", "plumbing", list(range(1, 11))),
        ("Waterproofing required", "waterproof", ["Yes", "No"]),
        ("Tile quality", "tile_quality", ["Economy", "Standard", "Premium"]),
        ("Sanitary fittings", "sanitary", ["Basic", "Standard", "Premium"]),
    ],
    "Painting": [
        ("Area to be painted (sq ft)", "work_area", 20),
        ("Paint type", "paint_type", ["Emulsion", "Enamel", "Weatherproof"]),
        ("Paint location", "paint_location", ["Interior", "Exterior"]),
        ("Number of coats", "coats", [1, 2, 3]),
    ],
    "Flooring & Tiling": [
        ("Flooring work area (sq ft)", "work_area", 20),
        ("Tile quality", "tile_quality", ["Economy", "Standard", "Premium"]),
        ("Existing floor condition (1 = poor, 10 = excellent)", "wall", list(range(1, 11))),
    ],
    "Roofing": [
        ("Roof work area (sq ft)", "work_area", 30),
        ("Roof condition (1 = poor, 10 = excellent)", "roof", list(range(1, 11))),
        ("Waterproofing required", "waterproof", ["Yes", "No"]),
    ],
    "Plumbing": [
        ("Plumbing service area (sq ft)", "work_area", 20),
        ("Plumbing condition (1 = poor, 10 = excellent)", "plumbing", list(range(1, 11))),
        ("Waterproofing required", "waterproof", ["Yes", "No"]),
    ],
    "Electrical Work": [
        ("Electrical work area (sq ft)", "work_area", 20),
        ("Electrical condition (1 = poor, 10 = excellent)", "electrical", list(range(1, 11))),
    ],
    "Interior Renovation": [
        ("Interior work area (sq ft)", "work_area", 30),
        ("Wall condition (1 = poor, 10 = excellent)", "wall", list(range(1, 11))),
        ("Flooring", "flooring", ["Ceramic", "Vitrified", "Natural stone"]),
        ("Painting needed", "painting", ["Yes", "No"]),
    ],
    "Exterior Renovation": [
        ("Exterior work area (sq ft)", "work_area", 30),
        ("Wall condition (1 = poor, 10 = excellent)", "wall", list(range(1, 11))),
        ("Roof condition (1 = poor, 10 = excellent)", "roof", list(range(1, 11))),
        ("Waterproofing required", "waterproof", ["Yes", "No"]),
    ],
    "Full House Renovation": [
        ("Estimated renovation area (sq ft)", "work_area", 50),
        ("Wall condition (1 = poor, 10 = excellent)", "wall", list(range(1, 11))),
        ("Roof condition (1 = poor, 10 = excellent)", "roof", list(range(1, 11))),
        ("Plumbing condition (1 = poor, 10 = excellent)", "plumbing", list(range(1, 11))),
        ("Electrical condition (1 = poor, 10 = excellent)", "electrical", list(range(1, 11))),
        ("Waterproofing required", "waterproof", ["Yes", "No"]),
    ],
}
HOUSE_DETAILS = [
    ("Total current house area (sq ft)", "area", 100),
    ("House age (years)", "house_age", 0),
    ("Number of rooms", "rooms", 1),
    ("Number of bathrooms", "bathrooms", 1),
    ("Number of floors", "floors", 1),
    ("Basement", "basement", ["Yes", "No"]),
]

FULL_HOUSE_SCOPE_OPTIONS = [
    "Wall / structural repair", "Roofing", "Plumbing", "Electrical work",
    "Flooring & tiling", "Painting", "Kitchen", "Bathroom", "Exterior work",
]

FULL_SCOPE_MATERIALS = {
    "Wall / structural repair": {"Cement", "Steel", "Sand", "Brick"},
    "Roofing": {"Cement", "Steel", "Sand", "Waterproofing"},
    "Plumbing": {"PVC/CPVC Pipes", "Sanitary Fixtures"},
    "Electrical work": {"Electrical Cable"},
    "Flooring & tiling": {"Tiles"},
    "Painting": {"Paint"},
    "Kitchen": {"Wood", "Tiles"},
    "Bathroom": {"Tiles", "Waterproofing", "Sanitary Fixtures", "PVC/CPVC Pipes"},
    "Exterior work": {"Paint", "Cement", "Sand", "Waterproofing"},
}


# Full-house is a project mode, not a second list of renovation types. The user
# selects actual work components, and each component contributes its own inputs,
# materials and relative planning weight.
FULL_SCOPE_WEIGHTS = {
    "Wall / structural repair": 0.18,
    "Roofing": 0.12,
    "Plumbing": 0.10,
    "Electrical work": 0.10,
    "Flooring & tiling": 0.12,
    "Painting": 0.08,
    "Kitchen": 0.15,
    "Bathroom": 0.10,
    "Exterior work": 0.05,
}

FULL_SCOPE_PROFILES = {
    "Wall / structural repair": {"Cement": .32, "Steel": .24, "Sand": .20, "Brick": .24},
    "Roofing": {"Cement": .30, "Steel": .25, "Sand": .20, "Waterproofing": .25},
    "Plumbing": {"PVC/CPVC Pipes": .55, "Plumbing Fittings": .45},
    "Electrical work": {"Electrical Cable": .55, "Switches & Sockets": .25, "MCB & Conduit": .20},
    "Flooring & tiling": {"Tiles": .62, "Tile Adhesive": .24, "Sand": .08, "Cement": .06},
    "Painting": {"Paint": .68, "Primer": .17, "Putty": .15},
    "Kitchen": {"Wood": .35, "Countertop": .25, "Tiles": .20, "Paint": .08, "Tile Adhesive": .12},
    "Bathroom": {"Tiles": .35, "Tile Adhesive": .18, "Waterproofing": .18, "Sanitary Fixtures": .17, "PVC/CPVC Pipes": .12},
    "Exterior work": {"Paint": .35, "Cement": .25, "Sand": .20, "Waterproofing": .20},
}

FULL_SCOPE_REQUIREMENTS = {
    "Wall / structural repair": [("Wall condition (1 = poor, 10 = excellent)", "wall", list(range(1, 11)))],
    "Roofing": [("Roof work area (sq ft)", "roof_area", 30), ("Roof condition (1 = poor, 10 = excellent)", "roof", list(range(1, 11))), ("Waterproofing required", "roof_waterproof", ["Yes", "No"])],
    "Plumbing": [("Plumbing condition (1 = poor, 10 = excellent)", "plumbing", list(range(1, 11)))],
    "Electrical work": [("Electrical condition (1 = poor, 10 = excellent)", "electrical", list(range(1, 11)))],
    "Flooring & tiling": [("Flooring work area (sq ft)", "flooring_area", 20), ("Tile quality", "tile_quality", ["Economy", "Standard", "Premium"])],
    "Painting": [("Painting area (sq ft)", "painting_area", 20), ("Paint location", "paint_location", ["Interior", "Exterior", "Both"]), ("Number of coats", "coats", [1, 2, 3])],
    "Kitchen": [("Kitchen work area (sq ft)", "kitchen_area", 20), ("New cupboards needed (number)", "additional_cupboards", 0), ("New countertop area needed (sq ft)", "additional_countertop_area", 0)],
    "Bathroom": [("Bathroom work area (sq ft)", "bathroom_area", 15), ("Bathroom waterproofing required", "bathroom_waterproof", ["Yes", "No"])],
    "Exterior work": [("Exterior work area (sq ft)", "exterior_area", 30), ("Exterior wall condition (1 = poor, 10 = excellent)", "exterior_wall", list(range(1, 11))), ("Exterior waterproofing required", "exterior_waterproof", ["Yes", "No"])],
}



def _init():
    for key, value in {
        "flow_step": 1,
        "project": {},
        "prediction_result": None,
        # Map/search selections remain temporary until explicitly confirmed.
        "pending_work_site_location": None,
        "pending_material_site_location": None,
    }.items():
        st.session_state.setdefault(key, value)


FIELD_HELP = {
    "house_rooms": "Total rooms currently in the house. This is used only as background information for planning; it is not the number of rooms being renovated.",
    "house_bathrooms": "Total bathrooms currently in the house. For a bathroom renovation, the next step asks for the actual bathroom work area.",
    "house_area": "Enter the existing total floor area of the house, not just the area being renovated.",
    "req_work_area": "Enter only the area that will actually be renovated. If you are unsure, use the approximate measured area.",
    "req_flooring_area": "Measure the floor area where new flooring/tiles will be installed. You do not need to calculate tile pieces yourself.",
    "req_tile_quality": "Choose the quality level you want to budget for. Economy = lower-cost, Standard = balanced, Premium = higher-end.",
}

def _field(label, key, values):
    help_text = FIELD_HELP.get(key)
    if isinstance(values, list):
        st.selectbox(label, values, index=None, placeholder="Select an option", key=key, help=help_text)
    else:
        st.number_input(label, min_value=values, value=None, step=1, placeholder="Enter a value", key=key, help=help_text)


def _work_specific_inputs(renovation):
    """Render optional measurements/points that drive the material engine."""
    details = fields_for(renovation)
    if not details:
        return
    st.markdown("#### Work-specific measurements")
    if renovation == "Flooring & Tiling":
        st.info("💡 Tile quantity is calculated automatically from the renovation work area, including the standard 8% wastage allowance. You do not need to choose a tile size or count tile pieces.")
    st.caption("These measurements drive the material quantities. Leave an item at zero only when that work is not included.")
    for label, field, kind, values in details:
        widget = f"detail_{field}"
        prior = st.session_state.project.get(field)
        if kind == "multi":
            selected = st.multiselect(label, values, default=prior or [], key=widget)
            st.session_state.project[field] = selected
        elif kind == "select":
            options = ["Not specified"] + values
            value = st.selectbox(label, options, index=options.index(prior) if prior in options else 0, key=widget)
            st.session_state.project[field] = None if value == "Not specified" else value
        else:
            value = st.number_input(label, min_value=0.0, value=float(prior or 0), step=1.0, key=widget)
            st.session_state.project[field] = value


def _number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _work_specific_valid(renovation, project):
    """Prevent area-only estimates for inherently point/length based work."""
    required = {
        "Plumbing": "plumbing_work",
        "Electrical Work": "electrical_work",
    }
    if renovation == "Full House Renovation":
        for component in project.get("full_scope", []):
            work = FULL_COMPONENT_TO_WORK.get(component)
            if work in required and not project.get(required[work]):
                return False, f"Choose the specific {work.lower()} work before continuing."
            if work in {"Plumbing", "Electrical Work"}:
                valid, message = _work_specific_valid(work, project)
                if not valid:
                    return valid, message
        return True, ""
    key = required.get(renovation)
    if key and not project.get(key):
        return False, f"Choose the specific {renovation.lower()} work before continuing."
    if renovation == "Plumbing":
        works = set(project.get("plumbing_work") or [])
        if works - {"Leakage repair"} and _number(project.get("pipe_length_m")) <= 0:
            return False, "Enter the pipe length required for the selected plumbing work."
        if works == {"Leakage repair"} and _number(project.get("leakage_points")) <= 0:
            return False, "Enter the number of leakage points."
    if renovation == "Electrical Work":
        total = sum(_number(project.get(name)) for name in ("rewiring_length_m", "switch_points", "socket_points", "light_points", "fan_points"))
        if total <= 0 and "Distribution board" not in set(project.get("electrical_work") or []):
            return False, "Enter the cable length or number of electrical points for the selected work."
    return True, ""


def _restore(mapping):
    for project_key, widget_key in mapping.items():
        if widget_key not in st.session_state and project_key in st.session_state.project:
            st.session_state[widget_key] = st.session_state.project[project_key]


def _save(mapping):
    for project_key, widget_key in mapping.items():
        st.session_state.project[project_key] = st.session_state.get(widget_key)


def _complete(mapping):
    _save(mapping)
    return not [name for name in mapping if st.session_state.project.get(name) is None]


def _house_details_page():
    fields = {key: f"house_{key}" for _, key, _ in HOUSE_DETAILS}
    _restore(fields)
    st.subheader("Current house details")
    st.caption("Enter your existing house details. These values help the planner understand the house; they are not the work area.")
    st.info("💡 **Quick guide:** Number of rooms and bathrooms means the total count in the existing house. You do not have to decide which rooms to renovate here—the renovation-specific step will ask that separately.")
    for label, key, values in HOUSE_DETAILS:
        _field(label, fields[key], values)
    return fields


def _requirements_page():
    renovation = st.session_state.project["renovation"]
    st.subheader("Renovation requirements")
    st.caption("Answer only the questions needed for the selected renovation.")

    # Full-house work must still define the actual scope. Area alone cannot tell
    # the system whether the roof, plumbing, electrical work, etc. are included.
    if renovation == "Full House Renovation":
        st.info("Full House Renovation is an overall project. Select only the actual work components needed in this house. You will then see questions only for those selected works.")
        saved_scope = st.session_state.project.get("full_scope", [])
        scope = st.multiselect(
            "Select actual work required",
            FULL_HOUSE_SCOPE_OPTIONS,
            default=saved_scope,
            key="req_full_scope",
        )
        st.session_state.project["full_scope"] = scope
        if scope:
            st.success("Selected work: " + " • ".join(scope))
            st.caption("For the overall AI estimate, enter the approximate floor area of the house affected by this renovation. Do not add kitchen, bathroom and roof areas together.")
        fields = {"work_area": "req_work_area", "full_scope": "req_full_scope"}
        _restore({"work_area": "req_work_area"})
        _field("Approximate house area affected overall (sq ft)", "req_work_area", 50)

        for component in scope:
            st.markdown(f"### {component}")
            component_fields = FULL_SCOPE_REQUIREMENTS.get(component, [])
            mapping = {key: f"req_{key}" for _, key, _ in component_fields}
            _restore(mapping)
            for label, key, values in component_fields:
                _field(label, mapping[key], values)
            fields.update(mapping)
            _work_specific_inputs(FULL_COMPONENT_TO_WORK.get(component, component))
        return fields

    fields = {key: f"req_{key}" for _, key, _ in REQUIREMENTS[renovation]}
    _restore(fields)
    st.caption("Work area means only the part of the house included in this renovation. **You do not need to calculate tile pieces yourself; the planner estimates material quantities from the work area and selected quality.**")
    if renovation == "Kitchen Renovation":
        st.info("Existing kitchen items are recorded for context. Only new countertop and cupboard work is added to the renovation scope.")
    for label, key, values in REQUIREMENTS[renovation]:
        _field(label, fields[key], values)
    _work_specific_inputs(renovation)
    return fields


@st.cache_data(ttl=900, show_spinner=False)
def _search_location(query):
    """Search Indian locations with OpenStreetMap/Nominatim."""
    query = (query or "").strip()
    if not query:
        return []
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 6,
                "countrycodes": "in",
            },
            headers={"User-Agent": "LuminaNest-renovation-planner/1.0"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return []


@st.cache_data(ttl=900, show_spinner=False)
def _reverse_location(latitude, longitude):
    """Turn an exact map point into a friendly address and planning region."""
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": latitude,
                "lon": longitude,
                "format": "jsonv2",
                "addressdetails": 1,
                "zoom": 18,
            },
            headers={"User-Agent": "LuminaNest-renovation-planner/1.0"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        address = data.get("address", {})

        state = address.get("state") or address.get("state_district") or ""
        city = (
            address.get("city")
            or address.get("town")
            or address.get("municipality")
            or address.get("village")
            or address.get("suburb")
            or address.get("county")
            or ""
        )

        if address.get("city") or address.get("municipality"):
            region = "Urban"
        elif address.get("town") or address.get("suburb"):
            region = "Semi-Urban"
        else:
            region = "Rural"

        return {
            "lat": float(latitude),
            "lon": float(longitude),
            "state": state,
            "city": city,
            "region": region,
            "display_name": data.get("display_name", "Selected location"),
        }
    except (requests.RequestException, ValueError):
        return None


def _location_from_search_result(result):
    return _reverse_location(float(result["lat"]), float(result["lon"]))


@st.cache_data(ttl=900, show_spinner=False)
def _get_road_route(start, end):
    """Return actual driving distance, duration and route geometry."""
    if not start or not end:
        return None
    try:
        url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{start['lon']},{start['lat']};{end['lon']},{end['lat']}"
        )
        response = requests.get(
            url,
            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "false",
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return None
        route = data["routes"][0]
        return {
            "distance_km": route["distance"] / 1000,
            "duration_min": route["duration"] / 60,
            "geometry": route.get("geometry"),
        }
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


def _model_location_proxy(state, city, encoders):
    """Keep the exact map location for routing while giving the ML encoder a known label.

    The saved model was trained only on a fixed set of states/cities.  An arbitrary
    pin such as Kothamangalam must therefore not be passed directly to LabelEncoder.
    If the exact city is unknown to the model, the first trained city in the same
    state is used only for the AI estimate.  Transportation still uses the exact pin.
    """
    state_classes = set(str(x) for x in encoders["State"].classes_)
    city_classes = set(str(x) for x in encoders["City"].classes_)

    model_state = state if state in state_classes else None
    model_city = city if city in city_classes else None

    state_city_map = {
        "Kerala": ["Kochi", "Thiruvananthapuram", "Kozhikode", "Thrissur", "Kottayam", "Kannur"],
        "Karnataka": ["Bengaluru", "Mysuru", "Mangaluru", "Hubli", "Belagavi"],
        "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli"],
        "Telangana": ["Hyderabad", "Warangal", "Karimnagar", "Nizamabad"],
        "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Thane"],
        "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot"],
        "Delhi": ["New Delhi"],
        "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota"],
        "Uttar Pradesh": ["Lucknow", "Kanpur", "Noida", "Agra", "Varanasi"],
        "West Bengal": ["Kolkata", "Howrah", "Siliguri", "Durgapur"],
    }

    if model_state is None:
        # Exact location remains unchanged for transport. For ML, use Kerala as a
        # safe trained fallback rather than throwing an unseen-label exception.
        model_state = "Kerala" if "Kerala" in state_classes else next(iter(state_classes))

    if model_city is None or model_city not in city_classes:
        candidates = [c for c in state_city_map.get(model_state, []) if c in city_classes]
        model_city = candidates[0] if candidates else next(iter(city_classes))

    return model_state, model_city


def _set_work_site(location):
    """Permanently save a confirmed work-site location."""
    if not location:
        return
    st.session_state.work_site_location = location
    st.session_state.project_site_location = {
        "lat": location["lat"],
        "lon": location["lon"],
    }
    st.session_state.project["site_location"] = st.session_state.project_site_location
    st.session_state.project["work_site_location"] = location
    st.session_state.project["site_location_confirmed"] = True
    st.session_state.project["selected_area_name"] = location["display_name"]
    st.session_state.project["state"] = location["state"]
    st.session_state.project["city"] = location["city"]
    st.session_state.project["region"] = location["region"]
    st.session_state.pending_work_site_location = None


def _set_material_site(location):
    """Permanently save a confirmed material-site location."""
    if not location:
        return
    st.session_state.material_site_location = location
    st.session_state.project["material_site_location"] = location
    st.session_state.pending_material_site_location = None


def _set_pending_location(kind, location):
    """Store a location temporarily; it is not part of the saved project."""
    if not location:
        return
    key = "pending_work_site_location" if kind == "work" else "pending_material_site_location"
    st.session_state[key] = location


def _get_pending_location(kind):
    key = "pending_work_site_location" if kind == "work" else "pending_material_site_location"
    return st.session_state.get(key)


def _clear_pending_location(kind):
    key = "pending_work_site_location" if kind == "work" else "pending_material_site_location"
    st.session_state[key] = None


def _location_preview(location, kind):
    """Show a confirmation card for a temporary map/search selection."""
    if not location:
        return False

    is_work = kind == "work"
    icon = "🏠" if is_work else "🏭"
    label = "Work Site" if is_work else "Material Site"
    confirm_key = f"confirm_{kind}_site_location"
    cancel_key = f"cancel_{kind}_site_location"

    city = location.get("city") or "Location"
    state = location.get("state") or ""
    display_name = location.get("display_name", "Selected location")

    st.markdown(
        f"""
        <div style="padding:16px;border:1px solid #d9dee8;border-radius:12px;
                    background:#f8fafc;margin:10px 0 12px 0;">
            <div style="font-size:18px;font-weight:700;">📍 Selected Location</div>
            <div style="font-size:16px;margin-top:6px;"><b>{city}, {state}</b></div>
            <div style="margin-top:4px;color:#555;">Exact coordinates: {location["lat"]:.6f}, {location["lon"]:.6f}</div>
            <div style="margin-top:4px;color:#666;font-size:13px;">{display_name}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button(f"✅ Confirm this {label.lower()}", key=confirm_key, type="primary", width='stretch'):
            if is_work:
                _set_work_site(location)
            else:
                _set_material_site(location)
            st.rerun()
    with c2:
        if st.button("↩️ Choose again", key=cancel_key, width='stretch'):
            _clear_pending_location(kind)
            st.rerun()
    return True

def _render_location_search(kind, title, help_text, default_query=""):
    """Small, self-contained search box whose button is always visible."""
    prefix = "work" if kind == "work" else "material"
    st.markdown(f"#### {title}")
    st.caption(help_text)

    with st.form(key=f"{prefix}_location_search_form", clear_on_submit=False):
        query = st.text_input(
            "Search location",
            value=default_query,
            placeholder="Example: Kothamangalam, Kerala" if kind == "work" else "Example: cement supplier, Kochi",
            key=f"{prefix}_location_query",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button(
            "🔍 Search location",
            type="primary",
            width='stretch',
        )

    if submitted:
        results = _search_location(query)
        st.session_state[f"{prefix}_search_results"] = results
        if results:
            st.success(f"Found {len(results)} location option(s). Choose the correct one below.")
        else:
            st.warning("No matching location found. Try adding the town, district or state.")

    return st.session_state.get(f"{prefix}_search_results", [])


def _location_page():
    """Exact work-site picker: search -> click map -> preview -> confirm."""
    st.markdown("## 📍 Select Work-Site Location")
    st.caption("Search for your exact house/work-site location. Click anywhere on the map to fine-tune the exact spot.")

    work_site = st.session_state.get("work_site_location")
    pending_work = _get_pending_location("work")

    # Search bar matching the requested single-location flow.
    c1, c2 = st.columns([6, 1])
    with c1:
        query = st.text_input(
            "Search your exact work-site location",
            placeholder="Example: Nellimattom, Kothamangalam, Ernakulam, Kerala, India",
            key="work_exact_location_query",
            label_visibility="collapsed",
        )
    with c2:
        search_clicked = st.button("Search", type="primary", width='stretch', key="work_exact_search_btn")

    if search_clicked:
        results = _search_location(query)
        st.session_state.work_search_results = results
        if results:
            # Use the best search result immediately and still allow the user
            # to click the map for the exact house/work-site point.
            location = _location_from_search_result(results[0])
            if location:
                _set_pending_location("work", location)
                st.rerun()
        else:
            st.warning("Location not found. Try adding town, district and state.")

    results = st.session_state.get("work_search_results", [])
    if results:
        labels = [r.get("display_name", "Location") for r in results]
        selected_index = st.selectbox(
            "Search results", range(len(labels)), format_func=lambda i: labels[i],
            key="work_search_result_choice",
        )
        if st.button("Use selected result", width='stretch', key="use_work_search_result"):
            location = _location_from_search_result(results[selected_index])
            if location:
                _set_pending_location("work", location)
                st.rerun()

    # Always show a map. If nothing is selected yet, start from Kerala.
    map_location = pending_work or work_site or {"lat": 10.25, "lon": 76.35}
    try:
        import folium
        from streamlit_folium import st_folium

        work_map = folium.Map(
            location=[map_location["lat"], map_location["lon"]],
            zoom_start=17 if (pending_work or work_site) else 7,
            control_scale=True,
        )
        if pending_work or work_site:
            folium.Marker(
                [map_location["lat"], map_location["lon"]],
                tooltip="Selected work-site (click map to adjust)",
                popup="Exact work-site selection",
                icon=folium.Icon(color="red", icon="map-marker", prefix="fa"),
            ).add_to(work_map)

        map_data = st_folium(
            work_map,
            height=390,
            width='stretch',
            returned_objects=["last_clicked"],
            key="work_site_exact_map",
        )
        clicked = map_data.get("last_clicked") if map_data else None
        if clicked:
            clicked_lat = round(float(clicked["lat"]), 7)
            clicked_lon = round(float(clicked["lng"]), 7)
            current_click = (clicked_lat, clicked_lon)
            if current_click != st.session_state.get("last_work_map_click"):
                st.session_state.last_work_map_click = current_click
                location = _reverse_location(clicked_lat, clicked_lon)
                if location:
                    _set_pending_location("work", location)
                    st.rerun()
                st.warning("We could not identify that map point. Please try another point.")
    except ImportError:
        st.warning("Map support is unavailable. Install folium and streamlit-folium from requirements.txt.")

    st.info("ⓘ Click on the exact location on the map (your house / work-site).")

    if pending_work:
        st.markdown("### 📍 Selected Location (Preview)")
        st.subheader(pending_work.get("display_name", "Selected location"))
        address = pending_work.get("display_name", "Selected location")
        st.caption(address)
        a, b, c = st.columns(3)
        a.metric("Latitude", f"{pending_work['lat']:.6f}")
        b.metric("Longitude", f"{pending_work['lon']:.6f}")
        c.metric("Region Type", pending_work.get("region", "Not found"))
        st.info("💡 Please verify the location above. Confirm this work-site only if this is the exact location.")
        left, right = st.columns([1, 1])
        with left:
            if st.button("↻ Choose Again", width='stretch', key="choose_work_again"):
                _clear_pending_location("work")
                st.rerun()
        with right:
            if st.button("✓ Confirm this Work-Site", type="primary", width='stretch', key="confirm_work_exact"):
                _set_work_site(pending_work)
                st.rerun()
    elif work_site:
        st.success(f"✓ Work-site confirmed: {work_site.get('display_name', 'Selected location')}")
        a, b, c = st.columns(3)
        a.metric("Latitude", f"{work_site['lat']:.6f}")
        b.metric("Longitude", f"{work_site['lon']:.6f}")
        c.metric("Region Type", work_site.get("region", "Not found"))
        st.caption("Your confirmed work-site will be used as the destination for material delivery routing.")
    else:
        st.warning("Search for your location or click the map to choose the exact work-site.")

    st.divider()
    _material_supplier_location_picker()


def _material_supplier_location_picker():
    """Pick the actual material supplier/yard so delivery is calculated supplier → work-site."""
    st.markdown("### 🏪 Select Material Supplier Location")
    st.caption("Search for the building-material shop, supplier or yard where materials will be collected. Click the map to fine-tune the exact supplier location.")

    supplier = st.session_state.get("material_site_location")
    pending = _get_pending_location("material")
    work_site = st.session_state.get("work_site_location")

    c1, c2 = st.columns([6, 1])
    with c1:
        query = st.text_input(
            "Search material supplier",
            placeholder="Example: building materials supplier, Kothamangalam, Kerala",
            key="supplier_exact_location_query",
            label_visibility="collapsed",
        )
    with c2:
        search_clicked = st.button("Search", type="primary", width='stretch', key="supplier_exact_search_btn")

    if search_clicked:
        results = _search_location(query)
        st.session_state.material_search_results = results
        if results:
            location = _location_from_search_result(results[0])
            if location:
                _set_pending_location("material", location)
                st.rerun()
        else:
            st.warning("Supplier location not found. Try the shop name together with town and state.")

    results = st.session_state.get("material_search_results", [])
    if results:
        labels = [r.get("display_name", "Location") for r in results]
        selected_index = st.selectbox(
            "Supplier search results", range(len(labels)),
            format_func=lambda i: labels[i], key="material_search_result_choice",
        )
        if st.button("Use selected supplier result", width='stretch', key="use_material_search_result"):
            location = _location_from_search_result(results[selected_index])
            if location:
                _set_pending_location("material", location)
                st.rerun()

    map_location = pending or supplier or work_site or {"lat": 10.25, "lon": 76.35}
    try:
        import folium
        from streamlit_folium import st_folium

        supplier_map = folium.Map(
            location=[map_location["lat"], map_location["lon"]],
            zoom_start=16 if (pending or supplier or work_site) else 7,
            control_scale=True,
        )
        if work_site:
            folium.Marker(
                [work_site["lat"], work_site["lon"]],
                tooltip="Confirmed work-site (delivery destination)",
                icon=folium.Icon(color="red", icon="home", prefix="fa"),
            ).add_to(supplier_map)
        if pending or supplier:
            selected = pending or supplier
            folium.Marker(
                [selected["lat"], selected["lon"]],
                tooltip="Selected material supplier",
                icon=folium.Icon(color="green", icon="shopping-cart", prefix="fa"),
            ).add_to(supplier_map)

        map_data = st_folium(
            supplier_map, height=330, width='stretch',
            returned_objects=["last_clicked"], key="material_supplier_exact_map",
        )
        clicked = map_data.get("last_clicked") if map_data else None
        if clicked:
            clicked_lat = round(float(clicked["lat"]), 7)
            clicked_lon = round(float(clicked["lng"]), 7)
            current_click = (clicked_lat, clicked_lon)
            if current_click != st.session_state.get("last_material_map_click"):
                st.session_state.last_material_map_click = current_click
                location = _reverse_location(clicked_lat, clicked_lon)
                if location:
                    _set_pending_location("material", location)
                    st.rerun()
    except ImportError:
        st.warning("Map support is unavailable. Install folium and streamlit-folium.")

    st.info("ⓘ Choose the exact shop/supplier point on the map. This point is the **FROM** location for transportation.")
    if pending:
        st.markdown("#### 🏪 Selected Supplier (Preview)")
        st.subheader(pending.get("display_name", "Selected supplier"))
        a, b, c = st.columns(3)
        a.metric("Latitude", f"{pending['lat']:.6f}")
        b.metric("Longitude", f"{pending['lon']:.6f}")
        c.metric("Region Type", pending.get("region", "Not found"))
        left, right = st.columns(2)
        with left:
            if st.button("↻ Choose Supplier Again", width='stretch', key="choose_supplier_again"):
                _clear_pending_location("material")
                st.rerun()
        with right:
            if st.button("✓ Confirm this Material Supplier", type="primary", width='stretch', key="confirm_supplier_exact"):
                _set_material_site(pending)
                st.rerun()
    elif supplier:
        st.success(f"✓ Material supplier confirmed: {supplier.get('display_name', 'Selected supplier')}")
        if work_site:
            st.caption("Transportation will be calculated as: **Material Supplier (FROM) → Work-Site (TO)** using the road route.")
    else:
        st.warning("Search for and confirm the material supplier location to calculate the actual delivery route.")


def _location_complete():
    # Both exact points are required for a meaningful FROM → TO delivery calculation.
    return bool(st.session_state.get("work_site_location") and st.session_state.get("material_site_location"))


def _logistics_page():
    fields = {"material": "material_quality", "quality": "finish_quality", "season": "season", "budget": "user_budget"}
    _restore(fields)
    st.subheader("Transportation and budget review")
    st.info("Transportation uses the supplier-to-site distance, vehicle mileage and fuel price. Material quantities use work area, requirement rates and an 8% wastage allowance.")
    st.selectbox("Material quality", ["Economy", "Standard", "Premium"], index=None, placeholder="Select quality", key="material_quality")
    st.selectbox("Finish quality", list(QUALITY_FACTORS), index=None, placeholder="Select quality", key="finish_quality")
    st.selectbox("Work season", ["Summer", "Monsoon", "Winter"], index=None, placeholder="Select season", key="season")
    st.number_input("Available budget (INR)", min_value=1.0, value=None, step=1000.0, placeholder="Enter your budget", key="user_budget")
    # A 10% contingency is included automatically so users do not need to choose it.
    # It is a planning reserve for unexpected renovation expenses.
    st.session_state["contingency_rate"] = 10
    st.info("💡 **Contingency reserve (10%)** is automatically added to your estimate. It is a safety amount kept aside for unexpected costs such as minor repairs, price changes or extra work. You do not need to select anything.")
    return fields


def _collect_project():
    project = st.session_state.project
    # Material rates, quantities, weights and transport are calculated by the
    # planner after prediction. Users only answer renovation-related questions.
    project["prices"] = dict(BASE_PRICES)
    missing = [name for name, value in project.items() if value is None or (name == "prices" and any(price is None for price in value.values()))]
    return project, missing


def _additional_scope_factor(project):
    """Scale the whole-house ML estimate to the actual renovation work area."""
    house_area = max(1.0, float(project.get("area") or 1))
    work_area = max(1.0, float(project.get("work_area") or house_area))
    work_area = min(work_area, house_area)
    project["work_area"] = work_area

    if project["renovation"] == "Full House Renovation":
        selected_weight = sum(FULL_SCOPE_WEIGHTS.get(item, 0) for item in project.get("full_scope", []))
        base_factor = (work_area / house_area) * max(0.05, min(1.0, selected_weight))
    else:
        base_factor = max(0.03, min(1.0, work_area / house_area))

    explanation = (
        f"AI uses the current house details ({house_area:,.0f} sq ft) and then "
        f"scales the estimate to the selected renovation work area ({work_area:,.0f} sq ft)."
    )
    if project["renovation"] == "Full House Renovation":
        explanation += " The full-house estimate is also limited to the work components you selected."

    if project["renovation"] == "Kitchen Renovation":
        countertop = project.get("additional_countertop_area") or 0
        cupboards = project.get("additional_cupboards") or 0
        typical_countertop = max(1, work_area * .16)
        typical_cupboards = max(1, round(work_area / 50))
        kitchen_addition = max(
            .35,
            min(1.4, .45 + .25 * countertop / typical_countertop + .30 * cupboards / typical_cupboards)
        )
        base_factor *= kitchen_addition
        explanation += (
            f" Kitchen additions are based only on {countertop:,.0f} sq ft of new countertop "
            f"and {cupboards:,.0f} new cupboards; existing items are not charged again."
        )

    return max(.03, min(1.6, base_factor)), explanation


@st.cache_data(ttl=3600, show_spinner=False)
def _selected_area_name(latitude, longitude):
    """Return a friendly locality name for a map pin, never coordinates."""
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": latitude, "lon": longitude, "format": "jsonv2", "addressdetails": 1},
            headers={"User-Agent": "LuminaNest-renovation-planner/1.0"}, timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        address = data.get("address", {})
        parts = [address.get(key) for key in ("neighbourhood", "suburb", "village", "town", "city", "state")]
        return ", ".join(dict.fromkeys(part for part in parts if part)) or data.get("display_name", "Selected map location")
    except (requests.RequestException, ValueError):
        return "Selected map location"


def _required_materials(project):
    """Return only materials logically required by the selected renovation."""
    if project["renovation"] == "Full House Renovation":
        selected_scope = project.get("full_scope") or []
        # Combine selected component profiles using their real project weights.
        combined = {}
        for component in selected_scope:
            component_weight = FULL_SCOPE_WEIGHTS.get(component, 0)
            for name, share in FULL_SCOPE_PROFILES.get(component, {}).items():
                combined[name] = combined.get(name, 0) + component_weight * share
        total = sum(combined.values())
        shares = {name: value / total for name, value in combined.items()} if total else {}
    else:
        shares = dict(MATERIAL_PROFILES[project["renovation"]])

    if project.get("painting") == "No":
        shares.pop("Paint", None)
    if project["renovation"] == "Kitchen Renovation":
        if not (project.get("additional_cupboards") or 0):
            shares.pop("Wood", None)
        if not (project.get("additional_countertop_area") or 0):
            shares.pop("Countertop", None)
    if project.get("waterproof") == "No":
        shares.pop("Waterproofing", None)
    if project.get("roof_waterproof") == "No":
        shares.pop("Waterproofing", None)
    if project.get("bathroom_waterproof") == "No" and project["renovation"] == "Full House Renovation":
        # Keep waterproofing only if another selected component still requires it.
        if not any(c in {"Roofing", "Exterior work"} for c in project.get("full_scope", [])):
            shares.pop("Waterproofing", None)
    if project.get("exterior_waterproof") == "No" and project["renovation"] == "Full House Renovation":
        if not any(c in {"Roofing", "Bathroom"} for c in project.get("full_scope", [])):
            shares.pop("Waterproofing", None)

    total = sum(value for value in shares.values() if value > 0)
    return {name: value / total for name, value in shares.items() if value > 0} if total else {}


def _model_frame(project, models):
    # The exact map location is NOT added to the trained feature matrix.
    # The saved ML model only accepts its original 25 features.
    area = project["area"]
    model_state, model_city = _model_location_proxy(
        project["state"], project["city"], models["encoders"]
    )
    project["model_state"] = model_state
    project["model_city"] = model_city

    return pd.DataFrame([{
        "House_Area_sqft": area,
        "Number_of_Rooms": project.get("rooms") or max(1, round(area / 400)),
        "Number_of_Bathrooms": project.get("bathrooms") or 1,
        "Number_of_Floors": project.get("floors") or 1,
        "House_Age": project.get("house_age") or 10,
        "Basement": int(project.get("basement") == "Yes"),
        "State": model_state,
        "City": model_city,
        "Region_Type": project["region"],
        "Renovation_Type": MODEL_RENOVATION_MAP[project["renovation"]],
        "Quality_Grade": project["quality"],
        "Material_Quality": project["material"],
        "Wall_Condition": project.get("wall") or 6,
        "Roof_Condition": project.get("roof") or 6,
        "Plumbing_Condition": project.get("plumbing") or 6,
        "Electrical_Condition": project.get("electrical") or 6,
        "Waterproofing_Required": project.get("waterproof") or "No",
        "Season": project["season"],
        **{
            f"{name[:-1] if name == 'Bricks' else name}_Price": value
            for name, value in project["prices"].items()
        },
    }])


def _save_history(project, result, status):
    record = {
        "date": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "renovation_type": project["renovation"],
        "estimated_cost": result["total"],
        "budget_status": status,
        "project": project,
        "result": result,
    }
    # Keep each user's history in users.json instead of the dataset folder.
    save_prediction_history(st.session_state.username, record)


def _catalog_rate(material, quality):
    """Return the numeric planning rate and display values for one material."""
    key = "Tiles" if material == "Tile" else material
    option = MATERIAL_OPTIONS.get(key, {}).get(quality)
    if not option:
        # Every profile material should be catalogued. Fallback keeps the UI
        # usable without inventing a 'Not catalogued' cost.
        return 1.0, "Local verified supplier", "INR 1 / unit", "Varies by installation"
    brand, rate_text, life = option
    match = re.search(r"\d+(?:\.\d+)?", str(rate_text).replace(",", ""))
    rate = float(match.group()) if match else 1.0
    return rate, brand, rate_text, life


def _run(project):
    models = load_models()

    # 1. AI prediction — only the original trained feature set is used.
    frame = _model_frame(project, models)
    encoded = encode_input(frame, models["encoders"])[models["features"]]
    forecast = predict(models, encoded)

    scope_factor, scope_explanation = _additional_scope_factor(project)
    # Keep the trained model output as a reference, while the displayed core
    # material cost is now calculated from physical work quantities below.
    ml_core_reference = forecast["cost"] * scope_factor
    labour_cost = forecast["labour"] * scope_factor

    material_detail = []
    total_weight = 0
    selected_material_quality = project["material"]
    core_renovation_cost = 0
    # Physical quantities are calculated from actual area, length or points.
    # No percentage of the AI cost is used to reverse-calculate quantities.
    for requirement in calculate_materials(project):
        name = requirement["Material"]
        rate, brand, rate_text, lifespan = _catalog_rate(name, selected_material_quality)
        quantity = requirement["Estimated quantity"]
        amount = quantity * rate
        core_renovation_cost += amount
        weight = quantity * MATERIAL_WEIGHT_KG.get(name, 1)
        total_weight += weight
        material_detail.append({
            "Material": name,
            "Why included": requirement["Why included"],
            "Recommended brand / company": brand,
            "Base quantity": round(requirement["Base quantity"], 2),
            "Wastage": f"{requirement['Wastage rate']:.0%}",
            "Estimated quantity": round(quantity, 1),
            "Unit": requirement["Unit"],
            "Reference market rate": rate_text,
            "Typical service life": lifespan,
            "Estimated weight (kg)": round(weight),
            "Estimated material cost (INR)": round(amount),
        })

    # 2. Transportation — calculate FROM the confirmed material supplier TO the confirmed work-site.
    work_site = project.get("work_site_location")
    material_site = project.get("material_site_location")
    if not material_site or not work_site:
        raise ValueError("Confirm both the material supplier and work-site locations before prediction.")
    route = _get_road_route(material_site, work_site)
    if route:
        distance = route["distance_km"]
        travel_time = route["duration_min"]
        route_geometry = route.get("geometry")
        route_source = "OSRM road route"
    else:
        # Network fallback only: straight-line distance is inflated for a practical planning route.
        from math import asin, cos, radians, sin, sqrt
        lat1, lon1 = radians(material_site["lat"]), radians(material_site["lon"])
        lat2, lon2 = radians(work_site["lat"]), radians(work_site["lon"])
        dlat, dlon = lat2-lat1, lon2-lon1
        a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        straight_km = 6371 * 2 * asin(sqrt(a))
        distance = max(0.5, straight_km * 1.20)
        travel_time = distance / 35 * 60
        route_geometry = None
        route_source = "Fallback planning route (road service unavailable)"
    vehicle = (
        "Mini truck" if total_weight <= 1000
        else "Pickup" if total_weight <= 3500
        else "Medium truck" if total_weight <= 10000
        else "Large truck"
    )

    mileage = VEHICLE_SPECS[vehicle]["mileage"]
    fuel_cost = round((distance / mileage) * FUEL_PRICE_PER_LITRE)
    loading_unloading = round(max(250, fuel_cost * .08))
    transportation_cost = fuel_cost + loading_unloading

    additional_charges = round((core_renovation_cost + labour_cost + transportation_cost) * .05)
    base_estimate = core_renovation_cost + labour_cost + transportation_cost + additional_charges
    # Always apply the standard 10% contingency automatically.
    contingency_rate = 0.10
    project["contingency_rate"] = 10
    contingency = round(base_estimate * contingency_rate)
    breakdown = {
        "Core Renovation Cost": round(core_renovation_cost),
        "Labour Cost": round(labour_cost),
        "Transportation Cost": transportation_cost,
        "Additional Charges": additional_charges,
        f"Contingency ({contingency_rate:.0%})": contingency,
    }
    total = sum(breakdown.values())

    logistics = {
        "Region type": project["region"],
        "Estimated delivery distance (km)": round(distance, 2),
        "Estimated travel time (min)": round(travel_time),
        "Recommended vehicle": vehicle,
        "From": material_site.get("display_name", "Selected material site"),
        "To": work_site.get("display_name", "Selected work site"),
        "Estimated load weight (kg)": round(total_weight),
        "Mileage (km/litre)": mileage,
        "Fuel price (INR/litre)": FUEL_PRICE_PER_LITRE,
        "Fuel cost": fuel_cost,
        "Loading & unloading": loading_unloading,
        "Transportation cost": transportation_cost,
        "Total logistics cost": transportation_cost,
        "Route source": route_source,
        "Supplier latitude": material_site.get("lat"),
        "Supplier longitude": material_site.get("lon"),
        "Work-site latitude": work_site.get("lat"),
        "Work-site longitude": work_site.get("lon"),
        "Route geometry": route_geometry,
    }

    reasons = [
        f"Work scope: {project['renovation']} for {project.get('work_area', project['area']):,.0f} sq ft of the current {project['area']:,.0f} sq ft house.",
        f"Exact work site: {project['city']}, {project['state']} ({project['region']}).",
        f"Material delivery route: {distance:.1f} km by road from the selected supplier/yard.",
        f"Material quantities use work-specific measurements (area, pipe length or electrical points) plus wastage; the AI core reference was INR {ml_core_reference:,.0f}.",
    ]
    if project["renovation"] == "Full House Renovation":
        reasons.insert(1, "Selected full-house scope: " + ", ".join(project.get("full_scope", [])) + ".")
    if project.get("model_city") and project.get("model_city") != project.get("city"):
        reasons.append(
            f"AI location model: the saved model does not contain {project['city']}; "
            f"it used the trained city {project['model_city']} for prediction only. "
            "The transportation calculation still uses your exact pinned location."
        )
    if scope_explanation:
        reasons.insert(1, scope_explanation)

    result = {
        "renovation_cost": round(core_renovation_cost),
        "ml_core_reference": round(ml_core_reference),
        "labour_cost": round(labour_cost),
        "duration": max(1, round(forecast["duration"] * scope_factor)),
        "breakdown": breakdown,
        "material_detail": material_detail,
        "logistics": logistics,
        "total": round(total),
        "reasons": reasons,
        "scope_factor": scope_factor,
    }
    status = "Within Budget" if total <= project["budget"] else "Over Budget"
    _save_history(project, result, status)
    return result, status


def _reset():
    for key in list(st.session_state):
        if key.startswith(("req_", "house_", "price_", "location_", "work_", "material_")) or key in {
            "material_quality", "finish_quality", "season", "user_budget",
            "work_search_results", "material_search_results",
            "work_search_result_choice", "material_search_result_choice",
        }:
            del st.session_state[key]
    st.session_state.flow_step = 1
    st.session_state.project = {}
    st.session_state.prediction_result = None
    st.session_state.pop("live_project_location", None)
    st.session_state.pop("project_site_location", None)
    st.session_state.pop("project_site_confirmed", None)
    st.session_state.pop("work_site_location", None)
    st.session_state.pop("material_site_location", None)


def show():
    _init()
    st.markdown("<div class='eyebrow'>A guided renovation plan</div>", unsafe_allow_html=True)
    st.title("Create your renovation estimate")
    st.markdown("<div class='planning-callout'><strong>Designed around your real work.</strong> Add the measurements, points and material requirements that matter—then let the planner organise the cost, delivery and timeline.</div>", unsafe_allow_html=True)

    # Step 1: renovation selection decides which requirements are shown next.
    if st.session_state.flow_step == 1:
        st.progress(1 / 5, text="Step 1 of 5 · Choose your renovation")
        st.subheader("🏠 What do you want to renovate?")
        st.caption("Choose the main renovation. The next form will show only questions relevant to this work.")
        current = st.session_state.project.get("renovation")
        idx = RENOVATION_OPTIONS.index(current) if current in RENOVATION_OPTIONS else None
        selected = st.selectbox("Renovation type", RENOVATION_OPTIONS, index=idx, placeholder="Select renovation type")
        if st.button("Continue →", type="primary", width='stretch'):
            if not selected:
                st.error("Please select a renovation type first.")
            else:
                st.session_state.project["renovation"] = selected
                st.session_state.flow_step = 2
                st.rerun()
        return

    steps = {
        2: ("Current house details", _house_details_page),
        3: ("Renovation requirements", _requirements_page),
        4: ("Exact work-site & material supplier", _location_page),
        5: ("Budget & planning", _logistics_page),
    }
    title, render_step = steps[st.session_state.flow_step]
    st.progress(st.session_state.flow_step / 5, text=f"Step {st.session_state.flow_step} of 5 · {title}")
    fields = render_step()

    left, right = st.columns(2)
    with left:
        if st.button("← Back", width='stretch'):
            st.session_state.flow_step -= 1
            st.rerun()

    with right:
        if st.session_state.flow_step < 5:
            if st.button("Continue →", type="primary", width='stretch'):
                if st.session_state.flow_step == 4:
                    if _location_complete():
                        st.session_state.flow_step += 1
                        st.rerun()
                    else:
                        st.error("Please confirm both the exact work-site and the material supplier location before continuing.")
                elif st.session_state.flow_step == 3 and st.session_state.project.get("renovation") == "Full House Renovation" and not st.session_state.get("req_full_scope"):
                    st.error("Please select at least one part of the house that needs renovation.")
                elif st.session_state.flow_step == 3:
                    valid, message = _work_specific_valid(st.session_state.project.get("renovation"), st.session_state.project)
                    if not _complete(fields):
                        st.error("Please complete all required fields before continuing.")
                    elif valid:
                        st.session_state.flow_step += 1
                        st.rerun()
                    else:
                        st.error(message)
                elif _complete(fields):
                    st.session_state.flow_step += 1
                    st.rerun()
                else:
                    st.error("Please complete all required fields before continuing.")
        else:
            if st.button("🤖 Run AI prediction", type="primary", width='stretch'):
                if not _complete(fields):
                    st.error("Complete the budget preferences before predicting.")
                    return
                project, missing = _collect_project()
                if missing:
                    st.error("Review the previous steps and complete all fields.")
                    return
                try:
                    with st.spinner("Calculating your renovation plan..."):
                        result, status = _run(project)
                    st.session_state.project = project
                    st.session_state.prediction_result = result
                    st.session_state.page = "results"
                    st.rerun()
                except Exception as exc:
                    st.error(f"Prediction could not be completed: {exc}")

def show_results(section):
    _init()
    result, project = st.session_state.prediction_result, st.session_state.project
    if section == "projects":
        st.title("My projects")
        if project and result:
            name = st.text_input("Project name", value=f"{project.get('renovation', 'Renovation')} plan")
            if st.button("Save current estimate as project", type="primary"):
                create_project(st.session_state.username, name, {"project": project, "result": result})
                st.success("Project saved.")
        saved = get_projects(st.session_state.username)
        if saved:
            st.dataframe(pd.DataFrame([{"Project": x["name"], "Created": x["created_at"][:10], "ID": x["id"]} for x in saved]), hide_index=True, width='stretch')
        else: st.info("Save an estimate here to track its expenses and contractor quotes.")
        return
    saved_projects = get_projects(st.session_state.username)
    if section in {"expenses", "quotes"}:
        st.title("Expense tracking" if section == "expenses" else "Contractor quote comparison")
        if not saved_projects:
            st.info("Save a project first in My Projects."); return
        ids = [p["id"] for p in saved_projects]
        chosen = st.selectbox("Project", ids, format_func=lambda ident: next(p["name"] for p in saved_projects if p["id"] == ident))
        if section == "expenses":
            st.title("Track actual project spending")
            st.caption("Record money you have actually spent during the renovation. These entries are separate from the AI estimate and do not change the predicted project cost.")
            st.info("💡 Use this page like a simple renovation expense diary: add each payment for materials, labour, transport or other work. Keep bills/receipts separately for verification.")
            with st.form("expense_form", clear_on_submit=True):
                category = st.selectbox("What did you pay for?", ["Materials", "Labour", "Transportation", "Additional charges", "Other"])
                amount = st.number_input("Amount paid (INR)", min_value=1.0, value=None, step=100.0, placeholder="Enter amount")
                expense_date = st.date_input("Payment date")
                note = st.text_input("Short note", placeholder="e.g. Cement purchase, electrician advance")
                if st.form_submit_button("Add spending"):
                    if amount is not None:
                        add_expense(st.session_state.username, chosen, category, amount, expense_date, note)
                        st.rerun()
                    st.error("Enter the amount you actually paid.")

            expenses = get_expenses(st.session_state.username, chosen)
            total_spent = sum(float(x.get("amount", 0) or 0) for x in expenses)
            project_budget = float(next((p.get("budget", 0) for p in saved_projects if p["id"] == chosen), 0) or 0)
            m1, m2 = st.columns(2)
            m1.metric("Spent so far", f"INR {total_spent:,.0f}")
            if project_budget > 0:
                remaining = project_budget - total_spent
                label = "Budget remaining" if remaining >= 0 else "Over budget by"
                m2.metric(label, f"INR {abs(remaining):,.0f}")
            else:
                m2.metric("Entries recorded", len(expenses))

            if expenses:
                display = pd.DataFrame(expenses)[["expense_date", "category", "amount", "note"]].rename(columns={
                    "expense_date": "Date", "category": "Category", "amount": "Amount paid (INR)", "note": "Note"
                })
                st.subheader("Spending history")
                st.dataframe(display.style.format({"Amount paid (INR)": "INR {:,.0f}"}), hide_index=True, width='stretch')
            else:
                st.success("No spending recorded yet. Add your first actual payment above.")
        else:
            with st.form("quote_form", clear_on_submit=True):
                contractor=st.text_input("Contractor name"); amount=st.number_input("Quoted amount (INR)",min_value=1.0,step=1000.0); days=st.number_input("Duration (days)",min_value=1,step=1); warranty=st.text_input("Warranty / terms"); note=st.text_input("Notes")
                if st.form_submit_button("Add quote"):
                    if contractor.strip(): add_quote(st.session_state.username, chosen, contractor, amount, days, warranty, note); st.rerun()
                    else: st.error("Enter the contractor name.")
            quotes=get_quotes(st.session_state.username, chosen)
            if quotes: st.dataframe(pd.DataFrame(quotes)[["contractor_name", "amount", "duration_days", "warranty", "note"]].rename(columns={"contractor_name":"Contractor", "amount":"Quote (INR)", "duration_days":"Days"}), hide_index=True, width='stretch')
        return
    if section == "history":
        st.title("Prediction history")
        rows = get_prediction_history(st.session_state.username)
        if rows:
            st.dataframe(pd.DataFrame([{ "Date": x["date"], "Renovation type": x["renovation_type"], "Estimated cost": f"INR {x['estimated_cost']:,.0f}", "Budget status": x["budget_status"]} for x in rows]), hide_index=True, width='stretch')
            chosen = st.selectbox("View report again", range(len(rows)), format_func=lambda x: f"{rows[x]['date']} — {rows[x]['renovation_type']}")
            if st.button("Open selected prediction"):
                st.session_state.project, st.session_state.prediction_result = rows[chosen]["project"], rows[chosen]["result"]
                st.session_state.page = "results"; st.rerun()
        else:
            st.info("No predictions have been saved yet.")
        return
    if not result:
        st.info("Run a prediction to view this module.")
        return
    total, budget = result["total"], project["budget"]
    status, difference = ("Within Budget", budget - total) if total <= budget else ("Over Budget", total - budget)
    tips = project_suggestions(MODEL_RENOVATION_MAP[project["renovation"]], project["season"], status, difference, result["duration"], result["breakdown"])
    relevant_materials = [item["Material"] for item in result["material_detail"]]
    if section == "overview":
        st.markdown("<div class='eyebrow'>Your renovation snapshot</div>", unsafe_allow_html=True)
        st.title("Your plan, clearly summarised")
        st.markdown(f"<div class='result-banner'><div class='label'>Recommended planning budget</div><div class='value'>INR {total:,.0f}</div><div class='sub'>Expected working range: INR {total*.90:,.0f} – INR {total*1.10:,.0f}</div></div>", unsafe_allow_html=True)
        a, b, c = st.columns(3)
        a.metric("Core renovation cost", f"INR {result['renovation_cost']:,.0f}")
        b.metric("Labour cost", f"INR {result['labour_cost']:,.0f}")
        c.metric("Transportation cost", f"INR {result['logistics']['Transportation cost']:,.0f}")
        d, e, f = st.columns(3)
        d.metric("Total estimated budget", f"INR {result['total']:,.0f}")
        e.metric("Project duration", f"{result['duration']} days")
        f.metric("Budget status", status, f"INR {abs(difference):,.0f} {'remaining' if status == 'Within Budget' else 'over budget'}")
        contingency_amount = result["breakdown"].get("Contingency (10%)", 0)
        base_estimate = total - contingency_amount
        st.info(f"💡 **Contingency reserve: 10% automatically included — INR {contingency_amount:,.0f}.** This is a safety amount kept aside for unexpected renovation costs. It is calculated on the full base estimate (renovation + labour + transportation + additional charges).")
        st.caption(f"**Final estimated budget = Base estimate INR {base_estimate:,.0f} + Contingency INR {contingency_amount:,.0f} = INR {total:,.0f}.**")
        st.subheader("Budget health")
        usage = total / budget
        health = "Excellent" if usage <= .75 else "Good" if usage <= .9 else "Average" if usage <= 1 else "High Risk"
        st.progress(min(1.0, usage), text=f"{health}: {usage * 100:.0f}% of available budget used")
        if status == "Over Budget":
            st.error(f"Your estimated project total is INR {total:,.0f}, which is INR {difference:,.0f} more than your INR {budget:,.0f} budget.")
        else:
            st.success(f"Your estimated project total is INR {total:,.0f}, leaving INR {difference:,.0f} within your INR {budget:,.0f} budget.")
        st.subheader("Why this estimate?")
        for reason in result.get("reasons", []):
            st.write(f"- {reason}")
        st.caption("**Why is contingency included?** Renovation costs can change because of hidden repairs, material price changes or extra work. A 10% reserve is automatically kept aside so the budget is safer and more realistic.\n\nThis estimate is generated for preliminary renovation planning. Actual costs may vary based on site conditions, local market prices, contractor charges, and material availability.")
        st.info("Open Cost Breakdown, Transportation, Material Comparison and AI Suggestions from the sidebar for the detailed planning views.")
    elif section == "costs":
        st.title("Detailed cost breakdown")
        st.caption("Every estimate is separated into materials, labour, transport and statutory charges so you can review the plan before speaking with a contractor.")

        category_notes = {
            "Core Renovation Cost": "Physical material quantities calculated from work area, requirement and wastage",
            "Labour Cost": "Skilled workers, helpers and finishing work",
            "Transportation Cost": "Fuel for the supplier-to-site route plus loading and unloading",
            "Additional Charges": "Estimated taxes and additional project charges",
            "Contingency (10%)": "10% safety reserve on the full base estimate for unexpected renovation costs",
        }
        frame = pd.DataFrame(result["breakdown"].items(), columns=["Cost category", "Amount (INR)"])
        frame["Share of total"] = frame["Amount (INR)"].div(total).map(lambda amount: f"{amount:.1%}")
        frame["What this includes"] = frame["Cost category"].map(category_notes)
        st.subheader("Project cost summary")
        st.dataframe(
            frame.style.format({"Amount (INR)": "INR {:,.0f}"}),
            hide_index=True,
            width='stretch',
        )

        st.subheader("Material-wise estimate")
        st.caption(
            f"Only materials required for **{project['renovation']}** are included. "
            f"The displayed rate is the same planning rate used to calculate quantity and cost at your selected **{project['material']}** quality."
        )
        materials = pd.DataFrame(result["material_detail"]).copy()
        materials = materials[[
            "Material", "Why included", "Recommended brand / company",
            "Base quantity", "Wastage", "Estimated quantity", "Unit", "Reference market rate",
            "Estimated material cost (INR)"
        ]]
        st.dataframe(
            materials.style.format({"Base quantity": "{:,.1f}", "Estimated quantity": "{:,.1f}", "Estimated material cost (INR)": "INR {:,.0f}"}),
            hide_index=True,
            width='stretch',
        )

        st.subheader("Labour and site work")
        st.caption("This is a planning allocation of the AI-estimated labour amount; final contractor quotes may split these items differently.")
        labour_rows = pd.DataFrame([
            ("Skilled trade work", "Masonry, plumbing, electrical or finishing specialists", round(result["labour_cost"] * .55)),
            ("General site labour", "Helpers, preparation, cleaning and material handling", round(result["labour_cost"] * .30)),
            ("Final inspection and completion", "Site coordination, quality check and work completion before the contractor leaves", result["labour_cost"] - round(result["labour_cost"] * .55) - round(result["labour_cost"] * .30)),
        ], columns=["Labour section", "What this includes", "Amount (INR)"])
        st.dataframe(labour_rows.style.format({"Amount (INR)": "INR {:,.0f}"}), hide_index=True, width='stretch')

        st.subheader("Transport and statutory charges")
        logistics_rows = pd.DataFrame([
            ("Transportation", f"{result['logistics']['From']} → {result['logistics']['To']} · {result['logistics']['Recommended vehicle']} · {result['logistics']['Estimated delivery distance (km)']} km planning route", result["logistics"]["Transportation cost"]),
            ("Additional Charges", "Estimated taxes and additional project charges", result["breakdown"]["Additional Charges"]),
        ], columns=["Charge", "What this includes", "Amount (INR)"])
        st.dataframe(logistics_rows.style.format({"Amount (INR)": "INR {:,.0f}"}), hide_index=True, width='stretch')

        with st.expander("View cost chart", expanded=False):
            chart = px.bar(
                frame,
                x="Cost category",
                y="Amount (INR)",
                color="Cost category",
                text_auto=".2s",
                color_discrete_sequence=["#5b8def", "#6ec6a4", "#f3aa65", "#d984b5", "#8b9bb4", "#a58be0"],
            )
            chart.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=20, b=10))
            chart.update_xaxes(title=None, tickangle=-20)
            chart.update_yaxes(title="Amount (INR)", gridcolor="#dfe6f1")
            st.plotly_chart(chart, width='stretch')
    elif section == "transportation":
        st.title("Transportation cost")
        st.caption("A clear logistics estimate from the confirmed material supplier (**FROM**) to the confirmed work-site (**TO**), using road distance, predicted material load and a suitable vehicle.")
        logistics = result["logistics"]
        a, b, c = st.columns(3)
        a.metric("📍 Region", logistics.get("Region type", project["region"]))
        b.metric("🚚 Recommended vehicle", logistics["Recommended vehicle"])
        c.metric("📦 Estimated material load", f"{logistics['Estimated load weight (kg)']:,} kg")
        st.subheader("Transportation breakdown")
        logistics_rows = pd.DataFrame([
            ("📍 Distance", f"{logistics['Estimated delivery distance (km)']:.1f} km"),
            ("🚚 Vehicle type", logistics["Recommended vehicle"]),
            ("⛽ Mileage", f"{logistics['Mileage (km/litre)']} km/litre"),
            ("⛽ Fuel price", f"INR {logistics['Fuel price (INR/litre)']:.0f}/litre"),
            ("📦 Load", f"{logistics['Estimated load weight (kg)']:,} kg"),
            ("⛽ Fuel: distance ÷ mileage × fuel price", logistics["Fuel cost"]),
            ("📦 Loading & unloading", logistics.get("Loading & unloading", logistics["Transportation cost"] - round(logistics["Transportation cost"] * .55) - round(logistics["Transportation cost"] * .37))),
            ("💰 Total transportation cost", logistics["Transportation cost"]),
        ], columns=["Item", "Amount / detail"])
        st.dataframe(logistics_rows, hide_index=True, width='stretch')
        st.info(
            f"**FROM:** {logistics['From']}  →  **TO:** {logistics['To']}  ·  "
            f"**{logistics['Estimated delivery distance (km)']:.1f} km**  ·  "
            f"**{logistics.get('Estimated travel time (min)', 0):.0f} min**\n\n"
            f"Route source: {logistics.get('Route source', 'Planning route')}"
        )
        st.subheader("Supplier → Work-Site route")
        try:
            import folium
            from streamlit_folium import st_folium
            supplier_lat, supplier_lon = logistics.get("Supplier latitude"), logistics.get("Supplier longitude")
            work_lat, work_lon = logistics.get("Work-site latitude"), logistics.get("Work-site longitude")
            if None not in (supplier_lat, supplier_lon, work_lat, work_lon):
                route_map = folium.Map(
                    location=[(supplier_lat + work_lat) / 2, (supplier_lon + work_lon) / 2],
                    zoom_start=12, control_scale=True,
                )
                folium.Marker(
                    [supplier_lat, supplier_lon], tooltip="FROM: Material supplier",
                    icon=folium.Icon(color="green", icon="shopping-cart", prefix="fa"),
                ).add_to(route_map)
                folium.Marker(
                    [work_lat, work_lon], tooltip="TO: Work-site",
                    icon=folium.Icon(color="red", icon="home", prefix="fa"),
                ).add_to(route_map)
                geometry = logistics.get("Route geometry")
                if geometry and geometry.get("coordinates"):
                    points = [[lat, lon] for lon, lat in geometry["coordinates"]]
                    folium.PolyLine(points, weight=4, opacity=0.8).add_to(route_map)
                else:
                    folium.PolyLine([[supplier_lat, supplier_lon], [work_lat, work_lon]], weight=3, opacity=0.7, dash_array="8, 8").add_to(route_map)
                st_folium(route_map, height=360, width='stretch', key="transport_route_map")
        except ImportError:
            st.caption("Route map requires folium and streamlit-folium.")

        with st.expander("How the material load is calculated"):
            load_rows = pd.DataFrame([
                {
                    "Material": item["Material"],
                    "Estimated quantity": f"{item['Estimated quantity']:,.1f} {item['Unit']}",
                    "Standard weight basis": f"{MATERIAL_WEIGHT_KG[item['Material']]:g} kg per unit",
                    "Calculated load (kg)": item["Estimated weight (kg)"],
                }
                for item in result["material_detail"]
            ])
            st.dataframe(load_rows.style.format({"Calculated load (kg)": "{:,.0f}"}), hide_index=True, width='stretch')
            st.caption("Total material load = the sum of each estimated quantity multiplied by its standard planning weight. This total determines the recommended vehicle and fuel allowance.")
        st.caption("This is a planning estimate; final supplier and vehicle charges can vary by route and local availability.")
    elif section == "material_prices":
        st.title("Material and price estimate")
        st.caption("These are planning estimates generated after the AI prediction. They show what to discuss with a contractor or supplier—not fields you need to fill in.")
        price_rows = []
        for item in result["material_detail"]:
            name = item["Material"]
            price_rows.append({**item, "Planning rate": item.get("Reference market rate", "—")})
        st.dataframe(pd.DataFrame(price_rows).style.format({"Estimated material cost (INR)": "{:,.0f}", "Estimated quantity": "{:,.1f}", "Estimated weight (kg)": "{:,.0f}"}), hide_index=True, width='stretch')
        st.info("Useful next step: show this table to two local suppliers, compare their quotations, then use Material Comparison to choose the best value option.")
    elif section == "materials":
        st.title("Material comparison")
        show_comparison(project["material"], status, difference, relevant_materials)
    elif section == "smart_materials":
        st.title("Recommended materials")
        show_recommendation(project["material"], status, difference, result["material_detail"])
    elif section == "recommendations":
        st.title("AI planning suggestions")
        priority = "Urgent" if project.get("roof", 10) <= 4 or project.get("plumbing", 10) <= 4 else "Planned"
        st.subheader("Renovation priority")
        st.write(f"**{project['renovation']} — {priority}**  {'★★★★★' if priority == 'Urgent' else '★★★☆☆'}")
        for action, reason in tips:
            st.markdown(f"- **{action}**  \n  _Why:_ {reason}")
        st.subheader("Suggested project timeline")
        timeline_templates = {
            "Painting": [("Phase 1", "Surface inspection, cleaning and crack repair"), ("Phase 2", "Primer and first coat"), ("Phase 3", "Final coats, drying and inspection")],
            "Electrical Work": [("Phase 1", "Electrical inspection and planning"), ("Phase 2", "Wiring, protection devices and fixtures"), ("Phase 3", "Testing, safety checks and handover")],
            "Plumbing": [("Phase 1", "Leak inspection and service layout"), ("Phase 2", "Pipe, fitting and fixture work"), ("Phase 3", "Pressure testing and finishing")],
            "Kitchen Renovation": [("Phase 1", "Removal, layout and plumbing preparation"), ("Phase 2", "Cabinets, surfaces and service work"), ("Phase 3", "Fixtures, appliances and final finishing")],
            "Bathroom Renovation": [("Phase 1", "Demolition and waterproofing preparation"), ("Phase 2", "Plumbing, tiling and fittings"), ("Phase 3", "Water testing and final finishing")],
            "Flooring & Tiling": [("Phase 1", "Subfloor preparation and levelling"), ("Phase 2", "Tile/floor installation"), ("Phase 3", "Grouting, curing and inspection")],
            "Roofing": [("Phase 1", "Roof inspection and damaged-area removal"), ("Phase 2", "Repair, waterproofing and roof work"), ("Phase 3", "Leak test and final inspection")],
            "Exterior Renovation": [("Phase 1", "Surface repair and preparation"), ("Phase 2", "Waterproofing and exterior finishing"), ("Phase 3", "Curing, touch-ups and inspection")],
            "Interior Renovation": [("Phase 1", "Planning and site preparation"), ("Phase 2", "Services, finishes and renovation work"), ("Phase 3", "Fittings, cleaning and final inspection")],
            "Full House Renovation": [("Phase 1", "Survey, demolition and structural preparation"), ("Phase 2", "Services and core renovation work"), ("Phase 3", "Finishes, fittings and final inspection")],
        }
        timeline = pd.DataFrame(timeline_templates.get(project["renovation"], timeline_templates["Full House Renovation"]), columns=["Period", "Activity"])
        st.dataframe(timeline, hide_index=True, width='stretch')
        st.subheader("Maintenance planning")
        maintenance_rates = {
            "Painting": (0.015, "Paint and surface touch-ups are typically recurring."),
            "Flooring & Tiling": (0.012, "Routine cleaning, grout care and occasional tile replacement are the main needs."),
            "Electrical Work": (0.020, "Periodic checks, switches, fixtures and minor electrical replacements may be needed."),
            "Plumbing": (0.025, "Leak checks, fittings, seals and minor pipe repairs can recur over time."),
            "Bathroom Renovation": (0.030, "Bathroom fittings, seals, grout and waterproofing-related upkeep need regular attention."),
            "Kitchen Renovation": (0.028, "Cabinet hardware, plumbing fixtures, countertop care and fittings may need upkeep."),
            "Roofing": (0.035, "Roof inspections, waterproofing touch-ups and weather-related repairs can be significant."),
            "Exterior Renovation": (0.025, "Exterior paint, waterproofing and weather exposure create recurring maintenance."),
            "Interior Renovation": (0.018, "Interior finishes, fittings and minor repairs usually need moderate upkeep."),
            "Full House Renovation": (0.025, "A whole-house renovation covers multiple systems, so a moderate maintenance reserve is used."),
        }
        rate, reason = maintenance_rates.get(project["renovation"], (0.025, "A moderate maintenance reserve is used for planning."))
        maintenance = max(5_000, round(result["total"] * rate))
        m1, m2 = st.columns(2)
        m1.metric("Estimated annual maintenance", f"INR {maintenance:,.0f}", f"{rate:.1%} of estimated budget")
        m2.metric("Renovation type", project["renovation"])
        st.caption(f"**Why this rate?** {reason} This is a planning reserve, not a guaranteed yearly expense. Actual maintenance depends on usage, material quality, age and site conditions.")
        st.caption("Material-specific service-life ranges are shown in the Recommended Materials table.")
    elif section == "report":
        report = {"User": st.session_state.username, "House Details": f"{project['area']:,.0f} sq ft", "Renovation Type": project["renovation"], "Location": f"{project['city']}, {project['state']}", "Available Budget": budget, "Renovation Cost": result["renovation_cost"], "Labour Cost": result["labour_cost"], "Transportation Cost": result["logistics"]["Transportation cost"], "Total Cost": total, "Estimated Duration (Days)": result["duration"], "Budget Status": status}
        pdf = create_project_pdf(report, result["breakdown"], status, difference, suggested_quality(project["material"], status, difference), tips)
        st.title("Professional PDF report")
        st.download_button("Download PDF report", pdf, "renovation_plan_report.pdf", "application/pdf", type="primary")
