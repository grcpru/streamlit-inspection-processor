with tab2:
    st.markdown("## 🗺️ Trade Mapping Management")
    st.markdown("Upload your master trade mapping CSV file to get started")
    
    # Mapping source selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📋 Mapping Source")
        mapping_source = st.radio(
            "Choose your mapping source:",
            ["Upload master mapping CSV", "Start with empty mapping", "Use current mapping"],
            help="Upload your master CSV file with Room, Component, Trade columns"
        )
    
    with col2:
        st.markdown("### 🔧 Actions")
        if st.button("🔄 Clear All Mappings"):
            st.session_state.trade_mapping = pd.DataFrame(columns=['Room', 'Component', 'Trade'])
            st.session_state.mapping_edited = True
            st.success("✅ All mappings cleared")
        
        if st.button("📥 Download Current Mapping"):
            if st.session_state.trade_mapping is not None and len(st.session_state.trade_mapping) > 0:
                csv = st.session_state.trade_mapping.to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv,
                    file_name=f"trade_mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No mapping data to download")
    
    # Handle mapping source selection
    if mapping_source == "Upload master mapping CSV":
        st.markdown("#### 📤 Upload Your Master Trade Mapping")
        uploaded_mapping = st.file_uploader(
            "Upload Master Trade Mapping CSV",
            type=['csv'],
            help="Upload your CSV file with columns: Room, Component, Trade",
            key="master_mapping_upload"
        )
        
        if uploaded_mapping is not None:
            try:
                # Read the uploaded file
                mapping_df = pd.read_csv(uploaded_mapping)
                
                # Validate required columns
                required_cols = ['Room', 'Component', 'Trade']
                if all(col in mapping_df.columns for col in required_cols):
                    
                    # Display preview
                    st.markdown("#### 🔍 Preview of Uploaded Mapping")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Mappings", len(mapping_df))
                    with col2:
                        st.metric("Unique Rooms", mapping_df['Room'].nunique())
                    with col3:
                        st.metric("Unique Trades", mapping_df['Trade'].nunique())
                    
                    # Show first 10 rows
                    st.dataframe(mapping_df.head(10), use_container_width=True)
                    if len(mapping_df) > 10:
                        st.info(f"Showing first 10 of {len(mapping_df)} total mappings")
                    
                    # Option to use this mapping
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        use_uploaded = st.checkbox(
                            f"✅ Use this mapping as my master trade mapping ({len(mapping_df)} entries)",
                            key="use_uploaded_mapping"
                        )
                    
                    with col2:
                        if st.button("🚀 Apply Mapping", type="primary"):
                            if use_uploaded:
                                st.session_state.trade_mapping = mapping_df.copy()
                                st.session_state.mapping_edited = True
                                st.success(f"✅ Applied {len(mapping_df)} trade mappings successfully!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.warning("Please check the box to confirm using this mapping")
                    
                    # Show trade distribution
                    if len(mapping_df) > 0:
                        st.markdown("#### 📊 Trade Distribution")
                        trade_counts = mapping_df['Trade'].value_counts()
                        
                        # Create columns for trade counts
                        cols = st.columns(min(len(trade_counts), 5))
                        for i, (trade, count) in enumerate(trade_counts.head(5).items()):
                            with cols[i % 5]:
                                st.metric(trade, count)
                        
                        if len(trade_counts) > 5:
                            st.info(f"Showing top 5 trades. Total unique trades: {len(trade_counts)}")
                
                else:
                    st.error("❌ CSV must have columns: Room, Component, Trade")
                    st.markdown("**Expected format:**")
                    st.code("""Room,Component,Trade
Apartment Entry Door,Door Handle,Doors
Bathroom,Ceiling,Painting
Kitchen Area,Cabinets,Carpentry & Joinery""")
                    
            except Exception as e:
                st.error(f"❌ Error reading CSV file: {str(e)}")
                st.markdown("**Tips:**")
                st.markdown("- Ensure the file is a valid CSV")
                st.markdown("- Check that columns are named exactly: Room, Component, Trade")
                st.markdown("- Make sure there are no special characters causing issues")
    
    elif mapping_source == "Use current mapping":
        if st.session_state.trade_mapping is not None and len(st.session_state.trade_mapping) > 0:
            st.info(f"Using current mapping with {len(st.session_state.trade_mapping)} entries")
        else:
            st.warning("No current mapping available. Please upload a CSV file first.")
        
    elif mapping_source == "Start with empty mapping":
        if st.button("🆕 Initialize Empty Mapping"):
            st.session_state.trade_mapping = pd.DataFrame(columns=['Room', 'Component', 'Trade'])
            st.session_state.mapping_edited = True
            st.success("✅ Initialized with empty mapping")
    
    # Display current mapping if available
    if st.session_state.trade_mapping is not None and len(st.session_state.trade_mapping) > 0:
        st.markdown("---")
        st.markdown("### ✏️ Current Trade Mapping")
        
        # Mapping statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Mappings", len(st.session_state.trade_mapping))
        with col2:
            unique_rooms = st.session_state.trade_mapping['Room'].nunique()
            st.metric("Unique Rooms", unique_rooms)
        with col3:
            unique_trades = st.session_state.trade_mapping['Trade'].nunique()
            st.metric("Trade Categories", unique_trades)
        with col4:
            if st.session_state.mapping_edited:
                st.success("✅ Active")
            else:
                st.info("📝 Ready")
        
        # Quick preview
        with st.expander("🔍 Preview Current Mapping", expanded=False):
            st.dataframe(
                st.session_state.trade_mapping.head(15),
                use_container_width=True
            )
            if len(st.session_state.trade_mapping) > 15:
                st.info(f"Showing first 15 of {len(st.session_state.trade_mapping)} total mappings")
        
        # Editable mapping
        with st.expander("✏️ Edit Mapping (Advanced)", expanded=False):
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
        with st.expander("➕ Add Single Mapping", expanded=False):
            col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
            
            with col1:
                new_room = st.text_input("Room", key="new_room")
            
            with col2:
                new_component = st.text_input("Component", key="new_component")
            
            with col3:
                new_trade = st.selectbox("Trade", get_available_trades(), key="new_trade")
            
            with col4:
                if st.button("➕ Add", key="add_mapping"):
                    if new_room and new_component and new_tradedef load_default_mapping():
    """Load empty mapping by default - users will upload their own master data"""
    
    # Return empty DataFrame with correct columns
    df = pd.DataFrame(columns=['Room', 'Component', 'Trade'])
    
    st.info("📋 No default mapping loaded. Please upload your master trade mapping CSV file to get started.")
    
    return df,GPO,Electrical
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
Upstairs Bathroom,Walls,Painting"""
    
    # Parse the CSV data using StringIO
    from io import StringIO
    import pandas as pd
    
    # Create DataFrame from CSV string
    df = pd.read_csv(StringIO(master_mapping_csv))
    
    # Display confirmation message
    st.success(f"✅ Loaded exactly {len(df)} trade mappings from master data!")
    
    return df,Cold/Hot Water Outlets,Plumbing
Laundry Room,Doors,Doors
Laundry Room,Drainage,Plumbing
Laundry Room,Exhaust Fan,Electrical
Laundry Room,GPO,Electrical
Laundry Room,Laundry Sink,Plumbing
Laundry Room,Light Fixtures,Electrical
Laundry Room,Skirting,Carpentry & Joinery
Laundry Room,Tiles,Flooring - Tiles
Laundry Room,Walls,Painting
Laundry Room# Complete Working Streamlit App with Interactive Trade Mapping Management
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

def load_default_mapping():
    """Load comprehensive trade mappings"""
    
    # Create comprehensive mapping data
    mapping_data = []
    
    # Core room-component-trade mappings
    mappings = [
        # Entry Doors
        ("Apartment Entry Door", "Door Handle", "Doors"),
        ("Apartment Entry Door", "Door Locks and Keys", "Doors"),
        ("Apartment Entry Door", "Paint", "Painting"),
        ("Apartment Entry Door", "Self Latching", "Doors"),
        
        # Balcony
        ("Balcony", "Balustrade", "Carpentry & Joinery"),
        ("Balcony", "Drainage Point", "Plumbing"),
        ("Balcony", "GPO (if applicable)", "Electrical"),
        ("Balcony", "Glass", "Windows"),
        ("Balcony", "Glass Sliding Door", "Windows"),
        ("Balcony", "Tiles", "Flooring - Tiles"),
        
        # Bathroom
        ("Bathroom", "Bathtub (if applicable)", "Plumbing"),
        ("Bathroom", "Ceiling", "Painting"),
        ("Bathroom", "Doors", "Doors"),
        ("Bathroom", "Exhaust Fan", "Electrical"),
        ("Bathroom", "GPO", "Electrical"),
        ("Bathroom", "Light Fixtures", "Electrical"),
        ("Bathroom", "Mirror", "Carpentry & Joinery"),
        ("Bathroom", "Shower", "Plumbing"),
        ("Bathroom", "Sink", "Plumbing"),
        ("Bathroom", "Skirting", "Carpentry & Joinery"),
        ("Bathroom", "Tiles", "Flooring - Tiles"),
        ("Bathroom", "Toilet", "Plumbing"),
        ("Bathroom", "Walls", "Painting"),
        
        # Kitchen Area
        ("Kitchen Area", "Appliances", "Appliances"),
        ("Kitchen Area", "Benchtop", "Carpentry & Joinery"),
        ("Kitchen Area", "Cabinets", "Carpentry & Joinery"),
        ("Kitchen Area", "Ceiling", "Painting"),
        ("Kitchen Area", "Dishwasher (if applicable)", "Plumbing"),
        ("Kitchen Area", "Flooring", "Flooring - Timber"),
        ("Kitchen Area", "GPO", "Electrical"),
        ("Kitchen Area", "Kitchen Sink", "Plumbing"),
        ("Kitchen Area", "Kitchen Table Tops", "Carpentry & Joinery"),
        ("Kitchen Area", "Light Fixtures", "Electrical"),
        ("Kitchen Area", "Rangehood", "Appliances"),
        ("Kitchen Area", "Splashback", "Flooring - Tiles"),
        ("Kitchen Area", "Stovetop and Oven", "Appliances"),
        ("Kitchen Area", "Walls", "Painting"),
        ("Kitchen Area", "Windows (if applicable)", "Windows"),
        
        # Living Spaces
        ("Living Room", "Ceiling", "Painting"),
        ("Living Room", "Flooring", "Flooring - Timber"),
        ("Living Room", "GPO", "Electrical"),
        ("Living Room", "Light Fixtures", "Electrical"),
        ("Living Room", "Skirting", "Carpentry & Joinery"),
        ("Living Room", "Walls", "Painting"),
        ("Living Room", "Windows", "Windows"),
        
        ("Dining & Living Room Area", "Ceiling", "Painting"),
        ("Dining & Living Room Area", "Flooring", "Flooring - Timber"),
        ("Dining & Living Room Area", "GPO", "Electrical"),
        ("Dining & Living Room Area", "Light Fixtures", "Electrical"),
        ("Dining & Living Room Area", "Skirting", "Carpentry & Joinery"),
        ("Dining & Living Room Area", "Walls", "Painting"),
        ("Dining & Living Room Area", "Windows (if applicable)", "Windows"),
        
        # Laundry
        ("Laundry Room", "Ceiling", "Painting"),
        ("Laundry Room", "Cold/Hot Water Outlets", "Plumbing"),
        ("Laundry Room", "Doors", "Doors"),
        ("Laundry Room", "Drainage", "Plumbing"),
        ("Laundry Room", "Exhaust Fan", "Electrical"),
        ("Laundry Room", "GPO", "Electrical"),
        ("Laundry Room", "Laundry Sink", "Plumbing"),
        ("Laundry Room", "Light Fixtures", "Electrical"),
        ("Laundry Room", "Skirting", "Carpentry & Joinery"),
        ("Laundry Room", "Tiles", "Flooring - Tiles"),
        ("Laundry Room", "Walls", "Painting"),
        
        # Corridor
        ("Corridor", "Ceiling", "Painting"),
        ("Corridor", "Flooring", "Flooring - Timber"),
        ("Corridor", "Light Fixtures", "Electrical"),
        ("Corridor", "Skirting", "Carpentry & Joinery"),
        ("Corridor", "Walls", "Painting"),
        ("Corridor", "Intercom", "Electrical")
    ]
    
    # Add basic mappings
    for room, component, trade in mappings:
        mapping_data.append({"Room": room, "Component": component, "Trade": trade})
    
    # Add bedroom variations
    bedroom_types = ["Bedroom", "Bedroom 1", "Bedroom 2", "Bedroom 3", "Master Bedroom", "Guest Bedroom"]
    bedroom_components = [
        ("Carpets", "Flooring - Carpets"),
        ("Ceiling", "Painting"),
        ("Doors", "Doors"),
        ("GPO", "Electrical"),
        ("Light Fixtures", "Electrical"),
        ("Skirting", "Carpentry & Joinery"),
        ("Walls", "Painting"),
        ("Wardrobe", "Carpentry & Joinery"),
        ("Windows", "Windows")
    ]
    
    for bedroom in bedroom_types:
        for component, trade in bedroom_components:
            mapping_data.append({"Room": bedroom, "Component": component, "Trade": trade})
    
    # Add ensuite variations
    ensuite_types = ["Bedroom 1 w/Ensuite", "Bedroom 2 w/Ensuite", "Bedroom w/Ensuite"]
    ensuite_components = [
        ("Bathtub (if applicable)", "Plumbing"),
        ("Carpets", "Flooring - Carpets"),
        ("Ceiling", "Painting"),
        ("Doors", "Doors"),
        ("Exhaust Fan", "Electrical"),
        ("GPO", "Electrical"),
        ("Light Fixtures", "Electrical"),
        ("Mirror", "Carpentry & Joinery"),
        ("Shower", "Plumbing"),
        ("Sink", "Plumbing"),
        ("Skirting", "Carpentry & Joinery"),
        ("Tiles", "Flooring - Tiles"),
        ("Toilet", "Plumbing"),
        ("Walls", "Painting"),
        ("Wardrobe", "Carpentry & Joinery"),
        ("Windows", "Windows")
    ]
    
    for ensuite in ensuite_types:
        for component, trade in ensuite_components:
            mapping_data.append({"Room": ensuite, "Component": component, "Trade": trade})
    
    # Add bathroom variations
    bathroom_types = ["Upstairs Bathroom", "Downstairs Bathroom"]
    bathroom_components = [
        ("Ceiling", "Painting"),
        ("Doors", "Doors"),
        ("Exhaust Fan", "Electrical"),
        ("GPO", "Electrical"),
        ("Light Fixtures", "Electrical"),
        ("Mirror", "Carpentry & Joinery"),
        ("Shower", "Plumbing"),
        ("Sink", "Plumbing"),
        ("Skirting", "Carpentry & Joinery"),
        ("Tiles", "Flooring - Tiles"),
        ("Toilet", "Plumbing"),
        ("Walls", "Painting")
    ]
    
    for bathroom in bathroom_types:
        for component, trade in bathroom_components:
            mapping_data.append({"Room": bathroom, "Component": component, "Trade": trade})
    
    # Add more room types
    additional_mappings = [
        ("Butler's Pantry", "Cabinets/Shelving", "Carpentry & Joinery"),
        ("Butler's Pantry", "Ceiling", "Painting"),
        ("Butler's Pantry", "Flooring", "Flooring - Timber"),
        ("Butler's Pantry", "GPO", "Electrical"),
        ("Butler's Pantry", "Light Fixtures", "Electrical"),
        ("Butler's Pantry", "Sink", "Plumbing"),
        
        ("Butler's Pantry (if applicable)", "Cabinets/Shelving", "Carpentry & Joinery"),
        ("Butler's Pantry (if applicable)", "Ceiling", "Painting"),
        ("Butler's Pantry (if applicable)", "Flooring", "Flooring - Timber"),
        ("Butler's Pantry (if applicable)", "GPO", "Electrical"),
        ("Butler's Pantry (if applicable)", "Light Fixtures", "Electrical"),
        ("Butler's Pantry (if applicable)", "Sink", "Plumbing"),
        
        ("Bathroom / Laundry", "Ceiling", "Painting"),
        ("Bathroom / Laundry", "Doors", "Doors"),
        ("Bathroom / Laundry", "Drainage", "Plumbing"),
        ("Bathroom / Laundry", "Exhaust Fan", "Electrical"),
        ("Bathroom / Laundry", "GPO", "Electrical"),
        ("Bathroom / Laundry", "Light Fixtures", "Electrical"),
        ("Bathroom / Laundry", "Mirror", "Carpentry & Joinery"),
        ("Bathroom / Laundry", "Shower", "Plumbing"),
        ("Bathroom / Laundry", "Sink", "Plumbing"),
        ("Bathroom / Laundry", "Skirting", "Carpentry & Joinery"),
        ("Bathroom / Laundry", "Tiles", "Flooring - Tiles"),
        ("Bathroom / Laundry", "Toilet", "Plumbing"),
        ("Bathroom / Laundry", "Walls", "Painting"),
        ("Bathroom / Laundry", "Laundry Sink", "Plumbing"),
        
        ("Laundry Section", "Cold/Hot Water Outlets", "Plumbing"),
        ("Laundry Section", "Doors", "Doors"),
        ("Laundry Section", "Drainage", "Plumbing"),
        ("Laundry Section", "Exhaust Fan", "Electrical"),
        ("Laundry Section", "GPO", "Electrical"),
        ("Laundry Section", "Laundry Sink", "Plumbing"),
        ("Laundry Section", "Light Fixtures", "Electrical"),
        ("Laundry Section", "Skirting", "Carpentry & Joinery"),
        ("Laundry Section", "Tiles", "Flooring - Tiles"),
        ("Laundry Section", "Walls", "Painting"),
        
        ("Family Room", "Ceiling", "Painting"),
        ("Family Room", "Flooring", "Flooring - Timber"),
        ("Family Room", "GPO", "Electrical"),
        ("Family Room", "Light Fixtures", "Electrical"),
        ("Family Room", "Skirting", "Carpentry & Joinery"),
        ("Family Room", "Walls", "Painting"),
        ("Family Room", "Windows (if applicable)", "Windows"),
        
        ("Garage", "Ceiling", "Painting"),
        ("Garage", "Door", "Doors"),
        ("Garage", "Electrical", "Electrical"),
        ("Garage", "Flooring", "Flooring - Timber"),
        ("Garage", "Walls", "Painting"),
        
        ("Study Area (if applicable)", "Desk", "Carpentry & Joinery"),
        ("Study Area (if applicable)", "GPO", "Electrical"),
        ("Study Area (if applicable)", "Light Fixtures", "Electrical"),
        ("Study Area (if applicable)", "Skirting", "Carpentry & Joinery"),
        ("Study Area (if applicable)", "Walls", "Painting"),
        
        ("Staircase", "Railing (if applicable)", "Carpentry & Joinery"),
        ("Staircase", "Staircase", "Carpentry & Joinery"),
        
        ("Upstairs Landing", "Ceiling", "Painting"),
        ("Upstairs Landing", "Flooring", "Flooring - Timber"),
        ("Upstairs Landing", "Light Fixtures", "Electrical"),
        ("Upstairs Landing", "Skirting", "Carpentry & Joinery"),
        ("Upstairs Landing", "Walls", "Painting"),
        
        ("Upstair Corridor", "Ceiling", "Painting"),
        ("Upstair Corridor", "Walls", "Painting")
    ]
    
    for room, component, trade in additional_mappings:
        mapping_data.append({"Room": room, "Component": component, "Trade": trade})
    
    # Create DataFrame
    df = pd.DataFrame(mapping_data)
    
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
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#2E7D32', 'font_color': 'white',
            'border': 1, 'align': 'center'
        })
        
        building_info_header = workbook.add_format({
            'bold': True, 'font_size': 14, 'bg_color': '#2E7D32', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 2
        })
        
        label_format = workbook.add_format({
            'bold': True, 'font_size': 11, 'bg_color': '#F5F5F5', 'border': 1,
            'align': 'left', 'valign': 'vcenter'
        })
        
        data_format = workbook.add_format({
            'font_size': 11, 'border': 1, 'align': 'right', 'valign': 'vcenter'
        })
        
        # Create Executive Dashboard
        worksheet = workbook.add_worksheet("📊 Executive Dashboard")
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 35)
        
        current_row = 0
        
        # Building Information
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
        
        # Add other detailed data sheets
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
        
        # Trade Specific Summary Sheet
        if len(metrics['trade_specific_summary']) > 0:
            metrics['trade_specific_summary'].to_excel(writer, sheet_name="🔧 Trade Specific Summary", index=False)
            ws_trade = writer.sheets["🔧 Trade Specific Summary"]
            for col_num, value in enumerate(metrics['trade_specific_summary'].columns.values):
                ws_trade.write(0, col_num, value, header_format)
        
        # Component Details Summary Sheet
        if len(metrics['component_details_summary']) > 0:
            metrics['component_details_summary'].to_excel(writer, sheet_name="🔍 Component Details", index=False)
            ws_component = writer.sheets["🔍 Component Details"]
            for col_num, value in enumerate(metrics['component_details_summary'].columns.values):
                ws_component.write(0, col_num, value, header_format)
            
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
                        ws.write(0, col_num, value, header_format)
    
    excel_buffer.seek(0)
    return excel_buffer

def display_comprehensive_results(metrics, excel_buffer, original_filename):
    """Display comprehensive processing results"""
    
    st.markdown("---")
    st.markdown("## 🎉 Processing Complete!")
    
    # Success message
    st.markdown(f"""
    <div class="success-message">
        <h3>✅ Inspection Report Generated Successfully!</h3>
        <p><strong>🏢 Building:</strong> {metrics['building_name']}</p>
        <p><strong>📅 Inspection Date:</strong> {metrics['inspection_date']}</p>
        <p><strong>📄 Source File:</strong> {original_filename}</p>
        <p><strong>⏰ Processing Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Key metrics
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
    
    # Component Details Preview
    if len(metrics['component_details_summary']) > 0:
        st.markdown("### 🔍 Component Details Analysis")
        
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
    
    # Download section
    st.markdown("### 📥 Download Your Report")
    
    filename = f"{metrics['building_name'].replace(' ', '_')}_Inspection_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    st.download_button(
        label="📊 Download Complete Excel Report",
        data=excel_buffer,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    # Report contents
    st.markdown("#### 📋 What's in Your Report:")
    st.markdown("""
    - **📊 Executive Dashboard** - Key metrics and visual summary
    - **📋 All Inspections** - Complete detailed data
    - **🔍 Defects Only** - Filtered view of issues found
    - **🔧 Trade Specific Summary** - Comprehensive trade analysis with priorities
    - **🔍 Component Details** - Shows which specific units have defects for each component
    - **📊 By Trade** - Defects grouped by trade category
    - **🏠 By Unit** - Unit-specific defect summaries
    - **🚪 By Room** - Room-specific analysis
    """)
    
    st.success("🎉 Your professional inspection report is ready!")

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
            help="Choose how to initialize your trade mapping"
        )
    
    with col2:
        st.markdown("### 🔧 Actions")
        if st.button("🔄 Reset Mapping"):
            st.session_state.trade_mapping = load_default_mapping()
            st.session_state.mapping_edited = True
            st.success("✅ Mapping reset to default")
        
        if st.button("📥 Download Current Mapping"):
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
    
    elif mapping_source == "Load default mapping":
        if st.session_state.trade_mapping is None:
            st.session_state.trade_mapping = load_default_mapping()
            st.session_state.mapping_edited = True
            st.info(f"✅ Loaded {len(st.session_state.trade_mapping)} trade mappings successfully!")
        
    elif mapping_source == "Start with empty mapping":
        if st.session_state.trade_mapping is None or len(st.session_state.trade_mapping) > 0:
            st.session_state.trade_mapping = pd.DataFrame(columns=['Room', 'Component', 'Trade'])
            st.session_state.mapping_edited = True
    
    # Display mapping if available
    if st.session_state.trade_mapping is not None:
        st.markdown("---")
        st.markdown("### ✏️ Edit Trade Mapping")
        
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
        
        if len(st.session_state.trade_mapping) > 0:
            st.markdown("#### 📋 Current Mapping")
            
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
            
            if not edited_mapping.equals(st.session_state.trade_mapping):
                st.session_state.trade_mapping = edited_mapping
                st.session_state.mapping_edited = True
                st.success("✅ Mapping updated!")

with tab1:
    # Sidebar options
    st.sidebar.title("⚙️ Processing Options")
    st.sidebar.markdown("---")
    
    if st.session_state.trade_mapping is not None and len(st.session_state.trade_mapping) > 0:
        st.sidebar.success(f"✅ Trade mapping ready ({len(st.session_state.trade_mapping)} mappings)")
    else:
        st.sidebar.warning("⚠️ No trade mapping configured.")
    
    st.sidebar.subheader("📊 Report Options")
    include_charts = st.sidebar.checkbox("Include analysis charts", value=True)
    detailed_breakdown = st.sidebar.checkbox("Detailed trade breakdown", value=True)
    executive_summary = st.sidebar.checkbox("Executive summary", value=True)
    
    st.sidebar.subheader("📧 Notifications")
    notification_email = st.sidebar.text_input("Email for notifications (optional)")
    
    # Main content
    st.markdown("## 📤 Upload & Process Inspection Files")
    
    if st.session_state.trade_mapping is not None:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Mappings Loaded", len(st.session_state.trade_mapping))
        with col2:
            st.metric("Trade Categories", st.session_state.trade_mapping['Trade'].nunique() if len(st.session_state.trade_mapping) > 0 else 0)
        with col3:
            st.metric("Room Types", st.session_state.trade_mapping['Room'].nunique() if len(st.session_state.trade_mapping) > 0 else 0)
    
    st.markdown("### 📋 Upload Inspection File")
    uploaded_file = st.file_uploader(
        "Choose iAuditor CSV file",
        type=['csv'],
        help="Select the CSV file exported from iAuditor"
    )
    
    if st.session_state.trade_mapping is not None and len(st.session_state.trade_mapping) > 0:
        with st.expander("🔍 Preview Current Trade Mapping"):
            st.dataframe(
                st.session_state.trade_mapping.head(10),
                use_container_width=True
            )
            if len(st.session_state.trade_mapping) > 10:
                st.info(f"Showing first 10 of {len(st.session_state.trade_mapping)} total mappings")
    
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
            st.warning("⚠️ Please configure trade mapping first.")

with tab3:
    st.markdown("## 📊 Report Analytics & History")
    st.info("🚧 This section will show historical reports and analytics in future versions")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em; padding: 2rem;">
    <h4>🏢 Inspection Report Processor with Trade Analysis</h4>
    <p>Professional inspection report processing with comprehensive trade mapping</p>
</div>
""", unsafe_allow_html=True)
