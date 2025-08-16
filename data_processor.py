import pandas as pd
from datetime import datetime, timedelta

def process_inspection_data(df, mapping, building_info, user_priorities=None):
    """Process the inspection data with enhanced metrics calculation including user-defined urgent priorities and common area detection"""
    df = df.copy()
    
    # Extract unit number
    if "Lot Details_Lot Number" in df.columns and df["Lot Details_Lot Number"].notna().any():
        df["Unit"] = df["Lot Details_Lot Number"].astype(str).str.strip()
    elif "Title Page_Lot number" in df.columns and df["Title Page_Lot number"].notna().any():
        df["Unit"] = df["Title Page_Lot number"].astype(str).str.strip()
    else:
        def extract_unit(audit_name):
            parts = str(audit_name).split("/")
            if len(parts) >= 3:
                candidate = parts[1].strip()
                if len(candidate) <= 6 and any(ch.isdigit() for ch in candidate):
                    return candidate
            return f"Unit_{hash(str(audit_name)) % 1000}"
        df["Unit"] = df["auditName"].apply(extract_unit) if "auditName" in df.columns else [f"Unit_{i}" for i in range(1, len(df) + 1)]

    # Derive unit type
    def derive_unit_type(row):
        unit_type = str(row.get("Pre-Settlement Inspection_Unit Type", "")).strip()
        townhouse_type = str(row.get("Pre-Settlement Inspection_Townhouse Type", "")).strip()
        apartment_type = str(row.get("Pre-Settlement Inspection_Apartment Type", "")).strip()
        
        if unit_type.lower() == "townhouse":
            return f"{townhouse_type} Townhouse" if townhouse_type else "Townhouse"
        elif unit_type.lower() == "apartment":
            return f"{apartment_type} Apartment" if apartment_type else "Apartment"
        elif unit_type:
            return unit_type
        else:
            return "Unknown Type"

    df["UnitType"] = df.apply(derive_unit_type, axis=1)

    # Get inspection columns
    inspection_cols = [
        c for c in df.columns if c.startswith("Pre-Settlement Inspection_") and not c.endswith("_notes")
    ]

    if not inspection_cols:
        inspection_cols = [c for c in df.columns if any(keyword in c.lower() for keyword in 
                          ['inspection', 'check', 'item', 'defect', 'issue', 'status'])]

    # Melt to long format
    long_df = df.melt(
        id_vars=["Unit", "UnitType"],
        value_vars=inspection_cols,
        var_name="InspectionItem",
        value_name="Status"
    )

    # Split into Room and Component
    parts = long_df["InspectionItem"].str.split("_", n=2, expand=True)
    if len(parts.columns) >= 3:
        long_df["Room"] = parts[1]
        long_df["Component"] = parts[2].str.replace(r"\.\d+$", "", regex=True)
        long_df["Component"] = long_df["Component"].apply(lambda x: x.split("_")[-1] if isinstance(x, str) else x)
    else:
        long_df["Room"] = "General"
        long_df["Component"] = long_df["InspectionItem"].str.replace("Pre-Settlement Inspection_", "")

    # Remove metadata rows
    metadata_rooms = ["Unit Type", "Building Type", "Townhouse Type", "Apartment Type"]
    metadata_components = ["Room Type"]
    long_df = long_df[~long_df["Room"].isin(metadata_rooms)]
    long_df = long_df[~long_df["Component"].isin(metadata_components)]

    # Classify area type (Apartment vs Common Area)
    def classify_area_type(room, unit):
        room_str = str(room).lower()
        unit_str = str(unit).lower()
        
        # Common area indicators
        common_area_rooms = [
            "lobby", "foyer", "entrance", "reception", "mailroom", "mail room",
            "corridor", "hallway", "staircase", "stairwell", "lift", "elevator",
            "parking", "garage", "basement", "storage", "plant room", "mechanical room",
            "roof", "rooftop", "balcony common", "common balcony", "terrace common",
            "laundry common", "common laundry", "gym", "pool", "spa", "sauna",
            "bbq area", "common kitchen", "meeting room", "community room",
            "fire stair", "fire escape", "emergency", "utility", "bin room",
            "loading dock", "loading bay", "common area", "public area"
        ]
        
        # Check if unit indicates common area
        common_unit_indicators = ["common", "ca", "public", "shared", "general", "building"]
        
        # Check room name for common area indicators
        if any(common_room in room_str for common_room in common_area_rooms):
            return "Common Area"
        
        # Check unit name for common area indicators
        if any(common_unit in unit_str for common_unit in common_unit_indicators):
            return "Common Area"
        
        return "Apartment"

    long_df["AreaType"] = long_df.apply(lambda row: classify_area_type(row["Room"], row["Unit"]), axis=1)

    # Classify status
    def classify_status(val):
        if pd.isna(val):
            return "Blank"
        val_str = str(val).strip().lower()
        if val_str in ["✓", "✔", "ok", "pass", "passed", "good", "satisfactory"]:
            return "OK"
        elif val_str in ["✗", "✘", "x", "fail", "failed", "not ok", "defect", "issue"]:
            return "Not OK"
        elif val_str == "":
            return "Blank"
        else:
            return "Not OK"

    def classify_urgency_with_user_priorities(val, component, room, trade, user_priorities):
        """Enhanced urgency classification based on user-defined priorities"""
        if pd.isna(val):
            return "Normal"
        
        val_str = str(val).strip().lower()
        component_str = str(component).lower()
        room_str = str(room).lower()
        trade_str = str(trade).lower() if pd.notna(trade) else ""
        
        # User-defined priority categories
        priority_categories = {
            "Fire Safety": {
                "components": ["fire", "smoke", "fire compliance", "fire door", "fire extinguisher", "sprinkler", "fire alarm"],
                "rooms": ["fire stair", "fire escape", "emergency"],
                "trades": ["fire", "safety"]
            },
            "Electrical Safety": {
                "components": ["electrical", "gpo", "power", "switch", "light", "circuit", "wiring", "outlet"],
                "rooms": ["electrical", "switch"],
                "trades": ["electrical"]
            },
            "Gas Safety": {
                "components": ["gas", "gas outlet", "gas pipe", "gas meter", "gas appliance"],
                "rooms": ["gas"],
                "trades": ["gas", "plumbing"]
            },
            "Security Systems": {
                "components": ["security", "lock", "door lock", "intercom", "access", "key", "door handle", "self latching"],
                "rooms": ["entry", "security"],
                "trades": ["security", "doors"]
            },
            "Water/Plumbing": {
                "components": ["water", "plumbing", "pipe", "drain", "toilet", "shower", "sink", "tap", "drainage"],
                "rooms": ["bathroom", "laundry", "kitchen"],
                "trades": ["plumbing"]
            },
            "Entry Doors": {
                "components": ["door", "door handle", "door lock", "self latching", "paint"],
                "rooms": ["apartment entry door", "entry", "door"],
                "trades": ["doors", "painting"]
            },
            "Structural": {
                "components": ["structural", "concrete", "wall", "ceiling", "floor", "foundation", "beam"],
                "rooms": ["structural"],
                "trades": ["structural", "concrete"]
            }
        }
        
        # Check against user priorities
        if user_priorities:
            for category, is_priority in user_priorities.items():
                if is_priority and category in priority_categories:
                    category_data = priority_categories[category]
                    
                    # Check components
                    if any(comp in component_str for comp in category_data["components"]):
                        return "Urgent"
                    
                    # Check rooms
                    if any(room_keyword in room_str for room_keyword in category_data["rooms"]):
                        return "Urgent"
                    
                    # Check trades
                    if any(trade_keyword in trade_str for trade_keyword in category_data["trades"]):
                        return "Urgent"
        
        # Default classification for non-priority items
        urgent_keywords = ["broken", "not working", "fail", "failed", "dangerous", "hazard"]
        if any(keyword in val_str for keyword in urgent_keywords):
            return "High Priority"
        
        # Default high priority components
        high_priority_components = ["mirror", "tiles", "paint", "ceiling", "walls"]
        if any(hp_comp in component_str for hp_comp in high_priority_components):
            return "High Priority"
            
        return "Normal"

    long_df["StatusClass"] = long_df["Status"].apply(classify_status)
    
    # Merge with trade mapping first to get trade information
    merged = long_df.merge(mapping, on=["Room", "Component"], how="left")
    merged["Trade"] = merged["Trade"].fillna("Unknown Trade")
    
    # Apply urgency classification with user priorities
    merged["Urgency"] = merged.apply(
        lambda row: classify_urgency_with_user_priorities(
            row["Status"], row["Component"], row["Room"], row["Trade"], user_priorities
        ), axis=1
    )

    # Add planned completion dates
    def assign_planned_completion(urgency):
        base_date = datetime.now()
        if urgency == "Urgent":
            return base_date + timedelta(days=2)
        elif urgency == "High Priority":
            return base_date + timedelta(days=7)
        else:
            return base_date + timedelta(days=14)
    
    merged["PlannedCompletion"] = merged["Urgency"].apply(assign_planned_completion)
    
    final_df = merged[["Unit", "UnitType", "Room", "Component", "StatusClass", "Trade", "Urgency", "PlannedCompletion", "AreaType"]]
    
    # Separate apartment and common area data
    apartment_data = final_df[final_df["AreaType"] == "Apartment"]
    common_area_data = final_df[final_df["AreaType"] == "Common Area"]
    
    # Calculate settlement readiness using apartment defects only
    apartment_defects_per_unit = apartment_data[apartment_data["StatusClass"] == "Not OK"].groupby("Unit").size()
    
    ready_units = (apartment_defects_per_unit <= 2).sum() if len(apartment_defects_per_unit) > 0 else 0
    minor_work_units = ((apartment_defects_per_unit > 2) & (apartment_defects_per_unit <= 7)).sum() if len(apartment_defects_per_unit) > 0 else 0
    major_work_units = ((apartment_defects_per_unit > 7) & (apartment_defects_per_unit <= 15)).sum() if len(apartment_defects_per_unit) > 0 else 0
    extensive_work_units = (apartment_defects_per_unit > 15).sum() if len(apartment_defects_per_unit) > 0 else 0
    
    # Add units with zero defects to ready category
    units_with_defects = set(apartment_defects_per_unit.index)
    all_units = set(apartment_data["Unit"].dropna())
    units_with_no_defects = len(all_units - units_with_defects)
    ready_units += units_with_no_defects
    
    total_units = apartment_data["Unit"].nunique()
    
    # Extract building information
    sample_audit = df.loc[0, "auditName"] if "auditName" in df.columns and len(df) > 0 else ""
    if sample_audit:
        audit_parts = str(sample_audit).split("/")
        extracted_building_name = audit_parts[2].strip() if len(audit_parts) >= 3 else building_info["name"]
        extracted_inspection_date = audit_parts[0].strip() if len(audit_parts) >= 1 else building_info["date"]
    else:
        extracted_building_name = building_info["name"]
        extracted_inspection_date = building_info["date"]
    
    # Address information extraction
    location = ""
    area = ""
    region = ""
    
    if "Title Page_Site conducted_Location" in df.columns:
        location_series = df["Title Page_Site conducted_Location"].dropna()
        location = location_series.astype(str).str.strip().iloc[0] if len(location_series) > 0 else ""
    if "Title Page_Site conducted_Area" in df.columns:
        area_series = df["Title Page_Site conducted_Area"].dropna()
        area = area_series.astype(str).str.strip().iloc[0] if len(area_series) > 0 else ""
    if "Title Page_Site conducted_Region" in df.columns:
        region_series = df["Title Page_Site conducted_Region"].dropna()
        region = region_series.astype(str).str.strip().iloc[0] if len(region_series) > 0 else ""
    
    address_parts = [part for part in [location, area, region] if part]
    extracted_address = ", ".join(address_parts) if address_parts else building_info["address"]
    
    # Create comprehensive metrics for apartments
    apartment_defects_only = apartment_data[apartment_data["StatusClass"] == "Not OK"]
    
    # Enhanced metrics with urgency tracking
    urgent_defects = apartment_defects_only[apartment_defects_only["Urgency"] == "Urgent"]
    high_priority_defects = apartment_defects_only[apartment_defects_only["Urgency"] == "High Priority"]
    
    # Common area metrics
    common_defects_only = common_area_data[common_area_data["StatusClass"] == "Not OK"]
    common_urgent_defects = common_defects_only[common_defects_only["Urgency"] == "Urgent"]
    
    # Planned work in next 2 weeks (only items due within 14 days)
    next_two_weeks = datetime.now() + timedelta(days=14)
    planned_work_2weeks = apartment_defects_only[apartment_defects_only["PlannedCompletion"] <= next_two_weeks]
    
    # Planned work in next month (items due between 2 weeks and 1 month)
    next_month = datetime.now() + timedelta(days=30)
    planned_work_month = apartment_defects_only[
        (apartment_defects_only["PlannedCompletion"] > next_two_weeks) & 
        (apartment_defects_only["PlannedCompletion"] <= next_month)
    ]
    
    metrics = {
        "building_name": extracted_building_name,
        "address": extracted_address,
        "inspection_date": extracted_inspection_date,
        "unit_types_str": ", ".join(sorted(apartment_data["UnitType"].astype(str).unique())),
        "total_units": total_units,
        "total_inspections": len(apartment_data),
        "total_defects": len(apartment_defects_only),
        "defect_rate": (len(apartment_defects_only) / len(apartment_data) * 100) if len(apartment_data) > 0 else 0.0,
        "avg_defects_per_unit": (len(apartment_defects_only) / max(total_units, 1)),
        "ready_units": ready_units,
        "minor_work_units": minor_work_units,
        "major_work_units": major_work_units,
        "extensive_work_units": extensive_work_units,
        "ready_pct": (ready_units / total_units * 100) if total_units > 0 else 0,
        "minor_pct": (minor_work_units / total_units * 100) if total_units > 0 else 0,
        "major_pct": (major_work_units / total_units * 100) if total_units > 0 else 0,
        "extensive_pct": (extensive_work_units / total_units * 100) if total_units > 0 else 0,
        "urgent_defects": len(urgent_defects),
        "high_priority_defects": len(high_priority_defects),
        "planned_work_2weeks": len(planned_work_2weeks),
        "planned_work_month": len(planned_work_month),
        # Common area metrics
        "common_total_defects": len(common_defects_only),
        "common_urgent_defects": len(common_urgent_defects),
        "common_areas_count": common_area_data["Room"].nunique() if len(common_area_data) > 0 else 0,
        # Summary tables
        "summary_trade": apartment_defects_only.groupby("Trade").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(apartment_defects_only) > 0 else pd.DataFrame(columns=["Trade", "DefectCount"]),
        "summary_unit": apartment_defects_only.groupby("Unit").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(apartment_defects_only) > 0 else pd.DataFrame(columns=["Unit", "DefectCount"]),
        "summary_room": apartment_defects_only.groupby("Room").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(apartment_defects_only) > 0 else pd.DataFrame(columns=["Room", "DefectCount"]),
        "urgent_defects_table": urgent_defects[["Unit", "Room", "Component", "Trade", "PlannedCompletion"]].copy() if len(urgent_defects) > 0 else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "PlannedCompletion"]),
        "planned_work_2weeks_table": planned_work_2weeks[["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]].copy() if len(planned_work_2weeks) > 0 else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]),
        "planned_work_month_table": planned_work_month[["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]].copy() if len(planned_work_month) > 0 else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]),
        "component_details_summary": apartment_defects_only.groupby(["Trade", "Room", "Component"])["Unit"].apply(lambda s: ", ".join(sorted(s.astype(str).unique()))).reset_index().rename(columns={"Unit": "Units with Defects"}) if len(apartment_defects_only) > 0 else pd.DataFrame(columns=["Trade", "Room", "Component", "Units with Defects"]),
        # Common area tables
        "common_summary_trade": common_defects_only.groupby("Trade").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(common_defects_only) > 0 else pd.DataFrame(columns=["Trade", "DefectCount"]),
        "common_summary_room": common_defects_only.groupby("Room").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(common_defects_only) > 0 else pd.DataFrame(columns=["Room", "DefectCount"]),
        "common_urgent_defects_table": common_urgent_defects[["Unit", "Room", "Component", "Trade", "PlannedCompletion"]].copy() if len(common_urgent_defects) > 0 else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "PlannedCompletion"])
    }
    
    return final_df, metrics, common_area_data

def lookup_unit_defects(processed_data, unit_number):
    """Lookup defect history for a specific unit"""
    if processed_data is None or unit_number is None:
        return pd.DataFrame()
    
    unit_data = processed_data[
        (processed_data["Unit"].astype(str).str.strip().str.lower() == str(unit_number).strip().lower()) &
        (processed_data["StatusClass"] == "Not OK")
    ].copy()
    
    if len(unit_data) > 0:
        # Sort by urgency and planned completion
        urgency_order = {"Urgent": 1, "High Priority": 2, "Normal": 3}
        unit_data["UrgencySort"] = unit_data["Urgency"].map(urgency_order).fillna(3)
        unit_data = unit_data.sort_values(["UrgencySort", "PlannedCompletion"])
        
        # Format planned completion dates
        unit_data["PlannedCompletion"] = pd.to_datetime(unit_data["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
        
        return unit_data[["Room", "Component", "Trade", "Urgency", "PlannedCompletion"]]
    
    return pd.DataFrame(columns=["Room", "Component", "Trade", "Urgency", "PlannedCompletion"])