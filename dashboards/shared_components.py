"""
Shared components used across multiple dashboards
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3

def lookup_unit_defects(processed_data, unit_number):
    """Lookup defect history for a specific unit - shared across dashboards"""
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

def show_unit_lookup_widget(processed_data, key_prefix=""):
    """Reusable unit lookup widget"""
    if processed_data is None:
        st.info("No processed data available for unit lookup")
        return
    
    st.markdown("#### Unit Lookup")
    # ✅ Coerce to string to avoid mixed-type sort errors
    all_units = sorted(processed_data["Unit"].astype(str).unique())
    
    selected_unit = st.selectbox(
        "Select Unit Number:",
        options=[""] + all_units,
        help="Quick lookup of defects for any unit",
        key=f"{key_prefix}unit_lookup"
    )
    
    if selected_unit:
        unit_defects = lookup_unit_defects(processed_data, selected_unit)
        
        if len(unit_defects) > 0:
            st.markdown(f"**Unit {selected_unit} Defects:**")
            # ... (unchanged counts/metrics) ...
            st.dataframe(unit_defects, use_container_width=True)
        else:
            st.success(f"Unit {selected_unit} has no defects!")

def get_corrected_database_stats(db_path="inspection_system.db"):
    """Get corrected database statistics - shared across dashboards"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Count unique buildings with inspection data
        cursor.execute('''
            SELECT COUNT(DISTINCT building_name) 
            FROM processed_inspections 
            WHERE is_active = 1
        ''')
        active_inspections = cursor.fetchone()[0]
        
        # Count total unique buildings ever processed
        cursor.execute('''
            SELECT COUNT(DISTINCT building_name) 
            FROM processed_inspections
        ''')
        total_inspections = cursor.fetchone()[0]
        
        # Count total defects
        cursor.execute('''
            SELECT COUNT(*) 
            FROM inspection_defects id
            JOIN processed_inspections pi ON id.inspection_id = pi.id
            WHERE pi.is_active = 1
        ''')
        total_defects = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_inspections': total_inspections,
            'active_inspections': active_inspections,
            'total_defects': total_defects
        }
        
    except Exception as e:
        return {
            'total_inspections': 0,
            'active_inspections': 0,
            'total_defects': 0
        }

def show_system_status_widget():
    """Reusable system status widget"""
    stats = get_corrected_database_stats()
    
    with st.expander("System Status", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Buildings Processed", stats.get("total_inspections", 0))
        with col2:
            st.metric("Active Buildings", stats.get("active_inspections", 0))
        with col3:
            st.metric("Total Defects", stats.get("total_defects", 0))