"""
Updated Dashboard Modules - Replace your existing dashboard files with these
"""

# =============================================================================
# UPDATED developer_dashboard.py
# =============================================================================

"""
Enhanced Property Developer Dashboard Module  
Addresses requirement: Property developers no longer need to upload CSV files
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from shared_components import show_system_status_widget, get_corrected_database_stats, lookup_unit_defects
import sqlite3

class EnhancedDeveloperDashboard:
    def __init__(self):
        self.user = self.get_current_user()
        self.init_enhanced_persistence()
    
    def get_current_user(self):
        return {
            "username": st.session_state.get("username", ""),
            "name": st.session_state.get("user_name", "Developer"),
            "email": st.session_state.get("user_email", ""),
            "role": st.session_state.get("user_role", "property_developer")
        }
    
    def init_enhanced_persistence(self):
        """Initialize enhanced persistence for persistent data access"""
        try:
            from data_persistence import DataPersistenceManager
            self.persistence_manager = DataPersistenceManager()
        except ImportError:
            self.persistence_manager = None
    
    def show(self):
        """Main developer dashboard with persistent data access"""
        st.markdown(f"""
        <div class="main-header">
            <h1>Portfolio Management Dashboard</h1>
            <p>Property Developer Interface - No CSV Upload Required</p>
            <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
                <span>Welcome back, <strong>{self.user['name']}</strong>!</span>
                <span style="margin-left: 2rem;">Role: <strong>Property Developer</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Show available buildings - NO CSV UPLOAD NEEDED
        self.show_building_selection()
    
    def show_building_selection(self):
        """Show all available buildings with inspection data"""
        st.markdown("### Your Portfolio Buildings")
        
        # Get all buildings with inspection data
        buildings = self.get_accessible_buildings()
        
        if not buildings:
            st.warning("No buildings with inspection data found. Contact your team to process inspection data for your buildings.")
            return
        
        st.success(f"Found {len(buildings)} buildings with inspection data")
        
        # Building selection interface
        building_options = []
        building_lookup = {}
        
        for building in buildings:
            display_name = f"{building['name']} - {building['total_units']} units - Last inspected: {building['inspection_date']}"
            building_options.append(display_name)
            building_lookup[display_name] = building
        
        selected_building_display = st.selectbox(
            "Select building to analyze:",
            options=building_options,
            help="All buildings with processed inspection data are automatically available"
        )
        
        if selected_building_display:
            selected_building = building_lookup[selected_building_display]
            self.show_building_analytics(selected_building)
    
    def get_accessible_buildings(self):
        """Get all buildings accessible to this developer"""
        try:
            conn = sqlite3.connect("inspection_system.db")
            cursor = conn.cursor()
            
            # Property developers can access all buildings with inspection data
            cursor.execute('''
                SELECT DISTINCT 
                    pi.building_name as name,
                    pi.address,
                    pi.inspection_date,
                    pi.processed_at,
                    pi.id as inspection_id,
                    COALESCE(
                        JSON_EXTRACT(pi.metrics_json, '$.total_units'),
                        (SELECT COUNT(DISTINCT id.unit_number) 
                         FROM inspection_defects id 
                         WHERE id.inspection_id = pi.id)
                    ) as total_units
                FROM processed_inspections pi
                WHERE pi.is_active = 1
                ORDER BY pi.processed_at DESC
            ''')
            
            buildings = []
            for row in cursor.fetchall():
                buildings.append({
                    'name': row[0],
                    'address': row[1], 
                    'inspection_date': row[2],
                    'processed_at': row[3],
                    'inspection_id': row[4],
                    'total_units': row[5] or 0
                })
            
            conn.close()
            return buildings
            
        except Exception as e:
            st.error(f"Error loading buildings: {e}")
            return []
    
    def show_building_analytics(self, building):
        """Show analytics for selected building"""
        st.markdown(f"### Analytics for {building['name']}")
        
        # Load building data from database
        processed_data, metrics = self.load_building_data(building['inspection_id'])
        
        if processed_data is None:
            st.error("Failed to load building data from database")
            return
        
        # Store in session state for other components
        st.session_state.processed_data = processed_data
        st.session_state.metrics = metrics
        
        # Building overview
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Building", building['name'])
        with col2:
            st.metric("Total Units", building['total_units'])
        with col3:
            ready_pct = metrics.get('ready_pct', 0)
            ready_units = metrics.get('ready_units', 0)
            st.metric("Ready for Settlement", f"{ready_units} ({ready_pct:.1f}%)")
        with col4:
            urgent_defects = metrics.get('urgent_defects', 0)
            st.metric("Urgent Issues", urgent_defects)
        
        # Show defect approval interface for completed work
        self.show_defect_approval_interface(building)
        
        # Show portfolio analytics
        self.show_portfolio_analytics(metrics)
        
        # Unit lookup
        self.show_unit_lookup()
    
    def load_building_data(self, inspection_id):
        """Load processed data and metrics from database"""
        try:
            if self.persistence_manager:
                return self.persistence_manager.load_latest_inspection()
            
            # Fallback direct database access
            conn = sqlite3.connect("inspection_system.db")
            cursor = conn.cursor()
            
            # Load inspection items
            cursor.execute('''
                SELECT unit_number, unit_type, room, component, trade, 
                       status_class, urgency, planned_completion
                FROM inspection_items 
                WHERE inspection_id = ?
                ORDER BY unit_number, room, component
            ''', (inspection_id,))
            
            items = cursor.fetchall()
            if not items:
                # Fallback to defects table
                cursor.execute('''
                    SELECT unit_number, unit_type, room, component, trade, 
                           urgency, planned_completion, 'Not OK' as status_class
                    FROM inspection_defects 
                    WHERE inspection_id = ?
                ''', (inspection_id,))
                items = cursor.fetchall()
            
            if items:
                processed_data = pd.DataFrame(
                    items,
                    columns=["Unit", "UnitType", "Room", "Component", "Trade", 
                            "StatusClass", "Urgency", "PlannedCompletion"]
                )
                
                # Load metrics
                cursor.execute('SELECT metrics_json FROM processed_inspections WHERE id = ?', (inspection_id,))
                metrics_result = cursor.fetchone()
                
                if metrics_result and metrics_result[0]:
                    import json
                    metrics = json.loads(metrics_result[0])
                else:
                    metrics = self.calculate_basic_metrics(processed_data)
                
                conn.close()
                return processed_data, metrics
            
            conn.close()
            return None, None
            
        except Exception as e:
            st.error(f"Error loading building data: {e}")
            return None, None
    
    def calculate_basic_metrics(self, processed_data):
        """Calculate basic metrics if not stored"""
        defects = processed_data[processed_data["StatusClass"] == "Not OK"] if "StatusClass" in processed_data.columns else processed_data
        
        total_units = processed_data["Unit"].nunique()
        total_defects = len(defects)
        
        # Simple settlement readiness calculation
        if total_defects > 0:
            defects_per_unit = defects.groupby("Unit").size()
            ready_units = (defects_per_unit <= 2).sum()
            ready_units += total_units - len(defects_per_unit)  # Units with no defects
        else:
            ready_units = total_units
        
        return {
            'building_name': 'Building',
            'total_units': total_units,
            'total_defects': total_defects,
            'ready_units': ready_units,
            'ready_pct': (ready_units / total_units * 100) if total_units > 0 else 0,
            'urgent_defects': len(defects[defects["Urgency"] == "Urgent"]) if "Urgency" in defects.columns else 0,
            'summary_trade': defects.groupby("Trade").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(defects) > 0 else pd.DataFrame(columns=["Trade", "DefectCount"]),
            'summary_unit': defects.groupby("Unit").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(defects) > 0 else pd.DataFrame(columns=["Unit", "DefectCount"])
        }
    
    def show_defect_approval_interface(self, building):
        """Interface for approving completed defects"""
        st.markdown("---")
        st.markdown("### Defect Completion Approval")
        
        try:
            conn = sqlite3.connect("inspection_system.db")
            cursor = conn.cursor()
            
            # Check if enhanced tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='enhanced_defects'")
            has_enhanced_tables = cursor.fetchone() is not None
            
            if has_enhanced_tables:
                # Get defects pending approval
                cursor.execute('''
                    SELECT ed.id, ed.unit_number, ed.room, ed.component, ed.trade, 
                           ed.urgency, ed.completed_by, ed.completed_at, ed.completion_notes
                    FROM enhanced_defects ed
                    JOIN processed_inspections pi ON ed.inspection_id = pi.id
                    WHERE pi.building_name = ? AND ed.status = 'completed_pending_approval'
                    ORDER BY ed.urgency, ed.completed_at
                ''', (building['name'],))
                
                pending_defects = cursor.fetchall()
                
                if pending_defects:
                    st.warning(f"**{len(pending_defects)} defects are pending your approval**")
                    
                    for defect_data in pending_defects:
                        defect_id = defect_data[0]
                        
                        with st.expander(f"Unit {defect_data[1]} - {defect_data[2]} - {defect_data[3]} ({defect_data[4]})", expanded=False):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.markdown(f"""
                                **Unit:** {defect_data[1]}  
                                **Location:** {defect_data[2]} - {defect_data[3]}  
                                **Trade:** {defect_data[4]}  
                                **Urgency:** {defect_data[5]}  
                                **Completed by:** {defect_data[6]}  
                                **Completed at:** {defect_data[7]}  
                                **Notes:** {defect_data[8] or 'No notes provided'}
                                """)
                            
                            with col2:
                                # Check for completion photos
                                cursor.execute('''
                                    SELECT id, photo_type, description, uploaded_at
                                    FROM defect_photos 
                                    WHERE defect_id = ? AND photo_type = 'after'
                                    ORDER BY uploaded_at DESC
                                    LIMIT 2
                                ''', (defect_id,))
                                
                                photos = cursor.fetchall()
                                if photos:
                                    st.markdown("**Completion Photos:**")
                                    for photo in photos:
                                        st.caption(f"Photo: {photo[2]} (uploaded {photo[3]})")
                                else:
                                    st.info("No completion photos provided")
                            
                            # Approval actions
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                if st.button(f"Approve", key=f"approve_{defect_id}", type="primary"):
                                    cursor.execute('''
                                        UPDATE enhanced_defects 
                                        SET status = 'approved', approved_by = ?, approved_at = ?
                                        WHERE id = ?
                                    ''', (self.user['username'], datetime.now(), defect_id))
                                    conn.commit()
                                    st.success("Defect approved!")
                                    st.rerun()
                            
                            with col2:
                                if st.button(f"Reject", key=f"reject_{defect_id}", type="secondary"):
                                    rejection_reason = st.text_area(
                                        "Rejection reason:", 
                                        key=f"reject_reason_{defect_id}",
                                        placeholder="Explain why this work is not acceptable..."
                                    )
                                    if rejection_reason:
                                        cursor.execute('''
                                            UPDATE enhanced_defects 
                                            SET status = 'rejected', rejected_by = ?, rejected_at = ?, rejection_reason = ?
                                            WHERE id = ?
                                        ''', (self.user['username'], datetime.now(), rejection_reason, defect_id))
                                        conn.commit()
                                        st.success("Defect rejected. Builder will be notified.")
                                        st.rerun()
                else:
                    st.success("No defects pending approval! All work is either in progress or already approved.")
            else:
                st.info("Enhanced defect approval system not yet configured. Contact your administrator to enable photo evidence and approval workflow.")
            
            conn.close()
            
        except Exception as e:
            st.error(f"Error loading defect approval interface: {e}")
    
    def show_portfolio_analytics(self, metrics):
        """Show portfolio analytics"""
        st.markdown("---")
        st.markdown("### Portfolio Performance Analytics")
        
        # Performance grade calculation
        avg_defects_per_unit = metrics.get('total_defects', 0) / max(metrics.get('total_units', 1), 1)
        
        if avg_defects_per_unit <= 2:
            performance_grade = "A"
            grade_color = "success"
            grade_description = "Excellent Quality"
        elif avg_defects_per_unit <= 5:
            performance_grade = "B"
            grade_color = "info"
            grade_description = "Good Quality"
        elif avg_defects_per_unit <= 10:
            performance_grade = "C"
            grade_color = "warning"
            grade_description = "Needs Improvement"
        else:
            performance_grade = "D"
            grade_color = "error"
            grade_description = "Critical Quality Issues"
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if grade_color == "success":
                st.success(f"Quality Grade: **{performance_grade}**")
            elif grade_color == "info":
                st.info(f"Quality Grade: **{performance_grade}**")
            elif grade_color == "warning":
                st.warning(f"Quality Grade: **{performance_grade}**")
            else:
                st.error(f"Quality Grade: **{performance_grade}**")
            st.caption(grade_description)
        
        with col2:
            completion_score = metrics.get('ready_pct', 0)
            st.metric("Settlement Readiness", f"{completion_score:.1f}%")
        
        with col3:
            urgent_defects = metrics.get('urgent_defects', 0)
            risk_level = "Low" if urgent_defects == 0 else "Medium" if urgent_defects <= 3 else "High"
            if risk_level == "Low":
                st.success(f"Risk Level: **{risk_level}**")
            elif risk_level == "Medium":
                st.warning(f"Risk Level: **{risk_level}**")
            else:
                st.error(f"Risk Level: **{risk_level}**")
        
        with col4:
            st.metric("Avg Defects/Unit", f"{avg_defects_per_unit:.1f}")
        
        # Summary tables
        if 'summary_trade' in metrics and len(metrics['summary_trade']) > 0:
            st.markdown("#### Trade Performance Summary")
            st.dataframe(metrics['summary_trade'], use_container_width=True)
    
    def show_unit_lookup(self):
        """Unit lookup functionality"""
        if st.session_state.get('processed_data') is not None:
            st.markdown("---")
            st.markdown("### Unit Lookup")
            
            processed_data = st.session_state.processed_data
            all_units = sorted(processed_data["Unit"].astype(str).unique())
            
            selected_unit = st.selectbox(
                "Select Unit to View Details:",
                options=[""] + all_units,
                key="dev_unit_lookup"
            )
            
            if selected_unit:
                unit_defects = lookup_unit_defects(processed_data, selected_unit)
                
                if len(unit_defects) > 0:
                    st.markdown(f"**Unit {selected_unit} Defects:**")
                    st.dataframe(unit_defects, use_container_width=True)
                else:
                    st.success(f"Unit {selected_unit} has no defects!")