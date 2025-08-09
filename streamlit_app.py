# Complete Working Streamlit App with Interactive Trade Mapping Management
# File: streamlit_app.py

import streamlit as st
import pandas as pd
import io
import base64
import json
from datetime import datetime
import xlsxwriter
from io import BytesIO, StringIO

# Configure the page
st.set_page_config(
    page_title="🏢 Inspection Report Processor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #2E7D32, #1976D2);
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
    }
    .main-header p {
        color: white;
        margin: 0.5rem 0 0 0;
        font-size: 1.2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #dee2e6;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #2E7D32;
        margin: 0;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        margin: 0.5rem 0 0 0;
    }
    .success-message {
        background: linear-gradient(135deg, #d4edda, #c3e6cb);
        color: #155724;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    .readiness-card {
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        text-align: center;
        font-weight: bold;
    }
    .ready { background: linear-gradient(135deg, #d4edda, #c3e6cb); color: #155724; }
    .minor { background: linear-gradient(135deg, #fff3cd, #ffeaa7); color: #856404; }
    .major { background: linear-gradient(135deg, #f8d7da, #f5c6cb); color: #721c24; }
    .extensive { background: linear-gradient(135deg, #f8d7da, #dc3545); color: white; }
    .trade-item {
        background: linear-gradient(135deg, #fff, #f8f9fa);
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #007bff;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for mapping data
if 'trade_mapping' not in st.session_state:
    st.session_state.trade_mapping = None
if 'mapping_edited' not in st.session_state:
    st.session_state.mapping_edited = False

# Header
st.markdown("""
<div class="main-header">
    <h1>🏢 Inspection Report Processor</h1>
    <p>Upload iAuditor CSV files and generate beautiful Excel reports with custom trade mapping</p>
</div>
""", unsafe_allow_html=True)

Electrical"},
        {"Room": "Master Bedroom", "Component": "Skirting", "Trade": "Carpentry & Joinery"},
        {"Room": "Master Bedroom", "Component": "Sliding Glass Door (if applicable)", "Trade": "Windows"},
        {"Room": "Master Bedroom", "Component": "Walls", "Trade": "Painting"},
        {"Room": "Master Bedroom", "Component": "Wardrobe", "Trade": "Carpentry & Joinery"},
        {"Room": "Master Bedroom", "Component": "Windows", "Trade": "Windows"},
        {"Room": "Staircase", "Component": "Railing (if applicable)", "Trade": "Carpentry & Joinery"},
        {"Room": "Staircase", "Component": "Staircase", "Trade": "Carpentry & Joinery"},
        {"Room": "Study Area (if applicable)", "Component": "Desk", "Trade": "Carpentry & Joinery"},
        {"Room": "Study Area (if applicable)", "Component": "GPO", "Trade": "Electrical"},
        {"Room": "Study Area (if applicable)", "Component": "Light Fixtures", "Trade": "Electrical"},
        {"Room": "Study Area (if applicable)", "Component": "Skirting", "Trade": "Carpentry & Joinery"},
        {"Room": "Study Area (if applicable)", "Component": "Walls", "Trade": "Painting"},
        {"Room": "Upstair Corridor", "Component": "Ceiling", "Trade": "Painting"},
        {"Room": "Upstair Corridor", "Component": "Walls", "Trade": "Painting"},
        {"Room": "Upstairs Bathroom", "Component": "Bathtub (if applicable)", "Trade": "Plumbing"},
        {"Room": "Upstairs Bathroom", "Component": "Ceiling", "Trade": "Painting"},
        {"Room": "Upstairs Bathroom", "Component": "Doors", "Trade": "Doors"},
        {"Room": "Upstairs Bathroom", "Component": "Exhaust Fan", "Trade": "Electrical"},
        {"Room": "Upstairs Bathroom", "Component": "GPO", "Trade": "Electrical"},
        {"Room": "Upstairs Bathroom", "Component": "Light Fixtures", "Trade": "Electrical"},
        {"Room": "Upstairs Bathroom", "Component": "Mirror", "Trade": "Carpentry & Joinery"},
        {"Room": "Upstairs Bathroom", "Component": "Shower", "Trade": "Plumbing"},
        {"Room": "Upstairs Bathroom", "Component": "Sink", "Trade": "Plumbing"},
        {"Room": "Upstairs Bathroom", "Component": "Skirting", "Trade": "Carpentry & Joinery"},
        {"Room": "Upstairs Bathroom", "Component": "Tiles", "Trade": "Flooring - Tiles"},
        {"Room": "Upstairs Bathroom", "Component": "Toilet", "Trade": "Plumbing"},
        {"Room": "Upstairs Bathroom", "Component": "Walls", "Trade": "Painting"},
        {"Room": "Upstairs Landing", "Component": "Ceiling", "Trade": "Painting"},
        {"Room": "Upstairs Landing", "Component": "Flooring", "Trade": "Flooring - Timber"},
        {"Room": "Upstairs Landing", "Component": "Light Fixtures", "Trade": "Electrical"},
        {"Room": "Upstairs Landing", "Component": "Skirting", "Trade": "Carpentry & Joinery"},
        {"Room": "Upstairs Landing", "Component": "Walls", "Trade": "Painting"}
    ]
    
    return pd.DataFrame(mapping_data)

def generate_component_details_summary(defects_only):
    """Generate detailed component analysis showing which units have defects for each Trade/Room/Component"""
    
    if len(defects_only) == 0:
        return pd.DataFrame(columns=['Trade', 'Room', 'Component', 'Units with Defects'])
    
    # Group by Trade, Room, Component and get list of units with defects
    component_details = defects_only.groupby(['Trade', 'Room', 'Component'])['Unit'].apply(
        lambda x: ', '.join(sorted(x.astype(str).unique()))
    ).reset_index()
    
    # Rename column to match your example
    component_details.rename(columns={'Unit': 'Units with Defects'}, inplace=True)
    
    # Sort by Trade, then by number of units (descending)
    component_details['Unit_Count'] = component_details['Units with Defects'].apply(
        lambda x: len(x.split(', ')) if x else 0
    )
    component_details = component_details.sort_values(['Trade', 'Unit_Count'], ascending=[True, False])
    
    # Remove the temporary count column
    component_details = component_details[['Trade', 'Room', 'Component', 'Units with Defects']]
    
    return component_detailsPainting"},
        {"Room": "Master Bedroom", "Component": "Wardrobe", "Trade": "Carpentry & Joinery"},
        {"Room": "Master Bedroom", "Component": "Windows", "Trade": "Windows"},
        {"Room": "Study", "Component": "Carpets", "Trade": "Flooring - Carpets"},
        {"Room": "Study", "Component": "Ceiling", "Trade": "Painting"},
        {"Room": "Study", "Component": "Doors", "Trade": "Doors"},
        {"Room": "Study", "Component": "GPO", "Trade": "Electrical"},
        {"Room": "Study", "Component": "Light Fixtures", "Trade": "Electrical"},
        {"Room": "Study", "Component": "Network Router (if applicable)", "Trade": "Electrical"},
        {"Room": "Study", "Component": "Skirting", "Trade": "Carpentry & Joinery"},
        {"Room": "Study", "Component": "Walls", "Trade": "Painting"},
        {"Room": "Study", "Component": "Windows", "Trade": "Windows"},
        {"Room": "Upstairs Bathroom", "Component": "Bathtub (if applicable)", "Trade": "Plumbing"},
        {"Room": "Upstairs Bathroom", "Component": "Ceiling", "Trade": "Painting"},
        {"Room": "Upstairs Bathroom", "Component": "Doors", "Trade": "Doors"},
        {"Room": "Upstairs Bathroom", "Component": "Exhaust Fan", "Trade": "Electrical"},
        {"Room": "Upstairs Bathroom", "Component": "GPO", "Trade": "Electrical"},
        {"Room": "Upstairs Bathroom", "Component": "Light Fixtures", "Trade": "Electrical"},
        {"Room": "Upstairs Bathroom", "Component": "Mirror", "Trade": "Carpentry & Joinery"},
        {"Room": "Upstairs Bathroom", "Component": "Shower", "Trade": "Plumbing"},
        {"Room": "Upstairs Bathroom", "Component": "Sink", "Trade": "Plumbing"},
        {"Room": "Upstairs Bathroom", "Component": "Skirting", "Trade": "Carpentry & Joinery"},
        {"Room": "Upstairs Bathroom", "Component": "Tiles", "Trade": "Flooring - Tiles"},
        {"Room": "Upstairs Bathroom", "Component": "Toilet", "Trade": "Plumbing"},
        {"Room": "Upstairs Bathroom", "Component": "Walls", "Trade": "Painting"},
        {"Room": "Upstairs Landing", "Component": "Ceiling", "Trade": "Painting"},
        {"Room": "Upstairs Landing", "Component": "Flooring", "Trade": "Flooring - Timber"},
        {"Room": "Upstairs Landing", "Component": "Light Fixtures", "Trade": "Electrical"},
        {"Room": "Upstairs Landing", "Component": "Skirting", "Trade": "Carpentry & Joinery"},
        {"Room": "Upstairs Landing", "Component": "Walls", "Trade": "Painting"}
    ]
    
    return pd.DataFrame(mapping_data)

def get_available_trades():
    """Get list of available trade categories from the mapping"""
    return [
        "Doors",
        "Electrical", 
        "Plumbing",
        "Painting",
        "Carpentry & Joinery",
        "Flooring - Tiles",
        "Flooring - Carpets", 
        "Flooring - Timber",
        "Windows",
        "Appliances"
    ]

def process_inspection_data(df, trade_mapping):
    """Process inspection data using enhanced logic"""
    
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
            return f"Unit_{hash(str(audit_name)) % 1000}"  # Fallback unit number
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
        # Fallback: look for any columns that might contain inspection data
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
        # Fallback parsing
        long_df["Room"] = "General"
        long_df["Component"] = long_df["InspectionItem"].str.replace("Pre-Settlement Inspection_", "")

    # Remove metadata rows
    metadata_rooms = ["Unit Type", "Building Type", "Townhouse Type", "Apartment Type"]
    metadata_components = ["Room Type"]
    long_df = long_df[~long_df["Room"].isin(metadata_rooms)]
    long_df = long_df[~long_df["Component"].isin(metadata_components)]

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
            return "Not OK"  # Conservative approach - treat unclear as defect

    long_df["StatusClass"] = long_df["Status"].apply(classify_status)

    # Merge with trade mapping
    merged = long_df.merge(trade_mapping, on=["Room", "Component"], how="left")
    
    # Fill missing trades with "Unknown Trade"
    merged["Trade"] = merged["Trade"].fillna("Unknown Trade")
    
    final_df = merged[["Unit", "UnitType", "Room", "Component", "StatusClass", "Trade"]]
    
    return final_df, df

def calculate_comprehensive_metrics(final_df, df):
    """Calculate comprehensive inspection metrics including trade-specific analysis"""
    
    defects_only = final_df[final_df["StatusClass"] == "Not OK"]
    
    # Extract building information
    sample_audit = df["auditName"].dropna().iloc[0] if "auditName" in df.columns and len(df["auditName"].dropna()) > 0 else ""
    if sample_audit:
        audit_parts = str(sample_audit).split("/")
        building_name = audit_parts[2].strip() if len(audit_parts) >= 3 else "Unknown Building"
        inspection_date = audit_parts[0].strip() if len(audit_parts) >= 1 else "Unknown Date"
    else:
        building_name = "Unknown Building"
        inspection_date = datetime.now().strftime("%Y-%m-%d")
    
    # Address information
    location = ""
    area = ""
    region = ""
    
    if "Title Page_Site conducted_Location" in df.columns:
        location = df["Title Page_Site conducted_Location"].dropna().astype(str).str.strip().iloc[0] if len(df["Title Page_Site conducted_Location"].dropna()) > 0 else ""
    if "Title Page_Site conducted_Area" in df.columns:
        area = df["Title Page_Site conducted_Area"].dropna().astype(str).str.strip().iloc[0] if len(df["Title Page_Site conducted_Area"].dropna()) > 0 else ""
    if "Title Page_Site conducted_Region" in df.columns:
        region = df["Title Page_Site conducted_Region"].dropna().astype(str).str.strip().iloc[0] if len(df["Title Page_Site conducted_Region"].dropna()) > 0 else ""
    
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
    
    # NEW: Generate Trade Specific Summary with detailed analysis
    trade_specific_summary = generate_trade_specific_summary(final_df, defects_only, total_units)
    
    # NEW: Generate Component Details Summary like your example
    component_details_summary = generate_component_details_summary(defects_only)
    
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
        "defects_only": defects_only,
        "trade_specific_summary": trade_specific_summary,  # NEW
        "component_details_summary": component_details_summary  # NEW
    }

def generate_trade_specific_summary(final_df, defects_only, total_units):
    """Generate comprehensive trade-specific analysis"""
    
    # Get all trades in the system
    all_trades = final_df['Trade'].unique()
    trade_summary = []
    
    for trade in all_trades:
        # Basic defect metrics
        trade_defects = defects_only[defects_only['Trade'] == trade]
        total_defects = len(trade_defects)
        
        # Total inspections for this trade
        total_inspections = len(final_df[final_df['Trade'] == trade])
        defect_rate = (total_defects / total_inspections * 100) if total_inspections > 0 else 0
        
        # Units affected
        units_affected = trade_defects['Unit'].nunique()
        percentage_units_affected = (units_affected / total_units * 100) if total_units > 0 else 0
        
        # Most common defect components for this trade
        top_components = trade_defects['Component'].value_counts().head(3)
        top_components_str = ", ".join([f"{comp} ({count})" for comp, count in top_components.items()])
        
        # Most affected rooms for this trade
        top_rooms = trade_defects['Room'].value_counts().head(3)
        top_rooms_str = ", ".join([f"{room} ({count})" for room, count in top_rooms.items()])
        
        # Priority level based on defect count and percentage
        if total_defects >= 20 or percentage_units_affected >= 30:
            priority = "High"
        elif total_defects >= 10 or percentage_units_affected >= 15:
            priority = "Medium"
        elif total_defects > 0:
            priority = "Low"
        else:
            priority = "None"
        
        # Average defects per affected unit
        avg_defects_per_affected_unit = (total_defects / units_affected) if units_affected > 0 else 0
        
        trade_summary.append({
            'Trade': trade,
            'Total_Defects': total_defects,
            'Total_Inspections': total_inspections,
            'Defect_Rate_Percent': round(defect_rate, 2),
            'Units_Affected': units_affected,
            'Percentage_Units_Affected': round(percentage_units_affected, 2),
            'Avg_Defects_Per_Affected_Unit': round(avg_defects_per_affected_unit, 2),
            'Priority_Level': priority,
            'Top_Components': top_components_str if top_components_str else "None",
            'Top_Rooms': top_rooms_str if top_rooms_str else "None"
        })
    
    # Convert to DataFrame and sort by total defects
    trade_summary_df = pd.DataFrame(trade_summary)
    trade_summary_df = trade_summary_df.sort_values('Total_Defects', ascending=False)
    
    return trade_summary_df

def generate_enhanced_excel_report(final_df, metrics, include_charts, detailed_breakdown, executive_summary):
    """Generate the enhanced Excel report with beautiful formatting and Trade Specific Summary"""
    
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
        
        trade_specific_header = workbook.add_format({
            'bold': True, 'font_size': 14, 'bg_color': '#D32F2F', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 2, 'border_color': '#B71C1C'
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
        worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', '⚠️ TOP PROBLEM TRADES', problem_trades_header)
        current_row += 2
        
        top_trades = metrics['summary_trade'].head(5)
        for i, (_, row) in enumerate(top_trades.iterrows(), 1):
            trade_name = row['Trade'] if pd.notna(row['Trade']) else 'Unknown Trade'
            defect_count = row['DefectCount']
            
            # Create gradient colors for top trades
            colors = ['#FFCDD2', '#FFE0B2', '#FFF9C4', '#E1F5FE', '#F3E5F5']
            color = colors[min(i-1, len(colors)-1)]
            
            trade_format = workbook.add_format({
                'font_size': 11, 'border': 1, 'border_color': '#BDBDBD',
                'bg_color': color, 'align': 'left', 'valign': 'vcenter', 'bold': True
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
        if len(metrics['defects_only']) > 0:
            metrics['defects_only'].to_excel(writer, sheet_name="🔍 Defects Only", index=False)
            ws_defects = writer.sheets["🔍 Defects Only"]
            for col_num, value in enumerate(metrics['defects_only'].columns.values):
                ws_defects.write(0, col_num, value, header_format)
        
        # NEW: Trade Specific Summary Sheet - This was missing!
        if len(metrics['trade_specific_summary']) > 0:
            metrics['trade_specific_summary'].to_excel(writer, sheet_name="🔧 Trade Specific Summary", index=False)
            ws_trade_summary = writer.sheets["🔧 Trade Specific Summary"]
            
            # Apply beautiful formatting to Trade Specific Summary
            for col_num, value in enumerate(metrics['trade_specific_summary'].columns.values):
                ws_trade_summary.write(0, col_num, value, header_format)
            
            # Set column widths for better readability
            ws_trade_summary.set_column('A:A', 18)  # Trade
            ws_trade_summary.set_column('B:B', 12)  # Total_Defects
            ws_trade_summary.set_column('C:C', 15)  # Total_Inspections
            ws_trade_summary.set_column('D:D', 15)  # Defect_Rate_Percent
            ws_trade_summary.set_column('E:E', 12)  # Units_Affected
            ws_trade_summary.set_column('F:F', 20)  # Percentage_Units_Affected
            ws_trade_summary.set_column('G:G', 25)  # Avg_Defects_Per_Affected_Unit
            ws_trade_summary.set_column('H:H', 12)  # Priority_Level
            ws_trade_summary.set_column('I:I', 30)  # Top_Components
            ws_trade_summary.set_column('J:J', 25)  # Top_Rooms
            
            # Add conditional formatting for priority levels
            high_priority_format = workbook.add_format({
                'bg_color': '#FFCDD2', 'font_color': '#B71C1C', 'bold': True
            })
            medium_priority_format = workbook.add_format({
                'bg_color': '#FFF3E0', 'font_color': '#E65100'
            })
            low_priority_format = workbook.add_format({
                'bg_color': '#E8F5E8', 'font_color': '#2E7D32'
            })
            
            # Apply conditional formatting to priority column
            for row_num in range(1, len(metrics['trade_specific_summary']) + 1):
                priority_value = metrics['trade_specific_summary'].iloc[row_num - 1]['Priority_Level']
                if priority_value == 'High':
                    ws_trade_summary.write(row_num, 7, priority_value, high_priority_format)
                elif priority_value == 'Medium':
                    ws_trade_summary.write(row_num, 7, priority_value, medium_priority_format)
                elif priority_value == 'Low':
                    ws_trade_summary.write(row_num, 7, priority_value, low_priority_format)
        
        # NEW: Component Details Summary Sheet - Shows which units have defects for each component
        if len(metrics['component_details_summary']) > 0:
            metrics['component_details_summary'].to_excel(writer, sheet_name="🔍 Component Details", index=False)
            ws_component_details = writer.sheets["🔍 Component Details"]
            
            # Apply beautiful formatting to Component Details
            for col_num, value in enumerate(metrics['component_details_summary'].columns.values):
                ws_component_details.write(0, col_num, value, header_format)
            
            # Set column widths for better readability
            ws_component_details.set_column('A:A', 18)  # Trade
            ws_component_details.set_column('B:B', 25)  # Room
            ws_component_details.set_column('C:C', 30)  # Component
            ws_component_details.set_column('D:D', 50)  # Units with Defects
            
            # Add alternating row colors for better readability
            light_format = workbook.add_format({
                'bg_color': '#F8F9FA', 'border': 1, 'border_color': '#E9ECEF'
            })
            
            for row_num in range(1, len(metrics['component_details_summary']) + 1):
                if row_num % 2 == 0:  # Even rows
                    for col_num in range(len(metrics['component_details_summary'].columns)):
                        cell_value = metrics['component_details_summary'].iloc[row_num - 1, col_num]
                        ws_component_details.write(row_num, col_num, cell_value, light_format)
        
        # Summary sheets if detailed breakdown is requested
        if detailed_breakdown:
            summary_sheets = [
                (metrics['summary_trade'], "📊 By Trade"),
                (metrics['summary_unit'], "🏠 By Unit"),
                (metrics['summary_room'], "🚪 By Room"),
                (metrics['summary_unit_trade'], "🏠📊 By Unit & Trade"),
                (metrics['summary_room_comp'], "🚪🔧 By Room & Component")
            ]
            
            for summary_data, sheet_name in summary_sheets:
                if len(summary_data) > 0:
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

def display_comprehensive_results(metrics, excel_buffer, original_filename):
    """Display comprehensive processing results"""
    
    st.markdown("---")
    st.markdown("## 🎉 Processing Complete!")
    
    # Success message with building info
    st.markdown(f"""
    <div class="success-message">
        <h3>✅ Inspection Report Generated Successfully!</h3>
        <p><strong>🏢 Building:</strong> {metrics['building_name']}</p>
        <p><strong>📅 Inspection Date:</strong> {metrics['inspection_date']}</p>
        <p><strong>📄 Source File:</strong> {original_filename}</p>
        <p><strong>⏰ Processing Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Key metrics in a beautiful layout
    st.markdown("### 📊 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metrics['total_units']:,}</div>
            <div class="metric-label">🏠 Total Units</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metrics['total_defects']:,}</div>
            <div class="metric-label">⚠️ Total Defects</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metrics['defect_rate']:.1f}%</div>
            <div class="metric-label">📊 Defect Rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metrics['avg_defects_per_unit']:.1f}</div>
            <div class="metric-label">📈 Avg per Unit</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Settlement readiness in beautiful cards
    st.markdown("### 🏠 Settlement Readiness Analysis")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="readiness-card ready">
            <h4>🟢 Ready</h4>
            <p><strong>{metrics['ready_units']}</strong> units</p>
            <small>({metrics['ready_pct']:.1f}%) • 0-2 defects</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="readiness-card minor">
            <h4>🟡 Minor Work</h4>
            <p><strong>{metrics['minor_work_units']}</strong> units</p>
            <small>({metrics['minor_pct']:.1f}%) • 3-7 defects</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="readiness-card major">
            <h4>🟠 Major Work</h4>
            <p><strong>{metrics['major_work_units']}</strong> units</p>
            <small>({metrics['major_pct']:.1f}%) • 8-15 defects</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="readiness-card extensive">
            <h4>🔴 Extensive Work</h4>
            <p><strong>{metrics['extensive_work_units']}</strong> units</p>
            <small>({metrics['extensive_pct']:.1f}%) • 15+ defects</small>
        </div>
        """, unsafe_allow_html=True)
    
    # NEW: Trade Specific Analysis Preview
    if len(metrics['trade_specific_summary']) > 0:
        st.markdown("### 🔧 Trade Specific Analysis")
        
        # Show top 5 problematic trades with enhanced display
        top_trades_detailed = metrics['trade_specific_summary'].head(5)
        
        for i, (_, row) in enumerate(top_trades_detailed.iterrows(), 1):
            trade_name = row['Trade']
            defect_count = row['Total_Defects']
            defect_rate = row['Defect_Rate_Percent']
            units_affected = row['Units_Affected']
            priority = row['Priority_Level']
            
            # Color coding based on priority
            if priority == 'High':
                border_color = "#D32F2F"
                bg_color = "#FFEBEE"
            elif priority == 'Medium':
                border_color = "#F57C00"
                bg_color = "#FFF3E0"
            else:
                border_color = "#388E3C"
                bg_color = "#E8F5E8"
            
            st.markdown(f"""
            <div class="trade-item" style="border-left-color: {border_color}; background: {bg_color};">
                <strong>{i}. {trade_name}</strong> 
                <span style="color: {border_color}; font-weight: bold;">({priority} Priority)</span>
                <br>
                <small>
                    📊 {defect_count} defects ({defect_rate:.1f}% rate) • 
                    🏠 {units_affected} units affected
                </small>
            </div>
            """, unsafe_allow_html=True)
    
    # Top problem trades (existing)
    if len(metrics['summary_trade']) > 0:
        st.markdown("### ⚠️ Top Problem Trades (Quick View)")
        
        for i, (_, row) in enumerate(metrics['summary_trade'].head(5).iterrows(), 1):
            trade_name = row['Trade'] if pd.notna(row['Trade']) else 'Unknown Trade'
            defect_count = row['DefectCount']
            
            # Color coding based on ranking
            colors = ["#ff4444", "#ff8800", "#ffcc00", "#88cc00", "#44cc44"]
            color = colors[min(i-1, len(colors)-1)]
            
            st.markdown(f"""
            <div class="trade-item" style="border-left-color: {color};">
                <strong>{i}. {trade_name}</strong>
                <span style="float: right; background: {color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.9em;">
                    {defect_count} defects
                </span>
            </div>
            """, unsafe_allow_html=True)
    
    # NEW: Component Details Preview
    if len(metrics['component_details_summary']) > 0:
        st.markdown("### 🔍 Component Details Analysis")
        
        # Show top 10 most problematic components
        top_components = metrics['component_details_summary'].head(10)
        
        st.markdown("#### Top 10 Most Problematic Components")
        st.dataframe(
            top_components,
            use_container_width=True,
            column_config={
                "Trade": st.column_config.TextColumn("Trade", width="medium"),
                "Room": st.column_config.TextColumn("Room", width="medium"),
                "Component": st.column_config.TextColumn("Component", width="large"),
                "Units with Defects": st.column_config.TextColumn("Units with Defects", width="x-large")
            }
        )
        
        # Summary stats
        col1, col2, col3 = st.columns(3)
        with col1:
            unique_problematic_components = len(metrics['component_details_summary'])
            st.metric("Components with Issues", unique_problematic_components)
        with col2:
            most_affected_component = metrics['component_details_summary'].iloc[0] if len(metrics['component_details_summary']) > 0 else None
            if most_affected_component is not None:
                max_units = len(most_affected_component['Units with Defects'].split(', '))
                st.metric("Max Units Affected (Single Component)", max_units)
        with col3:
            avg_units_per_component = metrics['component_details_summary']['Units with Defects'].apply(
                lambda x: len(x.split(', ')) if x else 0
            ).mean()
            st.metric("Avg Units per Problematic Component", f"{avg_units_per_component:.1f}")
    
    # Charts and visualization
    if len(metrics['summary_trade']) > 0:
        st.markdown("### 📈 Visual Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Defects by Trade")
            chart_data = metrics['summary_trade'].head(10)
            st.bar_chart(chart_data.set_index('Trade')['DefectCount'])
        
        with col2:
            st.markdown("#### Settlement Readiness Distribution")
            readiness_data = pd.DataFrame({
                'Category': ['Ready', 'Minor Work', 'Major Work', 'Extensive Work'],
                'Units': [metrics['ready_units'], metrics['minor_work_units'], 
                         metrics['major_work_units'], metrics['extensive_work_units']]
            })
            st.bar_chart(readiness_data.set_index('Category')['Units'])
    
    # Download section
    st.markdown("### 📥 Download Your Report")
    
    filename = f"{metrics['building_name'].replace(' ', '_')}_Inspection_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.download_button(
            label="📊 Download Complete Excel Report",
            data=excel_buffer,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col2:
        st.metric("📄 File Size", f"{len(excel_buffer.getvalue()) / 1024:.1f} KB")
    
    # Report contents summary - UPDATED to include Component Details
    st.markdown("#### 📋 What's in Your Report:")
    st.markdown("""
    - **📊 Executive Dashboard** - Key metrics and visual summary
    - **📋 All Inspections** - Complete detailed data
    - **🔍 Defects Only** - Filtered view of issues found
    - **🔧 Trade Specific Summary** - Comprehensive trade analysis with priorities
    - **🔍 Component Details** - Shows which specific units have defects for each component (NEW!)
    - **📊 By Trade** - Defects grouped by trade category
    - **🏠 By Unit** - Unit-specific defect summaries
    - **🚪 By Room** - Room-specific analysis
    - **🔧 Multiple Views** - Various data perspectives for analysis
    """)
    
    st.success("🎉 Your professional inspection report is ready! The Excel file contains multiple worksheets with comprehensive analysis, including the new Component Details sheet showing exactly which units have defects for each component - just like your example format.")

def process_inspection_file(uploaded_file, trade_mapping, include_charts, detailed_breakdown, executive_summary, notification_email):
    """Process the inspection file using the current trade mapping"""
    
    # Create progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Step 1: Read uploaded file
        status_text.text("📖 Reading uploaded file...")
        progress_bar.progress(10)
        
        df = pd.read_csv(uploaded_file)
        st.success(f"✅ Loaded {len(df)} rows from inspection file: {uploaded_file.name}")
        
        # Step 2: Process the data using the provided trade mapping
        status_text.text("🔄 Processing inspection data with trade mapping...")
        progress_bar.progress(40)
        
        # Your enhanced processing logic
        final_df, processed_df = process_inspection_data(df, trade_mapping)
        
        progress_bar.progress(60)
        
        # Step 3: Calculate metrics (including new trade-specific analysis)
        status_text.text("📊 Calculating metrics and generating trade-specific insights...")
        
        metrics = calculate_comprehensive_metrics(final_df, processed_df)
        
        progress_bar.progress(80)
        
        # Step 4: Generate Excel report (now includes Trade Specific Summary)
        status_text.text("📈 Generating beautiful Excel report with Trade Specific Summary...")
        
        excel_buffer = generate_enhanced_excel_report(final_df, metrics, include_charts, detailed_breakdown, executive_summary)
        
        progress_bar.progress(100)
        status_text.text("✅ Processing completed successfully!")
        
        # Display results
        display_comprehensive_results(metrics, excel_buffer, uploaded_file.name)
        
        # Optional email notification
        if notification_email and notification_email.strip():
            st.info(f"📧 Email notification would be sent to: {notification_email}")
        
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.exception(e)
        
        # Show helpful troubleshooting tips
        st.markdown("### 🔧 Troubleshooting Tips")
        st.markdown("""
        - **Check file format**: Ensure it's a valid CSV file from iAuditor
        - **Check file size**: Very large files may take longer to process
        - **Check column names**: Ensure the CSV has the expected iAuditor column structure
        - **Try a different file**: Test with a smaller or different inspection file
        """)

# Navigation tabs
tab1, tab2, tab3 = st.tabs(["📤 Upload & Process", "🗺️ Manage Trade Mapping", "📊 View Reports"])

with tab2:
    st.markdown("## 🗺️ Trade Mapping Management")
    st.markdown("Review and customize how inspection items are mapped to trade categories")
    
    # Mapping source selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📋 Mapping Source")
        mapping_source = st.radio(
            "Choose your mapping source:",
            ["Load default mapping (266 mappings)", "Upload custom mapping file", "Start with empty mapping"],
            help="Choose how to initialize your trade mapping"
        )
    
    with col2:
        st.markdown("### 🔧 Actions")
        if st.button("🔄 Reset Mapping", help="Reset to default 266 mappings"):
            st.session_state.trade_mapping = load_default_mapping()
            st.session_state.mapping_edited = True
            st.success("✅ Mapping reset to default (266 mappings)")
        
        if st.button("📥 Download Current Mapping", help="Download mapping as CSV"):
            if st.session_state.trade_mapping is not None:
                csv = st.session_state.trade_mapping.to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv,
                    file_name=f"trade_mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    # Handle mapping source selection
    if mapping_source == "Upload custom mapping file":
        uploaded_mapping = st.file_uploader(
            "Upload Trade Mapping CSV",
            type=['csv'],
            help="Upload a CSV file with columns: Room, Component, Trade"
        )
        if uploaded_mapping is not None:
            try:
                mapping_df = pd.read_csv(uploaded_mapping)
                if all(col in mapping_df.columns for col in ['Room', 'Component', 'Trade']):
                    st.session_state.trade_mapping = mapping_df
                    st.session_state.mapping_edited = True
                    st.success(f"✅ Loaded {len(mapping_df)} mappings from uploaded file")
                else:
                    st.error("❌ CSV must have columns: Room, Component, Trade")
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
    
    elif mapping_source == "Load default mapping (266 mappings)":
        if st.session_state.trade_mapping is None:
            st.session_state.trade_mapping = load_default_mapping()
            st.session_state.mapping_edited = True
        
    elif mapping_source == "Start with empty mapping":
        if st.session_state.trade_mapping is None or len(st.session_state.trade_mapping) > 0:
            st.session_state.trade_mapping = pd.DataFrame(columns=['Room', 'Component', 'Trade'])
            st.session_state.mapping_edited = True
    
    # Display and edit mapping if available
    if st.session_state.trade_mapping is not None:
        st.markdown("---")
        st.markdown("### ✏️ Edit Trade Mapping")
        
        # Mapping statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Mappings", len(st.session_state.trade_mapping))
        with col2:
            unique_rooms = st.session_state.trade_mapping['Room'].nunique() if len(st.session_state.trade_mapping) > 0 else 0
            st.metric("Unique Rooms", unique_rooms)
        with col3:
            unique_trades = st.session_state.trade_mapping['Trade'].nunique() if len(st.session_state.trade_mapping) > 0 else 0
            st.metric("Trade Categories", unique_trades)
        with col4:
            if st.session_state.mapping_edited:
                st.success("✅ Modified")
            else:
                st.info("📝 Ready")
        
        # Simple editable dataframe
        if len(st.session_state.trade_mapping) > 0:
            st.markdown("#### 📋 Current Mapping")
            
            # Editable dataframe
            edited_mapping = st.data_editor(
                st.session_state.trade_mapping,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "Room": st.column_config.TextColumn("Room", width="medium"),
                    "Component": st.column_config.TextColumn("Component", width="large"),
                    "Trade": st.column_config.SelectboxColumn(
                        "Trade",
                        options=get_available_trades(),
                        width="medium"
                    )
                },
                key="mapping_editor"
            )
            
            # Update session state if changes were made
            if not edited_mapping.equals(st.session_state.trade_mapping):
                st.session_state.trade_mapping = edited_mapping
                st.session_state.mapping_edited = True
                st.success("✅ Mapping updated!")
        
        # Add new mapping entry
        st.markdown("#### ➕ Add New Mapping")
        with st.expander("Add New Room-Component-Trade Mapping"):
            col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
            
            with col1:
                new_room = st.text_input("Room", key="new_room")
            
            with col2:
                new_component = st.text_input("Component", key="new_component")
            
            with col3:
                new_trade = st.selectbox("Trade", get_available_trades(), key="new_trade")
            
            with col4:
                if st.button("➕ Add", key="add_mapping"):
                    if new_room and new_component and new_trade:
                        new_row = pd.DataFrame({
                            'Room': [new_room],
                            'Component': [new_component], 
                            'Trade': [new_trade]
                        })
                        st.session_state.trade_mapping = pd.concat([
                            st.session_state.trade_mapping, new_row
                        ], ignore_index=True)
                        st.session_state.mapping_edited = True
                        st.success(f"✅ Added: {new_room} → {new_component} → {new_trade}")
                        st.rerun()
                    else:
                        st.error("❌ Please fill in all fields")

with tab1:
    # Sidebar for options
    st.sidebar.title("⚙️ Processing Options")
    st.sidebar.markdown("---")
    
    # Check if mapping is ready
    if st.session_state.trade_mapping is not None and len(st.session_state.trade_mapping) > 0:
        st.sidebar.success(f"✅ Trade mapping ready ({len(st.session_state.trade_mapping)} mappings)")
    else:
        st.sidebar.warning("⚠️ No trade mapping configured. Please set up mapping in the 'Manage Trade Mapping' tab.")
    
    st.sidebar.subheader("📊 Report Options")
    include_charts = st.sidebar.checkbox("Include analysis charts", value=True)
    detailed_breakdown = st.sidebar.checkbox("Detailed trade breakdown", value=True)
    executive_summary = st.sidebar.checkbox("Executive summary", value=True)
    
    st.sidebar.subheader("📧 Notifications")
    notification_email = st.sidebar.text_input("Email for notifications (optional)", placeholder="admin@company.com")
    
    # Main upload and processing area
    st.markdown("## 📤 Upload & Process Inspection Files")
    
    # Show mapping status
    if st.session_state.trade_mapping is not None:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Mappings Loaded", len(st.session_state.trade_mapping))
        with col2:
            st.metric("Trade Categories", st.session_state.trade_mapping['Trade'].nunique() if len(st.session_state.trade_mapping) > 0 else 0)
        with col3:
            st.metric("Room Types", st.session_state.trade_mapping['Room'].nunique() if len(st.session_state.trade_mapping) > 0 else 0)
    
    # File upload
    st.markdown("### 📋 Upload Inspection File")
    uploaded_file = st.file_uploader(
        "Choose iAuditor CSV file",
        type=['csv'],
        help="Select the CSV file exported from iAuditor"
    )
    
    # Preview mapping that will be used
    if st.session_state.trade_mapping is not None and len(st.session_state.trade_mapping) > 0:
        with st.expander("🔍 Preview Current Trade Mapping"):
            st.dataframe(
                st.session_state.trade_mapping.head(10),
                use_container_width=True
            )
            if len(st.session_state.trade_mapping) > 10:
                st.info(f"Showing first 10 of {len(st.session_state.trade_mapping)} total mappings")
    
    # Processing
    if uploaded_file is not None:
        st.markdown("---")
        if st.session_state.trade_mapping is not None and len(st.session_state.trade_mapping) > 0:
            if st.button("🚀 Process Inspection Report", type="primary", use_container_width=True):
                process_inspection_file(
                    uploaded_file, 
                    st.session_state.trade_mapping, 
                    include_charts, 
                    detailed_breakdown, 
                    executive_summary, 
                    notification_email
                )
        else:
            st.warning("⚠️ Please configure trade mapping in the 'Manage Trade Mapping' tab before processing files.")

with tab3:
    st.markdown("## 📊 Report Analytics & History")
    st.info("🚧 This section will show historical reports and analytics in future versions")
    
    # Placeholder for future features
    st.markdown("### 🔮 Coming Soon:")
    st.markdown("""
    - 📈 **Historical Report Analysis** - Track trends over time
    - 📊 **Cross-Project Comparisons** - Compare different buildings
    - 🎯 **Performance Metrics** - Settlement readiness trends
    - 📱 **Mobile Dashboard** - View reports on any device
    - 🔔 **Alert System** - Notifications for critical issues
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em; padding: 2rem;">
    <h4>🏢 Inspection Report Processor with Trade Specific Analysis</h4>
    <p>Professional inspection report processing with comprehensive trade analysis and 266 mappings</p>
    <p>✅ Trade Specific Summary | ✅ Priority Analysis | ✅ 266 Mappings | ✅ Professional Reports</p>
    <p>📊 Beautiful Excel reports | 🔄 Fast processing | 📱 Mobile friendly</p>
</div>
""", unsafe_allow_html=True)
