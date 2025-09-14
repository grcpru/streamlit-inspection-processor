# data_persistence_functions.py
# Add these functions to your streamlit_app.py

import streamlit as st
import sqlite3
import json
import uuid
from datetime import datetime
import pandas as pd

class DataPersistenceManager:
    """Manages saving and loading processed inspection data to/from database"""
    
    def __init__(self, db_path="inspection_system.db"):
        self.db_path = db_path
    
    def save_processed_inspection(self, processed_data, metrics, username):
        """Save processed inspection data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Generate unique ID for this inspection
            inspection_id = str(uuid.uuid4())
            
            # Save main inspection record
            cursor.execute('''
                INSERT INTO processed_inspections 
                (id, building_name, address, inspection_date, uploaded_by, metrics_json)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                inspection_id,
                metrics['building_name'],
                metrics['address'],
                metrics['inspection_date'],
                username,
                json.dumps(metrics)
            ))
            
            # Save individual defects
            defects = processed_data[processed_data["StatusClass"] == "Not OK"]
            
            for _, defect in defects.iterrows():
                cursor.execute('''
                    INSERT INTO inspection_defects 
                    (inspection_id, unit_number, unit_type, room, component, trade, urgency, planned_completion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    inspection_id,
                    defect["Unit"],
                    defect["UnitType"],
                    defect["Room"],
                    defect["Component"],
                    defect["Trade"],
                    defect["Urgency"],
                    defect["PlannedCompletion"].strftime("%Y-%m-%d") if pd.notna(defect["PlannedCompletion"]) else None
                ))
            
            # Mark any previous inspections for this building as inactive
            cursor.execute('''
                UPDATE processed_inspections 
                SET is_active = 0 
                WHERE building_name = ? AND id != ?
            ''', (metrics['building_name'], inspection_id))
            
            conn.commit()
            conn.close()
            
            return True, inspection_id
            
        except Exception as e:
            return False, str(e)
    
    def save_trade_mapping(self, mapping_df, username):
        """Save trade mapping to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Mark existing mappings as inactive
            cursor.execute('UPDATE trade_mappings SET is_active = 0')
            
            # Insert new mappings
            for _, row in mapping_df.iterrows():
                cursor.execute('''
                    INSERT OR REPLACE INTO trade_mappings (room, component, trade, created_by)
                    VALUES (?, ?, ?, ?)
                ''', (row["Room"], row["Component"], row["Trade"], username))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            return False
    
    def load_latest_inspection(self):
        """Load the most recent active inspection"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get latest active inspection
            cursor.execute('''
                SELECT id, building_name, address, inspection_date, metrics_json
                FROM processed_inspections 
                WHERE is_active = 1 
                ORDER BY processed_at DESC 
                LIMIT 1
            ''')
            
            inspection = cursor.fetchone()
            
            if not inspection:
                conn.close()
                return None, None
            
            inspection_id, building_name, address, inspection_date, metrics_json = inspection
            
            # Load defects for this inspection
            cursor.execute('''
                SELECT unit_number, unit_type, room, component, trade, urgency, planned_completion, status
                FROM inspection_defects 
                WHERE inspection_id = ?
            ''', (inspection_id,))
            
            defects = cursor.fetchall()
            conn.close()
            
            # Reconstruct processed_data DataFrame
            if defects:
                processed_data = pd.DataFrame(defects, columns=[
                    "Unit", "UnitType", "Room", "Component", "Trade", "Urgency", "PlannedCompletion", "Status"
                ])
                processed_data["StatusClass"] = "Not OK"  # All saved items are defects
                processed_data["PlannedCompletion"] = pd.to_datetime(processed_data["PlannedCompletion"])
            else:
                processed_data = pd.DataFrame(columns=["Unit", "UnitType", "Room", "Component", "StatusClass", "Trade", "Urgency", "PlannedCompletion"])
            
            # Reconstruct metrics
            metrics = json.loads(metrics_json)
            
            return processed_data, metrics
            
        except Exception as e:
            return None, None
    
    def load_trade_mapping(self):
        """Load active trade mapping from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT room, component, trade 
                FROM trade_mappings 
                WHERE is_active = 1
                ORDER BY room, component
            ''')
            
            mappings = cursor.fetchall()
            conn.close()
            
            if mappings:
                return pd.DataFrame(mappings, columns=["Room", "Component", "Trade"])
            else:
                return pd.DataFrame(columns=["Room", "Component", "Trade"])
                
        except Exception as e:
            return pd.DataFrame(columns=["Room", "Component", "Trade"])
    
    def get_all_inspections(self):
        """Get list of all inspections for admin/developer view"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, building_name, address, inspection_date, uploaded_by, processed_at, is_active
                FROM processed_inspections 
                ORDER BY processed_at DESC
            ''')
            
            inspections = cursor.fetchall()
            conn.close()
            
            return inspections
            
        except Exception as e:
            return []
    
    def get_defects_by_status(self, status="open"):
        """Get defects filtered by status for builder interface"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT d.*, p.building_name 
                FROM inspection_defects d
                JOIN processed_inspections p ON d.inspection_id = p.id
                WHERE d.status = ? AND p.is_active = 1
                ORDER BY d.urgency, d.planned_completion
            ''', (status,))
            
            defects = cursor.fetchall()
            conn.close()
            
            return defects
            
        except Exception as e:
            return []

# Modified functions to integrate with your existing streamlit app

def save_data_to_database(processed_data, metrics, username):
    """Save processed data to database - call this after processing"""
    persistence_manager = DataPersistenceManager()
    success, result = persistence_manager.save_processed_inspection(processed_data, metrics, username)
    
    if success:
        st.success(f"Data saved to database! Inspection ID: {result}")
        return True
    else:
        st.error(f"Failed to save data: {result}")
        return False

def load_latest_data_from_database():
    """Load latest inspection data from database"""
    persistence_manager = DataPersistenceManager()
    processed_data, metrics = persistence_manager.load_latest_inspection()
    
    if processed_data is not None and metrics is not None:
        st.session_state.processed_data = processed_data
        st.session_state.metrics = metrics
        st.session_state.step_completed["processing"] = True
        return True
    
    return False

def save_mapping_to_database(mapping_df, username):
    """Save trade mapping to database"""
    persistence_manager = DataPersistenceManager()
    success = persistence_manager.save_trade_mapping(mapping_df, username)
    
    if success:
        st.success("Trade mapping saved to database!")
    else:
        st.error("Failed to save trade mapping to database")
    
    return success

def load_mapping_from_database():
    """Load trade mapping from database"""
    persistence_manager = DataPersistenceManager()
    mapping_df = persistence_manager.load_trade_mapping()
    
    if len(mapping_df) > 0:
        st.session_state.trade_mapping = mapping_df
        st.session_state.step_completed["mapping"] = True
        return True
    
    return False

def show_project_manager_dashboard():
    """Dashboard for Project Managers"""
    st.markdown("### Project Management Dashboard")
    
    persistence_manager = DataPersistenceManager()
    inspections = persistence_manager.get_all_inspections()
    
    if inspections:
        st.success(f"Managing {len(inspections)} inspection(s)")
        
        # Convert to DataFrame for display
        df = pd.DataFrame(inspections, columns=[
            "ID", "Building Name", "Address", "Inspection Date", 
            "Uploaded By", "Processed At", "Is Active"
        ])
        
        # Show only essential columns
        display_df = df[["Building Name", "Inspection Date", "Uploaded By", "Is Active"]].copy()
        display_df["Is Active"] = display_df["Is Active"].map({1: "✅ Active", 0: "⏸️ Archived"})
        
        st.dataframe(display_df, use_container_width=True)
        
        # Quick stats
        col1, col2, col3 = st.columns(3)
        with col1:
            active_count = len([i for i in inspections if i[6] == 1])
            st.metric("Active Inspections", active_count)
        
        with col2:
            total_defects = persistence_manager.get_defects_by_status("open")
            st.metric("Open Defects", len(total_defects))
        
        with col3:
            unique_buildings = len(set([i[1] for i in inspections]))
            st.metric("Buildings", unique_buildings)
    
    else:
        st.info("No inspections found. Upload and process inspection data to get started.")

def show_enhanced_builder_dashboard():
    """Enhanced Builder Dashboard with real data"""
    st.markdown("### Builder Workspace")
    
    persistence_manager = DataPersistenceManager()
    
    # Get defects by status
    open_defects = persistence_manager.get_defects_by_status("open")
    
    if open_defects:
        st.success(f"You have {len(open_defects)} open defects to work on")
        
        # Convert to DataFrame
        df = pd.DataFrame(open_defects, columns=[
            "ID", "Inspection ID", "Unit", "Unit Type", "Room", "Component", 
            "Trade", "Urgency", "Planned Completion", "Status", "Created At", "Building"
        ])
        
        # Show defects by urgency
        urgent_df = df[df["Urgency"] == "Urgent"]
        high_priority_df = df[df["Urgency"] == "High Priority"]
        normal_df = df[df["Urgency"] == "Normal"]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🚨 Urgent", len(urgent_df))
        with col2:
            st.metric("⚠️ High Priority", len(high_priority_df))
        with col3:
            st.metric("🔧 Normal", len(normal_df))
        
        # Show defects table
        st.markdown("**Your Assigned Defects:**")
        display_df = df[["Unit", "Room", "Component", "Trade", "Urgency", "Planned Completion", "Building"]].copy()
        st.dataframe(display_df, use_container_width=True)
        
    else:
        st.info("No open defects assigned. Check with your project manager.")

def show_enhanced_portfolio_dashboard():
    """Enhanced Portfolio Dashboard with real data"""
    st.markdown("### Portfolio Overview")
    
    persistence_manager = DataPersistenceManager()
    inspections = persistence_manager.get_all_inspections()
    
    if inspections:
        # Group by building
        buildings = {}
        for inspection in inspections:
            building_name = inspection[1]
            if building_name not in buildings:
                buildings[building_name] = []
            buildings[building_name].append(inspection)
        
        st.success(f"Managing {len(buildings)} building(s) across your portfolio")
        
        # Show building cards
        for building_name, building_inspections in buildings.items():
            latest_inspection = max(building_inspections, key=lambda x: x[5])  # Latest by processed_at
            
            with st.expander(f"🏢 {building_name}", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"**Address:** {latest_inspection[2]}")
                    st.markdown(f"**Last Inspection:** {latest_inspection[3]}")
                
                with col2:
                    # Get defect count for this building
                    all_defects = persistence_manager.get_defects_by_status("open")
                    building_defects = [d for d in all_defects if d[-1] == building_name]
                    
                    st.metric("Open Defects", len(building_defects))
                    
                with col3:
                    urgent_defects = [d for d in building_defects if d[7] == "Urgent"]
                    st.metric("🚨 Urgent", len(urgent_defects))
                
                if len(building_defects) > 0:
                    st.warning(f"Requires attention: {len(building_defects)} open defects")
                else:
                    st.success("Building ready for handover")
    
    else:
        st.info("No buildings in your portfolio yet. Contact your team to process inspection data.")