"""Measurement, length and point based material quantity calculator."""
from collections import defaultdict

WASTE = .10
def _n(project, key, default=0):
    try: return max(0.0, float(project.get(key, default) or default))
    except (TypeError, ValueError): return default
def _selected(project, key, default=()): return set(project.get(key) or default)
def _add(lines, material, quantity, unit, why, wastage=WASTE):
    if quantity > 0: lines.append({"Material": material, "Base quantity": quantity, "Wastage rate": wastage, "Estimated quantity": quantity*(1+wastage), "Unit": unit, "Why included": why})

def _for_type(project, renovation, area):
    lines=[]
    if renovation == "Painting":
        coats=max(1,_n(project,"coats",2));
        measured=_n(project,"painting_wall_area")+_n(project,"painting_ceiling_area")+_n(project,"painting_exterior_area")
        paint_area=measured or area
        # Coverage: 100 sq ft/litre/coat; primer and putty depend on condition.
        _add(lines,"Paint",paint_area*coats/100,"litre",f"{paint_area:.0f} sq ft × {coats} coats ÷ 100 sq ft/litre")
        _add(lines,"Primer",paint_area/130,"litre","Primer coverage: 130 sq ft/litre")
        if project.get("surface_condition") in {"Minor cracks","Major repair"}: _add(lines,"Putty",paint_area*(.08 if project.get("surface_condition")=="Minor cracks" else .18),"kg","Surface repair allowance")
    elif renovation == "Flooring & Tiling":
        works=_selected(project,"flooring_work")
        floor_area=_n(project,"flooring_work_area")
        if works & {"New flooring / tile installation", "Floor replacement"}:
            label = "new flooring" if "New flooring / tile installation" in works else "floor replacement"
            _add(lines,"Tiles",floor_area,"sq ft",f"Measured {label} area")
            _add(lines,"Tile Adhesive",floor_area*.30,"kg","0.30 kg adhesive per sq ft")
        if "Floor repair" in works:
            _add(lines,"Cement",floor_area*(.05 if project.get("floor_repair")=="Minor" else .12),"50 kg bag","Measured floor repair area")
    elif renovation == "Plumbing":
        works=_selected(project,"plumbing_work"); location=_selected(project,"plumbing_location"); fixtures=_selected(project,"plumbing_fixtures")
        # Pipe and fitting quantities are planning allowances derived from the
        # selected scope/location. The homeowner does not need contractor-level
        # metre/connection measurements.
        location_factor = 1.0
        if "Whole House" in location: location_factor = 1.8
        elif "Multiple Areas" in location: location_factor = 1.4
        elif "Kitchen" in location or "Bathroom" in location: location_factor = 0.9
        if works & {"Pipe replacement", "New pipe installation", "Drainage work", "Water tank connection"}:
            pipe_qty = _n(project,"plumbing_pipe_length_m") or max(6.0, min(60.0, area * 0.10 * location_factor))
            _add(lines,"PVC/CPVC Pipes",pipe_qty,"metre","Planning allowance based on selected plumbing scope")
            fitting_qty = max(4.0, round(pipe_qty / 2.0))
            _add(lines,"Plumbing Fittings",fitting_qty,"set","Estimated fittings for the selected pipe work")
        if "Leakage repair" in works:
            _add(lines,"Plumbing Fittings",_n(project,"plumbing_leak_count"),"repair set","Selected leak points",.05)
        if "Fixture replacement" in works:
            fixture_count = sum(_n(project,k) for k in ("plumbing_toilet_count","plumbing_basin_count","plumbing_shower_count","plumbing_tap_count"))
            _add(lines,"Sanitary Fixtures",fixture_count,"set","Selected plumbing fixtures",0)
        if "Water tank connection" in works:
            _add(lines,"PVC/CPVC Pipes",_n(project,"plumbing_tank_count") * 4.0,"metre","Water-tank connection allowance")
    elif renovation == "Electrical Work":
        works=_selected(project,"electrical_work"); areas=_selected(project,"electrical_areas")
        # Estimate points/cable from selected work and affected areas rather than
        # asking the homeowner to count every socket or metre of cable.
        area_factor=max(1, len(areas))
        if "Complete rewiring" in works:
            _add(lines,"Electrical Cable",_n(project,"electrical_cable_length_m") or max(15.0, area*0.65*area_factor),"metre","Measured/estimated cable length for selected rewiring scope")
        point_base=max(1, int(round(_n(project,"switch_points") or 4*area_factor)))
        if "New switches" in works: _add(lines,"Switches & Sockets",point_base,"point","Estimated switch points from affected areas",.03)
        if "New socket points" in works: _add(lines,"Switches & Sockets",max(1, int(round(_n(project,"socket_points") or point_base))),"point","Estimated socket points from affected areas",.03)
        if "Lighting" in works: _add(lines,"Electrical Cable",max(5.0, _n(project,"light_points")*5 if _n(project,"light_points") else area*0.08*area_factor),"metre","Estimated lighting cable allowance")
        if "Fan points" in works: _add(lines,"Electrical Cable",max(5.0, _n(project,"fan_points")*5 if _n(project,"fan_points") else 5*area_factor),"metre","Estimated fan-point cable allowance")
        if "Distribution board" in works: _add(lines,"MCB & Conduit",_n(project,"distribution_board_count"),"point","Selected distribution boards",0)
    elif renovation == "Kitchen Renovation":
        works=_selected(project,"kitchen_work"); cupboards=_n(project,"additional_cupboards")
        if "Cabinet work" in works: _add(lines,"Wood",cupboards*18,"sq ft","Measured cabinet replacement/addition units")
        if "Countertop" in works: _add(lines,"Countertop",_n(project,"additional_countertop_area"),"sq ft","Measured countertop replacement/addition area")
        if "Backsplash" in works: _add(lines,"Tiles",_n(project,"kitchen_backsplash_area"),"sq ft","Measured backsplash area")
        if "Sink" in works: _add(lines,"Sanitary Fixtures",_n(project,"kitchen_sink_count"),"set","Selected kitchen sinks",0)
        if "Plumbing" in works: _add(lines,"PVC/CPVC Pipes",max(3.0,_n(project,"kitchen_plumbing_points")*3),"metre","Kitchen plumbing points")
        if "Electrical" in works: _add(lines,"Electrical Cable",max(3.0,_n(project,"kitchen_electrical_points")*5),"metre","Kitchen electrical points")
    elif renovation == "Bathroom Renovation":
        works=_selected(project,"bathroom_work"); floor_area=_n(project,"bathroom_floor_area"); wall=_n(project,"bathroom_wall_tile_area")
        if "Floor tiles" in works: _add(lines,"Tiles",floor_area,"sq ft","Measured bathroom floor area")
        if "Wall tiles" in works: _add(lines,"Tiles",wall,"sq ft","Measured bathroom wall-tile area")
        if works & {"Floor tiles", "Wall tiles"}:
            adhesive_area = (floor_area if "Floor tiles" in works else 0) + (wall if "Wall tiles" in works else 0)
            _add(lines, "Tile Adhesive", adhesive_area*.30, "kg", "0.30 kg adhesive per sq ft of selected tiled area")
        if "Waterproofing" in works: _add(lines,"Waterproofing",_n(project,"bathroom_waterproof_area"),"sq ft","Measured bathroom waterproofing area")
        if "Plumbing" in works: _add(lines,"PVC/CPVC Pipes",_n(project,"bathroom_pipe_length_m"),"metre","Measured bathroom pipe run")
        for fixture,key in (("Toilet","bathroom_toilet_count"),("Wash basin","bathroom_basin_count"),("Shower","bathroom_shower_count")):
            if fixture in works: _add(lines,"Sanitary Fixtures",_n(project,key),"set",fixture,0)
    elif renovation == "Roofing":
        works=_selected(project,"roof_work"); roof_type=project.get("roof_type","Concrete")
        repair_area=_n(project,"roof_concrete_repair_area")
        if "Crack repair" in works: _add(lines,"Cement",_n(project,"roof_work_area")*.12,"50 kg bag","Measured roof crack-repair area")
        if "Concrete repair" in works: _add(lines,"Cement",repair_area*.12,"50 kg bag","Measured roof concrete repair area")
        if "Complete roof replacement" in works:
            _add(lines,"Cement",_n(project,"roof_work_area")*.12,"50 kg bag","Measured roof replacement area")
            _add(lines,"Steel",_n(project,"roof_work_area")*.35,"kg","Measured roof structural replacement area")
        if "Leakage repair" in works: _add(lines,"Waterproofing",_n(project,"roof_waterproof_area"),"sq ft","Measured roof waterproofing area")
        if "Complete roof replacement" in works: _add(lines,"Waterproofing",_n(project,"roof_waterproof_area"),"sq ft","Measured roof waterproofing area")
        if "Tile replacement" in works and roof_type=="Tile": _add(lines,"Tiles",_n(project,"roof_tile_replacement_area"),"sq ft","Measured replacement roof tile area")
    elif renovation == "Interior Renovation":
        works=_selected(project,"interior_work")
        if "False ceiling" in works: _add(lines,"Wood",_n(project,"false_ceiling_area")*.08,"sq ft","False ceiling support allowance")
        if "Flooring" in works: _add(lines,"Tiles",_n(project,"interior_flooring_area") or area*.35,"sq ft","Measured interior flooring area")
        if "Painting" in works: _add(lines,"Paint",(_n(project,"interior_painting_area") or area*.65)*2/100,"litre","Measured interior painting area")
        if "Wardrobe / Storage" in works or "Carpentry / Other interior work" in works:
            carp=_n(project,"wardrobe_count")
            _add(lines,"Wood",max(18.0*carp, area*.12 if not carp else 0),"sq ft","Wardrobe/storage planning allowance")
        if "Wall work" in works or "Partition" in works: _add(lines,"Cement",(_n(project,"partition_area") or area*.04)*.04,"50 kg bag","Measured interior wall/partition repair allowance")
        if "Plumbing" in works: _add(lines,"PVC/CPVC Pipes",10,"metre","Interior plumbing changes")
        if "Electrical" in works: _add(lines,"Electrical Cable",area*.10,"metre","Interior electrical changes")
    else: # Exterior renovation
        works=_selected(project,"exterior_work",["Painting","Waterproofing"])
        repair=_n(project,"exterior_repair_area")
        if works & {"Crack repair","Plaster repair"}:
            _add(lines,"Cement",repair*.10,"50 kg bag","Measured exterior repair / plaster area")
            _add(lines,"Sand",repair*.18,"kg","Repair mortar allowance for exterior work")
        if "Painting" in works:
            paint_area=_n(project,"exterior_painting_area") or area
            _add(lines,"Paint",paint_area*2/100,"litre","Measured exterior painting area × 2 coats")
            _add(lines,"Primer",paint_area/130,"litre","Primer coverage: 130 sq ft/litre")
        if "Waterproofing" in works:
            waterproof_area=_n(project,"exterior_waterproof_area") or area
            _add(lines,"Waterproofing",waterproof_area,"sq ft","Measured exterior waterproofing area")
        if "Compound wall / Gate" in works:
            length=_n(project,"compound_wall_gate_length_ft")
            # Planning allowance for compound-wall/gate construction along the
            # selected linear work length. Keep it separate from house-area scope.
            _add(lines,"Cement",length*.20,"50 kg bag","Compound wall / gate construction allowance")
            _add(lines,"Sand",length*.35,"kg","Compound wall / gate mortar allowance")
            _add(lines,"Brick",length*8,"unit","Compound wall masonry allowance")
            _add(lines,"Steel",length*.35,"kg","Gate / structural reinforcement allowance")
    return lines

def _full_structural_lines(project, area):
    """Calculate materials for the explicit Full House structural-repair scope."""
    lines=[]
    repair=_n(project,"exterior_repair_area") or area
    _add(lines,"Cement",repair*.12,"50 kg bag","Measured wall / structural repair area")
    _add(lines,"Steel",repair*.35,"kg","Structural reinforcement allowance")
    _add(lines,"Sand",repair*.25,"kg","Repair mortar allowance")
    _add(lines,"Brick",repair*2.5,"unit","Masonry repair allowance")
    return lines


def calculate_materials(project):
    area=max(1,_n(project,"work_area",project.get("area",1))); renovation=project.get("renovation")
    if renovation != "Full House Renovation": return _for_type(project,renovation,area)
    mapping={"Wall / structural repair":"Exterior Renovation","Roofing":"Roofing","Plumbing":"Plumbing","Electrical work":"Electrical Work","Flooring & tiling":"Flooring & Tiling","Painting":"Painting","Kitchen":"Kitchen Renovation","Bathroom":"Bathroom Renovation","Exterior work":"Exterior Renovation"}
    # Full-house mode is still quantity based. Each selected component reuses
    # the measurements entered for that component instead of assigning an
    # arbitrary percentage of the total house area.
    all_lines=[]
    component_area_defaults={
        "Wall / structural repair": _n(project, "exterior_repair_area"),
        "Roofing": _n(project, "roof_work_area"),
        "Plumbing": area,
        "Electrical work": area,
        "Flooring & tiling": _n(project, "flooring_work_area"),
        "Painting": _n(project, "painting_wall_area") + _n(project, "painting_ceiling_area") + _n(project, "painting_exterior_area"),
        "Kitchen": _n(project, "work_area"),
        "Bathroom": _n(project, "work_area"),
        "Exterior work": _n(project, "exterior_repair_area") + _n(project, "exterior_painting_area") + _n(project, "exterior_waterproof_area"),
    }
    for component in project.get("full_scope", []):
        mapped=mapping.get(component)
        if not mapped:
            continue
        component_area=component_area_defaults.get(component) or area
        if component == "Wall / structural repair":
            # Do not route structural repair through Exterior Renovation. That
            # would incorrectly default to paint/waterproofing.
            all_lines.extend(_full_structural_lines(project, component_area))
        else:
            all_lines.extend(_for_type(project, mapped, component_area))
    grouped=defaultdict(lambda:{"Base quantity":0,"Estimated quantity":0,"Wastage rate":WASTE,"Unit":"unit","Why included":[]})
    for line in all_lines:
        value=grouped[line["Material"]]; value["Base quantity"]+=line["Base quantity"]; value["Estimated quantity"]+=line["Estimated quantity"]; value["Unit"]=line["Unit"]; value["Why included"].append(line["Why included"])
    return [{"Material":k,**v,"Why included":"; ".join(v["Why included"])} for k,v in grouped.items()]
