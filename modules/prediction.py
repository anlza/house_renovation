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
from auth import get_prediction_history, save_prediction_history
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
VEHICLE_RATES = {"Mini truck": 18, "Pickup": 22, "Medium truck": 30, "Large truck": 40}
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


def _field(label, key, values):
    if isinstance(values, list):
        st.selectbox(label, values, index=None, placeholder="Select an option", key=key)
    else:
        st.number_input(label, min_value=values, value=None, step=1, placeholder="Enter a value", key=key)


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
    st.caption("Enter details of your existing house. These are the current values, not the values you want after renovation.")
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
        return fields

    fields = {key: f"req_{key}" for _, key, _ in REQUIREMENTS[renovation]}
    _restore(fields)
    st.caption("Work area means only the part of the house included in this renovation.")
    if renovation == "Kitchen Renovation":
        st.info("Existing kitchen items are recorded for context. Only new countertop and cupboard work is added to the renovation scope.")
    for label, key, values in REQUIREMENTS[renovation]:
        _field(label, fields[key], values)
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
        if st.button(f"✅ Confirm this {label.lower()}", key=confirm_key, type="primary", use_container_width=True):
            if is_work:
                _set_work_site(location)
            else:
                _set_material_site(location)
            st.rerun()
    with c2:
        if st.button("↩️ Choose again", key=cancel_key, use_container_width=True):
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
            use_container_width=True,
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
        search_clicked = st.button("Search", type="primary", use_container_width=True, key="work_exact_search_btn")

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
        if st.button("Use selected result", use_container_width=True, key="use_work_search_result"):
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
            use_container_width=True,
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
            if st.button("↻ Choose Again", use_container_width=True, key="choose_work_again"):
                _clear_pending_location("work")
                st.rerun()
        with right:
            if st.button("✓ Confirm this Work-Site", type="primary", use_container_width=True, key="confirm_work_exact"):
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
        search_clicked = st.button("Search", type="primary", use_container_width=True, key="supplier_exact_search_btn")

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
        if st.button("Use selected supplier result", use_container_width=True, key="use_material_search_result"):
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
            supplier_map, height=330, use_container_width=True,
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
            if st.button("↻ Choose Supplier Again", use_container_width=True, key="choose_supplier_again"):
                _clear_pending_location("material")
                st.rerun()
        with right:
            if st.button("✓ Confirm this Material Supplier", type="primary", use_container_width=True, key="confirm_supplier_exact"):
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
    st.info("Transportation cost will be calculated automatically from your region and the predicted material quantity and weight. You do not need to enter units, weight or vehicle details.")
    st.selectbox("Material quality", ["Economy", "Standard", "Premium"], index=None, placeholder="Select quality", key="material_quality")
    st.selectbox("Finish quality", list(QUALITY_FACTORS), index=None, placeholder="Select quality", key="finish_quality")
    st.selectbox("Work season", ["Summer", "Monsoon", "Winter"], index=None, placeholder="Select season", key="season")
    st.number_input("Available budget (INR)", min_value=1.0, value=None, step=1000.0, placeholder="Enter your budget", key="user_budget")
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
    renovation_cost = forecast["cost"] * scope_factor
    labour_cost = forecast["labour"] * scope_factor

    # Material shares distribute the already scoped AI estimate. They must not
    # be used as a second multiplier, otherwise selecting fewer material types
    # would incorrectly reduce the project cost twice.
    shares = _required_materials(project)

    material_detail = []
    total_weight = 0
    selected_material_quality = project["material"]

    # The same catalogue rate is used for quantity and displayed material cost.
    # This removes the previous inconsistency where a table could show one rate
    # but calculate cost using a different base rate.
    for name, share in shares.items():
        amount = renovation_cost * share
        rate, brand, rate_text, lifespan = _catalog_rate(name, selected_material_quality)
        quantity = amount / max(rate, 1)
        weight = quantity * MATERIAL_WEIGHT_KG.get(name, 1)
        total_weight += weight
        if project["renovation"] == "Full House Renovation":
            used_by = [component for component in project.get("full_scope", []) if name in FULL_SCOPE_PROFILES.get(component, {})]
            purpose = "Required for: " + ", ".join(used_by) if used_by else "Required renovation material"
        else:
            purpose = MATERIAL_PURPOSES.get(project["renovation"], {}).get(name, "Required renovation material")
        material_detail.append({
            "Material": name,
            "Why included": purpose,
            "Recommended brand / company": brand,
            "Estimated quantity": round(quantity, 1),
            "Unit": rate_text.split(" / ", 1)[-1] if " / " in rate_text else "unit",
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

    vehicle_cost = round(distance * VEHICLE_RATES[vehicle])
    fuel_cost = round(total_weight * 0.45)
    loading_unloading = round(max(250, (vehicle_cost + fuel_cost) * 0.08))
    transportation_cost = vehicle_cost + fuel_cost + loading_unloading

    additional_charges = round(
        (renovation_cost + labour_cost + transportation_cost) * 0.05
    )
    breakdown = {
        "Material cost": round(renovation_cost),
        "Labour cost": round(labour_cost),
        "Transportation cost": transportation_cost,
        "GST / additional charges": additional_charges,
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
        "Vehicle cost": vehicle_cost,
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
        f"Quality and timing: {project['material']} materials in {project['season']} season affect the planning estimate.",
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
        "renovation_cost": round(renovation_cost),
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
    st.title("Create a new estimate")
    st.caption("Choose the renovation first. Your exact work-site location later provides the state, city and region automatically.")

    # Step 1: renovation selection decides which requirements are shown next.
    if st.session_state.flow_step == 1:
        st.progress(1 / 5, text="Step 1 of 5 · Choose your renovation")
        st.subheader("🏠 What do you want to renovate?")
        st.caption("Choose the main renovation. The next form will show only questions relevant to this work.")
        current = st.session_state.project.get("renovation")
        idx = RENOVATION_OPTIONS.index(current) if current in RENOVATION_OPTIONS else None
        selected = st.selectbox("Renovation type", RENOVATION_OPTIONS, index=idx, placeholder="Select renovation type")
        if st.button("Continue →", type="primary", use_container_width=True):
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
        if st.button("← Back", use_container_width=True):
            st.session_state.flow_step -= 1
            st.rerun()

    with right:
        if st.session_state.flow_step < 5:
            if st.button("Continue →", type="primary", use_container_width=True):
                if st.session_state.flow_step == 4:
                    if _location_complete():
                        st.session_state.flow_step += 1
                        st.rerun()
                    else:
                        st.error("Please confirm both the exact work-site and the material supplier location before continuing.")
                elif st.session_state.flow_step == 3 and st.session_state.project.get("renovation") == "Full House Renovation" and not st.session_state.get("req_full_scope"):
                    st.error("Please select at least one part of the house that needs renovation.")
                elif _complete(fields):
                    st.session_state.flow_step += 1
                    st.rerun()
                else:
                    st.error("Please complete all required fields before continuing.")
        else:
            if st.button("🤖 Run AI prediction", type="primary", use_container_width=True):
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
    if section == "history":
        st.title("Prediction history")
        rows = get_prediction_history(st.session_state.username)
        if rows:
            st.dataframe(pd.DataFrame([{ "Date": x["date"], "Renovation type": x["renovation_type"], "Estimated cost": f"INR {x['estimated_cost']:,.0f}", "Budget status": x["budget_status"]} for x in rows]), hide_index=True, use_container_width=True)
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
        st.title("Final results dashboard")
        a, b, c = st.columns(3)
        a.metric("Estimated renovation cost", f"INR {result['renovation_cost']:,.0f}")
        b.metric("Labour cost", f"INR {result['labour_cost']:,.0f}")
        c.metric("Transportation cost", f"INR {result['logistics']['Transportation cost']:,.0f}")
        d, e, f = st.columns(3)
        d.metric("Total estimated cost", f"INR {result['total']:,.0f}")
        e.metric("Project duration", f"{result['duration']} days")
        f.metric("Budget status", status, f"INR {abs(difference):,.0f} {'remaining' if status == 'Within Budget' else 'over budget'}")
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
        st.caption("Materials and labour come from the AI estimate. Transportation uses the selected material-site to work-site road route and the predicted material load.")
        st.info("Open Cost Breakdown, Transportation, Material Comparison and AI Suggestions from the sidebar for the detailed planning views.")
    elif section == "costs":
        st.title("Detailed cost breakdown")
        st.caption("Every estimate is separated into materials, labour, transport and statutory charges so you can review the plan before speaking with a contractor.")

        category_notes = {
            "Material cost": "Core materials required for the selected renovation work",
            "Labour cost": "Skilled workers, helpers and finishing work",
            "Transportation cost": "Vehicle and estimated load movement to site",
            "GST / additional charges": "Estimated taxes and additional project charges",
        }
        frame = pd.DataFrame(result["breakdown"].items(), columns=["Cost category", "Amount (INR)"])
        frame["Share of total"] = frame["Amount (INR)"].div(total).map(lambda amount: f"{amount:.1%}")
        frame["What this includes"] = frame["Cost category"].map(category_notes)
        st.subheader("Project cost summary")
        st.dataframe(
            frame.style.format({"Amount (INR)": "INR {:,.0f}"}),
            hide_index=True,
            use_container_width=True,
        )

        st.subheader("Material-wise estimate")
        st.caption(
            f"Only materials required for **{project['renovation']}** are included. "
            f"The displayed rate is the same planning rate used to calculate quantity and cost at your selected **{project['material']}** quality."
        )
        materials = pd.DataFrame(result["material_detail"]).copy()
        materials = materials[[
            "Material", "Why included", "Recommended brand / company",
            "Estimated quantity", "Unit", "Reference market rate",
            "Estimated material cost (INR)"
        ]]
        st.dataframe(
            materials.style.format({"Estimated quantity": "{:,.1f}", "Estimated material cost (INR)": "INR {:,.0f}"}),
            hide_index=True,
            use_container_width=True,
        )

        st.subheader("Labour and site work")
        st.caption("This is a planning allocation of the AI-estimated labour amount; final contractor quotes may split these items differently.")
        labour_rows = pd.DataFrame([
            ("Skilled trade work", "Masonry, plumbing, electrical or finishing specialists", round(result["labour_cost"] * .55)),
            ("General site labour", "Helpers, preparation, cleaning and material handling", round(result["labour_cost"] * .30)),
            ("Final inspection and completion", "Site coordination, quality check and work completion before the contractor leaves", result["labour_cost"] - round(result["labour_cost"] * .55) - round(result["labour_cost"] * .30)),
        ], columns=["Labour section", "What this includes", "Amount (INR)"])
        st.dataframe(labour_rows.style.format({"Amount (INR)": "INR {:,.0f}"}), hide_index=True, use_container_width=True)

        st.subheader("Transport and statutory charges")
        logistics_rows = pd.DataFrame([
            ("Transportation", f"{result['logistics']['From']} → {result['logistics']['To']} · {result['logistics']['Recommended vehicle']} · {result['logistics']['Estimated delivery distance (km)']} km planning route", result["logistics"]["Transportation cost"]),
            ("GST / additional charges", "Estimated taxes and additional project charges", result["breakdown"]["GST / additional charges"]),
        ], columns=["Charge", "What this includes", "Amount (INR)"])
        st.dataframe(logistics_rows.style.format({"Amount (INR)": "INR {:,.0f}"}), hide_index=True, use_container_width=True)

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
            st.plotly_chart(chart, use_container_width=True)
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
            ("🚚 Vehicle cost", logistics.get("Vehicle cost", round(logistics["Transportation cost"] * .55))),
            ("⛽ Fuel cost", logistics.get("Fuel cost", round(logistics["Transportation cost"] * .37))),
            ("📦 Loading & unloading", logistics.get("Loading & unloading", logistics["Transportation cost"] - round(logistics["Transportation cost"] * .55) - round(logistics["Transportation cost"] * .37))),
            ("💰 Total transportation cost", logistics["Transportation cost"]),
            ("Total transport cost", logistics["Total logistics cost"]),
        ], columns=["Item", "Amount (INR)"])
        st.dataframe(logistics_rows.style.format({"Amount (INR)": "INR {:,.0f}"}), hide_index=True, use_container_width=True)
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
                st_folium(route_map, height=360, use_container_width=True, key="transport_route_map")
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
            st.dataframe(load_rows.style.format({"Calculated load (kg)": "{:,.0f}"}), hide_index=True, use_container_width=True)
            st.caption("Total material load = the sum of each estimated quantity multiplied by its standard planning weight. This total determines the recommended vehicle and fuel allowance.")
        st.caption("This is a planning estimate; final supplier and vehicle charges can vary by route and local availability.")
    elif section == "material_prices":
        st.title("Material and price estimate")
        st.caption("These are planning estimates generated after the AI prediction. They show what to discuss with a contractor or supplier—not fields you need to fill in.")
        price_rows = []
        for item in result["material_detail"]:
            name = item["Material"]
            price_rows.append({**item, "Planning rate": item.get("Reference market rate", "—")})
        st.dataframe(pd.DataFrame(price_rows).style.format({"Estimated material cost (INR)": "{:,.0f}", "Estimated quantity": "{:,.1f}", "Estimated weight (kg)": "{:,.0f}"}), hide_index=True, use_container_width=True)
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
        st.dataframe(timeline, hide_index=True, use_container_width=True)
        st.subheader("Maintenance planning")
        maintenance = max(5_000, round(result["total"] * .025))
        st.metric("Estimated annual maintenance reserve", f"INR {maintenance:,.0f}")
        st.caption("Material-specific service-life ranges are shown once in the Recommended Materials table to avoid conflicting duplicate lifespan values.")
    elif section == "report":
        report = {"User": st.session_state.username, "House Details": f"{project['area']:,.0f} sq ft", "Renovation Type": project["renovation"], "Location": f"{project['city']}, {project['state']}", "Available Budget": budget, "Renovation Cost": result["renovation_cost"], "Labour Cost": result["labour_cost"], "Transportation Cost": result["logistics"]["Transportation cost"], "Total Cost": total, "Estimated Duration (Days)": result["duration"], "Budget Status": status}
        pdf = create_project_pdf(report, result["breakdown"], status, difference, suggested_quality(project["material"], status, difference), tips)
        st.title("Professional PDF report")
        st.download_button("Download PDF report", pdf, "renovation_plan_report.pdf", "application/pdf", type="primary")