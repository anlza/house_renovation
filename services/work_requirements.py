"""Work-specific input definitions used by the renovation form."""

# (label, field, widget type, values/default). Fields are optional details; the
# existing work-area question remains the mandatory starting measurement.
WORK_INPUTS = {
    "Painting": [("Areas included", "painting_surfaces", "multi", ["Walls", "Ceiling", "Exterior wall"]), ("Surface condition", "surface_condition", "select", ["Good", "Minor cracks", "Major repair"])],
    "Flooring & Tiling": [("Floor repair needed", "floor_repair", "select", ["No", "Minor", "Major"])],
    "Plumbing": [("Plumbing work", "plumbing_work", "multi", ["Leakage repair", "Pipe replacement", "Bathroom plumbing", "Kitchen plumbing", "Drainage repair", "Water tank connection"]), ("Pipe length required (metres)", "pipe_length_m", "number", 0), ("Pipe type", "pipe_type", "select", ["PVC", "CPVC"]), ("Number of connections", "pipe_connections", "number", 0), ("Number of leakage points", "leakage_points", "number", 0)],
    "Electrical Work": [("Electrical work", "electrical_work", "multi", ["Complete rewiring", "New switches", "New socket points", "Lighting", "Fan points", "Distribution board"]), ("Rewiring cable length (metres)", "rewiring_length_m", "number", 0), ("Switch points", "switch_points", "number", 0), ("Socket points", "socket_points", "number", 0), ("Light points", "light_points", "number", 0), ("Fan points", "fan_points", "number", 0)],
    "Kitchen Renovation": [("Kitchen work included", "kitchen_work", "multi", ["Cabinet work", "Countertop", "Sink", "Plumbing", "Electrical", "Backsplash"])],
    "Bathroom Renovation": [("Bathroom work included", "bathroom_work", "multi", ["Floor tiles", "Wall tiles", "Toilet", "Wash basin", "Shower", "Plumbing", "Waterproofing"]), ("Wall-tile area (sq ft)", "bathroom_wall_tile_area", "number", 0)],
    "Roofing": [("Roof work", "roof_work", "multi", ["Crack repair", "Leakage repair", "Tile replacement", "Concrete repair", "Complete roof replacement"]), ("Roof type", "roof_type", "select", ["Concrete", "Tile", "Metal sheet"])],
    "Interior Renovation": [("Interior work included", "interior_work", "multi", ["Flooring", "Painting", "Carpentry", "Plumbing", "Electrical"]), ("Wardrobe / storage area (sq ft)", "carpentry_area", "number", 0)],
    "Exterior Renovation": [("Exterior work included", "exterior_work", "multi", ["Crack repair", "Plaster repair", "Painting", "Waterproofing"]), ("Crack / plaster repair area (sq ft)", "exterior_repair_area", "number", 0)],
}

FULL_COMPONENT_TO_WORK = {"Wall / structural repair": "Exterior Renovation", "Roofing": "Roofing", "Plumbing": "Plumbing", "Electrical work": "Electrical Work", "Flooring & tiling": "Flooring & Tiling", "Painting": "Painting", "Kitchen": "Kitchen Renovation", "Bathroom": "Bathroom Renovation", "Exterior work": "Exterior Renovation"}

def fields_for(renovation): return WORK_INPUTS.get(renovation, [])
