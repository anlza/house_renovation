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
        coats=max(1,_n(project,"coats",2)); paint_area=area
        # Coverage: 100 sq ft/litre/coat; primer and putty depend on condition.
        _add(lines,"Paint",paint_area*coats/100,"litre",f"{paint_area:.0f} sq ft × {coats} coats ÷ 100 sq ft/litre")
        _add(lines,"Primer",paint_area/130,"litre","Primer coverage: 130 sq ft/litre")
        if project.get("surface_condition") in {"Minor cracks","Major repair"}: _add(lines,"Putty",paint_area*(.08 if project.get("surface_condition")=="Minor cracks" else .18),"kg","Surface repair allowance")
    elif renovation == "Flooring & Tiling":
        _add(lines,"Tiles",area,"sq ft","Floor area")
        _add(lines,"Tile Adhesive",area*.30,"kg","0.30 kg adhesive per sq ft")
        if project.get("floor_repair") in {"Minor","Major"}: _add(lines,"Cement",area*(.05 if project.get("floor_repair")=="Minor" else .12),"50 kg bag","Floor repair")
    elif renovation == "Plumbing":
        works=_selected(project,"plumbing_work"); length=_n(project,"pipe_length_m"); connections=_n(project,"pipe_connections"); leaks=_n(project,"leakage_points")
        if works & {"Pipe replacement","Bathroom plumbing","Kitchen plumbing","Drainage repair","Water tank connection"}:
            _add(lines,"PVC/CPVC Pipes",length,"metre",f"Specified {length:.0f} m pipe run")
            _add(lines,"Plumbing Fittings",connections,"point",f"{connections:.0f} pipe connections")
        if "Leakage repair" in works: _add(lines,"Plumbing Fittings",leaks,"repair point","Leak repair fittings",.05)
        if "Bathroom plumbing" in works: _add(lines,"Sanitary Fixtures",1,"set","Bathroom fixture allowance",0)
    elif renovation == "Electrical Work":
        works=_selected(project,"electrical_work"); rewiring=_n(project,"rewiring_length_m"); sw=_n(project,"switch_points"); sockets=_n(project,"socket_points"); lights=_n(project,"light_points"); fans=_n(project,"fan_points")
        if "Complete rewiring" in works: _add(lines,"Electrical Cable",rewiring,"metre",f"Specified {rewiring:.0f} m rewiring length")
        _add(lines,"Switches & Sockets",sw+sockets,"point",f"{sw:.0f} switch + {sockets:.0f} socket points",.03)
        _add(lines,"Electrical Cable",(lights+fans)*5,"metre",f"5 m cable per {lights+fans:.0f} light/fan points")
        if "Distribution board" in works: _add(lines,"MCB & Conduit",1,"point","Distribution board",0)
        _add(lines,"MCB & Conduit",sw+sockets+lights+fans,"point","Protection/conduit per point",.03)
    elif renovation == "Kitchen Renovation":
        works=_selected(project,"kitchen_work",["Cabinet work","Countertop"]); counter=_n(project,"additional_countertop_area",area*.16); cupboards=_n(project,"additional_cupboards")
        if "Cabinet work" in works: _add(lines,"Wood",max(cupboards*18,area*.25),"sq ft","Cabinet panels")
        if "Countertop" in works: _add(lines,"Countertop",counter,"sq ft","New countertop area")
        if "Backsplash" in works: _add(lines,"Tiles",area*.20,"sq ft","Backsplash area")
        if "Sink" in works: _add(lines,"Sanitary Fixtures",1,"set","Kitchen sink",0)
        if "Plumbing" in works: _add(lines,"PVC/CPVC Pipes",8,"metre","Kitchen water/drain connection")
        if "Electrical" in works: _add(lines,"Electrical Cable",15,"metre","Kitchen electrical points")
    elif renovation == "Bathroom Renovation":
        works=_selected(project,"bathroom_work",["Floor tiles","Wall tiles","Plumbing","Waterproofing"]); wall=_n(project,"bathroom_wall_tile_area",area*2.5)
        if "Floor tiles" in works: _add(lines,"Tiles",area,"sq ft","Bathroom floor")
        if "Wall tiles" in works: _add(lines,"Tiles",wall,"sq ft","Bathroom wall tiles")
        if works & {"Floor tiles","Wall tiles"}: _add(lines,"Tile Adhesive",(area+wall)*.30,"kg","Tile adhesive")
        if "Waterproofing" in works: _add(lines,"Waterproofing",area+wall,"sq ft","Bathroom wet-area waterproofing")
        if "Plumbing" in works: _add(lines,"PVC/CPVC Pipes",12,"metre","Bathroom pipe run")
        for fixture in {"Toilet","Wash basin","Shower"}&works: _add(lines,"Sanitary Fixtures",1,"set",fixture,0)
    elif renovation == "Roofing":
        works=_selected(project,"roof_work"); roof_type=project.get("roof_type","Concrete")
        if works & {"Crack repair","Concrete repair","Complete roof replacement"}: _add(lines,"Cement",area*.12,"50 kg bag","Roof concrete repair")
        if "Concrete repair" in works or "Complete roof replacement" in works: _add(lines,"Steel",area*.35,"kg","Roof reinforcement")
        if works & {"Leakage repair","Complete roof replacement"}: _add(lines,"Waterproofing",area,"sq ft","Roof waterproofing")
        if "Tile replacement" in works and roof_type=="Tile": _add(lines,"Tiles",area*.25,"sq ft","Replacement roof tiles")
    elif renovation == "Interior Renovation":
        works=_selected(project,"interior_work"); carp=_n(project,"carpentry_area")
        if "Flooring" in works: _add(lines,"Tiles",area*.35,"sq ft","Interior flooring portion")
        if "Painting" in works: _add(lines,"Paint",area*.65*2/100,"litre","Interior painting allowance")
        if "Carpentry" in works: _add(lines,"Wood",carp or area*.20,"sq ft","Wardrobe/storage carpentry")
        if "Plumbing" in works: _add(lines,"PVC/CPVC Pipes",10,"metre","Interior plumbing changes")
        if "Electrical" in works: _add(lines,"Electrical Cable",area*.10,"metre","Interior electrical changes")
    else: # Exterior / structural repair
        works=_selected(project,"exterior_work",["Painting","Waterproofing"]); repair=_n(project,"exterior_repair_area")
        if works & {"Crack repair","Plaster repair"}: _add(lines,"Cement",repair*.10,"50 kg bag","Exterior repair")
        if "Painting" in works: _add(lines,"Paint",area*2/100,"litre","Exterior coating")
        if "Waterproofing" in works: _add(lines,"Waterproofing",area,"sq ft","Exterior moisture protection")
    return lines

def calculate_materials(project):
    area=max(1,_n(project,"work_area",project.get("area",1))); renovation=project.get("renovation")
    if renovation != "Full House Renovation": return _for_type(project,renovation,area)
    mapping={"Wall / structural repair":"Exterior Renovation","Roofing":"Roofing","Plumbing":"Plumbing","Electrical work":"Electrical Work","Flooring & tiling":"Flooring & Tiling","Painting":"Painting","Kitchen":"Kitchen Renovation","Bathroom":"Bathroom Renovation","Exterior work":"Exterior Renovation"}
    all_lines=[]
    for component in project.get("full_scope",[]): all_lines.extend(_for_type(project,mapping[component],area*0.25))
    grouped=defaultdict(lambda:{"Base quantity":0,"Estimated quantity":0,"Wastage rate":WASTE,"Unit":"unit","Why included":[]})
    for line in all_lines:
        value=grouped[line["Material"]]; value["Base quantity"]+=line["Base quantity"]; value["Estimated quantity"]+=line["Estimated quantity"]; value["Unit"]=line["Unit"]; value["Why included"].append(line["Why included"])
    return [{"Material":k,**v,"Why included":"; ".join(v["Why included"])} for k,v in grouped.items()]
