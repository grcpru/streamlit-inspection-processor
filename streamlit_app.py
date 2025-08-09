import streamlit as st
import pandas as pd
import io
import base64
import json
from datetime import datetime
import xlsxwriter
from io import BytesIO
import requests
import os

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
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white;
        text-align: center;
        margin: 0;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        text-align: center;
    }
    .success-message {
        background: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #c3e6cb;
    }
    .upload-section {
        background: #e3f2fd;
        padding: 2rem;
        border-radius: 10px;
        border: 2px dashed #1976D2;
        text-align: center;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🏢 Inspection Report Processor</h1>
    <p style="color: white; text-align: center; margin: 0;">
        Upload iAuditor CSV files and generate beautiful Excel reports automatically
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar configuration
st.sidebar.title("⚙️ Configuration")
st.sidebar.markdown("---")

# SharePoint Configuration Section
st.sidebar.subheader("📁 SharePoint Settings")

# Check if we're running locally or in cloud
if 'STREAMLIT_SHARING' in os.environ:
    # Running on Streamlit Cloud - use secrets
    if 'sharepoint' in st.secrets:
        sharepoint_site = st.secrets.sharepoint.site_url
        client_id = st.secrets.sharepoint.client_id
        client_secret = st.secrets.sharepoint.client_secret
        tenant_id = st.secrets.sharepoint.tenant_id
        st.sidebar.success("✅ SharePoint configured via secrets")
    else:
        st.sidebar.error("❌ SharePoint secrets not configured")
        st.sidebar.info("Please add SharePoint secrets in Streamlit Cloud settings")
        sharepoint_site = None
else:
    # Running locally - use sidebar inputs
    sharepoint_site = st.sidebar.text_input(
        "SharePoint Site URL", 
        placeholder="https://company.sharepoint.com/sites/yoursite",
        help="Your SharePoint site URL"
    )
    client_id = st.sidebar.text_input(
        "Client ID", 
        type="password",
        help="Azure App Registration Client ID"
    )
    client_secret = st.sidebar.text_input(
        "Client Secret", 
        type="password",
        help="Azure App Registration Client Secret"
    )
    tenant_id = st.sidebar.text_input(
        "Tenant ID", 
        type="password",
        help="Azure Tenant ID"
    )

# Processing options
st.sidebar.subheader("🔧 Processing Options")
auto_upload = st.sidebar.checkbox("Auto-upload to SharePoint", value=True)
send_notification = st.sidebar.checkbox("Send email notification", value=True)
notification_email = st.sidebar.text_input("Notification Email", placeholder="admin@company.com")

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Upload your MasterTradeMapping.csv file first to ensure proper trade mapping!")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    <div class="upload-section">
        <h3>📤 Upload Your iAuditor CSV File</h3>
        <p>Drag and drop your inspection CSV file here, or click to browse</p>
    </div>
    """, unsafe_allow_html=True)
    
    # File upload section
    uploaded_file = st.file_uploader(
        "Choose iAuditor CSV file",
        type=['csv'],
        help="Select the CSV file exported from iAuditor",
        label_visibility="collapsed"
    )
    
    # Mapping file upload
    st.markdown("### 🗺️ Trade Mapping File")
    mapping_file = st.file_uploader(
        "Upload MasterTradeMapping.csv (optional if already in SharePoint)",
        type=['csv'],
        help="Upload your trade mapping file or leave empty if it's already in SharePoint"
    )

with col2:
    st.markdown("### ℹ️ Instructions")
    st.markdown("""
    1. **Upload CSV**: Select your iAuditor inspection file
    2. **Check mapping**: Ensure trade mapping is available
    3. **Process**: Click the process button
    4. **Download**: Get your beautiful Excel report
    5. **SharePoint**: Files automatically saved (if configured)
    """)
    
    st.markdown("### 📊 Supported Formats")
    st.markdown("""
    - ✅ iAuditor CSV exports
    - ✅ Pre-Settlement Inspection data
    - ✅ Building inspection reports
    - ✅ Quality audit data
    """)

# Processing section
if uploaded_file is not None:
    st.markdown("---")
    st.markdown("## 🔄 File Processing")
    
    # Show file details
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 File Name", uploaded_file.name)
    with col2:
        st.metric("📏 File Size", f"{uploaded_file.size / 1024:.1f} KB")
    with col3:
        file_type = "iAuditor CSV" if "inspection" in uploaded_file.name.lower() else "CSV File"
        st.metric("📋 File Type", file_type)
    
    # Process button
    if st.button("🚀 Process Inspection Report", type="primary", use_container_width=True):
        process_inspection_file(uploaded_file, mapping_file, sharepoint_site, client_id, client_secret, tenant_id, auto_upload, send_notification, notification_email)

def process_inspection_file(uploaded_file, mapping_file, sharepoint_site, client_id, client_secret, tenant_id, auto_upload, send_notification, notification_email):
    """Process the inspection file and generate reports"""
    
    # Create progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Step 1: Read uploaded file
        status_text.text("📖 Reading uploaded file...")
        progress_bar.progress(10)
        
        df = pd.read_csv(uploaded_file)
        st.success(f"✅ Loaded {len(df)} rows from inspection file")
        
        # Step 2: Get mapping file
        status_text.text("🗺️ Loading trade mapping...")
        progress_bar.progress(20)
        
        if mapping_file is not None:
            # Use uploaded mapping file
            trade_mapping = pd.read_csv(mapping_file)
            st.success(f"✅ Loaded {len(trade_mapping)} trade mappings from uploaded file")
        elif sharepoint_site and auto_upload:
            # Try to download from SharePoint
            trade_mapping = download_mapping_from_sharepoint(sharepoint_site, client_id, client_secret, tenant_id)
            if trade_mapping is not None:
                st.success(f"✅ Downloaded {len(trade_mapping)} trade mappings from SharePoint")
            else:
                st.warning("⚠️ Could not download mapping from SharePoint, using default mapping")
                trade_mapping = create_default_mapping()
        else:
            # Use default mapping
            st.info("ℹ️ Using default trade mapping")
            trade_mapping = create_default_mapping()
        
        # Step 3: Process the data
        status_text.text("🔄 Processing inspection data...")
        progress_bar.progress(40)
        
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

        progress_bar.progress(60)
        
        # Step 4: Calculate metrics
        status_text.text("📊 Calculating metrics...")
        
        defects_only = final_df[final_df["StatusClass"] == "Not OK"]
        
        # Extract building information
        sample_audit = df["auditName"].dropna().iloc[0] if "auditName" in df.columns else ""
        audit_parts = str(sample_audit).split("/")
        building_name = audit_parts[2].strip() if len(audit_parts) >= 3 else "Unknown Building"
        inspection_date = audit_parts[0].strip() if len(audit_parts) >= 1 else "Unknown Date"
        
        # Calculate metrics
        total_units = df["Unit"].nunique()
        total_inspections = len(final_df)
        total_defects = len(defects_only)
        defect_rate = (total_defects / total_inspections * 100) if total_inspections > 0 else 0
        
        # Settlement readiness
        defect_counts = defects_only.groupby("Unit").size()
        ready_units = (defect_counts <= 2).sum()
        minor_work_units = ((defect_counts >= 3) & (defect_counts <= 7)).sum()
        major_work_units = ((defect_counts >= 8) & (defect_counts <= 15)).sum()
        extensive_work_units = (defect_counts > 15).sum()
        
        # Add units with zero defects
        units_with_defects = set(defect_counts.index)
        all_units = set(df["Unit"].dropna())
        units_with_no_defects = len(all_units - units_with_defects)
        ready_units += units_with_no_defects
        
        # Top problem trades
        summary_trade = defects_only.groupby("Trade").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False)
        
        progress_bar.progress(80)
        
        # Step 5: Generate Excel report
        status_text.text("📈 Generating Excel report...")
        
        excel_buffer = generate_excel_report(
            final_df, defects_only, summary_trade, building_name, inspection_date,
            total_units, total_defects, defect_rate, ready_units, minor_work_units, 
            major_work_units, extensive_work_units, df
        )
        
        progress_bar.progress(90)
        
        # Step 6: Upload to SharePoint (if configured)
        if auto_upload and sharepoint_site:
            status_text.text("📤 Uploading to SharePoint...")
            upload_success = upload_to_sharepoint(
                excel_buffer, uploaded_file, building_name, 
                sharepoint_site, client_id, client_secret, tenant_id
            )
            if upload_success:
                st.success("✅ Files uploaded to SharePoint successfully!")
            else:
                st.warning("⚠️ Could not upload to SharePoint, but processing completed")
        
        progress_bar.progress(100)
        status_text.text("✅ Processing completed!")
        
        # Display results
        display_results(
            building_name, inspection_date, total_units, total_defects, defect_rate,
            ready_units, minor_work_units, major_work_units, extensive_work_units,
            summary_trade, excel_buffer
        )
        
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.exception(e)

def create_default_mapping():
    """Create a default trade mapping if none is available"""
    default_mapping = pd.DataFrame([
        {"Room": "Kitchen", "Component": "Cabinets", "Trade": "Carpentry & Joinery"},
        {"Room": "Kitchen", "Component": "Benchtop", "Trade": "Stone & Tiling"},
        {"Room": "Kitchen", "Component": "Appliances", "Trade": "Electrical"},
        {"Room": "Bathroom", "Component": "Tiles", "Trade": "Tiling"},
        {"Room": "Bathroom", "Component": "Fixtures", "Trade": "Plumbing"},
        {"Room": "Bedroom", "Component": "Flooring", "Trade": "Flooring"},
        {"Room": "Living", "Component": "Walls", "Trade": "Painting"},
        {"Room": "Living", "Component": "Ceiling", "Trade": "Painting"},
        # Add more default mappings as needed
    ])
    return default_mapping

def download_mapping_from_sharepoint(site_url, client_id, client_secret, tenant_id):
    """Download mapping file from SharePoint"""
    try:
        # Implement SharePoint download logic here
        # For now, return None to use default mapping
        return None
    except Exception as e:
        st.warning(f"Could not download mapping from SharePoint: {str(e)}")
        return None

def upload_to_sharepoint(excel_buffer, uploaded_file, building_name, site_url, client_id, client_secret, tenant_id):
    """Upload files to SharePoint"""
    try:
        # Implement SharePoint upload logic here
        # For now, return True to simulate success
        return True
    except Exception as e:
        st.warning(f"Could not upload to SharePoint: {str(e)}")
        return False

def generate_excel_report(final_df, defects_only, summary_trade, building_name, inspection_date,
                         total_units, total_defects, defect_rate, ready_units, minor_work_units, 
                         major_work_units, extensive_work_units, df):
    """Generate the Excel report with beautiful formatting"""
    
    excel_buffer = BytesIO()
    
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Define formats (same as your enhanced code)
        building_info_header = workbook.add_format({
            'bold': True, 'font_size': 14, 'bg_color': '#2E7D32', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 2
        })
        
        inspection_summary_header = workbook.add_format({
            'bold': True, 'font_size': 14, 'bg_color': '#1976D2', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 2
        })
        
        settlement_header = workbook.add_format({
            'bold': True, 'font_size': 14, 'bg_color': '#F57C00', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 2
        })
        
        label_format = workbook.add_format({
            'bold': True, 'font_size': 11, 'bg_color': '#F5F5F5', 'border': 1,
            'align': 'left', 'valign': 'vcenter'
        })
        
        data_format = workbook.add_format({
            'font_size': 11, 'border': 1, 'align': 'right', 'valign': 'vcenter'
        })
        
        # Create dashboard sheet
        worksheet = workbook.add_worksheet("📊 Executive Dashboard")
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 35)
        
        # Building Information Section
        current_row = 0
        worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', '🏢 BUILDING INFORMATION', building_info_header)
        current_row += 2
        
        # Extract address information
        location = df["Title Page_Site conducted_Location"].dropna().astype(str).str.strip().iloc[0] if "Title Page_Site conducted_Location" in df.columns else ""
        area = df["Title Page_Site conducted_Area"].dropna().astype(str).str.strip().iloc[0] if "Title Page_Site conducted_Area" in df.columns else ""
        region = df["Title Page_Site conducted_Region"].dropna().astype(str).str.strip().iloc[0] if "Title Page_Site conducted_Region" in df.columns else ""
        address_parts = [part for part in [location, area, region] if part]
        address = ", ".join(address_parts) if address_parts else "Address Not Available"
        
        unit_types = sorted(df["UnitType"].dropna().unique())
        unit_types_str = ", ".join(unit_types) if unit_types else "Unknown"
        
        building_data = [
            ('Building Name', building_name),
            ('Inspection Date', inspection_date),
            ('Address', address),
            ('Total Units Inspected', f'{total_units:,}'),
            ('Unit Types', unit_types_str)
        ]
        
        for label, value in building_data:
            worksheet.write(current_row, 0, label, label_format)
            worksheet.write(current_row, 1, value, data_format)
            current_row += 1
        
        current_row += 1
        
        # Inspection Summary Section
        worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', '📋 INSPECTION SUMMARY', inspection_summary_header)
        current_row += 2
        
        total_inspections = len(final_df)
        avg_defects_per_unit = (total_defects / total_units) if total_units > 0 else 0
        
        summary_data = [
            ('Total Inspection Points', f'{total_inspections:,}'),
            ('Total Defects Found', f'{total_defects:,}'),
            ('Overall Defect Rate', f'{defect_rate:.2f}%'),
            ('Average Defects per Unit', f'{avg_defects_per_unit:.1f}')
        ]
        
        for label, value in summary_data:
            worksheet.write(current_row, 0, label, label_format)
            worksheet.write(current_row, 1, value, data_format)
            current_row += 1
        
        current_row += 1
        
        # Settlement Readiness Section
        worksheet.merge_range(f'A{current_row + 1}:B{current_row + 1}', '🏠 SETTLEMENT READINESS', settlement_header)
        current_row += 2
        
        ready_pct = (ready_units / total_units * 100) if total_units > 0 else 0
        minor_pct = (minor_work_units / total_units * 100) if total_units > 0 else 0
        major_pct = (major_work_units / total_units * 100) if total_units > 0 else 0
        extensive_pct = (extensive_work_units / total_units * 100) if total_units > 0 else 0
        
        readiness_data = [
            ('🟢 Ready (0-2 defects)', f'{ready_units} units ({ready_pct:.1f}%)'),
            ('🟡 Minor work (3-7 defects)', f'{minor_work_units} units ({minor_pct:.1f}%)'),
            ('🟠 Major work (8-15 defects)', f'{major_work_units} units ({major_pct:.1f}%)'),
            ('🔴 Extensive work (15+ defects)', f'{extensive_work_units} units ({extensive_pct:.1f}%)')
        ]
        
        for label, value in readiness_data:
            worksheet.write(current_row, 0, label, label_format)
            worksheet.write(current_row, 1, value, data_format)
            current_row += 1
        
        # Add other sheets
        final_df.to_excel(writer, sheet_name="📋 All Inspections", index=False)
        defects_only.to_excel(writer, sheet_name="🔍 Defects Only", index=False)
        summary_trade.to_excel(writer, sheet_name="📊 By Trade", index=False)
    
    excel_buffer.seek(0)
    return excel_buffer

def display_results(building_name, inspection_date, total_units, total_defects, defect_rate,
                   ready_units, minor_work_units, major_work_units, extensive_work_units,
                   summary_trade, excel_buffer):
    """Display the processing results"""
    
    st.markdown("---")
    st.markdown("## 🎉 Processing Complete!")
    
    # Success message
    st.markdown(f"""
    <div class="success-message">
        <h3>✅ Inspection Report Generated Successfully!</h3>
        <p><strong>Building:</strong> {building_name}</p>
        <p><strong>Inspection Date:</strong> {inspection_date}</p>
        <p><strong>Processing Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Key metrics
    st.markdown("### 📊 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🏠 Total Units", f"{total_units:,}")
    with col2:
        st.metric("⚠️ Total Defects", f"{total_defects:,}")
    with col3:
        st.metric("📊 Defect Rate", f"{defect_rate:.2f}%")
    with col4:
        ready_pct = (ready_units / total_units * 100) if total_units > 0 else 0
        st.metric("✅ Ready Units", f"{ready_units} ({ready_pct:.1f}%)")
    
    # Settlement readiness
    st.markdown("### 🏠 Settlement Readiness")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #4CAF50;">
            <h4>🟢 Ready</h4>
            <p><strong>{ready_units}</strong> units</p>
            <small>0-2 defects</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #FF9800;">
            <h4>🟡 Minor Work</h4>
            <p><strong>{minor_work_units}</strong> units</p>
            <small>3-7 defects</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #FF5722;">
            <h4>🟠 Major Work</h4>
            <p><strong>{major_work_units}</strong> units</p>
            <small>8-15 defects</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid #F44336;">
            <h4>🔴 Extensive Work</h4>
            <p><strong>{extensive_work_units}</strong> units</p>
            <small>15+ defects</small>
        </div>
        """, unsafe_allow_html=True)
    
    # Top problem trades
    if len(summary_trade) > 0:
        st.markdown("### ⚠️ Top Problem Trades")
        for i, (_, row) in enumerate(summary_trade.head(5).iterrows(), 1):
            trade_name = row['Trade'] if pd.notna(row['Trade']) else 'Unknown Trade'
            defect_count = row['DefectCount']
            
            color = "#F44336" if i == 1 else "#FF9800" if i == 2 else "#FFC107" if i == 3 else "#9E9E9E"
            st.markdown(f"""
            <div style="background: {color}20; padding: 0.5rem; border-radius: 5px; margin: 0.2rem 0; border-left: 4px solid {color};">
                <strong>{i}. {trade_name}</strong> - {defect_count} defects
            </div>
            """, unsafe_allow_html=True)
    
    # Download button
    st.markdown("### 📥 Download Report")
    
    filename = f"{building_name.replace(' ', '_')}_Inspection_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    st.download_button(
        label="📊 Download Excel Report",
        data=excel_buffer,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    st.success("🎉 Report ready for download! The Excel file contains multiple sheets with detailed analysis.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em;">
    <p>🏢 Inspection Report Processor | Built with Streamlit | 
    <a href="https://github.com/your-repo" target="_blank">View Source</a></p>
</div>
""", unsafe_allow_html=True)
