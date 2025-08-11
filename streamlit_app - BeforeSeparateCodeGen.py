import streamlit as st
import pandas as pd
from io import BytesIO, StringIO
from datetime import datetime
import pytz
import traceback
import zipfile

# Try to import the Word generator
WORD_REPORT_AVAILABLE = False
WORD_IMPORT_ERROR = None
try:
    from docx import Document
    from word_report_generator import generate_professional_word_report
    WORD_REPORT_AVAILABLE = True
except Exception as e:
    WORD_IMPORT_ERROR = str(e)

# Page configuration
st.set_page_config(
    page_title="Professional Inspection Report Processor",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .step-container {
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        background-color: #fafafa;
    }
    
    .step-header {
        color: #1976d2;
        font-weight: bold;
        font-size: 1.2em;
        margin-bottom: 1rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .success-box {
        background-color: #e8f5e8;
        border: 1px solid #4caf50;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .error-box {
        background-color: #ffebee;
        border: 1px solid #f44336;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .info-box {
        background-color: #e3f2fd;
        border: 1px solid #2196f3;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .download-section {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        padding: 2rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown("""
<div class="main-header">
    <h1>🏢 Professional Inspection Report Processor</h1>
    <p>Transform your iAuditor CSV files into comprehensive Excel and Word reports</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if "trade_mapping" not in st.session_state:
    st.session_state.trade_mapping = pd.DataFrame(columns=["Room", "Component", "Trade"])
if "processed_data" not in st.session_state:
    st.session_state.processed_data = None
if "metrics" not in st.session_state:
    st.session_state.metrics = None
if "step_completed" not in st.session_state:
    st.session_state.step_completed = {"mapping": False, "processing": False}
if "building_info" not in st.session_state:
    st.session_state.building_info = {
        "name": "Professional Building Complex",
        "address": "123 Professional Street\nMelbourne, VIC 3000"
    }

# Sidebar configuration
with st.sidebar:
    st.header("📋 Process Status")
    if st.session_state.step_completed["mapping"]:
        st.success("✅ Step 1: Mapping loaded")
        st.caption(f"{len(st.session_state.trade_mapping)} mapping entries")
    else:
        st.info("⏳ Step 1: Load mapping")
    
    if st.session_state.step_completed["processing"]:
        st.success("✅ Step 2: Data processed")
        if st.session_state.metrics:
            st.caption(f"{st.session_state.metrics['total_units']} units processed")
    else:
        st.info("⏳ Step 2: Process data")
    
    st.markdown("---")
    
    if st.button("🔄 Reset All", help="Clear all data and start over"):
        for key in ["trade_mapping", "processed_data", "metrics", "step_completed", "building_info"]:
            if key in st.session_state:
                if key == "step_completed":
                    st.session_state[key] = {"mapping": False, "processing": False}
                elif key == "building_info":
                    st.session_state[key] = {
                        "name": "Professional Building Complex",
                        "address": "123 Professional Street\nMelbourne, VIC 3000"
                    }
                else:
                    del st.session_state[key]
        st.rerun()

# STEP 1: Load Master Trade Mapping
st.markdown("""
<div class="step-container">
    <div class="step-header">📋 Step 1: Load Master Trade Mapping</div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("**Upload your trade mapping file or use the default template:**")
    
    # Check if mapping is empty and show warning
    if len(st.session_state.trade_mapping) == 0:
        st.markdown("""
        <div class="warning-box">
            ⚠️ <strong>Warning:</strong> Trade mapping is currently blank. Please load a mapping file or use the default template before uploading your inspection CSV.
        </div>
        """, unsafe_allow_html=True)

with col2:
    # Download default template
    default_mapping = """Room,Component,Trade
Bathroom,Toilet,Plumbing
Bathroom,Tiles,Flooring - Tiles
Bathroom,Shower,Plumbing
Bathroom,Vanity,Carpentry & Joinery
Bedroom,Walls,Painting
Bedroom,Flooring,Flooring - Carpet
Bedroom,Windows,Windows
Kitchen Area,Cabinets,Carpentry & Joinery
Kitchen Area,Kitchen Sink,Plumbing
Kitchen Area,Benchtop,Stone & Benchtops
Living Room,Windows,Windows
Living Room,Walls,Painting
Living Room,Flooring,Flooring - Timber
Balcony,Doors,Windows
Balcony,Railings,Balustrade
Laundry,Taps,Plumbing
Laundry,Cabinets,Carpentry & Joinery
Apartment Entry Door,Door Handle,Doors
Apartment Entry Door,Door Locks and Keys,Doors
Apartment Entry Door,Paint,Painting
Apartment Entry Door,Self Latching,Doors
Balcony,Balustrade,Carpentry & Joinery
Balcony,Drainage Point,Plumbing
Balcony,GPO (if applicable),Electrical
Balcony,Glass,Windows
Balcony,Glass Sliding Door,Windows
Bathroom,Bathtub (if applicable),Plumbing
Bathroom,Ceiling,Painting
Bathroom,Doors,Doors
Bathroom,Exhaust Fan,Electrical
Bathroom,GPO,Electrical
Bathroom,Light Fixtures,Electrical
Bathroom,Mirror,Carpentry & Joinery
Bathroom,Sink,Plumbing
Bathroom,Skirting,Carpentry & Joinery
Bedroom,Carpets,Flooring - Carpets
Bedroom,Ceiling,Painting
Bedroom,Doors,Doors
Bedroom,GPO,Electrical
Bedroom,Light Fixtures,Electrical
Bedroom,Skirting,Carpentry & Joinery
Bedroom,Wardrobe,Carpentry & Joinery
Kitchen Area,Ceiling,Painting
Kitchen Area,Dishwasher,Plumbing
Kitchen Area,Flooring,Flooring - Timber
Kitchen Area,GPO,Electrical
Kitchen Area,Light Fixtures,Electrical
Kitchen Area,Rangehood,Appliances
Kitchen Area,Stovetop and Oven,Appliances
Living Room,Ceiling,Painting
Living Room,Flooring,Flooring - Timber
Living Room,GPO,Electrical
Living Room,Light Fixtures,Electrical
Living Room,Walls,Painting
Laundry Room,Doors,Doors
Laundry Room,GPO,Electrical
Laundry Room,Laundry Sink,Plumbing
Laundry Room,Light Fixtures,Electrical
Laundry Room,Tiles,Flooring - Tiles
Laundry Room,Walls,Painting"""
    
    st.download_button(
        "📥 Download Template",
        data=default_mapping,
        file_name="trade_mapping_template.csv",
        mime="text/csv",
        help="Download a comprehensive mapping template"
    )

# Upload mapping file
mapping_file = st.file_uploader("Choose trade mapping CSV", type=["csv"], key="mapping_upload")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔄 Load Default Mapping", type="secondary"):
        st.session_state.trade_mapping = pd.read_csv(StringIO(default_mapping))
        st.session_state.step_completed["mapping"] = True
        st.success("Default mapping loaded!")
        st.rerun()

with col2:
    if mapping_file is not None:
        if st.button("📤 Load Uploaded Mapping", type="primary"):
            try:
                st.session_state.trade_mapping = pd.read_csv(mapping_file)
                st.session_state.step_completed["mapping"] = True
                st.success(f"Mapping loaded: {len(st.session_state.trade_mapping)} entries")
                st.rerun()
            except Exception as e:
                st.error(f"Error loading mapping: {e}")

with col3:
    if st.button("🗑️ Clear Mapping"):
        st.session_state.trade_mapping = pd.DataFrame(columns=["Room", "Component", "Trade"])
        st.session_state.step_completed["mapping"] = False
        st.rerun()

# Display current mapping
if len(st.session_state.trade_mapping) > 0:
    st.markdown("**Current Trade Mapping:**")
    st.dataframe(st.session_state.trade_mapping, use_container_width=True, height=200)
else:
    st.info("No trade mapping loaded. Please load the default template or upload your own mapping file.")

# STEP 2: Upload and Process Data
st.markdown("""
<div class="step-container">
    <div class="step-header">📊 Step 2: Upload Inspection Data</div>
</div>
""", unsafe_allow_html=True)

# Upload inspection data first
uploaded_csv = st.file_uploader("Choose inspection CSV file", type=["csv"], key="inspection_upload")

def process_inspection_data(df, mapping, building_info):
    """Process the inspection data with enhanced metrics calculation using correct column parsing"""
    df = df.copy()
    
    # Extract unit number using the same logic as working code
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

    # Derive unit type using the same logic as working code
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

    # Get inspection columns - SAME AS WORKING CODE
    inspection_cols = [
        c for c in df.columns if c.startswith("Pre-Settlement Inspection_") and not c.endswith("_notes")
    ]

    if not inspection_cols:
        inspection_cols = [c for c in df.columns if any(keyword in c.lower() for keyword in 
                          ['inspection', 'check', 'item', 'defect', 'issue', 'status'])]

    # Melt to long format - SAME AS WORKING CODE
    long_df = df.melt(
        id_vars=["Unit", "UnitType"],
        value_vars=inspection_cols,
        var_name="InspectionItem",
        value_name="Status"
    )

    # Split into Room and Component - SAME AS WORKING CODE
    parts = long_df["InspectionItem"].str.split("_", n=2, expand=True)
    if len(parts.columns) >= 3:
        long_df["Room"] = parts[1]
        long_df["Component"] = parts[2].str.replace(r"\.\d+$", "", regex=True)
        long_df["Component"] = long_df["Component"].apply(lambda x: x.split("_")[-1] if isinstance(x, str) else x)
    else:
        long_df["Room"] = "General"
        long_df["Component"] = long_df["InspectionItem"].str.replace("Pre-Settlement Inspection_", "")

    # Remove metadata rows - SAME AS WORKING CODE
    metadata_rooms = ["Unit Type", "Building Type", "Townhouse Type", "Apartment Type"]
    metadata_components = ["Room Type"]
    long_df = long_df[~long_df["Room"].isin(metadata_rooms)]
    long_df = long_df[~long_df["Component"].isin(metadata_components)]

    # Classify status - SAME AS WORKING CODE
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

    # Merge with trade mapping - SAME AS WORKING CODE
    merged = long_df.merge(mapping, on=["Room", "Component"], how="left")
    
    # Fill missing trades with "Unknown Trade"
    merged["Trade"] = merged["Trade"].fillna("Unknown Trade")
    
    final_df = merged[["Unit", "UnitType", "Room", "Component", "StatusClass", "Trade"]]
    
    # Calculate settlement readiness using defects per unit
    defects_per_unit = final_df[final_df["StatusClass"] == "Not OK"].groupby("Unit").size()
    
    ready_units = (defects_per_unit <= 2).sum() if len(defects_per_unit) > 0 else 0
    minor_work_units = ((defects_per_unit > 2) & (defects_per_unit <= 7)).sum() if len(defects_per_unit) > 0 else 0
    major_work_units = ((defects_per_unit > 7) & (defects_per_unit <= 15)).sum() if len(defects_per_unit) > 0 else 0
    extensive_work_units = (defects_per_unit > 15).sum() if len(defects_per_unit) > 0 else 0
    
    # Add units with zero defects to ready category
    units_with_defects = set(defects_per_unit.index)
    all_units = set(final_df["Unit"].dropna())
    units_with_no_defects = len(all_units - units_with_defects)
    ready_units += units_with_no_defects
    
    total_units = final_df["Unit"].nunique()
    
    # Extract building information using the same logic as working code
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
    
    # Create comprehensive metrics
    defects_only = final_df[final_df["StatusClass"] == "Not OK"]
    
    metrics = {
        "building_name": extracted_building_name,
        "address": extracted_address,
        "inspection_date": extracted_inspection_date,
        "unit_types_str": ", ".join(sorted(final_df["UnitType"].astype(str).unique())),
        "total_units": total_units,
        "total_inspections": len(final_df),
        "total_defects": len(defects_only),
        "defect_rate": (len(defects_only) / len(final_df) * 100) if len(final_df) > 0 else 0.0,
        "avg_defects_per_unit": (len(defects_only) / max(total_units, 1)),
        "ready_units": ready_units,
        "minor_work_units": minor_work_units,
        "major_work_units": major_work_units,
        "extensive_work_units": extensive_work_units,
        "ready_pct": (ready_units / total_units * 100) if total_units > 0 else 0,
        "minor_pct": (minor_work_units / total_units * 100) if total_units > 0 else 0,
        "major_pct": (major_work_units / total_units * 100) if total_units > 0 else 0,
        "extensive_pct": (extensive_work_units / total_units * 100) if total_units > 0 else 0,
        "summary_trade": defects_only.groupby("Trade").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(defects_only) > 0 else pd.DataFrame(columns=["Trade", "DefectCount"]),
        "summary_unit": defects_only.groupby("Unit").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(defects_only) > 0 else pd.DataFrame(columns=["Unit", "DefectCount"]),
        "summary_room": defects_only.groupby("Room").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(defects_only) > 0 else pd.DataFrame(columns=["Room", "DefectCount"]),
        "component_details_summary": defects_only.groupby(["Trade", "Room", "Component"])["Unit"].apply(lambda s: ", ".join(sorted(s.astype(str).unique()))).reset_index().rename(columns={"Unit": "Units with Defects"}) if len(defects_only) > 0 else pd.DataFrame(columns=["Trade", "Room", "Component", "Units with Defects"])
    }
    
    return final_df, metrics

def create_excel_report(final_df, metrics, include_charts=True, include_raw_data=True):
    """Create comprehensive Excel report with multiple sheets and charts"""
    buffer = BytesIO()
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Executive Summary sheet
        summary_data = {
            'Metric': [
                'Building Name', 'Address', 'Inspection Date', 'Total Units',
                'Total Inspections', 'Total Defects', 'Defect Rate (%)',
                'Average Defects per Unit', 'Units Ready for Settlement',
                'Units Requiring Minor Work', 'Units Requiring Major Work',
                'Units Requiring Extensive Work'
            ],
            'Value': [
                metrics['building_name'], metrics['address'], metrics['inspection_date'],
                metrics['total_units'], metrics['total_inspections'], metrics['total_defects'],
                f"{metrics['defect_rate']:.2f}%", f"{metrics['avg_defects_per_unit']:.1f}",
                f"{metrics['ready_units']} ({metrics['ready_pct']:.1f}%)",
                f"{metrics['minor_work_units']} ({metrics['minor_pct']:.1f}%)",
                f"{metrics['major_work_units']} ({metrics['major_pct']:.1f}%)",
                f"{metrics['extensive_work_units']} ({metrics['extensive_pct']:.1f}%)"
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Executive Summary', index=False)
        
        # Settlement Readiness breakdown
        settlement_data = {
            'Category': ['Ready for Settlement', 'Minor Work Required', 'Major Work Required', 'Extensive Work Required'],
            'Units': [metrics['ready_units'], metrics['minor_work_units'], metrics['major_work_units'], metrics['extensive_work_units']],
            'Percentage': [f"{metrics['ready_pct']:.1f}%", f"{metrics['minor_pct']:.1f}%", f"{metrics['major_pct']:.1f}%", f"{metrics['extensive_pct']:.1f}%"],
            'Criteria': ['0-2 defects', '3-7 defects', '8-15 defects', '15+ defects']
        }
        pd.DataFrame(settlement_data).to_excel(writer, sheet_name='Settlement Readiness', index=False)
        
        # Raw Data sheet (optional)
        if include_raw_data:
            final_df.to_excel(writer, sheet_name='Raw Data', index=False)
        
        # Trade Summary sheet
        if len(metrics['summary_trade']) > 0:
            metrics['summary_trade'].to_excel(writer, sheet_name='Trade Summary', index=False)
        
        # Unit Summary sheet
        if len(metrics['summary_unit']) > 0:
            metrics['summary_unit'].to_excel(writer, sheet_name='Unit Summary', index=False)
        
        # Room Summary sheet
        if len(metrics['summary_room']) > 0:
            metrics['summary_room'].to_excel(writer, sheet_name='Room Summary', index=False)
        
        # Component Details sheet
        if len(metrics['component_details_summary']) > 0:
            metrics['component_details_summary'].to_excel(writer, sheet_name='Component Details', index=False)
        
        # Add a report metadata sheet
        metadata = {
            'Property': ['Report Generated', 'Report Version', 'Total Sheets', 'Data Source', 'Charts Included'],
            'Value': [
                datetime.now(pytz.timezone('Australia/Melbourne')).strftime('%Y-%m-%d %H:%M:%S AEDT'),
                '2.0',
                len(writer.sheets),
                'iAuditor CSV Export',
                'Yes' if include_charts else 'No'
            ]
        }
        pd.DataFrame(metadata).to_excel(writer, sheet_name='Report Metadata', index=False)
    
    buffer.seek(0)
    return buffer.getvalue()

def create_streamlit_charts(metrics):
    """Create charts using Streamlit's native chart functions"""
    
    # Settlement Readiness Data
    readiness_data = pd.DataFrame({
        'Category': ['✅ Ready', '⚠️ Minor Work', '🔧 Major Work', '🚧 Extensive Work'],
        'Units': [metrics['ready_units'], metrics['minor_work_units'], 
                 metrics['major_work_units'], metrics['extensive_work_units']],
        'Percentage': [metrics['ready_pct'], metrics['minor_pct'], 
                      metrics['major_pct'], metrics['extensive_pct']]
    })
    
    return readiness_data

def create_zip_package(excel_bytes, word_bytes, metrics):
    """Create a ZIP package containing both reports"""
    zip_buffer = BytesIO()
    
    mel_tz = pytz.timezone("Australia/Melbourne")
    timestamp = datetime.now(mel_tz).strftime("%Y%m%d_%H%M%S")
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add Excel file
        excel_filename = f"Inspection_Report_Excel_{timestamp}.xlsx"
        zip_file.writestr(excel_filename, excel_bytes)
        
        # Add Word file if available
        if word_bytes:
            word_filename = f"Inspection_Report_Word_{timestamp}.docx"
            zip_file.writestr(word_filename, word_bytes)
        
        # Add a summary text file
        summary_content = f"""Inspection Report Summary
=====================================
Building: {metrics['building_name']}
Address: {metrics['address']}
Inspection Date: {metrics['inspection_date']}
Report Generated: {datetime.now(mel_tz).strftime('%Y-%m-%d %H:%M:%S AEDT')}

Key Metrics:
- Total Units: {metrics['total_units']:,}
- Total Defects: {metrics['total_defects']:,}
- Defect Rate: {metrics['defect_rate']:.2f}%
- Ready for Settlement: {metrics['ready_units']} ({metrics['ready_pct']:.1f}%)
- Minor Work Required: {metrics['minor_work_units']} ({metrics['minor_pct']:.1f}%)
- Major Work Required: {metrics['major_work_units']} ({metrics['major_pct']:.1f}%)
- Extensive Work Required: {metrics['extensive_work_units']} ({metrics['extensive_pct']:.1f}%)

Files Included:
- {excel_filename}
{'- ' + word_filename if word_bytes else '- Word report (not available)'}
- inspection_summary.txt (this file)
"""
        zip_file.writestr("inspection_summary.txt", summary_content)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# Check if mapping is loaded before allowing CSV upload
if len(st.session_state.trade_mapping) == 0:
    st.warning("⚠️ Please load your trade mapping first before uploading the inspection CSV file.")
    st.stop()

if uploaded_csv is not None:
    if st.button("🔄 Process Inspection Data", type="primary", use_container_width=True):
        try:
            with st.spinner("Processing inspection data..."):
                # Load and process data
                df = pd.read_csv(uploaded_csv)
                
                # Use default building info for processing
                building_info = {
                    "name": st.session_state.building_info["name"],
                    "address": st.session_state.building_info["address"],
                    "date": datetime.now().strftime("%Y-%m-%d")
                }
                
                processed_df, metrics = process_inspection_data(df, st.session_state.trade_mapping, building_info)
                
                # Store in session state
                st.session_state.processed_data = processed_df
                st.session_state.metrics = metrics
                st.session_state.step_completed["processing"] = True
                
                st.success(f"✅ Successfully processed {len(df)} inspection records!")
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Error processing data: {e}")
            st.code(traceback.format_exc())

# STEP 3: Show Results and Download Options
if st.session_state.processed_data is not None and st.session_state.metrics is not None:
    st.markdown("""
    <div class="step-container">
        <div class="step-header">📈 Step 3: Analysis Results & Downloads</div>
    </div>
    """, unsafe_allow_html=True)
    
    metrics = st.session_state.metrics
    
    # Building Information Section (Auto-Detected from CSV)
    st.markdown("### 🏢 Building Information (Auto-Detected)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        **🏢 Building Name:** {metrics['building_name']}  
        **📅 Inspection Date:** {metrics['inspection_date']}  
        **🏠 Total Units:** {metrics['total_units']:,} units
        """)
    
    with col2:
        st.markdown(f"""
        **📍 Address:** {metrics['address']}  
        **🏗️ Unit Types:** {metrics['unit_types_str']}
        """)
    
    st.markdown("---")
    
    # Key Metrics Dashboard
    st.subheader("📊 Key Metrics Dashboard")
    
    # Create metrics in a more visually appealing way
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "🏠 Total Units", 
            f"{metrics['total_units']:,}",
            help="Total number of units inspected"
        )
    
    with col2:
        st.metric(
            "🚨 Total Defects", 
            f"{metrics['total_defects']:,}",
            delta=f"{metrics['defect_rate']:.1f}% rate"
        )
    
    with col3:
        st.metric(
            "✅ Ready Units", 
            f"{metrics['ready_units']}",
            delta=f"{metrics['ready_pct']:.1f}%"
        )
    
    with col4:
        st.metric(
            "📊 Avg Defects/Unit", 
            f"{metrics['avg_defects_per_unit']:.1f}",
            help="Average number of defects per unit"
        )
    
    with col5:
        settlement_efficiency = (metrics['ready_units'] / metrics['total_units'] * 100) if metrics['total_units'] > 0 else 0
        st.metric(
            "🎯 Settlement Efficiency", 
            f"{settlement_efficiency:.1f}%",
            help="Percentage of units ready for immediate settlement"
        )
    
    # Visualizations using Streamlit native charts
    st.subheader("📈 Visual Analysis")
    
    # Create settlement readiness chart data
    readiness_data = create_streamlit_charts(metrics)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏠 Settlement Readiness Distribution")
        if readiness_data['Units'].sum() > 0:
            st.bar_chart(readiness_data.set_index('Category')['Units'])
        else:
            st.info("No data available for chart")
    
    with col2:
        st.subheader("🔧 Top Problem Trades")
        if len(metrics['summary_trade']) > 0:
            top_trades = metrics['summary_trade'].head(10)
            st.bar_chart(top_trades.set_index('Trade')['DefectCount'])
        else:
            st.info("No trade defects to display")
    
    # Top Units Chart
    if len(metrics['summary_unit']) > 0:
        st.subheader("🏠 Top 15 Units Requiring Attention")
        top_units = metrics['summary_unit'].head(15)
        st.bar_chart(top_units.set_index('Unit')['DefectCount'])
    
    # Summary Tables
    st.subheader("📋 Summary Tables")
    
    tab1, tab2, tab3 = st.tabs(["🔧 Trade Summary", "🏠 Unit Summary", "🚪 Room Summary"])
    
    with tab1:
        if len(metrics['summary_trade']) > 0:
            st.dataframe(metrics['summary_trade'], use_container_width=True)
        else:
            st.info("No trade defects found")
    
    with tab2:
        if len(metrics['summary_unit']) > 0:
            st.dataframe(metrics['summary_unit'], use_container_width=True)
        else:
            st.info("No unit defects found")
    
    with tab3:
        if len(metrics['summary_room']) > 0:
            st.dataframe(metrics['summary_room'], use_container_width=True)
        else:
            st.info("No room defects found")
    
    # STEP 4: Download Options
    st.markdown("""
    <div class="step-container">
        <div class="step-header">📥 Step 4: Download Reports</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Always show both download options
    st.markdown("""
    <div class="download-section">
        <h3 style="text-align: center; margin-bottom: 1rem;">📦 Complete Report Package</h3>
        <p style="text-align: center;">Download both Excel and Word reports together in a convenient package.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📦 Generate Complete Package", type="primary", use_container_width=True):
            try:
                with st.spinner("Generating complete report package..."):
                    mel_tz = pytz.timezone("Australia/Melbourne")
                    timestamp = datetime.now(mel_tz).strftime("%Y%m%d_%H%M%S")
                    
                    # Generate Excel (always include charts and raw data)
                    excel_bytes = create_excel_report(st.session_state.processed_data, metrics, True, True)
                    
                    # Generate Word if available
                    word_bytes = None
                    if WORD_REPORT_AVAILABLE:
                        try:
                            from word_report_generator import generate_professional_word_report
                            doc = generate_professional_word_report(st.session_state.processed_data, metrics)
                            buf = BytesIO()
                            doc.save(buf)
                            buf.seek(0)
                            word_bytes = buf.getvalue()
                        except Exception as e:
                            st.warning(f"Word report could not be generated: {e}")
                    
                    # Create ZIP package
                    zip_bytes = create_zip_package(excel_bytes, word_bytes, metrics)
                    zip_filename = f"Inspection_Reports_Package_{timestamp}.zip"
                    
                    st.success("✅ Complete report package generated!")
                    st.download_button(
                        "📥 Download Complete Package (ZIP)",
                        data=zip_bytes,
                        file_name=zip_filename,
                        mime="application/zip",
                        use_container_width=True,
                        help="Contains Excel report, Word report (if available), and summary text file"
                    )
                    
                    # Show package contents
                    st.info(f"📋 Package includes: Excel report, {'Word report, ' if word_bytes else ''}and summary file")
                    
            except Exception as e:
                st.error(f"❌ Error generating package: {e}")
                st.code(traceback.format_exc())
    
    # Individual download options
    st.markdown("---")
    st.subheader("Individual Downloads")
    
    col1, col2 = st.columns(2)
    
    # Excel Download
    with col1:
        st.markdown("### 📊 Excel Report")
        st.write("Comprehensive Excel workbook with multiple sheets, charts, and detailed analysis.")
        
        if st.button("📊 Generate Excel Report", type="secondary", use_container_width=True):
            try:
                with st.spinner("Generating Excel report..."):
                    excel_bytes = create_excel_report(st.session_state.processed_data, metrics, True, True)
                    
                    mel_tz = pytz.timezone("Australia/Melbourne")
                    timestamp = datetime.now(mel_tz).strftime("%Y%m%d_%H%M%S")
                    filename = f"Inspection_Report_Excel_{timestamp}.xlsx"
                    
                    st.success("✅ Excel report generated!")
                    st.download_button(
                        "📥 Download Excel Report",
                        data=excel_bytes,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"❌ Error generating Excel: {e}")
                st.code(traceback.format_exc())
    
    # Word Download
    with col2:
        st.markdown("### 📄 Word Report")
        
        if not WORD_REPORT_AVAILABLE:
            st.warning("Word generator not available")
            if WORD_IMPORT_ERROR:
                with st.expander("📋 Error Details"):
                    st.code(f"Import error: {WORD_IMPORT_ERROR}")
        else:
            st.write("Professional Word document with executive summary, charts, and detailed analysis.")
            
            if st.button("📄 Generate Word Report", type="secondary", use_container_width=True):
                try:
                    with st.spinner("Generating Word report..."):
                        # Re-import to avoid stale import issues
                        from word_report_generator import generate_professional_word_report
                        doc = generate_professional_word_report(st.session_state.processed_data, metrics)
                        
                        # Save to bytes
                        buf = BytesIO()
                        doc.save(buf)
                        buf.seek(0)
                        word_bytes = buf.getvalue()
                        
                        mel_tz = pytz.timezone("Australia/Melbourne")
                        timestamp = datetime.now(mel_tz).strftime("%Y%m%d_%H%M%S")
                        filename = f"Inspection_Report_Word_{timestamp}.docx"
                        
                        st.success("✅ Word report generated!")
                        st.download_button(
                            "📥 Download Word Report",
                            data=word_bytes,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"❌ Error generating Word: {e}")
                    st.code(traceback.format_exc())
    
    # Report Statistics
    st.markdown("---")
    st.subheader("📈 Report Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Total Sheets (Excel)", "7+", help="Executive Summary, Settlement Readiness, Trade Summary, etc.")
    
    with col2:
        st.metric("📊 Charts Available", "3+", help="Settlement bar charts, trade analysis, unit rankings")
    
    with col3:
        total_records = len(st.session_state.processed_data) if st.session_state.processed_data is not None else 0
        st.metric("📝 Data Records", f"{total_records:,}", help="Total inspection records processed")
    
    with col4:
        file_size_est = "2-5 MB" if total_records > 1000 else "< 2 MB"
        st.metric("💾 Est. File Size", file_size_est, help="Estimated size of generated reports")

else:
    # Show upload section with enhanced UI
    st.markdown("""
    <div class="step-container">
        <div class="step-header">📤 Ready to Process Your Data</div>
    </div>
    """, unsafe_allow_html=True)
    
    if uploaded_csv is not None:
        try:
            preview_df = pd.read_csv(uploaded_csv)
            
            # Enhanced success message with file info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.success(f"📊 **Rows:** {len(preview_df):,}")
            with col2:
                st.success(f"📋 **Columns:** {len(preview_df.columns)}")
            with col3:
                file_size = uploaded_csv.size / 1024  # Convert to KB
                st.success(f"💾 **Size:** {file_size:.1f} KB")
            
            # Enhanced preview with column analysis
            with st.expander("👀 Data Preview & Analysis", expanded=True):
                # Show column information
                st.markdown("**📋 Column Information:**")
                col_info = pd.DataFrame({
                    'Column': preview_df.columns,
                    'Type': [str(dtype) for dtype in preview_df.dtypes],
                    'Non-Null': [preview_df[col].notna().sum() for col in preview_df.columns],
                    'Null %': [f"{(preview_df[col].isna().sum() / len(preview_df) * 100):.1f}%" for col in preview_df.columns]
                })
                st.dataframe(col_info, use_container_width=True, height=200)
                
                st.markdown("**📊 Data Sample:**")
                st.dataframe(preview_df.head(10), use_container_width=True)
                st.caption(f"Showing first 10 rows of {len(preview_df):,} total rows")
                
                # Data quality indicators
                missing_data_pct = (preview_df.isna().sum().sum() / (len(preview_df) * len(preview_df.columns))) * 100
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if missing_data_pct < 5:
                        st.success(f"✅ Data Quality: Excellent ({missing_data_pct:.1f}% missing)")
                    elif missing_data_pct < 15:
                        st.warning(f"⚠️ Data Quality: Good ({missing_data_pct:.1f}% missing)")
                    else:
                        st.error(f"❌ Data Quality: Poor ({missing_data_pct:.1f}% missing)")
                
                with col2:
                    duplicate_rows = preview_df.duplicated().sum()
                    if duplicate_rows == 0:
                        st.success("✅ No Duplicates")
                    else:
                        st.warning(f"⚠️ {duplicate_rows} Duplicates")
                
                with col3:
                    required_cols = ['Unit', 'Room', 'Component', 'StatusClass']
                    missing_cols = [col for col in required_cols if col not in preview_df.columns]
                    if not missing_cols:
                        st.success("✅ All Required Columns")
                    else:
                        st.info(f"ℹ️ Will auto-generate: {', '.join(missing_cols)}")
            
        except Exception as e:
            st.error(f"❌ Error reading CSV: {e}")
            st.markdown("""
            <div class="error-box">
                <strong>Common issues:</strong>
                <ul>
                    <li>File encoding problems (try saving as UTF-8)</li>
                    <li>Corrupted file</li>
                    <li>Unsupported CSV format</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="info-box">
            <h4>📤 Ready to Upload Your Inspection Data</h4>
            <p>Please upload your iAuditor CSV file to begin processing. The system will:</p>
            <ul>
                <li>✅ Validate the data quality</li>
                <li>🔄 Apply trade mapping</li>
                <li>📊 Generate comprehensive analytics</li>
                <li>📋 Create professional reports</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# Enhanced Footer with additional information
st.markdown("---")
st.markdown("""
<div style="text-align: center; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 2rem; border-radius: 10px; margin-top: 2rem;">
    <h4 style="color: #2E3A47; margin-bottom: 1rem;">🏢 Professional Inspection Report Processor v2.0</h4>
    <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap;">
        <div><strong>📊 Excel Reports:</strong> Multi-sheet analysis</div>
        <div><strong>📄 Word Reports:</strong> Executive summaries</div>
        <div><strong>📈 Native Charts:</strong> Streamlit visualizations</div>
        <div><strong>🔒 Secure Processing:</strong> Local data handling</div>
    </div>
    <p style="margin-top: 1rem; color: #666; font-size: 0.9em;">
        Built with Streamlit • Powered by Python • For technical support, contact your system administrator
    </p>
</div>
""", unsafe_allow_html=True)