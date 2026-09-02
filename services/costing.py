"""Transparent, non-ML estimates for renovation operational expenses.

This module contains deterministic business rules only.
ML predictions should provide the core renovation and labour estimates.
If the application calculates actual route-based transportation separately,
pass that value through ``transportation_override`` to avoid double counting.
"""

from __future__ import annotations

from typing import Mapping, Optional


def _safe_factor(mapping: Mapping, key, default: float = 1.0) -> float:
    """Return a numeric multiplier without failing on an unknown category."""
    try:
        value = mapping.get(key, default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def operational_costs(
    renovation_cost: float,
    area: float,
    state: str,
    region: str,
    season: str,
    renovation_type: str,
    transportation_override: Optional[float] = None,
):
    """Return deterministic operational estimates in INR.

    ``transportation_override`` should be used when the main application has
    already calculated transportation from an actual road route, vehicle type,
    fuel, and loading/unloading. This prevents transportation from being
    calculated twice.
    """
    from config import REGION_MULTIPLIER, SEASON_MULTIPLIER, STATE_MULTIPLIERS

    renovation_cost = max(0.0, float(renovation_cost))
    area = max(0.0, float(area))

    state_data = STATE_MULTIPLIERS.get(state, {})
    state_factor = _safe_factor(state_data, "material", 1.0)
    region_factor = _safe_factor(REGION_MULTIPLIER, region, 1.0)

    season_data = SEASON_MULTIPLIER.get(season, {})
    season_factor = _safe_factor(season_data, "cost", 1.0)

    renovation_name = str(renovation_type or "").strip().lower()
    complexity = 1.25 if renovation_name in {"full", "roofing"} else 1.0

    if transportation_override is None:
        # Legacy fallback for callers that do not yet have route-based
        # transportation. New prediction flow should pass the actual route cost.
        transportation = max(
            3_000.0,
            renovation_cost * 0.035 * state_factor * region_factor,
        )
    else:
        transportation = max(0.0, float(transportation_override))

    equipment = max(
        2_000.0,
        area * 14.0 * complexity * season_factor,
    )
    miscellaneous = max(
        2_500.0,
        (renovation_cost + equipment) * 0.025,
    )

    return {
        "transportation": round(transportation),
        "equipment": round(equipment),
        "miscellaneous": round(miscellaneous),
    }


def build_breakdown(
    renovation_cost: float,
    labour_cost: float,
    operational: Mapping[str, float],
):
    """Build the single displayed cost breakdown and total.

    All negative values are clamped to zero so a failed/invalid intermediate
    calculation cannot produce a negative project total.
    """
    breakdown = {
        "Renovation / materials": round(max(0.0, float(renovation_cost))),
        "Labour": round(max(0.0, float(labour_cost))),
        "Transportation": round(max(0.0, float(operational.get("transportation", 0)))),
        "Equipment": round(max(0.0, float(operational.get("equipment", 0)))),
        "Miscellaneous": round(max(0.0, float(operational.get("miscellaneous", 0)))),
    }

    total = sum(breakdown.values())
    return breakdown, total