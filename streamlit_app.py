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
        background: linear-gradient(135deg, #4CAF50, #2196F3);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.8rem;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    .main-header p {
        color: white;
        margin: 0.8rem 0 0 0;
        font-size: 1.3rem;
        opacity: 0.95;
    }
    .metric-card {
        background: linear-gradient(135deg, #ffffff, #f8f9fa);
        padding: 2rem;
        border-radius: 15px;
        border: 2px solid #e9ecef;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
        height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: #2E7D32;
        margin: 0;
        line-height: 1;
    }
    .metric-label {
        font-size: 1rem;
        color: #666;
        margin: 0.8rem 0 0 0;
        font-weight: 500;
    }
    .success-message {
        background: linear-gradient(135deg, #d4edda, #c3e6cb);
        color: #155724;
        padding: 2rem;
        border-radius: 15px;
        border: 2px solid #c3e6cb;
        margin: 1.5rem 0;
        box-shadow: 0 4px 12px rgba(21, 87, 36, 0.1);
    }
    .success-message h3 {
        margin-top: 0;
        color: #155724;
    }
    .readiness-card {
        padding: 1.2rem;
        border-radius: 10px;
        margin: 0.8rem 0;
        text-align: center;
        font-weight: 600;
        font-size: 1.1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .ready { 
        background: linear-gradient(135deg, #c8e6c9, #a5d6a7); 
        color: #2e7d32; 
        border-left: 5px solid #4caf50;
    }
    .minor { 
        background: linear-gradient(135deg, #fff3c4, #fff176); 
        color: #f57f17; 
        border-left: 5px solid #ffeb3b;
    }
    .major { 
        background: linear-gradient(135deg, #ffcdd2, #ef9a9a); 
        color: #c62828; 
        border-left: 5px solid #f44336;
    }
    .extensive { 
        background: linear-gradient(135deg, #f8bbd9, #f48fb1); 
        color: #ad1457; 
        border-left: 5px solid #e91e63;
    }
    .trade-item {
        background: linear-gradient(135deg, #ffffff, #f8f9fa);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 0.8rem 0;
        border-left: 5px solid #2196f3;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .section-header {
        background: linear-gradient(135deg, #6c5ce7, #a29bfe);
        color: white;
        padding: 1rem 2rem;
        border-radius: 10px;
        margin: 2rem 0 1rem 0;
        text-align: center;
        font-weight: 600;
        font-size: 1.3rem;
        box-shadow: 0 4px 12px rgba(108, 92, 231, 0.3);
    }
    .info-card {
        background: linear-gradient(135deg, #e3f2fd, #bbdefb);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #2196f3;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(33, 150, 243, 0.1);
    }
    .warning-card {
        background: linear-gradient(135deg, #fff3e0, #ffcc02);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #ff9800;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(255, 152, 0, 0.1);
    }
    .stButton > button {
        background: linear-gradient(135deg, #4CAF50, #45a049);
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.8rem 2rem;
        font-weight: 600;
        font-size: 1.1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(76, 175, 80, 0.4);
    }
    .upload-section {
        background: linear-gradient(135deg, #f8f9fa, #ffffff);
        padding: 2rem;
        border-radius: 15px;
        border: 2px dashed #dee2e6;
        margin: 1.5rem 0;
        text-align: center;
    }
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
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

def load_default_mapping():
    """Load comprehensive trade mappings"""
    
    # Master mapping CSV data as a string
    master_mapping_csv = """Room,Component,Trade
Apartment Entry Door,Door Handle,Doors
Apartment Entry Door,Door Locks and Keys,Doors
Apartment Entry Door,Paint,Painting
Apartment Entry Door,Self Latching,Doors
Balcony,Balustrade,Carpentry & Joinery
Balcony,Drainage Point,Plumbing
Balcony,GPO (if applicable),Electrical
Balcony,Glass,Windows
Balcony,Glass Sliding Door,Windows
Balcony,Tiles,Flooring - Tiles
Bathroom,Bathtub (if applicable),Plumbing
Bathroom,Ceiling,Painting
Bathroom,Doors,Doors
Bathroom,Exhaust Fan,Electrical
Bathroom,GPO,Electrical
Bathroom,Light Fixtures,Electrical
Bathroom,Mirror,Carpentry & Joinery
Bathroom,Shower,Plumbing
Bathroom,Sink,Plumbing
Bathroom,Skirting,Carpentry & Joinery
Bathroom,Tiles,Flooring - Tiles
Bathroom,Toilet,Plumbing
Bathroom,Walls,Painting
Bedroom,Carpets,Flooring - Carpets
Bedroom,Ceiling,Painting
Bedroom,Doors,Doors
Bedroom,GPO,Electrical
Bedroom,Light Fixtures,Electrical
Bedroom,Skirting,Carpentry & Joinery
Bedroom,Walls,Painting
Bedroom,Wardrobe,Carpentry & Joinery
Bedroom,Windows,Windows
Bedroom 1,Carpets,Flooring - Carpets
Bedroom 1,Ceiling,Painting
Bedroom 1,Doors,Doors
Bedroom 1,GPO,Electrical
Bedroom 1,Light Fixtures,Electrical
Bedroom 1,Skirting,Carpentry & Joinery
Bedroom 1,Walls,Painting
Bedroom 1,Wardrobe,Carpentry & Joinery
Bedroom 1,Windows,Windows
Bedroom 1 w/Ensuite,Bathtub (if applicable),Plumbing
Bedroom 1 w/Ensuite,Carpets,Flooring - Carpets
Bedroom 1 w/Ensuite,Ceiling,Painting
Bedroom 1 w/Ensuite,Doors,Doors
Bedroom 1 w/Ensuite,Exhaust Fan,Electrical
Bedroom 1 w/Ensuite,GPO,Electrical
Bedroom 1 w/Ensuite,Light Fixtures,Electrical
Bedroom 1 w/Ensuite,Mirror,Carpentry & Joinery
Bedroom 1 w/Ensuite,Shower,Plumbing
Bedroom 1 w/Ensuite,Sink,Plumbing
Bedroom 1 w/Ensuite,Skirting,Carpentry & Joinery
Bedroom 1 w/Ensuite,Tiles,Flooring - Tiles
Bedroom 1 w/Ensuite,Toilet,Plumbing
Bedroom 1 w/Ensuite,Walls,Painting
Bedroom 1 w/Ensuite,Wardrobe,Carpentry & Joinery
Bedroom 1 w/Ensuite,Windows,Windows
Bedroom 2,Carpets,Flooring - Carpets
Bedroom 2,Ceiling,Painting
Bedroom 2,Doors,Doors
Bedroom 2,GPO,Electrical
Bedroom 2,Light Fixtures,Electrical
Bedroom 2,Skirting,Carpentry & Joinery
Bedroom 2,Walls,Painting
Bedroom 2,Wardrobe,Carpentry & Joinery
Bedroom 2,Windows,Windows
Bedroom 2 w/Ensuite,Bathtub (if applicable),Plumbing
Bedroom 2 w/Ensuite,Carpets,Flooring - Carpets
Bedroom 2 w/Ensuite,Ceiling,Painting
Bedroom 2 w/Ensuite,Doors,Doors
Bedroom 2 w/Ensuite,Exhaust Fan,Electrical
Bedroom 2 w/Ensuite,GPO,Electrical
Bedroom 2 w/Ensuite,Light Fixtures,Electrical
Bedroom 2 w/Ensuite,Mirror,Carpentry & Joinery
Bedroom 2 w/Ensuite,Shower,Plumbing
Bedroom 2 w/Ensuite,Sink,Plumbing
Bedroom 2 w/Ensuite,Skirting,Carpentry & Joinery
Bedroom 2 w/Ensuite,Tiles,Flooring - Tiles
Bedroom 2 w/Ensuite,Toilet,Plumbing
Bedroom 2 w/Ensuite,Walls,Painting
Bedroom 2 w/Ensuite,Wardrobe,Carpentry & Joinery
Bedroom 2 w/Ensuite,Windows,Windows
Bedroom 3,Carpets,Flooring - Carpets
Bedroom 3,Ceiling,Painting
Bedroom 3,Doors,Doors
Bedroom 3,GPO,Electrical
Bedroom 3,Light Fixtures,Electrical
Bedroom 3,Skirting,Carpentry & Joinery
Bedroom 3,Walls,Painting
Bedroom 3,Wardrobe,Carpentry & Joinery
Bedroom 3,Windows,Windows
Bedroom w/Ensuite,Bathtub (if applicable),Plumbing
Bedroom w/Ensuite,Carpets,Flooring - Carpets
Bedroom w/Ensuite,Ceiling,Painting
Bedroom w/Ensuite,Doors,Doors
Bedroom w/Ensuite,Exhaust Fan,Electrical
Bedroom w/Ensuite,GPO,Electrical
Bedroom w/Ensuite,Light Fixtures,Electrical
Bedroom w/Ensuite,Mirror,Carpentry & Joinery
Bedroom w/Ensuite,Shower,Plumbing
Bedroom w/Ensuite,Sink,Plumbing
Bedroom w/Ensuite,Skirting,Carpentry & Joinery
Bedroom w/Ensuite,Tiles,Flooring - Tiles
Bedroom w/Ensuite,Toilet,Plumbing
Bedroom w/Ensuite,Walls,Painting
Bedroom w/Ensuite,Wardrobe,Carpentry & Joinery
Bedroom w/Ensuite,Windows,Windows
Butler's Pantry,Cabinets/Shelving,Carpentry & Joinery
Butler's Pantry,Ceiling,Painting
Butler's Pantry,Flooring,Flooring - Timber
Butler's Pantry,GPO,Electrical
Butler's Pantry,Light Fixtures,Electrical
Butler's Pantry,Sink,Plumbing
Butler's Pantry (if applicable),Cabinets/Shelving,Carpentry & Joinery
Butler's Pantry (if applicable),Ceiling,Painting
Butler's Pantry (if applicable),Flooring,Flooring - Timber
Butler's Pantry (if applicable),GPO,Electrical
Butler's Pantry (if applicable),Light Fixtures,Electrical
Butler's Pantry (if applicable),Sink,Plumbing
Corridor,Ceiling,Painting
Corridor,Flooring,Flooring - Timber
Corridor,Intercom,Electrical
Corridor,Light Fixtures,Electrical
Corridor,Skirting,Carpentry & Joinery
Corridor,Walls,Painting
Dining & Living Room Area,Ceiling,Painting
Dining & Living Room Area,Flooring,Flooring - Timber
Dining & Living Room Area,GPO,Electrical
Dining & Living Room Area,Light Fixtures,Electrical
Dining & Living Room Area,Skirting,Carpentry & Joinery
Dining & Living Room Area,Walls,Painting
Dining & Living Room Area,Windows (if applicable),Windows
Downstairs Bathroom,Ceiling,Painting
Downstairs Bathroom,Doors,Doors
Downstairs Bathroom,Exhaust Fan,Electrical
Downstairs Bathroom,GPO,Electrical
Downstairs Bathroom,Light Fixtures,Electrical
Downstairs Bathroom,Mirror,Carpentry & Joinery
Downstairs Bathroom,Shower,Plumbing
Downstairs Bathroom,Sink,Plumbing
Downstairs Bathroom,Skirting,Carpentry & Joinery
Downstairs Bathroom,Tiles,Flooring - Tiles
Downstairs Bathroom,Toilet,Plumbing
Downstairs Bathroom,Walls,Painting
Downstairs Toilet (if applicable),Ceiling,Painting
Downstairs Toilet (if applicable),Doors,Doors
Downstairs Toilet (if applicable),Exhaust Fan,Electrical
Downstairs Toilet (if applicable),Light Fixtures,Electrical
Downstairs Toilet (if applicable),Sink,Plumbing
Downstairs Toilet (if applicable),Skirting,Carpentry & Joinery
Downstairs Toilet (if applicable),Tiles,Flooring - Tiles
Downstairs Toilet (if applicable),Toilet,Plumbing
Downstairs Toilet (if applicable),Walls,Painting
Kitchen Area,Cabinets,Carpentry & Joinery
Kitchen Area,Ceiling,Painting
Kitchen Area,Dishwasher,Plumbing
Kitchen Area,Dishwasher (if applicable),Plumbing
Kitchen Area,Flooring,Flooring - Timber
Kitchen Area,GPO,Electrical
Kitchen Area,Kitchen Sink,Plumbing
Kitchen Area,Kitchen Table Tops,Carpentry & Joinery
Kitchen Area,Light Fixtures,Electrical
Kitchen Area,Rangehood,Appliances
Kitchen Area,Splashbacks,Painting
Kitchen Area,Stovetop and Oven,Appliances
Laundry Room,Windows (if applicable),Windows
Laundry Section,Cold/Hot Water Outlets,Plumbing
Laundry Section,Doors,Doors
Laundry Section,Drainage,Plumbing
Laundry Section,Exhaust Fan,Electrical
Laundry Section,GPO,Electrical
Laundry Section,Laundry Sink,Plumbing
Laundry Section,Light Fixtures,Electrical
Laundry Section,Skirting,Carpentry & Joinery
Laundry Section,Tiles,Flooring - Tiles
Laundry Section,Walls,Painting
Staircase,Ceiling,Painting
Staircase,Light Fixtures,Electrical
Staircase,Railing (if applicable),Carpentry & Joinery
Staircase,Skirting,Carpentry & Joinery
Staircase,Staircase,Carpentry & Joinery
Staircase,Walls,Painting
Study Area (if applicable),Desk,Carpentry & Joinery
Study Area (if applicable),GPO,Electrical
Study Area (if applicable),Light Fixtures,Electrical
Study Area (if applicable),Skirting,Carpentry & Joinery
Study Area (if applicable),Walls,Painting
Upstair Corridor,Ceiling,Painting
Upstair Corridor,Flooring,Flooring - Timber
Upstair Corridor,Light Fixtures,Electrical
Upstair Corridor,Skirting,Carpentry & Joinery
Upstair Corridor,Walls,Painting
Upstairs Bathroom,Bathtub (if applicable),Plumbing
Upstairs Bathroom,Ceiling,Painting
Upstairs Bathroom,Doors,Doors
Upstairs Bathroom,Exhaust Fan,Electrical
Upstairs Bathroom,GPO,Electrical
Upstairs Bathroom,Light Fixtures,Electrical
Upstairs Bathroom,Mirror,Carpentry & Joinery
Upstairs Bathroom,Shower,Plumbing
Upstairs Bathroom,Sink,Plumbing
Upstairs Bathroom,Skirting,Carpentry & Joinery
Upstairs Bathroom,Tiles,Flooring - Tiles
Upstairs Bathroom,Toilet,Plumbing
Upstairs Bathroom,Walls,Painting
Laundry Room,Cold/Hot Water Outlets,Plumbing
Laundry Room,Doors,Doors
Laundry Room,Drainage,Plumbing
Laundry Room,Exhaust Fan,Electrical
Laundry Room,GPO,Electrical
Laundry Room,Laundry Sink,Plumbing
Laundry Room,Light Fixtures,Electrical
Laundry Room,Skirting,Carpentry & Joinery
Laundry Room,Tiles,Flooring - Tiles
Laundry Room,Walls,Painting"""
    
    # Parse the CSV data using StringIO
    df = pd.read_csv(StringIO(master_mapping_csv))
    
    # Display confirmation message
    st.success(f"✅ Loaded {len(df)} trade mappings from default data!")
    
    return df

def get_available_trades():
    """Get list of available trade categories"""
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
    
    return component_details

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
    
    # Generate Trade Specific Summary with detailed analysis
    trade_specific_summary = generate_trade_specific_summary(final_df, defects_only, total_units)
    
    # Generate Component Details Summary like your example
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
        "trade_specific_summary": trade_specific_summary,
        "component_details_summary": component_details_summary
    }

def generate_trade_specific_summary(final_df, defects_only, total_units):
    """Generate comprehensive trade-specific analysis"""
    
    all_trades = final_df['Trade'].unique()
    trade_summary = []
    
    for trade in all_trades:
        trade_defects = defects_only[defects_only['Trade'] == trade]
        total_defects = len(trade_defects)
        
        total_inspections = len(final_df[final_df['Trade'] == trade])
        defect_rate = (total_defects / total_inspections * 100) if total_inspections > 0 else 0
        
        units_affected = trade_defects['Unit'].nunique()
        percentage_units_affected = (units_affected / total_units * 100) if total_units > 0 else 0
        
        top_components = trade_defects['Component'].value_counts().head(3)
        top_components_str = ", ".join([f"{comp} ({count})" for comp, count in top_components.items()])
        
        top_rooms = trade_defects['Room'].value_counts().head(3)
        top_rooms_str = ", ".join([f"{room} ({count})" for room, count in top_rooms.items()])
        
        if total_defects >= 20 or percentage_units_affected >= 30:
            priority = "High"
        elif total_defects >= 10 or percentage_units_affected >= 15:
            priority = "Medium"
        elif total_defects > 0:
            priority = "Low"
        else:
            priority = "None"
        
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
    
    trade_summary_df = pd.DataFrame(trade_summary)
    trade_summary_df = trade_summary_df.sort_values('Total_Defects', ascending=False)
    
    return trade_summary_df

def generate_enhanced_excel_report(final_df, metrics, include_charts, detailed_breakdown, executive_summary):
    """Generate the enhanced Excel report with beautiful formatting"""
    
    excel_buffer = BytesIO()
    
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Define comprehensive formats matching the image style
        # Building Information Header (Green)
        building_header = workbook.add_format({
            'bold': True, 'font_size': 16, 'bg_color': '#4CAF50', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 2
        })
        
        # Inspection Summary Header (Blue)
        inspection_header = workbook.add_format({
            'bold': True, 'font_size': 16, 'bg_color': '#2196F3', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 2
        })
        
        # Settlement Readiness Header (Orange)
        settlement_header = workbook.add_format({
            'bold': True, 'font_size': 16, 'bg_color': '#FF9800', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 2
        })
        
        # Top Problem Trades Header (Purple)
        trades_header = workbook.add_format({
            'bold': True, 'font_size': 16, 'bg_color': '#9C27B0', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 2
        })
        
        # Label formats
        label_format = workbook.add_format({
            'bold': True, 'font_size': 12, 'bg_color': '#E8E8E8', 'border': 1,
            'align': 'left', 'valign': 'vcenter'
        })
        
        # Data formats
        data_format = workbook.add_format({
            'font_size': 12, 'border': 1, 'align': 'right', 'valign': 'vcenter'
        })
        
        # Special data formats for readiness categories
        ready_format = workbook.add_format({
            'font_size': 12, 'border': 1, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#C8E6C9'  # Light green
        })
        
        minor_format = workbook.add_format({
            'font_size': 12, 'border': 1, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#FFF3C4'  # Light yellow
        })
        
        major_format = workbook.add_format({
            'font_size': 12, 'border': 1, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#FFCDD2'  # Light red
        })
        
        extensive_format = workbook.add_format({
            'font_size': 12, 'border': 1, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#F8BBD9'  # Light pink
        })
        
        # Trade ranking formats
        trade_rank_format = workbook.add_format({
            'bold': True, 'font_size': 11, 'bg_color': '#F3E5F5', 'border': 1,
            'align': 'left', 'valign': 'vcenter'
        })
        
        trade_count_format = workbook.add_format({
            'font_size': 11, 'border': 1, 'align': 'right', 'valign': 'vcenter',
            'bg_color': '#F3E5F5'
        })
        
        # Footer format
        footer_format = workbook.add_format({
            'font_size': 10, 'border': 1, 'align': 'right', 'valign': 'vcenter',
            'italic': True, 'bg_color': '#F5F5F5'
        })
        
        # Create Executive Dashboard
        worksheet = workbook.add_worksheet("📊 Executive Dashboard")
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 40)
        
        current_row = 0
        
        # === BUILDING INFORMATION SECTION ===
        worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', '🏢 BUILDING INFORMATION', building_header)
        worksheet.set_row(current_row, 25)  # Make header row taller
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
        
        current_row += 1  # Add spacing
        
        # === INSPECTION SUMMARY SECTION ===
        worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', '📋 INSPECTION SUMMARY', inspection_header)
        worksheet.set_row(current_row, 25)
        current_row += 2
        
        inspection_data = [
            ('Total Inspection Points', f"{metrics['total_inspections']:,}"),
            ('Total Defects Found', f"{metrics['total_defects']:,}"),
            ('Overall Defect Rate', f"{metrics['defect_rate']:.2f}%"),
            ('Average Defects per Unit', f"{metrics['avg_defects_per_unit']:.1f}")
        ]
        
        for label, value in inspection_data:
            worksheet.write(current_row, 0, label, label_format)
            worksheet.write(current_row, 1, value, data_format)
            current_row += 1
        
        current_row += 1  # Add spacing
        
        # === SETTLEMENT READINESS SECTION ===
        worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', '🏠 SETTLEMENT READINESS', settlement_header)
        worksheet.set_row(current_row, 25)
        current_row += 2
        
        # Settlement readiness data with different colors
        readiness_data = [
            ('✅ Ready (0-2 defects)', f"{metrics['ready_units']} units ({metrics['ready_pct']:.1f}%)", ready_format),
            ('⚠️ Minor work (3-7 defects)', f"{metrics['minor_work_units']} units ({metrics['minor_pct']:.1f}%)", minor_format),
            ('🔧 Major work (8-15 defects)', f"{metrics['major_work_units']} units ({metrics['major_pct']:.1f}%)", major_format),
            ('🚧 Extensive work (15+ defects)', f"{metrics['extensive_work_units']} units ({metrics['extensive_pct']:.1f}%)", extensive_format)
        ]
        
        for label, value, cell_format in readiness_data:
            worksheet.write(current_row, 0, label, label_format)
            worksheet.write(current_row, 1, value, cell_format)
            current_row += 1
        
        current_row += 1  # Add spacing
        
        # === TOP PROBLEM TRADES SECTION ===
        worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', '⚠️ TOP PROBLEM TRADES', trades_header)
        worksheet.set_row(current_row, 25)
        current_row += 2
        
        # Get top 5 trades by defect count
        top_trades = metrics['summary_trade'].head(5)
        
        for idx, (_, row) in enumerate(top_trades.iterrows(), 1):
            trade_label = f"{idx}. {row['Trade']}"
            defect_count = f"{row['DefectCount']} defects"
            worksheet.write(current_row, 0, trade_label, trade_rank_format)
            worksheet.write(current_row, 1, defect_count, trade_count_format)
            current_row += 1
        
        current_row += 2  # Add more spacing before footer
        
        # === FOOTER ===
        worksheet.write(current_row, 0, 'Report Generated', label_format)
        report_time = datetime.now().strftime('%m/%d/%Y, %I:%M:%S %p')
        worksheet.write(current_row, 1, report_time, footer_format)
        
        # Add other detailed data sheets with proper formatting
        # All Inspections Sheet
        final_df.to_excel(writer, sheet_name="📋 All Inspections", index=False)
        ws_all = writer.sheets["📋 All Inspections"]
        
        # Create header format for data sheets
        data_header_format = workbook.add_format({
            'bold': True, 'bg_color': '#2E7D32', 'font_color': 'white',
            'border': 1, 'align': 'center', 'font_size': 11
        })
        
        for col_num, value in enumerate(final_df.columns.values):
            ws_all.write(0, col_num, value, data_header_format)
        
        # Auto-adjust column widths
        for i, col in enumerate(final_df.columns):
            max_len = max(final_df[col].astype(str).str.len().max(), len(str(col))) + 2
            ws_all.set_column(i, i, min(max_len, 50))
        
        # Defects Only Sheet
        if len(metrics['defects_only']) > 0:
            metrics['defects_only'].to_excel(writer, sheet_name="🔍 Defects Only", index=False)
            ws_defects = writer.sheets["🔍 Defects Only"]
            for col_num, value in enumerate(metrics['defects_only'].columns.values):
                ws_defects.write(0, col_num, value, data_header_format)
            
            # Auto-adjust column widths
            for i, col in enumerate(metrics['defects_only'].columns):
                max_len = max(metrics['defects_only'][col].astype(str).str.len().max(), len(str(col))) + 2
                ws_defects.set_column(i, i, min(max_len, 50))
        
        # Trade Specific Summary Sheet
        if len(metrics['trade_specific_summary']) > 0:
            metrics['trade_specific_summary'].to_excel(writer, sheet_name="🔧 Trade Specific Summary", index=False)
            ws_trade = writer.sheets["🔧 Trade Specific Summary"]
            for col_num, value in enumerate(metrics['trade_specific_summary'].columns.values):
                ws_trade.write(0, col_num, value, data_header_format)
            
            # Auto-adjust column widths
            for i, col in enumerate(metrics['trade_specific_summary'].columns):
                if col == 'Top_Components' or col == 'Top_Rooms':
                    ws_trade.set_column(i, i, 40)
                else:
                    max_len = max(len(str(col)), 15) + 2
                    ws_trade.set_column(i, i, max_len)
        
        # Component Details Summary Sheet
        if len(metrics['component_details_summary']) > 0:
            metrics['component_details_summary'].to_excel(writer, sheet_name="🔍 Component Details", index=False)
            ws_component = writer.sheets["🔍 Component Details"]
            for col_num, value in enumerate(metrics['component_details_summary'].columns.values):
                ws_component.write(0, col_num, value, data_header_format)
            
            # Set column widths
            ws_component.set_column('A:A', 18)  # Trade
            ws_component.set_column('B:B', 25)  # Room
            ws_component.set_column('C:C', 30)  # Component
            ws_component.set_column('D:D', 50)  # Units with Defects
        
        # Summary sheets if requested
        if detailed_breakdown:
            summary_sheets = [
                (metrics['summary_trade'], "📊 By Trade"),
                (metrics['summary_unit'], "🏠 By Unit"),
                (metrics['summary_room'], "🚪 By Room")
            ]
            
            for summary_data, sheet_name in summary_sheets:
                if len(summary_data) > 0:
                    summary_data.to_excel(writer, sheet_name=sheet_name, index=False)
                    ws = writer.sheets[sheet_name]
                    for col_num, value in enumerate(summary_data.columns.values):
                        ws.write(0, col_num, value, data_header_format)
                    
                    # Auto-adjust column widths
                    for i, col in enumerate(summary_data.columns):
                        max_len = max(summary_data[col].astype(str).str.len().max(), len(str(col))) + 2
                        ws.set_column(i, i, min(max_len, 40))
    
    excel_buffer.seek(0)
    return excel_buffer

def display_comprehensive_results(metrics, excel_buffer, original_filename):
    """Display comprehensive processing results with enhanced visual design"""
    
    st.markdown("---")
    st.markdown("## 🎉 Processing Complete!")
    
    # Success message with enhanced styling
    st.markdown(f"""
    <div class="success-message">
        <h3>✅ Inspection Report Generated Successfully!</h3>
        <p><strong>🏢 Building:</strong> {metrics['building_name']}</p>
        <p><strong>📅 Inspection Date:</strong> {metrics['inspection_date']}</p>
        <p><strong>📍 Address:</strong> {metrics['address']}</p>
        <p><strong>📄 Source File:</strong> {original_filename}</p>
        <p><strong>⏰ Processing Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Key metrics section with enhanced cards
    st.markdown('<div class="section-header">📊 Key Inspection Metrics</div>', unsafe_allow_html=True)
    
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
    
    # Settlement Readiness section
    st.markdown('<div class="section-header">🏠 Settlement Readiness Overview</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="readiness-card ready">
            ✅ Ready (0-2 defects): {metrics['ready_units']} units ({metrics['ready_pct']:.1f}%)
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="readiness-card minor">
            ⚠️ Minor work (3-7 defects): {metrics['minor_work_units']} units ({metrics['minor_pct']:.1f}%)
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="readiness-card major">
            🔧 Major work (8-15 defects): {metrics['major_work_units']} units ({metrics['major_pct']:.1f}%)
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="readiness-card extensive">
            🚧 Extensive work (15+ defects): {metrics['extensive_work_units']} units ({metrics['extensive_pct']:.1f}%)
        </div>
        """, unsafe_allow_html=True)
    
    # Top Problem Trades section
    st.markdown('<div class="section-header">⚠️ Top Problem Trades</div>', unsafe_allow_html=True)
    
    if len(metrics['summary_trade']) > 0:
        top_5_trades = metrics['summary_trade'].head(5)
        
        for idx, (_, row) in enumerate(top_5_trades.iterrows(), 1):
            st.markdown(f"""
            <div class="trade-item">
                <strong>{idx}. {row['Trade']}</strong> - {row['DefectCount']} defects
            </div>
            """, unsafe_allow_html=True)
    
    # Component Details Preview
    if len(metrics['component_details_summary']) > 0:
        st.markdown('<div class="section-header">🔍 Component Details Analysis</div>', unsafe_allow_html=True)
        
        with st.expander("📋 View Top 15 Most Problematic Components", expanded=False):
            top_components = metrics['component_details_summary'].head(15)
            
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
            
            if len(metrics['component_details_summary']) > 15:
                st.info(f"Showing top 15 of {len(metrics['component_details_summary'])} total component issues")
    
    # Download section
    st.markdown('<div class="section-header">📥 Download Your Professional Report</div>', unsafe_allow_html=True)
    
    filename = f"{metrics['building_name'].replace(' ', '_')}_Inspection_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.download_button(
            label="📊 Download Complete Excel Report",
            data=excel_buffer,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col2:
        st.markdown(f"""
        <div class="info-card">
            <strong>📁 File Size:</strong> {len(excel_buffer.getvalue()) / 1024:.1f} KB<br>
            <strong>📄 Sheets:</strong> 8+ comprehensive tabs<br>
            <strong>📊 Format:</strong> Professional Excel Report
        </div>
        """, unsafe_allow_html=True)
    
    # Report contents with enhanced styling
    st.markdown("#### 📋 What's included in your comprehensive report:")
    
    report_contents = [
        ("📊 Executive Dashboard", "Professional summary matching your image with building info, inspection summary, settlement readiness, and top problem trades"),
        ("📋 All Inspections", "Complete detailed inspection data for all units"),
        ("🔍 Defects Only", "Filtered view showing only items with issues"),
        ("🔧 Trade Specific Summary", "Comprehensive trade analysis with priorities and affected units"),
        ("🔍 Component Details", "Shows which specific units have defects for each component"),
        ("📊 By Trade", "Defects grouped by trade category"),
        ("🏠 By Unit", "Unit-specific defect summaries"),
        ("🚪 By Room", "Room-specific analysis")
    ]
    
    for title, description in report_contents:
        st.markdown(f"""
        <div class="trade-item">
            <strong>{title}</strong><br>
            <small style="color: #666;">{description}</small>
        </div>
        """, unsafe_allow_html=True)
    
    # Final success message
    st.markdown("""
    <div style="text-align: center; margin: 2rem 0;">
        <h3 style="color: #4CAF50;">🎉 Your professional inspection report is ready!</h3>
        <p style="color: #666; font-size: 1.1rem;">The Excel file includes a beautifully formatted Executive Dashboard that matches industry standards.</p>
    </div>
    """, unsafe_allow_html=True)

def process_inspection_file(uploaded_file, trade_mapping, include_charts, detailed_breakdown, executive_summary, notification_email):
    """Process the inspection file"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("📖 Reading uploaded file...")
        progress_bar.progress(10)
        
        df = pd.read_csv(uploaded_file)
        st.success(f"✅ Loaded {len(df)} rows from inspection file: {uploaded_file.name}")
        
        status_text.text("🔄 Processing inspection data with trade mapping...")
        progress_bar.progress(40)
        
        final_df, processed_df = process_inspection_data(df, trade_mapping)
        
        progress_bar.progress(60)
        
        status_text.text("📊 Calculating metrics and generating insights...")
        
        metrics = calculate_comprehensive_metrics(final_df, processed_df)
        
        progress_bar.progress(80)
        
        status_text.text("📈 Generating Excel report...")
        
        excel_buffer = generate_enhanced_excel_report(final_df, metrics, include_charts, detailed_breakdown, executive_summary)
        
        progress_bar.progress(100)
        status_text.text("✅ Processing completed successfully!")
        
        display_comprehensive_results(metrics, excel_buffer, uploaded_file.name)
        
        if notification_email and notification_email.strip():
            st.info(f"📧 Email notification would be sent to: {notification_email}")
        
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.exception(e)

# Navigation tabs
tab1, tab2, tab3 = st.tabs(["📤 Upload & Process", "🗺️ Manage Trade Mapping", "📊 View Reports"])

with tab2:
    st.markdown("## 🗺️ Trade Mapping Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📋 Mapping Source")
        mapping_source = st.radio(
            "Choose your mapping source:",
            ["Load default mapping", "Upload custom mapping file", "Start with empty mapping"],
