"""
Project Manager Dashboard Module
"""
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from permission_manager import get_permission_manager, check_permission_ui
from secure_ui_helpers import create_secure_ui, secure_section_header

try:
    from data_persistence import DataPersistenceManager
except ImportError:
    st.error("data_persistence module not found!")
    DataPersistenceManager = None

from .shared_components import lookup_unit_defects

class ProjectManagerDashboard:
    def __init__(self):
        self.user = self.get_current_user()
        if DataPersistenceManager:
            self.persistence_manager = DataPersistenceManager()
        else:
            self.persistence_manager = None
    
    def get_current_user(self):
        return {
            "username": st.session_state.get("username", ""),
            "name": st.session_state.get("user_name", "Project Manager"),
            "email": st.session_state.get("user_email", ""),
            "role": st.session_state.get("user_role", "project_manager")
        }
    
    def show(self):
        """Main project manager dashboard display"""
        st.markdown(f"""
        <div class="main-header">
            <h1>Project Management Dashboard</h1>
            <p>Project Manager Interface</p>
            <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
                <span>Welcome back, <strong>{self.user['name']}</strong>!</span>
                <span style="margin-left: 2rem;">Role: <strong>Project Manager</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if not self.persistence_manager:
            st.error("Database connection not available. Please check system setup.")
            return
        
        # Show processing capabilities
        st.markdown("### Your Management Capabilities")
        col1, col2 = st.columns(2)
        
        with col1:
            st.success("✓ Upload and process inspection data")
            st.success("✓ Manage building data")
            st.success("✓ Unit-level defect management")
        
        with col2:
            st.success("✓ Generate project reports")
            st.success("✓ Approve defect resolutions")
            st.success("✓ Access all building data")
        
        # Get buildings for management
        accessible_buildings = self.get_accessible_buildings()
        
        if len(accessible_buildings) == 0:
            self.show_fallback_interface()
            return
        
        self.show_building_selection(accessible_buildings)
    
    def get_accessible_buildings(self):
        """Get buildings accessible to this project manager"""
        if not self.persistence_manager:
            return []
            
        try:
            conn = sqlite3.connect(self.persistence_manager.db_path)
            cursor = conn.cursor()
            
            # Get buildings with inspection data
            cursor.execute('''
                SELECT DISTINCT 
                    pi.building_name,
                    (SELECT COUNT(DISTINCT id2.unit_number) 
                     FROM inspection_defects id2 
                     JOIN processed_inspections pi2 ON id2.inspection_id = pi2.id 
                     WHERE pi2.building_name = pi.building_name AND pi2.is_active = 1) as total_units,
                    MAX(pi.processed_at) as last_inspection
                FROM processed_inspections pi
                WHERE pi.is_active = 1
                GROUP BY pi.building_name
                ORDER BY pi.building_name
            ''')
            
            buildings = cursor.fetchall()
            conn.close()
            return buildings
            
        except Exception as e:
            st.error(f"Error loading buildings: {e}")
            return []
    
    def show_building_selection(self, accessible_buildings):
        """Building selection and management interface"""
        st.markdown("---")
        st.markdown("#### Select Building to Manage")
        
        building_options = []
        building_lookup = {}
        
        for building in accessible_buildings:
            building_name = building[0]
            total_units = building[1] if building[1] else 0
            last_inspection = building[2] if len(building) > 2 else "No data"
            
            display_name = f"{building_name} - {total_units} units"
            building_options.append(display_name)
            building_lookup[display_name] = {
                'name': building_name,
                'units': total_units,
                'last_inspection': last_inspection
            }
        
        selected_building_display = st.selectbox(
            "Choose building to manage:",
            options=building_options,
            help="Select a building to view detailed management tools"
        )
        
        if selected_building_display:
            selected_building = building_lookup[selected_building_display]
            self.show_building_management(selected_building)
    
    def show_building_management(self, building):
        """Building management interface"""
        # Building context
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Building", building['name'])
        with col2:
            st.metric("Total Units", building['units'])
        with col3:
            last_inspection = building['last_inspection']
            if last_inspection and last_inspection != "No data":
                display_date = str(last_inspection)[:10]
                st.metric("Last Inspection", display_date)
            else:
                st.metric("Last Inspection", "None")
        
        # Unit lookup for this building
        self.show_building_unit_lookup(building['name'])
        
        # Building overview
        self.show_building_overview(building)
    
    def show_building_unit_lookup(self, building_name):
        """Unit lookup for selected building"""
        st.markdown("---")
        st.markdown("#### Unit Management")
        
        try:
            conn = sqlite3.connect(self.persistence_manager.db_path)
            cursor = conn.cursor()
            
            # Get all units for this building
            cursor.execute('''
                SELECT DISTINCT id.unit_number
                FROM inspection_defects id
                JOIN processed_inspections pi ON id.inspection_id = pi.id
                WHERE pi.building_name = ? AND pi.is_active = 1
                ORDER BY CAST(id.unit_number AS INTEGER)
            ''', (building_name,))
            
            units_result = cursor.fetchall()
            available_units = [str(unit[0]) for unit in units_result] if units_result else []
            
            if available_units:
                selected_unit = st.selectbox(
                    "Select Unit for Detailed Management:",
                    options=[""] + available_units,
                    key="pm_unit_lookup"
                )
                
                if selected_unit:
                    self.show_unit_details(building_name, selected_unit)
            else:
                st.info("No units with defect data found for this building.")
            
            conn.close()
            
        except Exception as e:
            st.error(f"Error loading unit data: {e}")
    
    def show_unit_details(self, building_name, unit_number):
        """Show detailed unit information"""
        try:
            conn = sqlite3.connect(self.persistence_manager.db_path)
            cursor = conn.cursor()
            
            # Get defects for selected unit
            cursor.execute('''
                SELECT id.room, id.component, id.trade, id.urgency, 
                       id.planned_completion, id.status
                FROM inspection_defects id
                JOIN processed_inspections pi ON id.inspection_id = pi.id
                WHERE pi.building_name = ? AND id.unit_number = ? AND pi.is_active = 1
                ORDER BY 
                    CASE id.urgency 
                        WHEN 'Urgent' THEN 1 
                        WHEN 'High Priority' THEN 2 
                        ELSE 3 
                    END,
                    id.room, id.component
            ''', (building_name, unit_number))
            
            unit_defects = cursor.fetchall()
            conn.close()
            
            if unit_defects:
                st.markdown(f"**Unit {unit_number} Management Console:**")
                
                # Defect summary with management context
                urgent_count = len([d for d in unit_defects if d[3] == 'Urgent'])
                high_priority_count = len([d for d in unit_defects if d[3] == 'High Priority'])
                normal_count = len(unit_defects) - urgent_count - high_priority_count
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if urgent_count > 0:
                        st.error(f"🚨 Urgent: {urgent_count}")
                    else:
                        st.success("✅ Urgent: 0")
                with col2:
                    if high_priority_count > 0:
                        st.warning(f"⚠️ High Priority: {high_priority_count}")
                    else:
                        st.info("High Priority: 0")
                with col3:
                    st.info(f"🔧 Normal: {normal_count}")
                with col4:
                    st.metric("Total Items", len(unit_defects))
                
                # Management status
                if urgent_count > 0:
                    st.error(f"**MANAGEMENT ALERT:** Unit {unit_number} requires immediate contractor deployment!")
                elif high_priority_count > 5:
                    st.warning(f"**ATTENTION:** Unit {unit_number} has {high_priority_count} high-priority items")
                else:
                    st.success(f"**STATUS:** Unit {unit_number} defects are manageable")
                
                # Display defects table
                df_defects = pd.DataFrame(unit_defects, columns=[
                    "Room", "Component", "Trade", "Urgency", "Planned Completion", "Status"
                ])
                
                st.dataframe(df_defects, use_container_width=True)
                
                # Management actions
                self.show_unit_management_actions(building_name, unit_number, urgent_count, df_defects)
            
            else:
                st.success(f"✅ **Unit {unit_number} is DEFECT-FREE!**")
                st.info("This unit is ready for handover.")
                
        except Exception as e:
            st.error(f"Error loading unit details: {e}")
    
    def show_unit_management_actions(self, building_name, unit_number, urgent_count, df_defects):
        """Unit management actions"""
        st.markdown("**Project Management Actions:**")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(f"📊 Export Unit {unit_number} Report", use_container_width=True):
                csv = df_defects.to_csv(index=False)
                st.download_button(
                    "Download Unit Report",
                    data=csv,
                    file_name=f"unit_{unit_number}_management_report_{building_name.replace(' ', '_')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with col2:
            if urgent_count > 0:
                if st.button(f"🚨 Generate Urgent Work Order", use_container_width=True):
                    work_order = f"""URGENT WORK ORDER - PROJECT MANAGEMENT
Building: {building_name}
Unit: {unit_number}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Project Manager: {self.user['name']}

CRITICAL DEFECTS REQUIRING IMMEDIATE ATTENTION:
============================================

"""
                    urgent_defects = df_defects[df_defects["Urgency"] == "Urgent"]
                    for i, (_, defect) in enumerate(urgent_defects.iterrows(), 1):
                        work_order += f"{i}. {defect['Room']} - {defect['Component']} ({defect['Trade']})\n"
                        work_order += f"   Due: {defect['Planned Completion']}\n"
                        work_order += f"   Status: {defect['Status']}\n\n"
                    
                    work_order += f"MANAGEMENT DIRECTIVE:\n"
                    work_order += f"- Immediate contractor mobilization required\n"
                    work_order += f"- Timeline: 24-48 hours completion\n"
                    work_order += f"- Daily status updates required\n"
                    work_order += f"- Priority: CRITICAL\n\nEND WORK ORDER"
                    
                    st.download_button(
                        "Download Work Order",
                        data=work_order,
                        file_name=f"urgent_work_order_unit_{unit_number}_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
            else:
                st.success("✅ No urgent work orders needed")
    
    def show_building_overview(self, building):
        """Building overview and management actions"""
        st.markdown("---")
        st.markdown("#### Building-Wide Management Overview")
        
        # Get building statistics
        try:
            conn = sqlite3.connect(self.persistence_manager.db_path)
            cursor = conn.cursor()
            
            # Get comprehensive defect counts
            cursor.execute('''
                SELECT COUNT(*) as total_defects,
                       SUM(CASE WHEN id.urgency = 'Urgent' THEN 1 ELSE 0 END) as urgent_count,
                       SUM(CASE WHEN id.urgency = 'High Priority' THEN 1 ELSE 0 END) as high_priority_count,
                       COUNT(DISTINCT id.unit_number) as units_with_defects
                FROM inspection_defects id
                JOIN processed_inspections pi ON id.inspection_id = pi.id
                WHERE pi.building_name = ? AND pi.is_active = 1
            ''', (building['name'],))
            
            result = cursor.fetchone()
            total_defects = result[0] if result else 0
            urgent_count = result[1] if result else 0
            high_priority_count = result[2] if result else 0
            units_with_defects = result[3] if result else 0
            
            conn.close()
            
            # Display comprehensive metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Defects", total_defects)
            with col2:
                if urgent_count > 0:
                    st.error(f"🚨 Urgent: {urgent_count}")
                else:
                    st.success("✅ Urgent: 0")
            with col3:
                if high_priority_count > 0:
                    st.warning(f"⚠️ High Priority: {high_priority_count}")
                else:
                    st.info("High Priority: 0")
            with col4:
                units_ready = building['units'] - units_with_defects
                completion_rate = (units_ready / building['units'] * 100) if building['units'] > 0 else 100
                st.metric("Completion Rate", f"{completion_rate:.1f}%")
            
            # Management assessment
            st.markdown("#### Management Assessment")
            if urgent_count > 10:
                st.error("🚨 **CRITICAL SITUATION:** Immediate executive escalation required!")
                st.error(f"Building has {urgent_count} urgent defects across {units_with_defects} units.")
            elif urgent_count > 5:
                st.warning("⚠️ **HIGH PRIORITY:** Contractor mobilization needed immediately!")
            elif urgent_count > 0:
                st.warning(f"**ATTENTION:** {urgent_count} urgent defects require close monitoring")
            else:
                st.success("✅ **STATUS GOOD:** No urgent defects detected")
            
            # Building management actions
            st.markdown("#### Building Management Actions")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📊 Generate Building Summary Report", use_container_width=True):
                    st.info("Building summary report generation ready")
                    # Could integrate with existing report generation here
            
            with col2:
                if urgent_count > 0:
                    if st.button("🚨 Building-Wide Crisis Management", use_container_width=True):
                        st.error(f"Crisis management protocol activated for {urgent_count} urgent items")
                        # Could trigger emergency workflows here
                else:
                    st.success("✅ No crisis management needed")
            
        except Exception as e:
            st.error(f"Error loading building overview: {e}")
    
    def show_fallback_interface(self):
        """Fallback interface when no buildings found"""
        st.warning("No buildings with inspection data found in database.")
        
        # Show current session data if available
        if st.session_state.metrics is not None:
            st.info("Showing current session building for management:")
            
            metrics = st.session_state.metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Building", metrics['building_name'])
            with col2:
                st.metric("Total Units", metrics['total_units'])
            with col3:
                st.metric("Urgent Issues", metrics['urgent_defects'])
            
            # Show unit lookup for current session
            st.markdown("---")
            show_unit_lookup_widget(st.session_state.processed_data, "pm_fallback_")
        else:
            st.info("No inspection data available. Upload and process data using the main processing interface.")