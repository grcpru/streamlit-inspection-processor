"""
Enhanced Defect Management System
Addresses:
1. Persistent data for Property Developers (no re-upload needed)
2. Complete defect workflow with approval process
3. Photo evidence management for completed defects
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import base64
import os
from typing import Dict, List, Optional, Tuple
import uuid
from PIL import Image
import io

# =============================================================================
# ENHANCED DATA PERSISTENCE WITH PHOTO MANAGEMENT
# =============================================================================

class EnhancedDataPersistenceManager:
    """Enhanced persistence manager with photo support and approval workflow"""
    
    def __init__(self, db_path="inspection_system.db"):
        self.db_path = db_path
        self.ensure_enhanced_tables_exist()
    
    def ensure_enhanced_tables_exist(self):
        """Create enhanced tables for photos and approval workflow"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Enhanced defects table with workflow status
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS enhanced_defects (
                    id TEXT PRIMARY KEY,
                    inspection_id TEXT NOT NULL,
                    unit_number TEXT,
                    unit_type TEXT,
                    room TEXT,
                    component TEXT,
                    trade TEXT,
                    urgency TEXT CHECK (urgency IN ('Normal', 'High Priority', 'Urgent')),
                    planned_completion DATE,
                    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'assigned', 'in_progress', 'completed_pending_approval', 'approved', 'rejected')),
                    assigned_to TEXT,
                    completed_by TEXT,
                    completed_at TIMESTAMP,
                    completion_notes TEXT,
                    approved_by TEXT,
                    approved_at TIMESTAMP,
                    approval_notes TEXT,
                    rejected_by TEXT,
                    rejected_at TIMESTAMP,
                    rejection_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inspection_id) REFERENCES processed_inspections(id),
                    FOREIGN KEY (assigned_to) REFERENCES users(username),
                    FOREIGN KEY (completed_by) REFERENCES users(username),
                    FOREIGN KEY (approved_by) REFERENCES users(username),
                    FOREIGN KEY (rejected_by) REFERENCES users(username)
                )
            ''')
            
            # Photo evidence table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS defect_photos (
                    id TEXT PRIMARY KEY,
                    defect_id TEXT NOT NULL,
                    photo_type TEXT CHECK (photo_type IN ('before', 'during', 'after', 'evidence')),
                    filename TEXT NOT NULL,
                    photo_data BLOB NOT NULL,
                    uploaded_by TEXT,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    FOREIGN KEY (defect_id) REFERENCES enhanced_defects(id),
                    FOREIGN KEY (uploaded_by) REFERENCES users(username)
                )
            ''')
            
            # Defect workflow history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS defect_workflow_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    defect_id TEXT NOT NULL,
                    previous_status TEXT,
                    new_status TEXT,
                    changed_by TEXT,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (defect_id) REFERENCES enhanced_defects(id),
                    FOREIGN KEY (changed_by) REFERENCES users(username)
                )
            ''')
            
            # Building access permissions for persistent viewing
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS building_access (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    building_id TEXT NOT NULL,
                    access_level TEXT CHECK (access_level IN ('read', 'write', 'admin')),
                    granted_by TEXT,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (username) REFERENCES users(username),
                    FOREIGN KEY (building_id) REFERENCES buildings(id),
                    FOREIGN KEY (granted_by) REFERENCES users(username),
                    UNIQUE(username, building_id)
                )
            ''')
            
            # Indexes for performance
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_enhanced_defects_status ON enhanced_defects(status)',
                'CREATE INDEX IF NOT EXISTS idx_enhanced_defects_assigned ON enhanced_defects(assigned_to)',
                'CREATE INDEX IF NOT EXISTS idx_enhanced_defects_building ON enhanced_defects(inspection_id)',
                'CREATE INDEX IF NOT EXISTS idx_photos_defect ON defect_photos(defect_id)',
                'CREATE INDEX IF NOT EXISTS idx_workflow_defect ON defect_workflow_history(defect_id)',
                'CREATE INDEX IF NOT EXISTS idx_building_access_user ON building_access(username)',
                'CREATE INDEX IF NOT EXISTS idx_building_access_building ON building_access(building_id)'
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error creating enhanced tables: {e}")

    def migrate_legacy_defects(self):
        """Migrate existing defects to enhanced system"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if migration needed
            cursor.execute('SELECT COUNT(*) FROM enhanced_defects')
            enhanced_count = cursor.fetchone()[0]
            
            if enhanced_count == 0:
                # Migrate from legacy table
                cursor.execute('''
                    INSERT INTO enhanced_defects 
                    (id, inspection_id, unit_number, unit_type, room, component, 
                     trade, urgency, planned_completion, status, assigned_to, created_at)
                    SELECT 
                        'defect_' || id,
                        inspection_id, unit_number, unit_type, room, component,
                        trade, urgency, planned_completion, status, assigned_to, created_at
                    FROM inspection_defects
                ''')
                conn.commit()
                print("Migrated legacy defects to enhanced system")
            
            conn.close()
            
        except Exception as e:
            print(f"Error migrating defects: {e}")

    def save_defect_photo(self, defect_id: str, photo_file, photo_type: str, 
                         uploaded_by: str, description: str = "") -> bool:
        """Save photo evidence for a defect"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Read and compress image
            image = Image.open(photo_file)
            
            # Resize if too large (max 1920x1080)
            if image.width > 1920 or image.height > 1080:
                image.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
            
            # Convert to JPEG and compress
            img_buffer = io.BytesIO()
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            image.save(img_buffer, format='JPEG', quality=85, optimize=True)
            img_data = img_buffer.getvalue()
            
            photo_id = str(uuid.uuid4())
            filename = f"{defect_id}_{photo_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
            cursor.execute('''
                INSERT INTO defect_photos 
                (id, defect_id, photo_type, filename, photo_data, uploaded_by, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (photo_id, defect_id, photo_type, filename, img_data, uploaded_by, description))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error saving photo: {e}")
            return False

    def get_defect_photos(self, defect_id: str) -> List[Dict]:
        """Get all photos for a defect"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, photo_type, filename, uploaded_by, uploaded_at, description
                FROM defect_photos 
                WHERE defect_id = ?
                ORDER BY uploaded_at DESC
            ''', (defect_id,))
            
            photos = []
            for row in cursor.fetchall():
                photos.append({
                    'id': row[0],
                    'photo_type': row[1],
                    'filename': row[2],
                    'uploaded_by': row[3],
                    'uploaded_at': row[4],
                    'description': row[5]
                })
            
            conn.close()
            return photos
            
        except Exception as e:
            print(f"Error getting photos: {e}")
            return []

    def get_photo_data(self, photo_id: str) -> Optional[bytes]:
        """Get photo data for display"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT photo_data FROM defect_photos WHERE id = ?', (photo_id,))
            result = cursor.fetchone()
            
            conn.close()
            return result[0] if result else None
            
        except Exception as e:
            print(f"Error getting photo data: {e}")
            return None

    def update_defect_status(self, defect_id: str, new_status: str, 
                           changed_by: str, notes: str = "") -> bool:
        """Update defect status with workflow tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current status
            cursor.execute('SELECT status FROM enhanced_defects WHERE id = ?', (defect_id,))
            result = cursor.fetchone()
            if not result:
                return False
            
            old_status = result[0]
            
            # Update defect
            if new_status == 'completed_pending_approval':
                cursor.execute('''
                    UPDATE enhanced_defects 
                    SET status = ?, completed_by = ?, completed_at = ?, 
                        completion_notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_status, changed_by, datetime.now(), notes, defect_id))
            elif new_status == 'approved':
                cursor.execute('''
                    UPDATE enhanced_defects 
                    SET status = ?, approved_by = ?, approved_at = ?, 
                        approval_notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_status, changed_by, datetime.now(), notes, defect_id))
            elif new_status == 'rejected':
                cursor.execute('''
                    UPDATE enhanced_defects 
                    SET status = ?, rejected_by = ?, rejected_at = ?, 
                        rejection_reason = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_status, changed_by, datetime.now(), notes, defect_id))
            else:
                cursor.execute('''
                    UPDATE enhanced_defects 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_status, defect_id))
            
            # Record workflow history
            cursor.execute('''
                INSERT INTO defect_workflow_history 
                (defect_id, previous_status, new_status, changed_by, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (defect_id, old_status, new_status, changed_by, notes))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error updating defect status: {e}")
            return False

    def get_user_accessible_buildings(self, username: str, user_role: str) -> List[Dict]:
        """Get buildings user can access based on role and permissions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if user_role in ['admin', 'property_developer']:
                # Admin and developers can see all buildings with inspection data
                cursor.execute('''
                    SELECT DISTINCT b.id, b.name, b.address, b.total_units,
                           pi.inspection_date, pi.processed_at
                    FROM buildings b
                    JOIN processed_inspections pi ON b.id = pi.building_id
                    WHERE pi.is_active = 1
                    ORDER BY b.name
                ''')
            else:
                # Other roles need explicit access
                cursor.execute('''
                    SELECT DISTINCT b.id, b.name, b.address, b.total_units,
                           pi.inspection_date, pi.processed_at
                    FROM buildings b
                    JOIN processed_inspections pi ON b.id = pi.building_id
                    JOIN building_access ba ON b.id = ba.building_id
                    WHERE pi.is_active = 1 AND ba.username = ? AND ba.is_active = 1
                    ORDER BY b.name
                ''', (username,))
            
            buildings = []
            for row in cursor.fetchall():
                buildings.append({
                    'id': row[0],
                    'name': row[1],
                    'address': row[2],
                    'total_units': row[3],
                    'inspection_date': row[4],
                    'processed_at': row[5]
                })
            
            conn.close()
            return buildings
            
        except Exception as e:
            print(f"Error getting accessible buildings: {e}")
            return []

    def load_building_data(self, building_id: str) -> Tuple[Optional[pd.DataFrame], Optional[Dict]]:
        """Load complete inspection data for a specific building"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get latest active inspection for this building
            cursor.execute('''
                SELECT id, building_name, address, inspection_date, metrics_json
                FROM processed_inspections 
                WHERE building_id = ? AND is_active = 1
                ORDER BY processed_at DESC 
                LIMIT 1
            ''', (building_id,))
            
            inspection = cursor.fetchone()
            if not inspection:
                return None, None
            
            inspection_id = inspection[0]
            
            # Load complete inspection items
            cursor.execute('''
                SELECT unit_number, unit_type, room, component, trade, 
                       status_class, urgency, planned_completion
                FROM inspection_items 
                WHERE inspection_id = ?
                ORDER BY unit_number, room, component
            ''', (inspection_id,))
            
            items = cursor.fetchall()
            if not items:
                return None, None
            
            processed_data = pd.DataFrame(
                items,
                columns=["Unit", "UnitType", "Room", "Component", "Trade", 
                        "StatusClass", "Urgency", "PlannedCompletion"]
            )
            processed_data["PlannedCompletion"] = pd.to_datetime(
                processed_data["PlannedCompletion"], errors='coerce'
            )
            
            # Load and restore metrics
            import json
            metrics = json.loads(inspection[4]) if inspection[4] else {}
            
            # Restore numeric values
            numeric_fields = [
                'total_units', 'total_inspections', 'total_defects', 'defect_rate',
                'avg_defects_per_unit', 'ready_units', 'minor_work_units', 
                'major_work_units', 'extensive_work_units', 'ready_pct', 
                'minor_pct', 'major_pct', 'extensive_pct', 'urgent_defects',
                'high_priority_defects', 'planned_work_2weeks', 'planned_work_month'
            ]
            
            for field in numeric_fields:
                if field in metrics and isinstance(metrics[field], str):
                    try:
                        if '.' not in metrics[field]:
                            metrics[field] = int(metrics[field])
                        else:
                            metrics[field] = float(metrics[field])
                    except (ValueError, TypeError):
                        pass
            
            conn.close()
            return processed_data, metrics
            
        except Exception as e:
            print(f"Error loading building data: {e}")
            return None, None

# =============================================================================
# ENHANCED PROPERTY DEVELOPER DASHBOARD
# =============================================================================

def show_enhanced_property_developer_dashboard():
    """Enhanced Property Developer dashboard with persistent data access"""
    st.markdown("### Portfolio Management Dashboard")
    
    # Initialize enhanced persistence manager
    enhanced_manager = EnhancedDataPersistenceManager()
    enhanced_manager.migrate_legacy_defects()
    
    user = {
        "username": st.session_state.get("username", ""),
        "name": st.session_state.get("user_name", "Developer"),
        "role": st.session_state.get("user_role", "property_developer")
    }
    
    # Get accessible buildings
    buildings = enhanced_manager.get_user_accessible_buildings(user['username'], user['role'])
    
    if not buildings:
        st.warning("No buildings with inspection data found. Contact your team to process inspection data.")
        return
    
    # Building selection interface
    st.markdown("#### Select Building to View")
    
    building_options = []
    building_lookup = {}
    
    for building in buildings:
        display_name = f"{building['name']} - {building['total_units']} units"
        building_options.append(display_name)
        building_lookup[display_name] = building
    
    selected_building_display = st.selectbox(
        "Choose building to view:",
        options=building_options,
        help="Select a building to view detailed analytics and approve defect completions"
    )
    
    if not selected_building_display:
        return
    
    selected_building = building_lookup[selected_building_display]
    
    # Load building data
    with st.spinner("Loading building data..."):
        processed_data, metrics = enhanced_manager.load_building_data(selected_building['id'])
    
    if processed_data is None or metrics is None:
        st.error("Failed to load building data. Contact your administrator.")
        return
    
    # Store in session state for other components
    st.session_state.processed_data = processed_data
    st.session_state.metrics = metrics
    
    # Building overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Building", metrics['building_name'])
    with col2:
        st.metric("Total Units", metrics['total_units'])
    with col3:
        st.metric("Ready for Settlement", f"{metrics['ready_units']} ({metrics['ready_pct']:.1f}%)")
    with col4:
        st.metric("Urgent Issues", metrics['urgent_defects'])
    
    # Show defect approval interface
    show_defect_approval_interface(enhanced_manager, selected_building['id'], user)
    
    # Portfolio analytics (existing functionality)
    show_portfolio_analytics_section(metrics)

def show_defect_approval_interface(enhanced_manager, building_id: str, user: Dict):
    """Interface for approving completed defects"""
    st.markdown("---")
    st.markdown("### Defect Approval Center")
    
    try:
        conn = sqlite3.connect(enhanced_manager.db_path)
        cursor = conn.cursor()
        
        # Get defects pending approval
        cursor.execute('''
            SELECT ed.id, ed.unit_number, ed.room, ed.component, ed.trade, 
                   ed.urgency, ed.completed_by, ed.completed_at, ed.completion_notes
            FROM enhanced_defects ed
            JOIN processed_inspections pi ON ed.inspection_id = pi.id
            WHERE pi.building_id = ? AND ed.status = 'completed_pending_approval'
            ORDER BY ed.urgency, ed.completed_at
        ''', (building_id,))
        
        pending_defects = cursor.fetchall()
        conn.close()
        
        if not pending_defects:
            st.success("No defects pending approval! All work is either in progress or already approved.")
            return
        
        st.warning(f"**{len(pending_defects)} defects are pending your approval**")
        
        # Display pending defects
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
                    # Show photos if available
                    photos = enhanced_manager.get_defect_photos(defect_id)
                    after_photos = [p for p in photos if p['photo_type'] == 'after']
                    
                    if after_photos:
                        st.markdown("**Completion Photos:**")
                        for photo in after_photos[:2]:  # Show max 2 photos
                            photo_data = enhanced_manager.get_photo_data(photo['id'])
                            if photo_data:
                                st.image(photo_data, caption=photo['description'], width=200)
                    else:
                        st.info("No completion photos provided")
                
                # Approval actions
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"✅ Approve", key=f"approve_{defect_id}", type="primary"):
                        approval_notes = st.text_input(
                            "Approval notes (optional):", 
                            key=f"approve_notes_{defect_id}"
                        )
                        if enhanced_manager.update_defect_status(
                            defect_id, 'approved', user['username'], approval_notes
                        ):
                            st.success("Defect approved!")
                            st.rerun()
                        else:
                            st.error("Failed to approve defect")
                
                with col2:
                    if st.button(f"❌ Reject", key=f"reject_{defect_id}", type="secondary"):
                        rejection_reason = st.text_area(
                            "Rejection reason (required):", 
                            key=f"reject_reason_{defect_id}",
                            placeholder="Explain why this work is not acceptable..."
                        )
                        if rejection_reason and enhanced_manager.update_defect_status(
                            defect_id, 'rejected', user['username'], rejection_reason
                        ):
                            st.success("Defect rejected. Builder will be notified.")
                            st.rerun()
                        elif not rejection_reason:
                            st.error("Rejection reason is required")
                
                with col3:
                    if st.button(f"📋 View Details", key=f"details_{defect_id}"):
                        show_defect_detail_modal(enhanced_manager, defect_id)
        
    except Exception as e:
        st.error(f"Error loading defect approval interface: {e}")

# =============================================================================
# ENHANCED BUILDER DASHBOARD
# =============================================================================

def show_enhanced_builder_dashboard():
    """Enhanced Builder dashboard with photo upload and completion workflow"""
    st.markdown("### Builder Workspace")
    
    # Initialize enhanced persistence manager
    enhanced_manager = EnhancedDataPersistenceManager()
    enhanced_manager.migrate_legacy_defects()
    
    user = {
        "username": st.session_state.get("username", ""),
        "name": st.session_state.get("user_name", "Builder"),
        "role": st.session_state.get("user_role", "builder")
    }
    
    # Get accessible buildings
    buildings = enhanced_manager.get_user_accessible_buildings(user['username'], user['role'])
    
    if not buildings:
        st.info("No buildings assigned. Contact your project manager for access.")
        return
    
    # Building selection
    building_options = [f"{b['name']} - {b['total_units']} units" for b in buildings]
    building_lookup = {opt: buildings[i] for i, opt in enumerate(building_options)}
    
    selected_building_display = st.selectbox(
        "Select building to work on:",
        options=building_options
    )
    
    if not selected_building_display:
        return
    
    selected_building = building_lookup[selected_building_display]
    
    # Show work assignments
    show_builder_work_assignments(enhanced_manager, selected_building['id'], user)

def show_builder_work_assignments(enhanced_manager, building_id: str, user: Dict):
    """Show builder work assignments with completion workflow"""
    try:
        conn = sqlite3.connect(enhanced_manager.db_path)
        cursor = conn.cursor()
        
        # Get assigned defects
        cursor.execute('''
            SELECT ed.id, ed.unit_number, ed.room, ed.component, ed.trade, 
                   ed.urgency, ed.planned_completion, ed.status
            FROM enhanced_defects ed
            JOIN processed_inspections pi ON ed.inspection_id = pi.id
            WHERE pi.building_id = ? AND ed.status IN ('open', 'assigned', 'in_progress')
            ORDER BY 
                CASE ed.urgency 
                    WHEN 'Urgent' THEN 1 
                    WHEN 'High Priority' THEN 2 
                    ELSE 3 
                END,
                ed.planned_completion
        ''', (building_id,))
        
        work_assignments = cursor.fetchall()
        conn.close()
        
        if not work_assignments:
            st.success("No open work assignments! All defects are completed or approved.")
            return
        
        st.markdown(f"### Your Work Assignments ({len(work_assignments)} items)")
        
        # Summary by urgency
        urgent_count = len([w for w in work_assignments if w[5] == 'Urgent'])
        high_priority_count = len([w for w in work_assignments if w[5] == 'High Priority'])
        normal_count = len(work_assignments) - urgent_count - high_priority_count
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Urgent", urgent_count)
        with col2:
            st.metric("High Priority", high_priority_count)
        with col3:
            st.metric("Normal", normal_count)
        
        # Work items interface
        for work_data in work_assignments:
            defect_id = work_data[0]
            
            urgency_emoji = "🚨" if work_data[5] == "Urgent" else "⚠️" if work_data[5] == "High Priority" else "🔧"
            
            with st.expander(f"{urgency_emoji} Unit {work_data[1]} - {work_data[2]} - {work_data[3]} ({work_data[4]})", expanded=False):
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"""
                    **Unit:** {work_data[1]}  
                    **Location:** {work_data[2]} - {work_data[3]}  
                    **Trade:** {work_data[4]}  
                    **Urgency:** {work_data[5]}  
                    **Due Date:** {work_data[6]}  
                    **Current Status:** {work_data[7].replace('_', ' ').title()}
                    """)
                
                with col2:
                    # Show existing photos
                    photos = enhanced_manager.get_defect_photos(defect_id)
                    if photos:
                        st.markdown("**Photos:**")
                        for photo in photos[-2:]:  # Show last 2 photos
                            photo_data = enhanced_manager.get_photo_data(photo['id'])
                            if photo_data:
                                st.image(photo_data, caption=f"{photo['photo_type']} - {photo['description']}", width=150)
                
                # Action buttons
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"📸 Add Photo", key=f"photo_{defect_id}"):
                        show_photo_upload_interface(enhanced_manager, defect_id, user)
                
                with col2:
                    if work_data[7] != 'in_progress' and st.button(f"🔄 Start Work", key=f"start_{defect_id}"):
                        if enhanced_manager.update_defect_status(defect_id, 'in_progress', user['username']):
                            st.success("Work started!")
                            st.rerun()
                
                with col3:
                    if st.button(f"✅ Mark Complete", key=f"complete_{defect_id}", type="primary"):
                        show_completion_interface(enhanced_manager, defect_id, user)
        
    except Exception as e:
        st.error(f"Error loading work assignments: {e}")

def show_photo_upload_interface(enhanced_manager, defect_id: str, user: Dict):
    """Interface for uploading photos"""
    st.markdown("#### Upload Photo Evidence")
    
    photo_type = st.selectbox(
        "Photo type:",
        options=['before', 'during', 'after', 'evidence'],
        help="Select the type of photo you're uploading"
    )
    
    description = st.text_input(
        "Photo description:",
        placeholder="Describe what this photo shows..."
    )
    
    uploaded_photo = st.file_uploader(
        "Choose photo file:",
        type=['png', 'jpg', 'jpeg'],
        help="Upload a clear photo showing the defect or work progress"
    )
    
    if uploaded_photo and st.button("Upload Photo"):
        if enhanced_manager.save_defect_photo(defect_id, uploaded_photo, photo_type, user['username'], description):
            st.success("Photo uploaded successfully!")
            st.rerun()
        else:
            st.error("Failed to upload photo")

def show_completion_interface(enhanced_manager, defect_id: str, user: Dict):
    """Interface for marking defects as complete"""
    st.markdown("#### Mark Defect as Complete")
    
    completion_notes = st.text_area(
        "Completion notes:",
        placeholder="Describe the work performed and any important details...",
        help="Provide details about how the defect was resolved"
    )
    
    st.markdown("**Upload completion photos (required):**")
    
    before_photo = st.file_uploader(
        "Before photo (if not already uploaded):",
        type=['png', 'jpg', 'jpeg'],
        key=f"before_{defect_id}"
    )
    
    after_photo = st.file_uploader(
        "After photo (required):",
        type=['png', 'jpg', 'jpeg'],
        key=f"after_{defect_id}"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Cancel", key=f"cancel_complete_{defect_id}"):
            st.rerun()
    
    with col2:
        if st.button("Submit for Approval", key=f"submit_complete_{defect_id}", type="primary"):
            if not after_photo:
                st.error("After photo is required for completion")
                return
            
            if not completion_notes.strip():
                st.error("Completion notes are required")
                return
            
            # Upload photos
            photos_uploaded = True
            
            if before_photo:
                if not enhanced_manager.save_defect_photo(defect_id, before_photo, 'before', user['username'], "Before work photo"):
                    photos_uploaded = False
            
            if after_photo:
                if not enhanced_manager.save_defect_photo(defect_id, after_photo, 'after', user['username'], "After work completion"):
                    photos_uploaded = False
            
            if photos_uploaded:
                # Mark as completed pending approval
                if enhanced_manager.update_defect_status(defect_id, 'completed_pending_approval', user['username'], completion_notes):
                    st.success("Work submitted for approval! The property developer will review your completion.")
                    st.rerun()
                else:
                    st.error("Failed to submit completion")
            else:
                st.error("Failed to upload photos")

def show_defect_detail_modal(enhanced_manager, defect_id: str):
    """Show detailed defect information including workflow history"""
    try:
        conn = sqlite3.connect(enhanced_manager.db_path)
        cursor = conn.cursor()
        
        # Get defect details
        cursor.execute('''
            SELECT ed.*, pi.building_name
            FROM enhanced_defects ed
            JOIN processed_inspections pi ON ed.inspection_id = pi.id
            WHERE ed.id = ?
        ''', (defect_id,))
        
        defect_details = cursor.fetchone()
        if not defect_details:
            st.error("Defect not found")
            return
        
        # Get workflow history
        cursor.execute('''
            SELECT previous_status, new_status, changed_by, changed_at, notes
            FROM defect_workflow_history
            WHERE defect_id = ?
            ORDER BY changed_at DESC
        ''', (defect_id,))
        
        workflow_history = cursor.fetchall()
        conn.close()
        
        # Display defect details
        st.markdown("#### Defect Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            **Building:** {defect_details[-1]}  
            **Unit:** {defect_details[2]}  
            **Location:** {defect_details[4]} - {defect_details[5]}  
            **Trade:** {defect_details[6]}  
            **Urgency:** {defect_details[7]}  
            **Status:** {defect_details[9].replace('_', ' ').title()}
            """)
        
        with col2:
            if defect_details[11]:  # completed_by
                st.markdown(f"""
                **Completed by:** {defect_details[11]}  
                **Completed at:** {defect_details[12]}  
                **Completion notes:** {defect_details[13] or 'None'}
                """)
            
            if defect_details[14]:  # approved_by
                st.markdown(f"""
                **Approved by:** {defect_details[14]}  
                **Approved at:** {defect_details[15]}  
                **Approval notes:** {defect_details[16] or 'None'}
                """)
        
        # Show photos
        photos = enhanced_manager.get_defect_photos(defect_id)
        if photos:
            st.markdown("#### Photos")
            
            photo_cols = st.columns(min(len(photos), 4))
            for i, photo in enumerate(photos):
                with photo_cols[i % 4]:
                    photo_data = enhanced_manager.get_photo_data(photo['id'])
                    if photo_data:
                        st.image(photo_data, caption=f"{photo['photo_type']} - {photo['description']}", width=150)
                        st.caption(f"By: {photo['uploaded_by']} at {photo['uploaded_at']}")
        
        # Show workflow history
        if workflow_history:
            st.markdown("#### Workflow History")
            
            for history in workflow_history:
                status_change = f"{history[0] or 'New'} → {history[1]}"
                st.markdown(f"""
                **{status_change}**  
                Changed by: {history[2]} at {history[3]}  
                Notes: {history[4] or 'No notes'}
                """)
                st.markdown("---")
        
    except Exception as e:
        st.error(f"Error loading defect details: {e}")

def show_portfolio_analytics_section(metrics: Dict):
    """Show portfolio analytics for property developers"""
    st.markdown("---")
    st.markdown("### Portfolio Analytics")
    
    # Performance overview
    avg_defects_per_unit = metrics['avg_defects_per_unit']
    
    # Performance grade
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
        completion_score = metrics['ready_pct']
        st.metric("Settlement Readiness", f"{completion_score:.1f}%")
    
    with col3:
        risk_level = "Low" if metrics['urgent_defects'] == 0 else "Medium" if metrics['urgent_defects'] <= 3 else "High"
        if risk_level == "Low":
            st.success(f"Risk Level: **{risk_level}**")
        elif risk_level == "Medium":
            st.warning(f"Risk Level: **{risk_level}**")
        else:
            st.error(f"Risk Level: **{risk_level}**")
    
    with col4:
        days_since_inspection = 7  # Placeholder
        velocity = metrics['ready_units'] / max(days_since_inspection / 7, 1)
        st.metric("Completion Velocity", f"{velocity:.1f} units/week")

# =============================================================================
# ENHANCED PROJECT MANAGER DASHBOARD
# =============================================================================

def show_enhanced_project_manager_dashboard():
    """Enhanced Project Manager dashboard with defect workflow oversight"""
    st.markdown("### Project Management Dashboard")
    
    # Initialize enhanced persistence manager
    enhanced_manager = EnhancedDataPersistenceManager()
    enhanced_manager.migrate_legacy_defects()
    
    user = {
        "username": st.session_state.get("username", ""),
        "name": st.session_state.get("user_name", "Manager"),
        "role": st.session_state.get("user_role", "project_manager")
    }
    
    # Get accessible buildings
    buildings = enhanced_manager.get_user_accessible_buildings(user['username'], user['role'])
    
    if not buildings:
        st.warning("No buildings with inspection data found.")
        return
    
    # Building selection
    building_options = [f"{b['name']} - {b['total_units']} units" for b in buildings]
    building_lookup = {opt: buildings[i] for i, opt in enumerate(building_options)}
    
    selected_building_display = st.selectbox(
        "Choose building to manage:",
        options=building_options
    )
    
    if not selected_building_display:
        return
    
    selected_building = building_lookup[selected_building_display]
    
    # Load building data
    processed_data, metrics = enhanced_manager.load_building_data(selected_building['id'])
    
    if processed_data is None:
        st.error("Failed to load building data.")
        return
    
    # Store in session state
    st.session_state.processed_data = processed_data
    st.session_state.metrics = metrics
    
    # Building overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Building", metrics['building_name'])
    with col2:
        st.metric("Total Units", metrics['total_units'])
    with col3:
        st.metric("Ready for Settlement", f"{metrics['ready_units']} ({metrics['ready_pct']:.1f}%)")
    with col4:
        st.metric("Urgent Issues", metrics['urgent_defects'])
    
    # Show defect management interface
    show_project_manager_defect_overview(enhanced_manager, selected_building['id'], user)

def show_project_manager_defect_overview(enhanced_manager, building_id: str, user: Dict):
    """Project manager's defect workflow overview"""
    try:
        conn = sqlite3.connect(enhanced_manager.db_path)
        cursor = conn.cursor()
        
        # Get defect counts by status
        cursor.execute('''
            SELECT ed.status, COUNT(*) as count
            FROM enhanced_defects ed
            JOIN processed_inspections pi ON ed.inspection_id = pi.id
            WHERE pi.building_id = ?
            GROUP BY ed.status
        ''', (building_id,))
        
        status_counts = dict(cursor.fetchall())
        
        st.markdown("---")
        st.markdown("### Defect Workflow Overview")
        
        # Status overview
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Open", status_counts.get('open', 0))
        with col2:
            st.metric("In Progress", status_counts.get('in_progress', 0))
        with col3:
            st.metric("Pending Approval", status_counts.get('completed_pending_approval', 0))
        with col4:
            st.metric("Approved", status_counts.get('approved', 0))
        with col5:
            st.metric("Rejected", status_counts.get('rejected', 0))
        
        # Defect assignment interface
        st.markdown("#### Assign Defects to Builders")
        
        # Get unassigned defects
        cursor.execute('''
            SELECT ed.id, ed.unit_number, ed.room, ed.component, ed.trade, ed.urgency
            FROM enhanced_defects ed
            JOIN processed_inspections pi ON ed.inspection_id = pi.id
            WHERE pi.building_id = ? AND ed.status = 'open' AND ed.assigned_to IS NULL
            ORDER BY 
                CASE ed.urgency 
                    WHEN 'Urgent' THEN 1 
                    WHEN 'High Priority' THEN 2 
                    ELSE 3 
                END
            LIMIT 10
        ''', (building_id,))
        
        unassigned_defects = cursor.fetchall()
        
        if unassigned_defects:
            st.warning(f"{len(unassigned_defects)} defects need to be assigned")
            
            # Get available builders
            cursor.execute('''
                SELECT username, full_name 
                FROM users 
                WHERE role = 'builder' AND is_active = 1
            ''')
            builders = cursor.fetchall()
            builder_options = {f"{b[1]} ({b[0]})": b[0] for b in builders}
            
            if builder_options:
                selected_builder = st.selectbox("Assign to builder:", options=list(builder_options.keys()))
                
                if st.button("Assign All Unassigned Defects"):
                    builder_username = builder_options[selected_builder]
                    assigned_count = 0
                    
                    for defect in unassigned_defects:
                        cursor.execute('''
                            UPDATE enhanced_defects 
                            SET assigned_to = ?, status = 'assigned', updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (builder_username, defect[0]))
                        assigned_count += 1
                    
                    conn.commit()
                    st.success(f"Assigned {assigned_count} defects to {selected_builder}")
                    st.rerun()
            else:
                st.info("No builders available for assignment")
        else:
            st.success("All defects are assigned!")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading defect overview: {e}")

# =============================================================================
# INTEGRATION FUNCTIONS
# =============================================================================

def update_main_streamlit_app():
    """
    Integration instructions for updating the main streamlit_app.py
    
    Replace the existing dashboard functions with these enhanced versions:
    
    1. Replace show_enhanced_developer_dashboard() with show_enhanced_property_developer_dashboard()
    2. Replace show_enhanced_builder_dashboard() with show_enhanced_builder_dashboard() 
    3. Replace show_enhanced_project_manager_dashboard() with show_enhanced_project_manager_dashboard()
    
    Add this import at the top:
    from enhanced_defect_system import (
        EnhancedDataPersistenceManager,
        show_enhanced_property_developer_dashboard,
        show_enhanced_builder_dashboard,
        show_enhanced_project_manager_dashboard
    )
    """
    pass

def create_database_migration_script():
    """
    Create a migration script to update existing installations.
    Run this once to migrate existing data to the enhanced system.
    """
    migration_sql = '''
    -- Migration script for enhanced defect management
    -- Run this once to upgrade existing installations
    
    -- Backup existing data
    CREATE TABLE IF NOT EXISTS backup_inspection_defects AS SELECT * FROM inspection_defects;
    
    -- Create enhanced tables (run the enhanced table creation from above)
    
    -- Migrate existing defects
    INSERT OR IGNORE INTO enhanced_defects 
    (id, inspection_id, unit_number, unit_type, room, component, 
     trade, urgency, planned_completion, status, assigned_to, created_at)
    SELECT 
        'defect_' || id,
        inspection_id, unit_number, unit_type, room, component,
        trade, urgency, planned_completion, status, assigned_to, created_at
    FROM inspection_defects;
    
    -- Grant building access to property developers for all buildings
    INSERT OR IGNORE INTO building_access (username, building_id, access_level, granted_by)
    SELECT u.username, b.id, 'admin', 'system'
    FROM users u, buildings b
    WHERE u.role = 'property_developer' AND u.is_active = 1;
    
    -- Grant building access to project managers for buildings they manage
    INSERT OR IGNORE INTO building_access (username, building_id, access_level, granted_by)
    SELECT u.username, b.id, 'write', 'system'
    FROM users u, buildings b
    WHERE u.role = 'project_manager' AND u.is_active = 1;
    '''
    
    return migration_sql

# =============================================================================
# CONFIGURATION AND SETUP
# =============================================================================

def setup_enhanced_system():
    """Setup function to initialize the enhanced defect management system"""
    
    # Initialize enhanced persistence manager
    enhanced_manager = EnhancedDataPersistenceManager()
    
    # Migrate legacy data
    enhanced_manager.migrate_legacy_defects()
    
    # Grant default building access permissions
    try:
        conn = sqlite3.connect(enhanced_manager.db_path)
        cursor = conn.cursor()
        
        # Grant property developers access to all buildings
        cursor.execute('''
            INSERT OR IGNORE INTO building_access (username, building_id, access_level, granted_by)
            SELECT u.username, b.id, 'admin', 'system'
            FROM users u
            CROSS JOIN buildings b
            WHERE u.role = 'property_developer' AND u.is_active = 1
        ''')
        
        # Grant project managers access to buildings
        cursor.execute('''
            INSERT OR IGNORE INTO building_access (username, building_id, access_level, granted_by)
            SELECT u.username, b.id, 'write', 'system'
            FROM users u
            CROSS JOIN buildings b
            WHERE u.role = 'project_manager' AND u.is_active = 1
        ''')
        
        conn.commit()
        conn.close()
        
        print("Enhanced defect management system initialized successfully!")
        
    except Exception as e:
        print(f"Error setting up enhanced system: {e}")

if __name__ == "__main__":
    # Run setup if this file is executed directly
    setup_enhanced_system()