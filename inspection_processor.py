import pandas as pd
import streamlit as st
from datetime import datetime
import xlsxwriter
from io import BytesIO

def process_inspection_data(df, trade_mapping):
    """Process inspection data using the enhanced logic"""
    
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
            return ""
        df["Unit"] = df["auditName"].apply(extract_unit)

    # Derive unit type
    def derive_unit_type(row):
        unit_type = str(row.get("Pre-Settlement Inspection_Unit Type", "")).strip()
        townhouse_type = str(row.get("Pre-Settlement Inspection_Townhouse Type", "")).strip()
        if unit_type.lower() == "townhouse":
            return f"{townhouse_type} Townhouse" if townhouse_type else "Townhouse"
        return unit_type

    df["UnitType"] = df.apply(derive_unit_type, axis=1)

    # Get inspection columns
    inspection_cols = [
        c for c in df.columns if c.startswith("Pre-Settlement Inspection_") and not c.endswith("_notes")
    ]

    # Melt to long format
    long_df = df.melt(
        id_vars=["Unit", "UnitType"],
        value_vars=inspection_cols,
        var_name="InspectionItem",
        value_name="Status"
    )

    # Split into Room and Component
    parts = long_df["InspectionItem"].str.split("_", n=2, expand=True)
    long_df["Room"] = parts[1]
    long_df["Component"] = parts[2].str.replace(r"\.\d+$", "", regex=True)
    long_df["Component"] = long_df["Component"].apply(lambda x: x.split("_")[-1] if isinstance(x, str) else x)

    # Remove metadata rows
    metadata_rooms = ["Unit Type", "Building Type", "Townhouse Type", "Apartment Type"]
    metadata_components = ["Room Type"]
    long_df = long_df[~long_df["Room"].isin(metadata_rooms)]
    long_df = long_df[~long_df["Component"].isin(metadata_components)]

    # Classify status
    def classify_status(val):
        if pd.isna(val):
            return "Blank"
        return "OK" if str(val).strip() == "✓" else "Not OK"

    long_df["StatusClass"] = long_df["Status"].apply(classify_status)

    # Merge with trade mapping
    merged = long_df.merge(trade_mapping, on=["Room", "Component"], how="left")
    final_df = merged[["Unit", "UnitType", "Room", "Component", "StatusClass", "Trade"]]
    
    return final_df, df

def calculate_metrics(final_df, df):
    """Calculate all inspection metrics"""
    
    defects_only = final_df[final_df["StatusClass"] == "Not OK"]
    
    # Extract building information
    sample_audit = df["auditName"].dropna().iloc[0] if "auditName" in df.columns else ""
    audit_parts = str(sample_audit).split("/")
    building_name = audit_parts[2].strip() if len(audit_parts) >= 3 else "Unknown Building"
    inspection_date = audit_parts[0].strip() if len(audit_parts) >= 1 else "Unknown Date"
    
    # Address information
    location = df["Title Page_Site conducted_Location"].dropna().astype(str).str.strip().iloc[0] if "Title Page_Site conducted_Location" in df.columns else ""
    area = df["Title Page_Site conducted_Area"].dropna().astype(str).str.strip().iloc[0] if "Title Page_Site conducted_Area" in df.columns else ""
    region = df["Title Page_Site conducted_Region"].dropna().astype(str).str.strip().iloc[0] if "Title Page_Site conducted_Region" in df.columns else ""
    address_parts = [part for part in [location, area, region] if part]
    address = ", ".join(address_parts) if address_parts else "Address Not Available"
    
    # Calculate basic metrics
    unit_types = sorted(df["UnitType"].dropna().unique())
    unit_types_str = ", ".join(unit_types) if unit_types else "Unknown"
    total_units = df["Unit"].nunique()
    total_inspections = len(final_df)
    total_defects = len(defects_only)
    defect_rate = (total_defects / total_inspections * 100) if total_inspections > 0 else 0
    avg_defects_per_unit = (total_defects / total_units) if total_units > 0 else 0

    # Calculate settlement readiness
    defect_counts = defects_only.groupby("Unit").size()
    ready_units = (defect_counts <= 2).sum()
    minor_work_units = ((defect_counts >= 3) & (defect_counts <= 7)).sum()
    major_work_units = ((defect_counts >= 8) & (defect_counts <= 15)).sum()
    extensive_work_units = (defect_counts > 15).sum()

    # Add units with zero defects to ready category
    units_with_defects = set(defect_counts.index)
    all_units = set(df["Unit"].dropna())
    units_with_no_defects = len(all_units - units_with_defects)
    ready_units += units_with_no_defects

    # Calculate percentages
    ready_pct = (ready_units / total_units * 100) if total_units > 0 else 0
    minor_pct = (minor_work_units / total_units * 100) if total_units > 0 else 0
    major_pct = (major_work_units / total_units * 100) if total_units > 0 else 0
    extensive_pct = (extensive_work_units / total_units * 100) if total_units > 0 else 0

    # Generate summary reports
    summary_trade = defects_only.groupby("Trade").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False)
    summary_unit = defects_only.groupby("Unit").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False)
    summary_room = defects_only.groupby("Room").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False)
    summary_unit_trade = defects_only.groupby(["Unit", "Trade"]).size().reset_index(name="DefectCount")
    summary_room_comp = defects_only.groupby(["Room", "Component"]).size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False)
    
    return {
        "building_name": building_name,
        "inspection_date": inspection_date,
        "address": address,
        "unit_types_str": unit_types_str,
        "total_units": total_units,
        "total_inspections": total_inspections,
        "total_defects": total_defects,
        "defect_rate": defect_rate,
        "avg_defects_per_unit": avg_defects_per_unit,
        "ready_units": ready_units,
        "minor_work_units": minor_work_units,
        "major_work_units": major_work_units,
        "extensive_work_units": extensive_work_units,
        "ready_pct": ready_pct,
        "minor_pct": minor_pct,
        "major_pct": major_pct,
        "extensive_pct": extensive_pct,
        "summary_trade": summary_trade,
        "summary_unit": summary_unit,
        "summary_room": summary_room,
        "summary_unit_trade": summary_unit_trade,
        "summary_room_comp": summary_room_comp,
        "defects_only": defects_only
    }

def generate_enhanced_excel_report(final_df, metrics):
    """Generate the enhanced Excel report with beautiful formatting"""
    
    excel_buffer = BytesIO()
    
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Define all your enhanced formats
        building_info_header = workbook.add_format({
            'bold': True, 'font_size': 14, 'bg_color': '#2E7D32', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 2, 'border_color': '#1B5E20'
        })
        
        inspection_summary_header = workbook.add_format({
            'bold': True, 'font_size': 14, 'bg_color': '#1976D2', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 2, 'border_color': '#0D47A1'
        })
        
        settlement_header = workbook.add_format({
            'bold': True, 'font_size': 14, 'bg_color': '#F57C00', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 2, 'border_color': '#E65100'
        })
        
        problem_trades_header = workbook.add_format({
            'bold': True, 'font_size': 14, 'bg_color': '#7B1FA2', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 2, 'border_color': '#4A148C'
        })
        
        label_format = workbook.add_format({
            'bold': True, 'font_size': 11, 'bg_color': '#F5F5F5', 'border': 1,
            'border_color': '#BDBDBD', 'align': 'left', 'valign': 'vcenter'
        })
        
        data_format = workbook.add_format({
            'font_size': 11, 'border': 1, 'border_color': '#BDBDBD',
            'align': 'right', 'valign': 'vcenter'
        })
        
        # Settlement readiness formats with colors
        ready_format = workbook.add_format({
            'font_size': 11, 'border': 1, 'border_color': '#BDBDBD',
            'bg_color': '#E8F5E8', 'align': 'left', 'valign': 'vcenter'
        })
        
        minor_format = workbook.add_format({
            'font_size': 11, 'border': 1, 'border_color': '#BDBDBD',
            'bg_color': '#FFF3E0', 'align': 'left', 'valign': 'vcenter'
        })
        
        major_format = workbook.add_format({
            'font_size': 11, 'border': 1, 'border_color': '#BDBDBD',
            'bg_color': '#FFE0B2', 'align': 'left', 'valign': 'vcenter'
        })
        
        extensive_format = workbook.add_format({
            'font_size': 11, 'border': 1, 'border_color': '#BDBDBD',
            'bg_color': '#FFEBEE', 'align': 'left', 'valign': 'vcenter'
        })
        
        # Create Executive Dashboard
        worksheet = workbook.add_worksheet("📊 Executive Dashboard")
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 35)
        worksheet.set_column('C:C', 5)  # Spacer column
        
        # Set row heights for better appearance
        for i in range(50):
            worksheet.set_row(i, 20)
        
        current_row = 0
        
        # Building Information Section
        worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', '🏢 BUILDING INFORMATION', building_info_header)
        current_row += 2
        
        building_data = [
            ('Building Name', metrics['building_name']),
            ('Inspection Date', metrics['inspection_date']),
            ('Address', metrics['address']),
            ('Total Units Inspected', f"{metrics['total_units']:,}"),
            ('Unit Types', metrics['unit_types_str'])
        ]
        
        for label, value in building_data:
            worksheet.write(current_row, 0, label, label_format)
            worksheet.write(current_row, 1, value, data_format)
            current_row += 1
        
        current_row += 1
        
        # Inspection Summary Section
        worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', '📋 INSPECTION SUMMARY', inspection_summary_header)
        current_row += 2
        
        summary_data = [
            ('Total Inspection Points', f"{metrics['total_inspections']:,}"),
            ('Total Defects Found', f"{metrics['total_defects']:,}"),
            ('Overall Defect Rate', f"{metrics['defect_rate']:.2f}%"),
            ('Average Defects per Unit', f"{metrics['avg_defects_per_unit']:.1f}")
        ]
        
        for label, value in summary_data:
            worksheet.write(current_row, 0, label, label_format)
            worksheet.write(current_row, 1, value, data_format)
            current_row += 1
        
        current_row += 1
        
        # Settlement Readiness Section
        worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', '🏠 SETTLEMENT READINESS', settlement_header)
        current_row += 2
        
        readiness_data = [
            ('🟢 Ready (0-2 defects)', f"{metrics['ready_units']} units ({metrics['ready_pct']:.1f}%)", ready_format),
            ('🟡 Minor work (3-7 defects)', f"{metrics['minor_work_units']} units ({metrics['minor_pct']:.1f}%)", minor_format),
            ('🟠 Major work (8-15 defects)', f"{metrics['major_work_units']} units ({metrics['major_pct']:.1f}%)", major_format),
            ('🔴 Extensive work (15+ defects)', f"{metrics['extensive_work_units']} units ({metrics['extensive_pct']:.1f}%)", extensive_format)
        ]
        
        for label, value, format_style in readiness_data:
            worksheet.write(current_row, 0, label, format_style)
            worksheet.write(current_row, 1, value, format_style)
            current_row += 1
        
        current_row += 1
        
        # Top Problem Trades Section
        worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', '⚠️ TOP 3 PROBLEM TRADES', problem_trades_header)
        current_row += 2
        
        top_3_trades = metrics['summary_trade'].head(3)
        for i, (_, row) in enumerate(top_3_trades.iterrows(), 1):
            trade_name = row['Trade'] if pd.notna(row['Trade']) else 'Unknown Trade'
            defect_count = row['DefectCount']
            
            # Create gradient colors for top trades
            if i == 1:
                trade_format = workbook.add_format({
                    'font_size': 11, 'border': 1, 'border_color': '#BDBDBD',
                    'bg_color': '#FFCDD2', 'align': 'left', 'valign': 'vcenter', 'bold': True
                })
            elif i == 2:
                trade_format = workbook.add_format({
                    'font_size': 11, 'border': 1, 'border_color': '#BDBDBD',
                    'bg_color': '#FFE0B2', 'align': 'left', 'valign': 'vcenter', 'bold': True
                })
            else:
                trade_format = workbook.add_format({
                    'font_size': 11, 'border': 1, 'border_color': '#BDBDBD',
                    'bg_color': '#FFF9C4', 'align': 'left', 'valign': 'vcenter', 'bold': True
                })
            
            worksheet.write(current_row, 0, f'{i}. {trade_name}', trade_format)
            worksheet.write(current_row, 1, f'{defect_count} defects', trade_format)
            current_row += 1
        
        current_row += 2
        
        # Report Generation Info
        report_format = workbook.add_format({
            'font_size': 10, 'italic': True, 'border': 1, 'border_color': '#9E9E9E',
            'bg_color': '#FAFAFA', 'align': 'center'
        })
        
        worksheet.write(current_row, 0, 'Report Generated', label_format)
        worksheet.write(current_row, 1, datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p"), report_format)
        
        # Add detailed data sheets
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#2E7D32', 'font_color': 'white',
            'border': 1, 'align': 'center'
        })
        
        # All Inspections Sheet
        final_df.to_excel(writer, sheet_name="📋 All Inspections", index=False)
        ws_all = writer.sheets["📋 All Inspections"]
        for col_num, value in enumerate(final_df.columns.values):
            ws_all.write(0, col_num, value, header_format)
        
        # Defects Only Sheet
        metrics['defects_only'].to_excel(writer, sheet_name="🔍 Defects Only", index=False)
        ws_defects = writer.sheets["🔍 Defects Only"]
        for col_num, value in enumerate(metrics['defects_only'].columns.values):
            ws_defects.write(0, col_num, value, header_format)
        
        # Summary sheets
        summary_sheets = [
            (metrics['summary_trade'], "📊 By Trade"),
            (metrics['summary_unit'], "🏠 By Unit"),
            (metrics['summary_room'], "🚪 By Room"),
            (metrics['summary_unit_trade'], "🏠📊 By Unit & Trade"),
            (metrics['summary_room_comp'], "🚪🔧 By Room & Component")
        ]
        
        for summary_data, sheet_name in summary_sheets:
            summary_data.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]
            
            # Format headers
            for col_num, value in enumerate(summary_data.columns.values):
                ws.write(0, col_num, value, header_format)
            
            # Auto-adjust column widths
            for i, col in enumerate(summary_data.columns):
                max_length = max(
                    summary_data[col].astype(str).str.len().max(),
                    len(str(col))
                )
                ws.set_column(i, i, min(max_length + 2, 50))
    
    excel_buffer.seek(0)
    return excel_buffer

def create_default_mapping():
    """Create a comprehensive default trade mapping"""
    default_mapping_data = [
        # Kitchen
        {"Room": "Kitchen", "Component": "Cabinets", "Trade": "Carpentry & Joinery"},
        {"Room": "Kitchen", "Component": "Benchtop", "Trade": "Stone & Tiling"},
        {"Room": "Kitchen", "Component": "Splashback", "Trade": "Tiling"},
        {"Room": "Kitchen", "Component": "Appliances", "Trade": "Electrical"},
        {"Room": "Kitchen", "Component": "Plumbing", "Trade": "Plumbing"},
        {"Room": "Kitchen", "Component": "Lighting", "Trade": "Electrical"},
        {"Room": "Kitchen", "Component": "Flooring", "Trade": "Flooring"},
        {"Room": "Kitchen", "Component": "Walls", "Trade": "Painting"},
        {"Room": "Kitchen", "Component": "Ceiling", "Trade": "Painting"},
        
        # Bathroom
        {"Room": "Bathroom", "Component": "Tiles", "Trade": "Tiling"},
        {"Room": "Bathroom", "Component": "Fixtures", "Trade": "Plumbing"},
        {"Room": "Bathroom", "Component": "Vanity", "Trade": "Carpentry & Joinery"},
        {"Room": "Bathroom", "Component": "Mirror", "Trade": "Glazing"},
        {"Room": "Bathroom", "Component": "Lighting", "Trade": "Electrical"},
        {"Room": "Bathroom", "Component": "Exhaust Fan", "Trade": "Electrical"},
        {"Room": "Bathroom", "Component": "Waterproofing", "Trade": "Waterproofing"},
        {"Room": "Bathroom", "Component": "Shower Screen", "Trade": "Glazing"},
        
        # Bedrooms
        {"Room": "Bedroom", "Component": "Flooring", "Trade": "Flooring"},
        {"Room": "Bedroom", "Component": "Walls", "Trade": "Painting"},
        {"Room": "Bedroom", "Component": "Ceiling", "Trade": "Painting"},
        {"Room": "Bedroom", "Component": "Windows", "Trade": "Glazing"},
        {"Room": "Bedroom", "Component": "Doors", "Trade": "Doors"},
        {"Room": "Bedroom", "Component": "Wardrobes", "Trade": "Carpentry & Joinery"},
        {"Room": "Bedroom", "Component": "Lighting", "Trade": "Electrical"},
        {"Room": "Bedroom", "Component": "Power Points", "Trade": "Electrical"},
        
        # Living Areas
        {"Room": "Living", "Component": "Flooring", "Trade": "Flooring"},
        {"Room": "Living", "Component": "Walls", "Trade": "Painting"},
        {"Room": "Living", "Component": "Ceiling", "Trade": "Painting"},
        {"Room": "Living", "Component": "Windows", "Trade": "Glazing"},
        {"Room": "Living", "Component": "Doors", "Trade": "Doors"},
        {"Room": "Living", "Component": "Lighting", "Trade": "Electrical"},
        {"Room": "Living", "Component": "Power Points", "Trade": "Electrical"},
        {"Room": "Living", "Component": "Air Conditioning", "Trade": "HVAC"},
        
        # Laundry
        {"Room": "Laundry", "Component": "Cabinets", "Trade": "Carpentry & Joinery"},
        {"Room": "Laundry", "Component": "Benchtop", "Trade": "Stone & Tiling"},
        {"Room": "Laundry", "Component": "Plumbing", "Trade": "Plumbing"},
        {"Room": "Laundry", "Component": "Flooring", "Trade": "Flooring"},
        {"Room": "Laundry", "Component": "Walls", "Trade": "Painting"},
        {"Room": "Laundry", "Component": "Lighting", "Trade": "Electrical"},
        
        # External
        {"Room": "External", "Component": "Balcony", "Trade": "Structural"},
        {"Room": "External", "Component": "Deck", "Trade": "Carpentry & Joinery"},
        {"Room": "External", "Component": "Facade", "Trade": "External Cladding"},
        {"Room": "External", "Component": "Roof", "Trade": "Roofing"},
        {"Room": "External", "Component": "Gutters", "Trade": "Roofing"},
        {"Room": "External", "Component": "Driveway", "Trade": "Concreting"},
        {"Room": "External", "Component": "Landscaping", "Trade": "Landscaping"},
        
        # General
        {"Room": "General", "Component": "Security System", "Trade": "Security Systems"},
        {"Room": "General", "Component": "Intercom", "Trade": "Communications"},
        {"Room": "General", "Component": "Fire Safety", "Trade": "Fire Safety"},
        {"Room": "General", "Component": "Ventilation", "Trade": "HVAC"}
    ]
    
    return pd.DataFrame(default_mapping_data)
