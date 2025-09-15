import streamlit as st
import pandas as pd
from io import BytesIO, StringIO
from datetime import datetime, timedelta
import pytz
import traceback
import zipfile
import hashlib
import time
import json
import os
import sqlite3
import uuid
from typing import Dict, List, Optional, Tuple
import uuid
from PIL import Image
import io

from enhanced_defect_system import (
    show_enhanced_property_developer_dashboard,
    show_enhanced_builder_dashboard, 
    show_enhanced_project_manager_dashboard,
    setup_enhanced_system
)
# Import data persistence module
from data_persistence import (
    DataPersistenceManager, 
    save_trade_mapping_to_database, 
    load_trade_mapping_from_database
)

# Add these missing functions to your streamlit_app.py

def setup_enhanced_defects_if_needed(cursor):
    """Auto-setup enhanced defects table if empty"""
    
    try:
        cursor.execute('SELECT COUNT(*) FROM enhanced_defects')
        enhanced_count = cursor.fetchone()[0]
        
        if enhanced_count == 0:
            print("Enhanced defects table is empty, attempting migration...")
            
            # Try to migrate from inspection_defects
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO enhanced_defects 
                    (id, inspection_id, unit_number, unit_type, room, component, trade, urgency, planned_completion, status, created_at)
                    SELECT 
                        'defect_' || id,
                        inspection_id, 
                        unit_number, 
                        unit_type, 
                        room, 
                        component, 
                        trade, 
                        COALESCE(urgency, 'Normal'),
                        COALESCE(planned_completion, date('now', '+14 days')),
                        CASE 
                            WHEN status = 'completed' THEN 'approved'
                            WHEN status IS NULL OR status = '' THEN 'open'
                            ELSE status 
                        END,
                        COALESCE(created_at, CURRENT_TIMESTAMP)
                    FROM inspection_defects
                ''')
                
                migrated = cursor.rowcount
                if migrated > 0:
                    sqlite3.connect("inspection_system.db").commit()
                    print(f"Successfully migrated {migrated} defects from inspection_defects")
                else:
                    print("No data found in inspection_defects to migrate")
                    
            except Exception as migrate_error:
                print(f"Migration from inspection_defects failed: {migrate_error}")
                
                # Try to migrate from inspection_items instead
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO enhanced_defects 
                        (id, inspection_id, unit_number, unit_type, room, component, trade, urgency, planned_completion, status, created_at)
                        SELECT 
                            'item_' || ROW_NUMBER() OVER (ORDER BY unit_number, room, component),
                            inspection_id,
                            unit_number,
                            unit_type,
                            room,
                            component,
                            trade,
                            COALESCE(urgency, 'Normal'),
                            date('now', '+14 days'),
                            'open',
                            CURRENT_TIMESTAMP
                        FROM inspection_items 
                        WHERE status_class = 'Not OK'
                    ''')
                    
                    migrated = cursor.rowcount
                    if migrated > 0:
                        sqlite3.connect("inspection_system.db").commit()
                        print(f"Successfully migrated {migrated} defects from inspection_items")
                    else:
                        print("No defect data found in inspection_items")
                        
                except Exception as items_error:
                    print(f"Migration from inspection_items also failed: {items_error}")
                    print("Enhanced defects table will remain empty")
        else:
            print(f"Enhanced defects table already has {enhanced_count} records")
            
    except Exception as e:
        print(f"Error in setup_enhanced_defects_if_needed: {e}")

def show_recent_completed_work(cursor):
    """Show recent completed work"""
    
    try:
        cursor.execute('''
            SELECT ed.unit_number, ed.room, ed.component, ed.status, ed.completed_at,
                   COALESCE(pi.building_name, 'Unknown Building') as building_name
            FROM enhanced_defects ed
            LEFT JOIN processed_inspections pi ON ed.inspection_id = pi.id
            WHERE ed.status IN ('completed_pending_approval', 'approved')
            ORDER BY ed.completed_at DESC
            LIMIT 10
        ''')
        
        completed_work = cursor.fetchall()
        
        if completed_work:
            st.markdown("### Recent Completed Work")
            for work in completed_work:
                status_icon = "⏳" if work[3] == "completed_pending_approval" else "✅"
                st.info(f"{status_icon} {work[5]} - Unit {work[0]} - {work[1]} - {work[2]} - {work[3].replace('_', ' ').title()}")
        else:
            st.info("No completed work found")
            
    except Exception as e:
        st.error(f"Error loading completed work: {e}")

def show_defect_work_detail(cursor, defect_id, user):
    """Focused work interface for a single defect"""
    
    # Get defect details
    cursor.execute('''
        SELECT ed.room, ed.component, ed.trade, ed.urgency, ed.planned_completion, ed.status, ed.unit_number
        FROM enhanced_defects ed
        WHERE ed.id = ?
    ''', (defect_id,))
    
    defect_details = cursor.fetchone()
    if not defect_details:
        st.error("Defect not found")
        return
    
    room, component, trade, urgency, due_date, status, unit_number = defect_details
    
    st.markdown("---")
    st.markdown(f"### Working on: {room} - {component}")
    st.caption(f"Unit: {unit_number}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"""
        **Trade:** {trade}  
        **Urgency:** {urgency}  
        **Due:** {due_date}  
        **Status:** {status.replace('_', ' ').title()}
        """)
    
    with col2:
        if st.button("← Back to Unit", type="secondary"):
            if "selected_defect" in st.session_state:
                del st.session_state["selected_defect"]
            st.rerun()
    
    # Photo management
    show_photo_management(cursor, defect_id, user)
    
    # Completion interface
    if status in ['open', 'assigned', 'in_progress']:
        show_quick_completion_interface(cursor, defect_id, user)

def show_photo_management(cursor, defect_id, user):
    """Streamlined photo management interface"""
    
    st.markdown("#### Photos")
    
    # Show existing photos
    cursor.execute('''
        SELECT id, photo_type, description, uploaded_at
        FROM defect_photos 
        WHERE defect_id = ?
        ORDER BY uploaded_at DESC
    ''', (defect_id,))
    
    photos = cursor.fetchall()
    
    if photos:
        photo_cols = st.columns(min(len(photos), 4))
        for i, photo in enumerate(photos):
            with photo_cols[i % 4]:
                st.caption(f"{photo[1]}: {photo[2] or 'No description'}")
    else:
        st.info("No photos uploaded yet")
    
    # Quick photo upload
    with st.expander("📸 Add Photo", expanded=False):
        photo_type = st.selectbox(
            "Type:",
            options=['before', 'during', 'after', 'evidence'],
            key=f"photo_type_{defect_id}"
        )
        
        uploaded_photo = st.file_uploader(
            "Choose photo:",
            type=['png', 'jpg', 'jpeg'],
            key=f"photo_file_{defect_id}"
        )
        
        description = st.text_input(
            "Description:",
            placeholder="Brief description...",
            key=f"photo_desc_{defect_id}"
        )
        
        if st.button("Upload", key=f"upload_{defect_id}") and uploaded_photo:
            if save_defect_photo_inline(defect_id, uploaded_photo, photo_type, description, user['username']):
                st.success("Photo uploaded!")
                st.rerun()

def show_quick_completion_interface(cursor, defect_id, user):
    """Quick completion interface"""
    
    st.markdown("#### Mark Complete")
    
    with st.form(f"complete_form_{defect_id}"):
        completion_notes = st.text_area(
            "Work completed:",
            placeholder="Briefly describe what was done...",
            height=100
        )
        
        after_photo = st.file_uploader(
            "After photo (required):",
            type=['png', 'jpg', 'jpeg'],
            help="Show the completed work"
        )
        
        submit_complete = st.form_submit_button("✅ Submit for Approval", type="primary")
        
        if submit_complete:
            if not after_photo:
                st.error("After photo is required")
            elif not completion_notes.strip():
                st.error("Please describe the work completed")
            else:
                # Save after photo
                if save_defect_photo_inline(defect_id, after_photo, 'after', "Completed work", user['username']):
                    # Mark as completed pending approval
                    cursor.execute('''
                        UPDATE enhanced_defects 
                        SET status = 'completed_pending_approval', 
                            completed_by = ?, 
                            completed_at = CURRENT_TIMESTAMP, 
                            completion_notes = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (user['username'], completion_notes, defect_id))
                    
                    sqlite3.connect("inspection_system.db").commit()
                    
                    st.success("Work submitted for approval!")
                    if "selected_defect" in st.session_state:
                        del st.session_state["selected_defect"]
                    st.rerun()
                else:
                    st.error("Failed to upload photo")

def save_defect_photo_inline(defect_id, photo_file, photo_type, description, username):
    """Save photo evidence for a defect"""
    try:
        from PIL import Image
        import io
        import uuid
        from datetime import datetime
        
        image = Image.open(photo_file)
        
        if image.width > 1920 or image.height > 1080:
            image.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
        
        img_buffer = io.BytesIO()
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        image.save(img_buffer, format='JPEG', quality=85, optimize=True)
        img_data = img_buffer.getvalue()
        
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        photo_id = str(uuid.uuid4())
        filename = f"{defect_id}_{photo_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        cursor.execute('''
            INSERT INTO defect_photos 
            (id, defect_id, photo_type, filename, photo_data, uploaded_by, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (photo_id, defect_id, photo_type, filename, img_data, username, description))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error saving photo: {e}")
        return False

def get_corrected_database_stats(db_path="inspection_system.db"):
    """Get corrected database statistics that count unique buildings"""
    try:
        import sqlite3
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
            'active_inspections': active_inspections,  # This will now show 1
            'total_defects': total_defects
        }
        
    except Exception as e:
        print(f"Error getting corrected stats: {e}")
        return {'total_inspections': 0, 'active_inspections': 0, 'total_defects': 0}
    
def load_master_trade_mapping():
    """Load the comprehensive MasterTradeMapping.csv data"""
    try:
        import os
        if os.path.exists("MasterTradeMapping_v2.csv"):
            return pd.read_csv("MasterTradeMapping_v2.csv")
        else:
            st.warning("MasterTradeMapping_v2.csv not found in project folder")
            # Fallback to basic mapping
            basic_mapping = """Room,Component,Trade
Apartment Entry Door,Door Handle,Doors
Apartment Entry Door,Door Locks and Keys,Doors
Balcony,Balustrade,Carpentry & Joinery
Bathroom,Tiles,Flooring - Tiles
Kitchen Area,Cabinets,Carpentry & Joinery"""
            return pd.read_csv(StringIO(basic_mapping))
    except Exception as e:
        st.error(f"Error loading master mapping: {e}")
        return pd.DataFrame(columns=["Room", "Component", "Trade"])

# Add this import at the top with other imports
try:
    from portfolio_analytics import generate_portfolio_analytics_report
    PORTFOLIO_ANALYTICS_AVAILABLE = True
    PORTFOLIO_ANALYTICS_ERROR = None
except ImportError as e:
    PORTFOLIO_ANALYTICS_AVAILABLE = False
    PORTFOLIO_ANALYTICS_ERROR = str(e)
    
# Try to import the professional report generators
WORD_REPORT_AVAILABLE = False
EXCEL_REPORT_AVAILABLE = False
WORD_IMPORT_ERROR = None
EXCEL_IMPORT_ERROR = None

try:
    from excel_report_generator import generate_professional_excel_report, generate_filename
    EXCEL_REPORT_AVAILABLE = True
except Exception as e:
    EXCEL_IMPORT_ERROR = str(e)

try:
    from docx import Document
    from word_report_generator import generate_professional_word_report
    WORD_REPORT_AVAILABLE = True
except Exception as e:
    WORD_IMPORT_ERROR = str(e)

# =============================================================================
# ENHANCED DATABASE AUTHENTICATION SYSTEM
# =============================================================================

class DatabaseAuthManager:
    """Database-powered authentication manager for Streamlit"""
    
    def __init__(self, db_path="inspection_system.db"):
        self.db_path = db_path
        self.session_timeout = 8 * 60 * 60  # 8 hours
        
        # Ensure database exists
        self._init_database_if_needed()
        
        # Role capabilities with enhanced permissions
        self.role_capabilities = {
            "admin": {
                "can_upload": True,
                "can_process": True,
                "can_manage_users": True,
                "can_approve_defects": True,
                "can_view_all": True,
                "can_generate_reports": True,
                "dashboard_type": "admin"
            },
            "property_developer": {
                "can_upload": False,
                "can_process": False,
                "can_manage_users": False,
                "can_approve_defects": True,
                "can_view_all": False,
                "can_generate_reports": True,  # Now can generate reports
                "dashboard_type": "portfolio"
            },
            "project_manager": {
                "can_upload": True,
                "can_process": True,
                "can_manage_users": False,
                "can_approve_defects": True,
                "can_view_all": False,
                "can_generate_reports": True,
                "dashboard_type": "project"
            },
            "inspector": {
                "can_upload": True,
                "can_process": True,
                "can_manage_users": False,
                "can_approve_defects": False,
                "can_view_all": False,
                "can_generate_reports": True,
                "dashboard_type": "inspector"
            },
            "builder": {
                "can_upload": False,
                "can_process": False,
                "can_manage_users": False,
                "can_approve_defects": False,
                "can_view_all": False,
                "can_generate_reports": True,  # Now can generate work reports
                "dashboard_type": "builder"
            }
        }
    
    def _init_database_if_needed(self):
        """Initialize database if it doesn't exist"""
        if not os.path.exists(self.db_path):
            st.error(f"Database not found! Please run: python complete_database_setup.py")
            st.stop()
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = "inspection_app_salt_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        """Authenticate user against database"""
        if not username or not password:
            return False, "Please enter username and password"
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            password_hash = self._hash_password(password)
            
            cursor.execute('''
                SELECT username, full_name, email, role, is_active
                FROM users 
                WHERE username = ? AND password_hash = ? AND is_active = 1
            ''', (username, password_hash))
            
            user_data = cursor.fetchone()
            
            if user_data:
                cursor.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?
                ''', (username,))
                conn.commit()
                conn.close()
                return True, "Login successful"
            else:
                conn.close()
                return False, "Invalid username or password"
                
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """Get complete user information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, full_name, email, role, is_active, last_login
                FROM users WHERE username = ?
            ''', (username,))
            
            user_data = cursor.fetchone()
            conn.close()
            
            if user_data:
                return {
                    "username": user_data[0],
                    "full_name": user_data[1],
                    "email": user_data[2],
                    "role": user_data[3],
                    "is_active": user_data[4],
                    "last_login": user_data[5],
                    "capabilities": self.role_capabilities.get(user_data[3], {})
                }
            return None
        except Exception:
            return None
    
    def create_session(self, username: str):
        """Create Streamlit session with database user info"""
        user_info = self.get_user_info(username)
        
        if user_info:
            st.session_state.authenticated = True
            st.session_state.username = user_info["username"]
            st.session_state.user_name = user_info["full_name"]
            st.session_state.user_email = user_info["email"]
            st.session_state.user_role = user_info["role"]
            st.session_state.login_time = time.time()
            st.session_state.user_capabilities = user_info["capabilities"]
            st.session_state.dashboard_type = user_info["capabilities"].get("dashboard_type", "inspector")
    
    def is_session_valid(self) -> bool:
        """Check if current session is valid"""
        if not st.session_state.get("authenticated", False):
            return False
        
        if not st.session_state.get("login_time"):
            return False
        
        if time.time() - st.session_state.login_time > self.session_timeout:
            self.logout()
            return False
        
        return True
    
    def logout(self):
        """Logout current user"""
        auth_keys = [
            "authenticated", "username", "user_name", "user_email", 
            "user_role", "login_time", "user_capabilities", "dashboard_type"
        ]
        for key in auth_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        app_keys = ["trade_mapping", "processed_data", "metrics", "step_completed", "report_images"]
        for key in app_keys:
            if key in st.session_state:
                del st.session_state[key]
    
    def get_current_user(self) -> Dict:
        """Get current user information"""
        return {
            "username": st.session_state.get("username", ""),
            "name": st.session_state.get("user_name", "User"),
            "email": st.session_state.get("user_email", ""),
            "role": st.session_state.get("user_role", "user"),
            "capabilities": st.session_state.get("user_capabilities", {}),
            "dashboard_type": st.session_state.get("dashboard_type", "inspector")
        }
    
    def can_user_perform_action(self, action: str) -> bool:
        """Check if current user can perform specific action"""
        capabilities = st.session_state.get("user_capabilities", {})
        return capabilities.get(action, False)
    
    def change_password(self, username, old_password, new_password):
        """Change user password"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            old_hash = self._hash_password(old_password)
            cursor.execute('''
                SELECT 1 FROM users WHERE username = ? AND password_hash = ?
            ''', (username, old_hash))
            
            if not cursor.fetchone():
                conn.close()
                return False, "Current password is incorrect"
            
            if len(new_password) < 6:
                conn.close()
                return False, "New password must be at least 6 characters"
            
            new_hash = self._hash_password(new_password)
            cursor.execute('''
                UPDATE users SET password_hash = ? WHERE username = ?
            ''', (new_hash, username))
            
            conn.commit()
            conn.close()
            
            return True, "Password changed successfully"
            
        except Exception as e:
            return False, f"Database error: {str(e)}"

def show_builder_interface():
    """Enhanced builder interface with photo upload and defect completion"""
    
    st.markdown(f"""
    <div class="main-header">
        <h1>Builder Workspace</h1>
        <p>Work Management with Photo Evidence</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{st.session_state.get('user_name', 'Builder')}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>Builder</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if enhanced system is available
    try:
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        # Check if enhanced tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='enhanced_defects'")
        has_enhanced_tables = cursor.fetchone() is not None
        
        if not has_enhanced_tables:
            st.error("Enhanced defect system not found. Please run the migration script:")
            st.code("python migrate_to_enhanced.py")
            conn.close()
            return
        
        # Show work assignments
        show_builder_work_assignments_inline()
        conn.close()
        
    except Exception as e:
        st.error(f"Error accessing defect system: {e}")
        st.info("Please ensure the enhanced defect system is properly installed.")

def show_builder_work_assignments_inline():
    """Show builder work assignments with photo upload capability"""
    
    st.markdown("### Your Work Assignments")
    
    user = {
        "username": st.session_state.get("username", ""),
        "name": st.session_state.get("user_name", "Builder"),
        "role": st.session_state.get("user_role", "builder")
    }
    
    try:
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        # First, let's populate enhanced_defects from inspection_defects if empty
        cursor.execute('SELECT COUNT(*) FROM enhanced_defects')
        enhanced_count = cursor.fetchone()[0]
        
        if enhanced_count == 0:
            st.info("Setting up enhanced defect system for the first time...")
            
            # Migrate defects from inspection_defects
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO enhanced_defects 
                    (id, inspection_id, unit_number, unit_type, room, component, trade, urgency, planned_completion, status, created_at)
                    SELECT 
                        'defect_' || id,
                        inspection_id, unit_number, unit_type, room, component, trade, 
                        COALESCE(urgency, 'Normal'),
                        planned_completion,
                        CASE 
                            WHEN status = 'completed' THEN 'approved'
                            WHEN status IS NULL OR status = '' THEN 'open'
                            ELSE status 
                        END,
                        COALESCE(created_at, CURRENT_TIMESTAMP)
                    FROM inspection_defects
                ''')
                
                migrated = cursor.rowcount
                conn.commit()
                
                if migrated > 0:
                    st.success(f"Successfully set up {migrated} defects in enhanced system!")
                else:
                    st.info("No existing defects found to migrate.")
            except Exception as e:
                st.warning(f"Migration attempt failed: {e}")
                st.info("This is normal if your database schema is different. The system will work with new defects.")
        
        # Get work assignments for builder
        cursor.execute('''
            SELECT ed.id, ed.unit_number, ed.room, ed.component, ed.trade, 
                   ed.urgency, ed.planned_completion, ed.status, 
                   COALESCE(pi.building_name, 'Building') as building_name
            FROM enhanced_defects ed
            LEFT JOIN processed_inspections pi ON ed.inspection_id = pi.id
            WHERE ed.status IN ('open', 'assigned', 'in_progress')
            ORDER BY 
                CASE ed.urgency 
                    WHEN 'Urgent' THEN 1 
                    WHEN 'High Priority' THEN 2 
                    ELSE 3 
                END,
                ed.planned_completion
        ''')
        
        work_assignments = cursor.fetchall()
        
        if not work_assignments:
            st.success("No open work assignments! All defects are completed or approved.")
            
            # Show completed work for reference
            cursor.execute('''
                SELECT ed.unit_number, ed.room, ed.component, ed.trade, ed.status, ed.completed_at
                FROM enhanced_defects ed
                WHERE ed.status IN ('completed_pending_approval', 'approved')
                ORDER BY ed.completed_at DESC
                LIMIT 5
            ''')
            
            completed_work = cursor.fetchall()
            
            if completed_work:
                st.markdown("### Recent Completed Work")
                for work in completed_work:
                    status_icon = "⏳" if work[4] == "completed_pending_approval" else "✅"
                    st.info(f"{status_icon} Unit {work[0]} - {work[1]} - {work[2]} ({work[3]}) - {work[4].replace('_', ' ').title()}")
            
            conn.close()
            return
        
        # Summary metrics
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
        
        st.markdown(f"**{len(work_assignments)} work items assigned:**")
        
        # Work items interface
        for work_data in work_assignments:
            defect_id = work_data[0]
            
            urgency_icon = "🚨" if work_data[5] == "Urgent" else "⚠️" if work_data[5] == "High Priority" else "🔧"
            
            with st.expander(f"{urgency_icon} Unit {work_data[1]} - {work_data[2]} - {work_data[3]} ({work_data[4]})", expanded=False):
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"""
                    **Building:** {work_data[8]}  
                    **Unit:** {work_data[1]}  
                    **Location:** {work_data[2]} - {work_data[3]}  
                    **Trade:** {work_data[4]}  
                    **Urgency:** {work_data[5]}  
                    **Due Date:** {work_data[6]}  
                    **Current Status:** {work_data[7].replace('_', ' ').title()}
                    """)
                
                with col2:
                    # Show existing photos
                    cursor.execute('''
                        SELECT id, photo_type, description, uploaded_at
                        FROM defect_photos 
                        WHERE defect_id = ?
                        ORDER BY uploaded_at DESC
                        LIMIT 3
                    ''', (defect_id,))
                    
                    photos = cursor.fetchall()
                    if photos:
                        st.markdown("**Photos:**")
                        for photo in photos:
                            st.caption(f"{photo[1]}: {photo[2] or 'No description'}")
                    else:
                        st.info("No photos uploaded yet")
                
                # Action buttons
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"📸 Add Photo", key=f"photo_{defect_id}"):
                        st.session_state[f"show_photo_upload_{defect_id}"] = True
                        st.rerun()
                
                with col2:
                    if work_data[7] != 'in_progress' and st.button(f"🔄 Start Work", key=f"start_{defect_id}"):
                        cursor.execute('''
                            UPDATE enhanced_defects 
                            SET status = 'in_progress', updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (defect_id,))
                        conn.commit()
                        st.success("Work started!")
                        st.rerun()
                
                with col3:
                    if st.button(f"✅ Mark Complete", key=f"complete_{defect_id}", type="primary"):
                        st.session_state[f"show_completion_{defect_id}"] = True
                        st.rerun()
                
                # Photo upload interface
                if st.session_state.get(f"show_photo_upload_{defect_id}", False):
                    st.markdown("---")
                    st.markdown("#### Upload Photo Evidence")
                    
                    photo_type = st.selectbox(
                        "Photo type:",
                        options=['before', 'during', 'after', 'evidence'],
                        help="Select the type of photo you're uploading",
                        key=f"photo_type_{defect_id}"
                    )
                    
                    description = st.text_input(
                        "Photo description:",
                        placeholder="Describe what this photo shows...",
                        key=f"photo_desc_{defect_id}"
                    )
                    
                    uploaded_photo = st.file_uploader(
                        "Choose photo file:",
                        type=['png', 'jpg', 'jpeg'],
                        help="Upload a clear photo showing the defect or work progress",
                        key=f"photo_file_{defect_id}"
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Upload Photo", key=f"upload_btn_{defect_id}"):
                            if uploaded_photo:
                                if save_defect_photo_inline(defect_id, uploaded_photo, photo_type, description, user['username']):
                                    st.success("Photo uploaded successfully!")
                                    st.session_state[f"show_photo_upload_{defect_id}"] = False
                                    st.rerun()
                                else:
                                    st.error("Failed to upload photo")
                            else:
                                st.error("Please select a photo file")
                    
                    with col2:
                        if st.button("Cancel", key=f"cancel_photo_{defect_id}"):
                            st.session_state[f"show_photo_upload_{defect_id}"] = False
                            st.rerun()
                
                # Completion interface
                if st.session_state.get(f"show_completion_{defect_id}", False):
                    st.markdown("---")
                    st.markdown("#### Mark Defect as Complete")
                    
                    completion_notes = st.text_area(
                        "Completion notes:",
                        placeholder="Describe the work performed and any important details...",
                        help="Provide details about how the defect was resolved",
                        key=f"completion_notes_{defect_id}"
                    )
                    
                    st.markdown("**Upload completion photos:**")
                    
                    before_photo = st.file_uploader(
                        "Before photo (if not already uploaded):",
                        type=['png', 'jpg', 'jpeg'],
                        key=f"before_photo_{defect_id}"
                    )
                    
                    after_photo = st.file_uploader(
                        "After photo (required):",
                        type=['png', 'jpg', 'jpeg'],
                        key=f"after_photo_{defect_id}"
                    )
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("Cancel", key=f"cancel_complete_{defect_id}"):
                            st.session_state[f"show_completion_{defect_id}"] = False
                            st.rerun()
                    
                    with col2:
                        if st.button("Submit for Approval", key=f"submit_complete_{defect_id}", type="primary"):
                            if not after_photo:
                                st.error("After photo is required for completion")
                            elif not completion_notes.strip():
                                st.error("Completion notes are required")
                            else:
                                # Upload photos and mark complete
                                photos_uploaded = True
                                
                                if before_photo:
                                    if not save_defect_photo_inline(defect_id, before_photo, 'before', "Before work photo", user['username']):
                                        photos_uploaded = False
                                
                                if after_photo:
                                    if not save_defect_photo_inline(defect_id, after_photo, 'after', "After work completion", user['username']):
                                        photos_uploaded = False
                                
                                if photos_uploaded:
                                    # Mark as completed pending approval
                                    cursor.execute('''
                                        UPDATE enhanced_defects 
                                        SET status = 'completed_pending_approval', 
                                            completed_by = ?, 
                                            completed_at = CURRENT_TIMESTAMP, 
                                            completion_notes = ?,
                                            updated_at = CURRENT_TIMESTAMP
                                        WHERE id = ?
                                    ''', (user['username'], completion_notes, defect_id))
                                    
                                    conn.commit()
                                    
                                    st.success("Work submitted for approval! The property developer will review your completion.")
                                    st.session_state[f"show_completion_{defect_id}"] = False
                                    st.rerun()
                                else:
                                    st.error("Failed to upload photos")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading work assignments: {e}")
        import traceback
        st.code(traceback.format_exc())

def save_defect_photo_inline(defect_id, photo_file, photo_type, description, username):
    """Save photo evidence for a defect - INLINE VERSION"""
    try:
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
        
        # Save to database
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        photo_id = str(uuid.uuid4())
        filename = f"{defect_id}_{photo_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        cursor.execute('''
            INSERT INTO defect_photos 
            (id, defect_id, photo_type, filename, photo_data, uploaded_by, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (photo_id, defect_id, photo_type, filename, img_data, username, description))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        st.error(f"Error saving photo: {e}")
        return False
    
# Initialize the enhanced auth manager
@st.cache_resource
def get_auth_manager():
    """Get singleton auth manager instance"""
    return DatabaseAuthManager()

def show_enhanced_login_page():
    """Enhanced login page with database authentication"""
    
    st.markdown("""
    <div style="max-width: 400px; margin: 2rem auto; padding: 2rem; 
                background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="text-align: center; color: #1976d2; margin-bottom: 2rem;">
            Building Inspection Report System
        </h2>
        <h3 style="text-align: center; color: #666; margin-bottom: 2rem;">
            Please Login to Continue
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    auth_manager = get_auth_manager()
    
    with st.form("enhanced_login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("### Login")
            
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            login_button = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if login_button:
                if username and password:
                    success, message = auth_manager.authenticate(username, password)
                    
                    if success:
                        auth_manager.create_session(username)
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please enter both username and password")
    
    # Demo credentials with role explanations
    with st.expander("Demo Credentials", expanded=False):
        st.info("""
        **Available Test Accounts:**
        
        **System Administrator:**
        - Username: `admin` | Password: `admin123`
        - Full system access, user management
        
        **Property Developer:**
        - Username: `developer1` | Password: `dev123`
        - Portfolio view, defect approval, can generate reports
        
        **Project Manager:**
        - Username: `manager1` | Password: `mgr123`
        - Project oversight, data processing
        
        **Site Inspector:**
        - Username: `inspector` | Password: `inspector123`
        - Data upload and processing
        
        **Builder:**
        - Username: `builder1` | Password: `build123`
        - Work reports, status updates
        """)

def show_enhanced_user_menu():
    """Enhanced user menu with role-specific content"""
    
    auth_manager = get_auth_manager()
    
    if not auth_manager.is_session_valid():
        return False
    
    user = auth_manager.get_current_user()
    
    # Create unique session key for this function
    sidebar_key_prefix = f"sidebar_{user['username']}_"
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("### User Information")
        
        # Enhanced user info display
        st.markdown(f"""
        **Name:** {user['name']}  
        **Role:** {user['role'].replace('_', ' ').title()}  
        **Email:** {user['email']}  
        **Access:** {user['capabilities'].get('dashboard_type', 'standard').title()}
        """)
        
        # User account actions (for all users)
        st.markdown("---")
        st.markdown("### Account")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Change Password", use_container_width=True):
                st.session_state.show_password_change = True
        
        with col2:
            if st.button("Logout", use_container_width=True, type="primary"):
                auth_manager.logout()
                st.success("Logged out successfully!")
                st.rerun()
        
        # Password change form (if requested)
        if st.session_state.get("show_password_change", False):
            st.markdown("---")
            st.markdown("### Change Password")
            
            with st.form("password_change_form"):
                old_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm New Password", type="password")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Update", use_container_width=True):
                        if new_password != confirm_password:
                            st.error("New passwords don't match")
                        elif len(new_password) < 6:
                            st.error("Password must be at least 6 characters")
                        else:
                            success, message = auth_manager.change_password(
                                user['username'], old_password, new_password
                            )
                            if success:
                                st.success(message)
                                st.session_state.show_password_change = False
                                st.rerun()
                            else:
                                st.error(message)
                
                with col2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state.show_password_change = False
                        st.rerun()
        
        # Role-specific sidebar content - FIXED LOGIC
        if user['role'] == 'admin':
            # Admin sidebar content
            st.markdown("---") 
            st.markdown("### Administrator Access")
            st.success("🔑 **Full System Access**")
            
            # Simple admin metrics
            try:
                conn = sqlite3.connect("inspection_system.db")
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
                active_users = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM projects")
                total_projects = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM buildings") 
                total_buildings = cursor.fetchone()[0]
                
                conn.close()
                
                st.markdown("### System Status")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Active Users", active_users)
                    st.metric("Projects", total_projects)
                with col2:
                    st.metric("Buildings", total_buildings)
                    
            except Exception as e:
                st.caption(f"System metrics unavailable: {str(e)}")
        
        else:
            # Non-admin users: Show their specific permissions
            st.markdown("---") 
            st.markdown("### Your Access Rights")
            
            capabilities = user['capabilities']
            
            # Data Operations
            data_perms = []
            if capabilities.get('can_upload'):
                data_perms.append("📤 Upload Data")
            if capabilities.get('can_process'):
                data_perms.append("⚙️ Process Data")
            if capabilities.get('can_view_data'):
                data_perms.append("👁️ View Data")
            
            if data_perms:
                st.markdown("**Data Operations:**")
                for perm in data_perms:
                    st.success(perm)
            
            # Report Operations  
            if capabilities.get('can_generate_reports'):
                st.markdown("**Reports:**")
                st.success("📊 Generate Reports")
            
            # Defect Management
            defect_perms = []
            if capabilities.get('can_approve_defects'):
                defect_perms.append("✅ Approve Defects")
            if capabilities.get('can_update_defect_status'):
                defect_perms.append("🔄 Update Status")
            
            if defect_perms:
                st.markdown("**Defect Management:**")
                for perm in defect_perms:
                    st.success(perm)
        
        # Unit Lookup Section (only show if there's processed data)
        if hasattr(st.session_state, 'processed_data') and st.session_state.processed_data is not None:
            st.markdown("---")
            st.header("Quick Unit Lookup")
            
            # Get all unique units for dropdown
            all_units = sorted(st.session_state.processed_data["Unit"].unique())
            
            # Unit search
            selected_unit = st.selectbox(
                "Select Unit Number:",
                options=[""] + all_units,
                help="Quick lookup of defects for any unit",
                key=f"{sidebar_key_prefix}unit_lookup"
            )
            
            if selected_unit:
                unit_defects = lookup_unit_defects(st.session_state.processed_data, selected_unit)
                
                if len(unit_defects) > 0:
                    st.markdown(f"**Unit {selected_unit} Defects:**")
                    
                    # Count by urgency
                    urgent_count = len(unit_defects[unit_defects["Urgency"] == "Urgent"])
                    high_priority_count = len(unit_defects[unit_defects["Urgency"] == "High Priority"])
                    normal_count = len(unit_defects[unit_defects["Urgency"] == "Normal"])
                    
                    if urgent_count > 0:
                        st.error(f"Urgent: {urgent_count}")
                    if high_priority_count > 0:
                        st.warning(f"High Priority: {high_priority_count}")
                    if normal_count > 0:
                        st.info(f"Normal: {normal_count}")
                    
                    # Show defects in compact format
                    for _, defect in unit_defects.iterrows():
                        urgency_icon = "🚨" if defect["Urgency"] == "Urgent" else "⚠️" if defect["Urgency"] == "High Priority" else "🔧"
                        st.caption(f"{urgency_icon} {defect['Room']} - {defect['Component']} ({defect['Trade']}) - Due: {defect['PlannedCompletion']}")
                else:
                    st.success(f"Unit {selected_unit} has no defects!")
        
        # Word Report Images Section (only for users who can upload)
        if auth_manager.can_user_perform_action("can_upload"):
            st.markdown("---")
            st.header("Word Report Images")
            st.markdown("Upload images to enhance your Word report (optional):")
            
            with st.expander("Upload Report Images", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    logo_upload = st.file_uploader("Company Logo", type=['png', 'jpg', 'jpeg'], key=f"{sidebar_key_prefix}logo_upload")
                
                with col2:
                    cover_upload = st.file_uploader("Cover Image", type=['png', 'jpg', 'jpeg'], key=f"{sidebar_key_prefix}cover_upload")
                
                # Process uploaded images
                if st.button("Save Images for Report"):
                    images_saved = 0
                    
                    import tempfile
                    import os
                    
                    temp_dir = tempfile.gettempdir()
                    
                    if logo_upload:
                        logo_path = os.path.join(temp_dir, f"logo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                        with open(logo_path, "wb") as f:
                            f.write(logo_upload.getbuffer())
                        st.session_state.report_images["logo"] = logo_path
                        images_saved += 1
                    
                    if cover_upload:
                        cover_path = os.path.join(temp_dir, f"cover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                        with open(cover_path, "wb") as f:
                            f.write(cover_upload.getbuffer())
                        st.session_state.report_images["cover"] = cover_path
                        images_saved += 1
                    
                    if images_saved > 0:
                        st.success(f"{images_saved} image(s) saved for Word report enhancement!")
                    else:
                        st.info("No images uploaded.")
                
                # Show current images status
                current_images = [k for k, v in st.session_state.report_images.items() if v is not None]
                if current_images:
                    st.info(f"Current images ready: {', '.join(current_images)}")
        
        # Reset button at the bottom
        st.markdown("---")
        if st.button("Reset All", help="Clear all data and start over"):
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
    
    return True

# Add this after authentication but before showing dashboards
if 'enhanced_system_initialized' not in st.session_state:
    setup_enhanced_system()
    st.session_state.enhanced_system_initialized = True
    
# =============================================================================
# DATA PROCESSING AND PERSISTENCE FUNCTIONS
# =============================================================================

def process_inspection_data_with_persistence(df, mapping, building_info, username):
    """Process data and automatically save to database"""
    
    # Process data (existing logic)
    processed_df, metrics = process_inspection_data(df, mapping, building_info)
    
    # Save to database immediately
    persistence_manager = DataPersistenceManager()
    success, inspection_id = persistence_manager.save_processed_inspection(
        processed_df, metrics, username
    )
    
    if success:
        st.success(f"Data processed and saved! Building: {metrics['building_name']}")
        # Update session state
        st.session_state.processed_data = processed_df
        st.session_state.metrics = metrics
        st.session_state.step_completed["processing"] = True
        return processed_df, metrics, True
    else:
        st.error(f"Data processing succeeded but database save failed: {inspection_id}")
        # Still update session state for current user
        st.session_state.processed_data = processed_df
        st.session_state.metrics = metrics
        st.session_state.step_completed["processing"] = True
        return processed_df, metrics, False

def initialize_user_data():
    """Load appropriate data based on user role"""
    user = get_auth_manager().get_current_user()
    
    # Always try to load latest data if session state is empty
    if st.session_state.processed_data is None:
        persistence_manager = DataPersistenceManager()
        processed_data, metrics = persistence_manager.load_latest_inspection()
        
        if processed_data is not None and metrics is not None:
            st.session_state.processed_data = processed_data
            st.session_state.metrics = metrics
            st.session_state.step_completed["processing"] = True
            return True
    
    return False

def load_trade_mapping():
    """Load trade mapping from database"""
    if len(st.session_state.trade_mapping) == 0:
        mapping_df = load_trade_mapping_from_database()
        if len(mapping_df) > 0:
            st.session_state.trade_mapping = mapping_df
            st.session_state.step_completed["mapping"] = True
            return True
    return False

# =============================================================================
# ROLE-SPECIFIC DASHBOARD FUNCTIONS
# =============================================================================

def show_admin_dashboard():
    """Complete admin dashboard with enhanced management capabilities"""
    try:
        from enhanced_admin_management import show_enhanced_admin_dashboard
        show_enhanced_admin_dashboard()
    except ImportError as e:
        st.error(f"Enhanced admin features not available: {str(e)}")
        st.info("Please ensure enhanced_admin_management.py is in your project folder")
        
        # Fallback to basic functionality
        st.markdown("### Basic Admin Interface")
        st.info("Using simplified admin interface. For full features, check file setup.")

def show_enhanced_developer_dashboard():
    """Enhanced Property Developer dashboard with optional financial analysis"""
    st.markdown("### Portfolio Executive Dashboard")
    
    # Show corrected database stats
    stats = get_corrected_database_stats()
    
    with st.expander("System Status", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Buildings Processed", stats.get("total_inspections", 0))
        with col2:
            st.metric("Active Buildings", stats.get("active_inspections", 0))
        with col3:
            st.metric("Total Defects", stats.get("total_defects", 0))
    
    if st.session_state.metrics is not None:
        metrics = st.session_state.metrics
        
        # Current Building Analysis
        st.markdown("### Current Building Analysis")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Building", metrics['building_name'])
        with col2:
            st.metric("Total Units", metrics['total_units'])
        with col3:
            st.metric("Ready for Settlement", f"{metrics['ready_units']} ({metrics['ready_pct']:.1f}%)")
        with col4:
            st.metric("Urgent Issues", metrics['urgent_defects'])
        
        # Summary tables (read-only)
        tab1, tab2, tab3 = st.tabs(["Trade Summary", "Unit Status", "Urgent Items"])
        
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
            if len(metrics['urgent_defects_table']) > 0:
                urgent_display = metrics['urgent_defects_table'].copy()
                urgent_display["PlannedCompletion"] = pd.to_datetime(urgent_display["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
                st.dataframe(urgent_display, use_container_width=True)
                st.error(f"**{len(urgent_display)} URGENT defects require immediate attention!**")
            else:
                st.success("No urgent defects found!")
        
        # Unit lookup
        st.markdown("### Unit Lookup")
        all_units = sorted(st.session_state.processed_data["Unit"].unique())
        selected_unit = st.selectbox("Select Unit to View Details:", [""] + all_units, key="dev_unit_lookup")
        
        if selected_unit:
            unit_defects = lookup_unit_defects(st.session_state.processed_data, selected_unit)
            
            if len(unit_defects) > 0:
                st.markdown(f"**Unit {selected_unit} Defects:**")
                st.dataframe(unit_defects, use_container_width=True)
            else:
                st.success(f"Unit {selected_unit} has no defects!")
        
        # Executive Report Generation
        st.markdown("---")
        st.markdown("### Executive Reports")
        
        if st.button("Generate Executive Summary", type="primary", use_container_width=True):
            try:
                if EXCEL_REPORT_AVAILABLE:
                    excel_buffer = generate_professional_excel_report(st.session_state.processed_data, metrics)
                    filename = f"Executive_Summary_{metrics['building_name']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                    
                    st.success("Executive summary generated!")
                    st.download_button(
                        "Download Executive Summary",
                        data=excel_buffer.getvalue(),
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.error("Excel report generator not available")
            except Exception as e:
                st.error(f"Error generating executive summary: {e}")
        
        st.markdown("")
        
        if st.button("Portfolio Analytics Dashboard", type="secondary", use_container_width=True):
            try:
                if PORTFOLIO_ANALYTICS_AVAILABLE:
                    generate_portfolio_analytics_report()
                else:
                    show_simple_portfolio_analytics()
            except Exception as e:
                st.error(f"Portfolio analytics error: {e}")
                show_simple_portfolio_analytics()
        
        # Portfolio Analytics Section
        st.markdown("---")
        st.markdown("### Portfolio Analytics")
        
        # Optional building value input for financial analysis
        st.markdown("#### Optional: Building Financial Data")
        col1, col2 = st.columns(2)

        with col1:
            building_value = st.number_input(
                "Building Value (AUD)", 
                min_value=0, 
                value=0,
                step=1000000,
                help="Enter actual building value for financial analysis (optional)"
            )

        with col2:
            if building_value > 0:
                calculated_unit_value = building_value / metrics['total_units']
                st.metric("Calculated Unit Value", f"${calculated_unit_value:,.0f}")
                st.caption("Automatically calculated from building value")
            else:
                st.info("Enter building value to see unit calculations")
        
        # Executive Performance Overview
        st.markdown("#### Executive Performance Overview")
        
        # Calculate performance metrics
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
        
        # Display performance metrics
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
            if completion_score >= 80:
                st.caption("Ready for handover")
            elif completion_score >= 50:
                st.caption("On track")
            else:
                st.caption("Requires attention")
        
        with col3:
            risk_level = "Low" if metrics['urgent_defects'] == 0 else "Medium" if metrics['urgent_defects'] <= 3 else "High"
            if risk_level == "Low":
                st.success(f"Risk Level: **{risk_level}**")
            elif risk_level == "Medium":
                st.warning(f"Risk Level: **{risk_level}**")
            else:
                st.error(f"Risk Level: **{risk_level}**")
            st.caption(f"{metrics['urgent_defects']} urgent items")
        
        with col4:
            # Completion velocity (units ready per week - estimated)
            days_since_inspection = 7  # Placeholder - should calculate from inspection date
            velocity = metrics['ready_units'] / max(days_since_inspection / 7, 1)
            st.metric("Completion Velocity", f"{velocity:.1f} units/week")
            st.caption("Estimated rate")
        
        # Financial Analysis (only if values provided)
        if building_value > 0:
            st.markdown("#### Financial Impact Analysis")
            
            unit_value = building_value / metrics['total_units']
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                ready_value = metrics['ready_units'] * unit_value
                st.metric("Ready Unit Value", f"${ready_value:,.0f}")
                st.caption("Value ready for settlement")
            
            with col2:
                incomplete_units = metrics['total_units'] - metrics['ready_units']
                revenue_at_risk = incomplete_units * unit_value * 0.02  # 2% risk factor
                st.metric("Revenue at Risk", f"${revenue_at_risk:,.0f}")
                st.caption("From settlement delays")
            
            with col3:
                estimated_resolution_cost = metrics['total_defects'] * 1500  # $1500 per defect
                st.metric("Est. Resolution Cost", f"${estimated_resolution_cost:,.0f}")
                st.caption("To fix all defects")
            
            with col4:
                if revenue_at_risk > estimated_resolution_cost:
                    roi = ((revenue_at_risk - estimated_resolution_cost) / estimated_resolution_cost) * 100
                    st.success(f"Positive ROI: {roi:.0f}%")
                    st.caption("Return on investment")
                else:
                    st.info("Resolution cost analysis")
                    st.caption("Cost vs risk assessment")
            
            # Financial recommendations
            st.markdown("**Financial Recommendations:**")
            
            if revenue_at_risk > 1000000:
                st.error("High revenue exposure - prioritize completion of near-ready units")
            
            if estimated_resolution_cost > building_value * 0.05:
                st.warning("Resolution costs exceed 5% of building value - review contractor pricing")
            
            if metrics['ready_pct'] > 70:
                st.success("Strong settlement position - consider accelerated marketing")
        
        # Strategic Insights
        st.markdown("#### Strategic Insights")
        
        insights = []
        recommendations = []
        
        # Generate insights based on data
        if metrics['urgent_defects'] > 0:
            insights.append(f"IMMEDIATE ACTION: {metrics['urgent_defects']} urgent defects require contractor deployment")
            recommendations.append("Deploy additional resources for urgent defect resolution")
        
        if metrics['ready_pct'] < 50:
            insights.append(f"COMPLETION FOCUS: Only {metrics['ready_pct']:.1f}% of units ready for settlement")
            recommendations.append("Accelerate defect resolution to improve handover timeline")
        
        if len(metrics['summary_trade']) > 0:
            top_trade = metrics['summary_trade'].iloc[0]['Trade']
            top_count = metrics['summary_trade'].iloc[0]['DefectCount']
            insights.append(f"TRADE FOCUS: {top_trade} represents highest defect category ({top_count} items)")
            recommendations.append(f"Review {top_trade} quality processes and contractor performance")
        
        if avg_defects_per_unit > 7:
            insights.append("QUALITY CONCERN: High defect rate indicates process issues")
            recommendations.append("Implement enhanced quality assurance and contractor oversight")
        
        # Display insights
        if insights:
            for insight in insights:
                if "IMMEDIATE" in insight:
                    st.error(insight)
                elif "CONCERN" in insight:
                    st.warning(insight)
                else:
                    st.info(insight)
        
        # Display recommendations
        if recommendations:
            st.markdown("**Strategic Recommendations:**")
            for i, rec in enumerate(recommendations, 1):
                st.markdown(f"{i}. {rec}")
        
        if not insights:
            st.success("Building performance is strong - continue current management approach")
        
        # Export Options
        st.markdown("#### Export Options")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Download Performance Summary", use_container_width=True):
                summary_data = {
                    'Metric': [
                        'Building Name', 'Quality Grade', 'Settlement Readiness', 
                        'Total Units', 'Ready Units', 'Urgent Defects',
                        'Risk Level', 'Performance Description'
                    ],
                    'Value': [
                        metrics['building_name'], performance_grade, f"{metrics['ready_pct']:.1f}%",
                        metrics['total_units'], metrics['ready_units'], metrics['urgent_defects'],
                        risk_level, grade_description
                    ]
                }
                
                # FIXED: Only add financial data if building_value > 0
                if building_value > 0:
                    ready_value = metrics['ready_units'] * (building_value / metrics['total_units'])
                    revenue_at_risk = (metrics['total_units'] - metrics['ready_units']) * (building_value / metrics['total_units']) * 0.02
                    estimated_resolution_cost = metrics['total_defects'] * 1500
                    
                    summary_data['Metric'].extend(['Ready Unit Value', 'Revenue at Risk', 'Resolution Cost'])
                    summary_data['Value'].extend([f"${ready_value:,.0f}", f"${revenue_at_risk:,.0f}", f"${estimated_resolution_cost:,.0f}"])
                
                summary_df = pd.DataFrame(summary_data)
                csv = summary_df.to_csv(index=False)
                
                st.download_button(
                    "Download CSV",
                    data=csv,
                    file_name=f"performance_summary_{metrics['building_name']}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with col2:
            if st.button("Generate Executive Brief", use_container_width=True):
                brief = f"""EXECUTIVE BRIEF - {metrics['building_name']}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

PERFORMANCE SUMMARY:
• Quality Grade: {performance_grade} ({grade_description})
• Settlement Readiness: {metrics['ready_pct']:.1f}% ({metrics['ready_units']} of {metrics['total_units']} units)
• Risk Level: {risk_level}
• Urgent Issues: {metrics['urgent_defects']} items

"""
                
                # FIXED: Only add financial data if building_value > 0
                if building_value > 0:
                    ready_value = metrics['ready_units'] * (building_value / metrics['total_units'])
                    revenue_at_risk = (metrics['total_units'] - metrics['ready_units']) * (building_value / metrics['total_units']) * 0.02
                    estimated_resolution_cost = metrics['total_defects'] * 1500
                    
                    brief += f"""FINANCIAL POSITION:
• Ready Unit Value: ${ready_value:,.0f}
• Revenue at Risk: ${revenue_at_risk:,.0f}
• Est. Resolution Cost: ${estimated_resolution_cost:,.0f}

"""
                
                brief += "KEY ACTIONS:\n"
                for i, rec in enumerate(recommendations[:3], 1):
                    brief += f"{i}. {rec}\n"
                
                brief += "\nEND BRIEF"
                
                st.download_button(
                    "Download Brief",
                    data=brief,
                    file_name=f"executive_brief_{metrics['building_name']}_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
        with col3:
            if st.button("Action Plan Export", use_container_width=True):
                if recommendations:
                    action_data = {
                        'Priority': range(1, len(recommendations) + 1),
                        'Action Required': recommendations,
                        'Category': ['Immediate' if 'urgent' in rec.lower() else 'Strategic' for rec in recommendations],
                        'Timeline': ['1-3 days' if 'urgent' in rec.lower() or 'immediate' in rec.lower() 
                                   else '1-2 weeks' if 'accelerate' in rec.lower() 
                                   else '2-4 weeks' for rec in recommendations]
                    }
                    
                    action_df = pd.DataFrame(action_data)
                    csv = action_df.to_csv(index=False)
                    
                    st.download_button(
                        "Download Action Plan",
                        data=csv,
                        file_name=f"action_plan_{metrics['building_name']}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.info("No specific actions required - building performing well")
    
    else:
        st.warning("No inspection data available. Contact your team to process inspection data.")

# Also add this helper function for the database stats fix:
def get_corrected_database_stats(db_path="inspection_system.db"):
    """Get corrected database statistics that count unique buildings"""
    try:
        import sqlite3
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

# Update the simple portfolio analytics function:
def show_simple_portfolio_analytics():
    """Simple portfolio analytics fallback when main module fails"""
    if st.session_state.metrics is None:
        st.warning("No inspection data available for analytics.")
        return
    
    st.subheader("Portfolio Analytics")
    st.info("Showing current building analytics.")
    
    metrics = st.session_state.metrics
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Building", metrics['building_name'])
    with col2:
        st.metric("Settlement Ready", f"{metrics['ready_pct']:.1f}%")
    with col3:
        st.metric("Urgent Issues", metrics['urgent_defects'])

def show_enhanced_builder_dashboard():
    """Enhanced Builder dashboard with work report generation"""
    st.markdown("### Builder Workspace")
    
    persistence_manager = DataPersistenceManager()
    
    # Get defects by status
    open_defects = persistence_manager.get_defects_by_status("open")
    
    if open_defects:
        st.success(f"You have {len(open_defects)} open defects to work on")
        
        # Convert to DataFrame for easier handling
        if open_defects:
            df_cols = ["ID", "Inspection ID", "Unit", "Unit Type", "Room", "Component", 
                      "Trade", "Urgency", "Planned Completion", "Status", "Created At", "Building"]
            df = pd.DataFrame(open_defects, columns=df_cols)
            
            # Show defects by urgency
            urgent_df = df[df["Urgency"] == "Urgent"]
            high_priority_df = df[df["Urgency"] == "High Priority"]
            normal_df = df[df["Urgency"] == "Normal"]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Urgent", len(urgent_df))
            with col2:
                st.metric("High Priority", len(high_priority_df))
            with col3:
                st.metric("Normal", len(normal_df))
            
            # Show defects table
            st.markdown("**Your Assigned Defects:**")
            display_df = df[["Unit", "Room", "Component", "Trade", "Urgency", "Planned Completion", "Building"]].copy()
            st.dataframe(display_df, use_container_width=True)
        
        # Builder Work Reports
        st.markdown("---")
        st.markdown("### Work Reports")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Today's Work List", type="primary", use_container_width=True):
                # Filter today's work
                today_work = df[pd.to_datetime(df["Planned Completion"]) <= pd.Timestamp.now() + pd.Timedelta(days=1)]
                if len(today_work) > 0:
                    csv = today_work.to_csv(index=False)
                    st.download_button(
                        "Download Today's Work List",
                        data=csv,
                        file_name=f"today_work_list_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.info("No work scheduled for today")
        
        with col2:
            if st.button("Weekly Schedule", type="secondary", use_container_width=True):
                # Filter this week's work
                week_work = df[pd.to_datetime(df["Planned Completion"]) <= pd.Timestamp.now() + pd.Timedelta(days=7)]
                if len(week_work) > 0:
                    csv = week_work.to_csv(index=False)
                    st.download_button(
                        "Download Weekly Schedule",
                        data=csv,
                        file_name=f"weekly_schedule_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.info("No work scheduled for this week")
        
        with col3:
            if st.button("Priority Items", use_container_width=True):
                # Filter urgent and high priority
                priority_work = df[df["Urgency"].isin(["Urgent", "High Priority"])]
                if len(priority_work) > 0:
                    csv = priority_work.to_csv(index=False)
                    st.download_button(
                        "Download Priority Items",
                        data=csv,
                        file_name=f"priority_items_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.success("No priority items!")
        
    else:
        st.info("No open defects assigned. Check with your project manager.")

def show_simple_portfolio_analytics(metrics=None):
    """Simple portfolio analytics fallback when main module fails"""
    if metrics is None:
        metrics = st.session_state.metrics
        
    if metrics is None:
        st.warning("No inspection data available for analytics.")
        return
    
    st.subheader("Portfolio Analytics")
    st.info("Showing current building analytics.")
    
    metrics = st.session_state.metrics
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Building", metrics['building_name'])
    with col2:
        st.metric("Settlement Ready", f"{metrics['ready_pct']:.1f}%")
    with col3:
        st.metric("Urgent Issues", metrics['urgent_defects'])
        
def show_unit_defects_with_completed(cursor, unit_info, user):
    """Show both active defects and completed work with status"""
    
    unit_number = unit_info['unit_number']
    building_name = unit_info['building_name']
    
    st.markdown(f"### Work in Unit {unit_number}")
    
    # Create tabs for active work and completed work
    tab1, tab2 = st.tabs(["Active Defects", "My Completed Work"])
    
    with tab1:
        show_active_defects_tab(cursor, unit_info, user)
    
    with tab2:
        show_completed_work_tab(cursor, unit_info, user)

def show_active_defects_tab(cursor, unit_info, user):
    """Tab for active defects that need fixing"""
    
    unit_number = unit_info['unit_number']
    building_name = unit_info['building_name']
    
    # Get active defects for this unit
    cursor.execute('''
        SELECT ed.id, ed.room, ed.component, ed.trade, ed.urgency, ed.planned_completion
        FROM enhanced_defects ed
        LEFT JOIN processed_inspections pi ON ed.inspection_id = pi.id
        WHERE ed.unit_number = ?
        AND COALESCE(pi.building_name, 'Unknown Building') = ?
        AND ed.status IN ('open', 'assigned', 'in_progress')
        AND pi.is_active = 1
        ORDER BY 
            CASE ed.urgency 
                WHEN 'Urgent' THEN 1 
                WHEN 'High Priority' THEN 2 
                ELSE 3 
            END
    ''', (unit_number, building_name))
    
    defects = cursor.fetchall()
    
    if not defects:
        st.success("No active defects to fix! All items completed.")
        return
    
    st.markdown(f"**{len(defects)} defects need fixing:**")
    
    # Track which defect is being worked on
    working_on = st.session_state.get("working_on_defect")
    
    # Show active defects with inline work area
    for defect_data in defects:
        defect_id = defect_data[0]
        room = defect_data[1]
        component = defect_data[2]
        trade = defect_data[3]
        urgency = defect_data[4]
        due_date = defect_data[5]
        
        is_working_on_this = (working_on == defect_id)
        
        # Defect header with action button
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if urgency == "Urgent":
                    st.error(f"**URGENT: {room} - {component}** ({trade}) - Due: {due_date}")
                elif urgency == "High Priority":
                    st.warning(f"**HIGH: {room} - {component}** ({trade}) - Due: {due_date}")
                else:
                    st.info(f"**{room} - {component}** ({trade}) - Due: {due_date}")
            
            with col2:
                if is_working_on_this:
                    if st.button("Done", key=f"done_{defect_id}", type="secondary"):
                        if "working_on_defect" in st.session_state:
                            del st.session_state["working_on_defect"]
                        st.rerun()
                else:
                    if st.button("Fix This", key=f"fix_{defect_id}", type="primary"):
                        st.session_state["working_on_defect"] = defect_id
                        st.rerun()
        
        # INLINE WORK AREA (same as before)
        if is_working_on_this:
            show_inline_work_area(cursor, defect_id, defect_data, user)
        
        st.markdown("")

def show_completed_work_tab(cursor, unit_info, user):
    """Tab showing completed work with approval status"""
    
    unit_number = unit_info['unit_number']
    building_name = unit_info['building_name']
    
    # Get completed work for this unit by this user
    cursor.execute('''
        SELECT ed.id, ed.room, ed.component, ed.trade, ed.status, 
               ed.completed_at, ed.completion_notes, ed.approved_by, 
               ed.approved_at, ed.rejected_by, ed.rejection_reason
        FROM enhanced_defects ed
        LEFT JOIN processed_inspections pi ON ed.inspection_id = pi.id
        WHERE ed.unit_number = ?
        AND COALESCE(pi.building_name, 'Unknown Building') = ?
        AND ed.completed_by = ?
        AND ed.status IN ('completed_pending_approval', 'approved', 'rejected')
        AND pi.is_active = 1
        ORDER BY ed.completed_at DESC
    ''', (unit_number, building_name, user['username']))
    
    completed_work = cursor.fetchall()
    
    if not completed_work:
        st.info("No completed work yet. Fix some defects to see your progress here!")
        return
    
    st.markdown(f"**Your completed work ({len(completed_work)} items):**")
    
    # Show completed work with status
    for work_data in completed_work:
        defect_id = work_data[0]
        room = work_data[1]
        component = work_data[2]
        trade = work_data[3]
        status = work_data[4]
        completed_at = work_data[5]
        completion_notes = work_data[6]
        approved_by = work_data[7]
        approved_at = work_data[8]
        rejected_by = work_data[9]
        rejection_reason = work_data[10]
        
        with st.container():
            # Status-based styling and icons
            if status == 'approved':
                st.success(f"✅ **APPROVED: {room} - {component}** ({trade})")
                st.caption(f"Completed: {completed_at[:10]} | Approved by: {approved_by} on {approved_at[:10]}")
                
            elif status == 'rejected':
                st.error(f"❌ **REJECTED: {room} - {component}** ({trade})")
                st.caption(f"Completed: {completed_at[:10]} | Rejected by: {rejected_by}")
                if rejection_reason:
                    st.warning(f"Reason: {rejection_reason}")
                
                # Option to rework rejected items
                if st.button(f"Rework This Item", key=f"rework_{defect_id}", type="secondary"):
                    # Reset status back to open so it appears in active tab
                    cursor.execute('''
                        UPDATE enhanced_defects 
                        SET status = 'open',
                            completed_by = NULL,
                            completed_at = NULL,
                            completion_notes = NULL,
                            rejected_by = NULL,
                            rejected_at = NULL,
                            rejection_reason = NULL
                        WHERE id = ?
                    ''', (defect_id,))
                    
                    cursor.connection.commit()
                    st.success("Item moved back to active defects for rework!")
                    st.rerun()
                
            else:  # completed_pending_approval
                st.warning(f"⏳ **PENDING: {room} - {component}** ({trade})")
                st.caption(f"Completed: {completed_at[:10]} | Waiting for approval")
            
            # Show work notes
            if completion_notes:
                with st.expander("Your work notes", expanded=False):
                    st.write(completion_notes)
            
            # Show photos
            cursor.execute('''
                SELECT photo_type, COUNT(*) as count
                FROM defect_photos 
                WHERE defect_id = ?
                GROUP BY photo_type
                ORDER BY photo_type
            ''', (defect_id,))
            
            photo_counts = cursor.fetchall()
            if photo_counts:
                photo_summary = " | ".join([f"{ptype}: {count}" for ptype, count in photo_counts])
                st.caption(f"Photos: {photo_summary}")
        
        st.markdown("")

def show_inline_work_area(cursor, defect_id, defect_data, user):
    """Inline work area for fixing defects"""
    
    room = defect_data[1]
    component = defect_data[2]
    
    with st.container():
        st.markdown("""
        <div style="background-color: #f0f8ff; padding: 1rem; border-radius: 8px; 
                   border-left: 4px solid #1f77b4; margin: 0.5rem 0;">
        """, unsafe_allow_html=True)
        
        st.markdown(f"**Working on: {room} - {component}**")
        
        # Photo upload section
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Before Photo:**")
            before_photo = st.file_uploader(
                "Upload before photo:",
                type=['png', 'jpg', 'jpeg'],
                key=f"before_{defect_id}",
                label_visibility="collapsed"
            )
            
            if before_photo and st.button("Upload Before", key=f"upload_before_{defect_id}"):
                if save_defect_photo_fixed(defect_id, before_photo, 'before', "Before fixing", user['username']):
                    st.success("Before photo uploaded!")
                    st.rerun()
                else:
                    st.error("Failed to upload before photo")
        
        with col2:
            st.markdown("**After Photo:**")
            after_photo = st.file_uploader(
                "Upload after photo:",
                type=['png', 'jpg', 'jpeg'],
                key=f"after_{defect_id}",
                label_visibility="collapsed"
            )
            
            if after_photo and st.button("Upload After", key=f"upload_after_{defect_id}"):
                if save_defect_photo_fixed(defect_id, after_photo, 'after', "After fixing", user['username']):
                    st.success("After photo uploaded!")
                    st.rerun()
                else:
                    st.error("Failed to upload after photo")
        
        # Show uploaded photos
        cursor.execute('''
            SELECT photo_type, description, uploaded_at
            FROM defect_photos 
            WHERE defect_id = ?
            ORDER BY uploaded_at DESC
        ''', (defect_id,))
        
        photos = cursor.fetchall()
        
        if photos:
            st.markdown("**Photos uploaded:**")
            photo_text = []
            for photo in photos:
                photo_text.append(f"{photo[0]} ({photo[2][:10]})")
            st.caption(" | ".join(photo_text))
        
        # Completion section
        st.markdown("**Mark as Fixed:**")
        
        completion_notes = st.text_area(
            "What did you do?",
            placeholder="Describe the work you completed...",
            height=60,
            key=f"notes_{defect_id}"
        )
        
        # Check requirements
        after_photos_exist = any(photo[0] == 'after' for photo in photos)
        has_notes = bool(completion_notes and completion_notes.strip())
        can_complete = after_photos_exist and has_notes
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if not after_photos_exist:
                st.warning("Need after photo to complete")
            elif not has_notes:
                st.warning("Need work description to complete")
            else:
                st.success("Ready to mark as fixed!")
        
        with col2:
            if st.button(
                "Mark as Fixed", 
                key=f"complete_{defect_id}", 
                type="primary",
                disabled=not can_complete,
                use_container_width=True
            ):
                if can_complete:
                    try:
                        cursor.execute('''
                            UPDATE enhanced_defects 
                            SET status = 'completed_pending_approval', 
                                completed_by = ?, 
                                completed_at = CURRENT_TIMESTAMP, 
                                completion_notes = ?
                            WHERE id = ?
                        ''', (user['username'], completion_notes, defect_id))
                        
                        cursor.connection.commit()
                        
                        st.success("Fixed! Check the 'My Completed Work' tab to see status.")
                        
                        # Clear work area
                        if "working_on_defect" in st.session_state:
                            del st.session_state["working_on_defect"]
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error marking as fixed: {str(e)}")
        
        st.markdown("</div>", unsafe_allow_html=True)

def show_building_summary_tables(cursor, building_name, user):
    """Show simple summary tables like admin/inspector, then unit selection"""
    
    st.markdown(f"### Building: {building_name}")
    
    # Get defects for this building
    cursor.execute('''
        SELECT ed.unit_number, ed.room, ed.component, ed.trade, ed.urgency, ed.planned_completion
        FROM enhanced_defects ed
        LEFT JOIN processed_inspections pi ON ed.inspection_id = pi.id
        WHERE COALESCE(pi.building_name, 'Unknown Building') = ?
        AND ed.status IN ('open', 'assigned', 'in_progress')
        AND pi.is_active = 1
        ORDER BY 
            CASE ed.urgency 
                WHEN 'Urgent' THEN 1 
                WHEN 'High Priority' THEN 2 
                ELSE 3 
            END,
            ed.unit_number
    ''', (building_name,))
    
    building_defects = cursor.fetchall()
    
    if not building_defects:
        st.success("No active defects in this building!")
        return
    
    # Convert to DataFrame for summary tables
    building_df = pd.DataFrame(building_defects, columns=[
        "Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"
    ])
    
    # Quick metrics
    total_defects = len(building_df)
    urgent_count = len(building_df[building_df["Urgency"] == "Urgent"])
    high_priority_count = len(building_df[building_df["Urgency"] == "High Priority"])
    normal_count = total_defects - urgent_count - high_priority_count
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Defects", total_defects)
    with col2:
        if urgent_count > 0:
            st.error(f"Urgent: {urgent_count}")
        else:
            st.success("Urgent: 0")
    with col3:
        if high_priority_count > 0:
            st.warning(f"High Priority: {high_priority_count}")
        else:
            st.info("High Priority: 0")
    with col4:
        st.info(f"Normal: {normal_count}")
    
    # Summary tables (same as admin/inspector interface)
    tab1, tab2, tab3 = st.tabs(["Unit Summary", "Trade Summary", "Urgent Items"])
    
    with tab1:
        st.markdown("**Units ranked by defect count:**")
        unit_summary = building_df.groupby("Unit").size().reset_index(name="DefectCount")
        unit_summary = unit_summary.sort_values("DefectCount", ascending=False)
        st.dataframe(unit_summary, use_container_width=True)
    
    with tab2:
        st.markdown("**Trades ranked by defect count:**")
        trade_summary = building_df.groupby("Trade").size().reset_index(name="DefectCount")
        trade_summary = trade_summary.sort_values("DefectCount", ascending=False)
        st.dataframe(trade_summary, use_container_width=True)
    
    with tab3:
        urgent_items = building_df[building_df["Urgency"] == "Urgent"]
        if len(urgent_items) > 0:
            st.error(f"**{len(urgent_items)} URGENT defects require immediate attention:**")
            st.dataframe(urgent_items[["Unit", "Room", "Component", "Trade", "PlannedCompletion"]], 
                        use_container_width=True)
        else:
            st.success("No urgent defects!")
    
    # Unit selection with detailed interface (using your existing good code)
    st.markdown("---")
    st.markdown("### Select Unit to Work On")
    
    # Get units with defect counts for better display
    cursor.execute('''
        SELECT ed.unit_number,
               COUNT(*) as total_defects,
               SUM(CASE WHEN ed.urgency = 'Urgent' THEN 1 ELSE 0 END) as urgent_count,
               SUM(CASE WHEN ed.urgency = 'High Priority' THEN 1 ELSE 0 END) as high_priority_count
        FROM enhanced_defects ed
        LEFT JOIN processed_inspections pi ON ed.inspection_id = pi.id
        WHERE COALESCE(pi.building_name, 'Unknown Building') = ?
        AND ed.status IN ('open', 'assigned', 'in_progress')
        AND pi.is_active = 1
        GROUP BY ed.unit_number
        ORDER BY 
            SUM(CASE WHEN ed.urgency = 'Urgent' THEN 1 ELSE 0 END) DESC,
            ed.unit_number
    ''', (building_name,))
    
    units_data = cursor.fetchall()
    
    if not units_data:
        st.success("No units with defects in this building!")
        return
    
    # Unit selection options with defect info
    unit_options = []
    unit_lookup = {}
    
    for unit_data in units_data:
        unit_number = unit_data[0]
        total_defects = unit_data[1]
        urgent_count = unit_data[2]
        high_priority_count = unit_data[3]
        
        icon = "🚨" if urgent_count > 0 else "⚠️" if high_priority_count > 0 else "🔧"
        display_name = f"{icon} Unit {unit_number} ({total_defects} defects)"
        
        unit_options.append(display_name)
        unit_lookup[display_name] = {
            'unit_number': unit_number,
            'building_name': building_name,
            'total_defects': total_defects,
            'urgent_count': urgent_count,
            'high_priority_count': high_priority_count
        }
    
    selected_unit_display = st.selectbox(
        "Choose unit to fix:",
        options=[""] + unit_options
    )
    
    if selected_unit_display:
        selected_unit = unit_lookup[selected_unit_display]
        # Use your existing detailed unit interface
        show_unit_defects_with_completed(cursor, selected_unit, user)


def show_simple_builder_building_selection(cursor, user):
    """Simple building selection for builders"""
    
    st.markdown("### Select Building")
    
    # Get buildings with basic stats
    cursor.execute('''
        SELECT COALESCE(pi.building_name, 'Unknown Building') as building_name,
               COUNT(DISTINCT ed.unit_number) as unit_count,
               COUNT(*) as total_defects,
               SUM(CASE WHEN ed.urgency = 'Urgent' THEN 1 ELSE 0 END) as urgent_count
        FROM enhanced_defects ed
        LEFT JOIN processed_inspections pi ON ed.inspection_id = pi.id
        WHERE ed.status IN ('open', 'assigned', 'in_progress')
        AND pi.is_active = 1
        GROUP BY pi.building_name
        ORDER BY SUM(CASE WHEN ed.urgency = 'Urgent' THEN 1 ELSE 0 END) DESC
    ''')
    
    buildings_data = cursor.fetchall()
    
    if not buildings_data:
        st.success("No buildings with active defects! All work completed.")
        return
    
    # Simple building options
    building_options = []
    building_lookup = {}
    
    for building_data in buildings_data:
        building_name = building_data[0]
        unit_count = building_data[1]
        total_defects = building_data[2]
        urgent_count = building_data[3]
        
        icon = "🚨" if urgent_count > 0 else "📋"
        display_name = f"{icon} {building_name} - {unit_count} units ({total_defects} defects)"
        
        building_options.append(display_name)
        building_lookup[display_name] = building_name
    
    selected_building_display = st.selectbox(
        "Choose building:",
        options=building_options
    )
    
    if selected_building_display:
        selected_building_name = building_lookup[selected_building_display]
        show_building_summary_tables(cursor, selected_building_name, user)


# Replace the existing builder interface function
def show_streamlined_builder_interface():
    """Streamlined builder interface: Building → Summary Tables → Unit Selection → Work"""
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 1rem; border-radius: 10px; text-align: center; margin-bottom: 1rem;">
        <h2>Builder Workspace</h2>
        <p>Quick access to your assigned work</p>
    </div>
    """, unsafe_allow_html=True)
    
    user = {
        "username": st.session_state.get("username", ""),
        "name": st.session_state.get("user_name", "Builder"),
        "role": st.session_state.get("user_role", "builder")
    }
    
    try:
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        # Simple flow: Building → Tables → Unit → Work
        show_simple_builder_building_selection(cursor, user)
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading builder interface: {e}")

def show_building_units_inline(cursor, building_name, user):
    """Show units in selected building"""
    
    st.markdown(f"### Units in {building_name}")
    
    # Get units with defects in this building
    cursor.execute('''
        SELECT ed.unit_number,
               COUNT(*) as total_defects,
               SUM(CASE WHEN ed.urgency = 'Urgent' THEN 1 ELSE 0 END) as urgent_count,
               SUM(CASE WHEN ed.urgency = 'High Priority' THEN 1 ELSE 0 END) as high_priority_count
        FROM enhanced_defects ed
        LEFT JOIN processed_inspections pi ON ed.inspection_id = pi.id
        WHERE COALESCE(pi.building_name, 'Unknown Building') = ?
        AND ed.status IN ('open', 'assigned', 'in_progress')
        AND pi.is_active = 1
        GROUP BY ed.unit_number
        ORDER BY 
            SUM(CASE WHEN ed.urgency = 'Urgent' THEN 1 ELSE 0 END) DESC,
            ed.unit_number
    ''', (building_name,))
    
    units_data = cursor.fetchall()
    
    if not units_data:
        st.success(f"No defects in {building_name}! All units complete.")
        return
    
    # Unit selection
    unit_options = []
    unit_lookup = {}
    
    for unit_data in units_data:
        unit_number = unit_data[0]
        total_defects = unit_data[1]
        urgent_count = unit_data[2]
        high_priority_count = unit_data[3]
        
        icon = "🚨" if urgent_count > 0 else "⚠️" if high_priority_count > 0 else "🔧"
        display_name = f"{icon} Unit {unit_number} ({total_defects} defects)"
        
        unit_options.append(display_name)
        unit_lookup[display_name] = {
            'unit_number': unit_number,
            'building_name': building_name,
            'total_defects': total_defects,
            'urgent_count': urgent_count,
            'high_priority_count': high_priority_count
        }
    
    selected_unit_display = st.selectbox(
        "Choose unit to fix:",
        options=[""] + unit_options
    )
    
    if selected_unit_display:
        selected_unit = unit_lookup[selected_unit_display]
        show_unit_defects_with_completed(cursor, selected_unit, user)

def save_defect_photo_fixed(defect_id, photo_file, photo_type, description, username):
    """Fixed photo save function"""
    try:
        from PIL import Image
        import io
        import uuid
        from datetime import datetime
        
        # Process image
        image = Image.open(photo_file)
        if image.width > 1920 or image.height > 1080:
            image.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
        
        img_buffer = io.BytesIO()
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        image.save(img_buffer, format='JPEG', quality=85, optimize=True)
        img_data = img_buffer.getvalue()
        
        # Save to database
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        photo_id = str(uuid.uuid4())
        filename = f"{defect_id}_{photo_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        cursor.execute('''
            INSERT INTO defect_photos 
            (id, defect_id, photo_type, filename, photo_data, uploaded_by, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (photo_id, defect_id, photo_type, filename, img_data, username, description))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        return False

def show_enhanced_project_manager_dashboard():
    """Enhanced Project Manager dashboard with building selection and Unit Lookup"""
    import sqlite3
    import pandas as pd
    from datetime import datetime
    
    st.markdown("### Project Management Dashboard")
    
    # Get buildings with inspection data
    try:
        persistence_manager = DataPersistenceManager()
        conn = sqlite3.connect(persistence_manager.db_path)
        cursor = conn.cursor()
        
        # Check what columns exist in processed_inspections
        cursor.execute("PRAGMA table_info(processed_inspections)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Build query based on available columns
        if 'total_units' in column_names:
            total_units_col = 'pi.total_units'
        else:
            # Count unique units from defects table as fallback
            total_units_col = '''
                (SELECT COUNT(DISTINCT id2.unit_number) 
                 FROM inspection_defects id2 
                 JOIN processed_inspections pi2 ON id2.inspection_id = pi2.id 
                 WHERE pi2.building_name = pi.building_name AND pi2.is_active = 1)
            '''
        
        # Get buildings with inspection data
        query = f'''
            SELECT DISTINCT 
                pi.building_name,
                {total_units_col} as total_units,
                MAX(pi.processed_at) as last_inspection
            FROM processed_inspections pi
            WHERE pi.is_active = 1
            GROUP BY pi.building_name
            ORDER BY pi.building_name
        '''
        
        cursor.execute(query)
        accessible_buildings = cursor.fetchall()
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading building data: {e}")
        accessible_buildings = []
    
    if len(accessible_buildings) == 0:
        st.warning("No buildings with inspection data found.")
        
        # Show current session data as fallback
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
            
            # Unit Lookup for current session building
            if st.session_state.processed_data is not None:
                st.markdown("---")
                st.markdown("#### Unit Lookup")
                
                all_units = sorted(st.session_state.processed_data["Unit"].unique())
                selected_unit = st.selectbox(
                    "Select Unit to View Details:",
                    options=[""] + all_units,
                    key="pm_session_unit_lookup"
                )
                
                if selected_unit:
                    unit_defects = lookup_unit_defects(st.session_state.processed_data, selected_unit)
                    
                    if len(unit_defects) > 0:
                        st.markdown(f"**Unit {selected_unit} Defects:**")
                        
                        # Defect counts by urgency
                        urgent_count = len(unit_defects[unit_defects["Urgency"] == "Urgent"])
                        high_priority_count = len(unit_defects[unit_defects["Urgency"] == "High Priority"])
                        normal_count = len(unit_defects[unit_defects["Urgency"] == "Normal"])
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            if urgent_count > 0:
                                st.error(f"Urgent: {urgent_count}")
                            else:
                                st.success("Urgent: 0")
                        with col2:
                            if high_priority_count > 0:
                                st.warning(f"High Priority: {high_priority_count}")
                            else:
                                st.info("High Priority: 0")
                        with col3:
                            st.info(f"Normal: {normal_count}")
                        with col4:
                            st.metric("Total Defects", len(unit_defects))
                        
                        st.dataframe(unit_defects, use_container_width=True)
                        
                        # Export unit report
                        if st.button("Export Unit Report", use_container_width=True):
                            csv = unit_defects.to_csv(index=False)
                            st.download_button(
                                "Download Unit Report",
                                data=csv,
                                file_name=f"unit_{selected_unit}_defects.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                    else:
                        st.success(f"Unit {selected_unit} has no defects!")
            
            # Simple management actions for current building
            st.markdown("---")
            st.markdown("#### Management Actions")
            
            if st.button("Generate Current Building Report", use_container_width=True):
                try:
                    if st.session_state.processed_data is not None:
                        defects_only = st.session_state.processed_data[
                            st.session_state.processed_data["StatusClass"] == "Not OK"
                        ]
                        csv = defects_only.to_csv(index=False)
                        
                        st.download_button(
                            "Download Building Report",
                            data=csv,
                            file_name=f"building_report_{metrics['building_name'].replace(' ', '_')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    else:
                        st.info("No processed data available")
                except Exception as e:
                    st.error(f"Error generating report: {e}")
        
        return
    
    # Building Selection Interface
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
        
        # Display building context
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Building", selected_building['name'])
        with col2:
            st.metric("Total Units", selected_building['units'])
        with col3:
            last_inspection = selected_building['last_inspection']
            if last_inspection and last_inspection != "No data":
                try:
                    display_date = str(last_inspection)[:10]
                    st.metric("Last Inspection", display_date)
                except:
                    st.metric("Last Inspection", "No data")
            else:
                st.metric("Last Inspection", "None")
        
        # Unit Lookup Section
        st.markdown("---")
        st.markdown("#### Unit Lookup")
        
        try:
            conn = sqlite3.connect(persistence_manager.db_path)
            cursor = conn.cursor()
            
            # Get all units for this building
            cursor.execute('''
                SELECT DISTINCT id.unit_number
                FROM inspection_defects id
                JOIN processed_inspections pi ON id.inspection_id = pi.id
                WHERE pi.building_name = ? AND pi.is_active = 1
                ORDER BY CAST(id.unit_number AS INTEGER)
            ''', (selected_building['name'],))
            
            units_result = cursor.fetchall()
            available_units = [str(unit[0]) for unit in units_result] if units_result else []
            
            if available_units:
                selected_unit = st.selectbox(
                    "Select Unit to View Details:",
                    options=[""] + available_units,
                    key="pm_unit_lookup"
                )
                
                if selected_unit:
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
                    ''', (selected_building['name'], selected_unit))
                    
                    unit_defects = cursor.fetchall()
                    
                    if unit_defects:
                        st.markdown(f"**Unit {selected_unit} Defect Analysis:**")
                        
                        # Show defect counts by urgency
                        urgent_count = len([d for d in unit_defects if d[3] == 'Urgent'])
                        high_priority_count = len([d for d in unit_defects if d[3] == 'High Priority'])
                        normal_count = len(unit_defects) - urgent_count - high_priority_count
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            if urgent_count > 0:
                                st.error(f"Urgent: {urgent_count}")
                            else:
                                st.success("Urgent: 0")
                        with col2:
                            if high_priority_count > 0:
                                st.warning(f"High Priority: {high_priority_count}")
                            else:
                                st.info("High Priority: 0")
                        with col3:
                            st.info(f"Normal: {normal_count}")
                        with col4:
                            st.metric("Total Defects", len(unit_defects))
                        
                        # Display defects table
                        df_defects = pd.DataFrame(unit_defects, columns=[
                            "Room", "Component", "Trade", "Urgency", "Planned Completion", "Status"
                        ])
                        
                        # Format planned completion dates
                        try:
                            df_defects["Planned Completion"] = pd.to_datetime(df_defects["Planned Completion"]).dt.strftime("%Y-%m-%d")
                        except:
                            pass  # Keep original format if conversion fails
                        
                        st.dataframe(df_defects, use_container_width=True)
                        
                        # Unit management actions
                        st.markdown("**Unit Management Actions:**")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button(f"Export Unit {selected_unit} Report", use_container_width=True):
                                csv = df_defects.to_csv(index=False)
                                st.download_button(
                                    "Download Unit Report",
                                    data=csv,
                                    file_name=f"unit_{selected_unit}_defects_{selected_building['name'].replace(' ', '_')}.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )
                        
                        with col2:
                            if urgent_count > 0:
                                if st.button(f"Generate Urgent Work Order", use_container_width=True):
                                    urgent_defects = [d for d in unit_defects if d[3] == 'Urgent']
                                    
                                    work_order = f"""URGENT WORK ORDER
Building: {selected_building['name']}
Unit: {selected_unit}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Project Manager: {st.session_state.get('user_name', 'Project Manager')}

CRITICAL DEFECTS REQUIRING IMMEDIATE ATTENTION:
============================================

"""
                                    for i, defect in enumerate(urgent_defects, 1):
                                        work_order += f"{i}. {defect[0]} - {defect[1]} ({defect[2]})\n"
                                        work_order += f"   Due: {defect[4]}\n"
                                        work_order += f"   Status: {defect[5]}\n\n"
                                    
                                    work_order += f"Total Urgent Items: {urgent_count}\n"
                                    work_order += "Priority: IMMEDIATE ACTION REQUIRED\n"
                                    work_order += "Timeline: 24-48 hours\n"
                                    work_order += "\nEND WORK ORDER"
                                    
                                    st.download_button(
                                        "Download Urgent Work Order",
                                        data=work_order,
                                        file_name=f"urgent_work_order_unit_{selected_unit}_{datetime.now().strftime('%Y%m%d')}.txt",
                                        mime="text/plain",
                                        use_container_width=True
                                    )
                            else:
                                st.success("No urgent work orders needed")
                        
                        # Unit status assessment
                        if urgent_count > 0:
                            st.error(f"Unit {selected_unit} requires immediate attention - {urgent_count} urgent defect(s)")
                        elif high_priority_count > 5:
                            st.warning(f"Unit {selected_unit} has moderate priority work - {high_priority_count} items")
                        elif len(unit_defects) > 10:
                            st.info(f"Unit {selected_unit} has extensive defects - {len(unit_defects)} items total")
                        else:
                            st.success(f"Unit {selected_unit} defects are manageable - standard workflow")
                    
                    else:
                        st.success(f"Unit {selected_unit} has no defects!")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.info("This unit is ready for handover")
                        with col2:
                            if st.button("Generate Completion Certificate"):
                                certificate = f"""UNIT COMPLETION CERTIFICATE
Building: {selected_building['name']}
Unit: {selected_unit}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Project Manager: {st.session_state.get('user_name', 'Project Manager')}

CERTIFICATION:
This unit has been inspected and shows NO outstanding defects.
Unit is READY FOR HANDOVER.

Status: APPROVED
Date: {datetime.now().strftime('%Y-%m-%d')}

END CERTIFICATE"""
                                
                                st.download_button(
                                    "Download Completion Certificate",
                                    data=certificate,
                                    file_name=f"completion_cert_unit_{selected_unit}.txt",
                                    mime="text/plain"
                                )
            
            else:
                st.info("No units with defect data found for this building.")
            
            conn.close()
            
        except Exception as e:
            st.error(f"Error loading unit data: {e}")
        
        # Building Management Overview
        try:
            conn = sqlite3.connect(persistence_manager.db_path)
            cursor = conn.cursor()
            
            # Get building defect summary
            cursor.execute('''
                SELECT COUNT(*) as total_defects
                FROM inspection_defects id
                JOIN processed_inspections pi ON id.inspection_id = pi.id
                WHERE pi.building_name = ? AND pi.is_active = 1
            ''', (selected_building['name'],))
            
            total_defects_result = cursor.fetchone()
            total_defects = total_defects_result[0] if total_defects_result else 0
            
            # Get urgent defects
            cursor.execute('''
                SELECT COUNT(*) as urgent_count
                FROM inspection_defects id
                JOIN processed_inspections pi ON id.inspection_id = pi.id
                WHERE pi.building_name = ? AND pi.is_active = 1 AND id.urgency = 'Urgent'
            ''', (selected_building['name'],))
            
            urgent_result = cursor.fetchone()
            urgent_count = urgent_result[0] if urgent_result else 0
            
            # Get high priority defects
            cursor.execute('''
                SELECT COUNT(*) as high_priority_count
                FROM inspection_defects id
                JOIN processed_inspections pi ON id.inspection_id = pi.id
                WHERE pi.building_name = ? AND pi.is_active = 1 AND id.urgency = 'High Priority'
            ''', (selected_building['name'],))
            
            high_priority_result = cursor.fetchone()
            high_priority_count = high_priority_result[0] if high_priority_result else 0
            
            conn.close()
            
            # Display building management overview
            st.markdown("---")
            st.markdown("#### Building Management Overview")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Defects", total_defects)
            with col2:
                if urgent_count > 0:
                    st.error(f"Urgent: {urgent_count}")
                else:
                    st.success("Urgent: 0")
            with col3:
                if high_priority_count > 0:
                    st.warning(f"High Priority: {high_priority_count}")
                else:
                    st.info("High Priority: 0")
            with col4:
                if selected_building['units'] > 0:
                    completion_rate = max(0, (1 - (total_defects / (selected_building['units'] * 10))) * 100)
                    st.metric("Est. Completion", f"{completion_rate:.1f}%")
                else:
                    st.metric("Est. Completion", "0%")
            
            # Building management actions
            st.markdown("#### Building Management Actions")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Generate Complete Building Report", use_container_width=True):
                    try:
                        conn = sqlite3.connect(persistence_manager.db_path)
                        cursor = conn.cursor()
                        
                        cursor.execute('''
                            SELECT id.unit_number, id.room, id.component, id.trade, 
                                   id.urgency, id.planned_completion, id.status
                            FROM inspection_defects id
                            JOIN processed_inspections pi ON id.inspection_id = pi.id
                            WHERE pi.building_name = ? AND pi.is_active = 1
                            ORDER BY CAST(id.unit_number AS INTEGER), 
                                     CASE id.urgency 
                                         WHEN 'Urgent' THEN 1 
                                         WHEN 'High Priority' THEN 2 
                                         ELSE 3 
                                     END
                        ''', (selected_building['name'],))
                        
                        defect_data = cursor.fetchall()
                        conn.close()
                        
                        if defect_data:
                            df = pd.DataFrame(defect_data, columns=[
                                "Unit", "Room", "Component", "Trade", "Urgency", "Planned Completion", "Status"
                            ])
                            csv = df.to_csv(index=False)
                            
                            st.download_button(
                                "Download Building Report (CSV)",
                                data=csv,
                                file_name=f"building_report_{selected_building['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        else:
                            st.info("No defect data available for this building")
                            
                    except Exception as e:
                        st.error(f"Error generating report: {e}")
            
            with col2:
                if urgent_count > 0:
                    if st.button("Generate Building-Wide Urgent Action Plan", use_container_width=True):
                        try:
                            conn = sqlite3.connect(persistence_manager.db_path)
                            cursor = conn.cursor()
                            
                            cursor.execute('''
                                SELECT id.unit_number, id.room, id.component, id.trade, 
                                       id.planned_completion
                                FROM inspection_defects id
                                JOIN processed_inspections pi ON id.inspection_id = pi.id
                                WHERE pi.building_name = ? AND pi.is_active = 1 AND id.urgency = 'Urgent'
                                ORDER BY CAST(id.unit_number AS INTEGER), id.room
                            ''', (selected_building['name'],))
                            
                            urgent_data = cursor.fetchall()
                            conn.close()
                            
                            if urgent_data:
                                action_plan = f"""BUILDING-WIDE URGENT ACTION PLAN
Building: {selected_building['name']}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Project Manager: {st.session_state.get('user_name', 'Project Manager')}

CRITICAL SITUATION: {urgent_count} URGENT DEFECTS ACROSS BUILDING

IMMEDIATE ACTION REQUIRED:
========================

"""
                                for i, defect in enumerate(urgent_data, 1):
                                    action_plan += f"{i}. Unit {defect[0]} - {defect[1]} - {defect[2]} ({defect[3]})\n"
                                    action_plan += f"   Due: {defect[4]}\n\n"
                                
                                action_plan += f"""
DEPLOYMENT REQUIREMENTS:
• Immediate contractor mobilization required
• {urgent_count} urgent items across {len(set(d[0] for d in urgent_data))} units
• Timeline: 24-48 hours for all urgent items
• Status reporting: Daily updates required

ESCALATION: This situation requires immediate executive attention.

END ACTION PLAN"""
                                
                                st.download_button(
                                    "Download Urgent Action Plan",
                                    data=action_plan,
                                    file_name=f"urgent_action_plan_{selected_building['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt",
                                    mime="text/plain",
                                    use_container_width=True
                                )
                        except Exception as e:
                            st.error(f"Error generating action plan: {e}")
                else:
                    st.success("No urgent action plan needed")
            
            # Building status summary
            st.markdown("#### Building Status Summary")
            
            if urgent_count > 10:
                st.error(f"CRITICAL: {urgent_count} urgent defects - immediate executive escalation required")
            elif urgent_count > 5:
                st.error(f"HIGH PRIORITY: {urgent_count} urgent defects - contractor mobilization needed")
            elif urgent_count > 0:
                st.warning(f"ATTENTION: {urgent_count} urgent defects - monitor closely")
            else:
                st.success("Building urgent status: CLEAR")
            
            if total_defects == 0:
                st.success("Building is DEFECT-FREE and ready for handover!")
            elif completion_rate > 90:
                st.success(f"Building is {completion_rate:.1f}% complete - nearing handover readiness")
            elif completion_rate > 70:
                st.info(f"Building is {completion_rate:.1f}% complete - on track for completion")
            else:
                st.warning(f"Building is {completion_rate:.1f}% complete - requires focused effort")
                
        except Exception as e:
            st.error(f"Error loading building management data: {e}")
    
    else:
        st.info("Please select a building to manage.")

# Helper function to get building summary manually if method doesn't exist
def get_manual_building_summary(building_id: str, db_path: str) -> dict:
    """Manual building summary when DataPersistenceManager method doesn't exist"""
    import sqlite3
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get building info
        cursor.execute('''
            SELECT b.name, b.address, b.total_units
            FROM buildings b
            WHERE b.id = ?
        ''', (building_id,))
        
        building_info = cursor.fetchone()
        if not building_info:
            conn.close()
            return {}
        
        # Get defect counts
        cursor.execute('''
            SELECT COUNT(*) as total_defects
            FROM inspection_defects id
            JOIN processed_inspections pi ON id.inspection_id = pi.id
            WHERE pi.building_id = ? AND pi.is_active = 1
        ''', (building_id,))
        
        defect_result = cursor.fetchone()
        total_defects = defect_result[0] if defect_result else 0
        
        # Get urgent defects
        cursor.execute('''
            SELECT COUNT(*) as urgent_count
            FROM inspection_defects id
            JOIN processed_inspections pi ON id.inspection_id = pi.id
            WHERE pi.building_id = ? AND pi.is_active = 1 AND id.urgency = 'Urgent'
        ''', (building_id,))
        
        urgent_result = cursor.fetchone()
        urgent_count = urgent_result[0] if urgent_result else 0
        
        conn.close()
        
        return {
            'name': building_info[0],
            'address': building_info[1],
            'total_units': building_info[2],
            'total_defects': total_defects,
            'urgent_count': urgent_count
        }
        
    except Exception as e:
        print(f"Error getting manual building summary: {e}")
        return {}

# Support functions you'll need to implement:

def load_building_defects_paginated(building_id, page=1, urgency_filter="All"):
    """Load building defects with pagination"""
    try:
        persistence_manager = DataPersistenceManager()
        conn = sqlite3.connect(persistence_manager.db_path)
        cursor = conn.cursor()
        
        where_clause = "WHERE pi.building_id = ?"
        params = [building_id]
        
        if urgency_filter != "All":
            where_clause += " AND id.urgency = ?"
            params.append(urgency_filter)
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*)
            FROM inspection_defects id
            JOIN processed_inspections pi ON id.inspection_id = pi.id
            {where_clause} AND pi.is_active = 1
        """
        
        cursor.execute(count_query, params)
        total_rows = cursor.fetchone()[0]
        
        # Get paginated data
        page_size = 50
        offset = (page - 1) * page_size
        
        data_query = f"""
            SELECT id.unit_number, id.room, id.component, id.trade, 
                   id.urgency, id.planned_completion, id.status
            FROM inspection_defects id
            JOIN processed_inspections pi ON id.inspection_id = pi.id
            {where_clause} AND pi.is_active = 1
            ORDER BY 
                CASE id.urgency 
                    WHEN 'Urgent' THEN 1 
                    WHEN 'High Priority' THEN 2 
                    ELSE 3 
                END,
                id.unit_number
            LIMIT ? OFFSET ?
        """
        
        params.extend([page_size, offset])
        cursor.execute(data_query, params)
        
        data = cursor.fetchall()
        columns = ["Unit", "Room", "Component", "Trade", "Urgency", "Planned Completion", "Status"]
        
        conn.close()
        
        return {
            'data': pd.DataFrame(data, columns=columns),
            'total_rows': total_rows,
            'total_pages': (total_rows + page_size - 1) // page_size,
            'current_page': page,
            'page_size': page_size
        }
        
    except Exception as e:
        return {'error': str(e)}

def get_building_team_members(building_id):
    """Get team members with access to this building"""
    try:
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT u.full_name, u.role, up.permission_level, u.last_login
            FROM users u
            JOIN user_permissions up ON u.username = up.username
            JOIN buildings b ON (
                (up.resource_type = 'building' AND up.resource_id = b.id) OR
                (up.resource_type = 'project' AND up.resource_id = b.project_id)
            )
            WHERE b.id = ? AND u.is_active = 1
            ORDER BY u.role, u.full_name
        """, (building_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'name': r[0],
                'role': r[1],
                'permission_level': r[2],
                'last_activity': r[3]
            }
            for r in results
        ]
        
    except Exception as e:
        print(f"Error getting team members: {e}")
        return []

# =============================================================================
# EXISTING DATA PROCESSING FUNCTIONS
# =============================================================================
def diagnose_database_content():
    """Diagnostic function to check what's actually in the database"""
    try:
        conn = sqlite3.connect("inspection_system.db")
        cursor = conn.cursor()
        
        print("=== DATABASE DIAGNOSTIC ===")
        
        # Check if inspection_items table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='inspection_items'
        """)
        items_table_exists = cursor.fetchone() is not None
        print(f"inspection_items table exists: {items_table_exists}")
        
        # Check inspection_items count
        if items_table_exists:
            cursor.execute("SELECT COUNT(*) FROM inspection_items")
            items_count = cursor.fetchone()[0]
            print(f"inspection_items records: {items_count}")
            
            if items_count > 0:
                cursor.execute("SELECT status_class, COUNT(*) FROM inspection_items GROUP BY status_class")
                items_by_status = cursor.fetchall()
                print("inspection_items by status:")
                for status, count in items_by_status:
                    print(f"  {status}: {count}")
        
        # Check inspection_defects count
        cursor.execute("SELECT COUNT(*) FROM inspection_defects")
        defects_count = cursor.fetchone()[0]
        print(f"inspection_defects records: {defects_count}")
        
        # Check latest inspection
        cursor.execute("""
            SELECT id, building_name, processed_at 
            FROM processed_inspections 
            WHERE is_active = 1 
            ORDER BY processed_at DESC 
            LIMIT 1
        """)
        latest_inspection = cursor.fetchone()
        if latest_inspection:
            inspection_id, building_name, processed_at = latest_inspection
            print(f"Latest inspection: {building_name} ({inspection_id}) at {processed_at}")
            
            # Check what data exists for this inspection
            if items_table_exists:
                cursor.execute("SELECT COUNT(*) FROM inspection_items WHERE inspection_id = ?", (inspection_id,))
                items_for_inspection = cursor.fetchone()[0]
                print(f"inspection_items for latest: {items_for_inspection}")
            
            cursor.execute("SELECT COUNT(*) FROM inspection_defects WHERE inspection_id = ?", (inspection_id,))
            defects_for_inspection = cursor.fetchone()[0]
            print(f"inspection_defects for latest: {defects_for_inspection}")
        else:
            print("No active inspections found")
        
        conn.close()
        print("=== END DIAGNOSTIC ===")
        
    except Exception as e:
        print(f"Diagnostic error: {e}")
  
def check_database_migration():
    """Check if database migration is needed and guide user"""
    
    try:
        from database_migration_script import check_migration_status, migrate_database
        
        if not check_migration_status():
            st.error("Database Migration Required!")
            st.warning("""
            Your database needs to be updated to store complete inspection data.
            This will fix the Excel report consistency issue.
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Run Migration", type="primary"):
                    with st.spinner("Migrating database..."):
                        success = migrate_database()
                        
                    if success:
                        st.success("Migration completed! Please restart the app.")
                        st.info("After restart, upload a new CSV file to get complete data.")
                    else:
                        st.error("Migration failed. Check console for details.")
            
            with col2:
                if st.button("Skip (Not Recommended)"):
                    st.session_state.skip_migration = True
                    st.warning("Excel reports may be inconsistent until migration is completed.")
            
            if not st.session_state.get('skip_migration', False):
                st.stop()
    
    except ImportError:
        st.sidebar.error("Migration script not found. Please create database_migration_script.py")

# Add this near the beginning of your main app, after imports but before the main interface
if __name__ == "__main__":
    # Check migration status early
    # check_database_migration()

def process_inspection_data(df, mapping, building_info):
    """Process the inspection data with enhanced metrics calculation including urgent defects"""
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

    # Classify status with enhanced urgency detection
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

    def classify_urgency(val, component, room):
        """Classify defects by urgency level"""
        if pd.isna(val):
            return "Normal"
        
        val_str = str(val).strip().lower()
        component_str = str(component).lower()
        room_str = str(room).lower()
        
        # Urgent keywords
        urgent_keywords = ["urgent", "immediate", "safety", "hazard", "dangerous", "critical", "severe"]
        
        # Safety-critical components
        safety_components = ["fire", "smoke", "electrical", "gas", "water", "security", "lock", "door handle"]
        
        # Check for urgent keywords in the value
        if any(keyword in val_str for keyword in urgent_keywords):
            return "Urgent"
        
        # Check for safety-critical components
        if any(safety in component_str for safety in safety_components):
            return "High Priority"
        
        # Entry door issues are high priority
        if "entry" in room_str and "door" in component_str:
            return "High Priority"
            
        return "Normal"

    long_df["StatusClass"] = long_df["Status"].apply(classify_status)
    long_df["Urgency"] = long_df.apply(lambda row: classify_urgency(row["Status"], row["Component"], row["Room"]), axis=1)

    # Merge with trade mapping
    merged = long_df.merge(mapping, on=["Room", "Component"], how="left")
    
    # Fill missing trades with "Unknown Trade"
    merged["Trade"] = merged["Trade"].fillna("Unknown Trade")
    
    # Add planned completion dates
    def assign_planned_completion(urgency):
        base_date = datetime.now()
        if urgency == "Urgent":
            return base_date + timedelta(days=3)
        elif urgency == "High Priority":
            return base_date + timedelta(days=7)
        else:
            return base_date + timedelta(days=14)
    
    merged["PlannedCompletion"] = merged["Urgency"].apply(assign_planned_completion)
    
    final_df = merged[["Unit", "UnitType", "Room", "Component", "StatusClass", "Trade", "Urgency", "PlannedCompletion"]]
    
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
    
    # Extract building information
    sample_audit = df.loc[0, "auditName"] if "auditName" in df.columns and len(df) > 0 else ""
    if sample_audit:
        audit_parts = str(sample_audit).split("/")
        extracted_building_name = audit_parts[2].strip() if len(audit_parts) >= 3 else building_info["name"]
        extracted_inspection_date = audit_parts[0].strip() if len(audit_parts) >= 1 else building_info.get("date", datetime.now().strftime("%Y-%m-%d"))
    else:
        extracted_building_name = building_info["name"]
        extracted_inspection_date = building_info.get("date", datetime.now().strftime("%Y-%m-%d"))
    
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
    
    # Enhanced metrics with urgency tracking
    urgent_defects = defects_only[defects_only["Urgency"] == "Urgent"]
    high_priority_defects = defects_only[defects_only["Urgency"] == "High Priority"]
    
    # Planned work calculations
    next_two_weeks = datetime.now() + timedelta(days=14)
    planned_work_2weeks = defects_only[defects_only["PlannedCompletion"] <= next_two_weeks]
    
    next_month = datetime.now() + timedelta(days=30)
    planned_work_month = defects_only[
        (defects_only["PlannedCompletion"] > next_two_weeks) & 
        (defects_only["PlannedCompletion"] <= next_month)
    ]
    
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
        "urgent_defects": len(urgent_defects),
        "high_priority_defects": len(high_priority_defects),
        "planned_work_2weeks": len(planned_work_2weeks),
        "planned_work_month": len(planned_work_month),
        "summary_trade": defects_only.groupby("Trade").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(defects_only) > 0 else pd.DataFrame(columns=["Trade", "DefectCount"]),
        "summary_unit": defects_only.groupby("Unit").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(defects_only) > 0 else pd.DataFrame(columns=["Unit", "DefectCount"]),
        "summary_room": defects_only.groupby("Room").size().reset_index(name="DefectCount").sort_values("DefectCount", ascending=False) if len(defects_only) > 0 else pd.DataFrame(columns=["Room", "DefectCount"]),
        "urgent_defects_table": urgent_defects[["Unit", "Room", "Component", "Trade", "PlannedCompletion"]].copy() if len(urgent_defects) > 0 else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "PlannedCompletion"]),
        "planned_work_2weeks_table": planned_work_2weeks[["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]].copy() if len(planned_work_2weeks) > 0 else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]),
        "planned_work_month_table": planned_work_month[["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]].copy() if len(planned_work_month) > 0 else pd.DataFrame(columns=["Unit", "Room", "Component", "Trade", "Urgency", "PlannedCompletion"]),
        "component_details_summary": defects_only.groupby(["Trade", "Room", "Component"])["Unit"].apply(lambda s: ", ".join(sorted(s.astype(str).unique()))).reset_index().rename(columns={"Unit": "Units with Defects"}) if len(defects_only) > 0 else pd.DataFrame(columns=["Trade", "Room", "Component", "Units with Defects"])
    }
    
    return final_df, metrics

def lookup_unit_defects(processed_data, unit_number):
    """Lookup defect history for a specific unit"""
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

def create_zip_package(excel_bytes, word_bytes, metrics):
    """Create a ZIP package containing both reports"""
    zip_buffer = BytesIO()
    
    mel_tz = pytz.timezone("Australia/Melbourne")
    timestamp = datetime.now(mel_tz).strftime("%Y%m%d_%H%M%S")
    
    # Generate professional filenames
    from excel_report_generator import generate_filename
    excel_filename = f"{generate_filename(metrics['building_name'], 'Excel')}.xlsx"
    word_filename = f"{generate_filename(metrics['building_name'], 'Word')}.docx" if word_bytes else None
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add Excel file
        zip_file.writestr(excel_filename, excel_bytes)
        
        # Add Word file if available
        if word_bytes and word_filename:
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
- Urgent Defects: {metrics['urgent_defects']}
- Planned Work (Next 2 Weeks): {metrics['planned_work_2weeks']}
- Planned Work (Next Month): {metrics['planned_work_month']}

Files Included:
- {excel_filename}
{'- ' + word_filename if word_bytes else '- Word report (not available)'}
- inspection_summary.txt (this file)
"""
        zip_file.writestr("inspection_summary.txt", summary_content)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# =============================================================================
# STREAMLIT APP CONFIGURATION AND INITIALIZATION
# =============================================================================

# Page configuration
st.set_page_config(
    page_title="Inspection Report Processor",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide Streamlit styling
hide_streamlit_style = """
<style>
/* Only hide what we really need to hide */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Keep sidebar functionality intact */
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

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
    
    .unit-lookup-container {
        background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%);
        border-radius: 10px;
        padding: 1.5rem;
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

# Initialize enhanced authentication
auth_manager = get_auth_manager()

# Check authentication with database
if not auth_manager.is_session_valid():
    show_enhanced_login_page()
    st.stop()

# Initialize session state FIRST (move this section up)
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
if "report_images" not in st.session_state:
    st.session_state.report_images = {
        "logo": None,
        "cover": None,
    }

# Show enhanced user menu (now session state is initialized)
if not show_enhanced_user_menu():
    st.stop()

# Initialize user data (load from database if available)
data_loaded = initialize_user_data()
mapping_loaded = load_trade_mapping()

if data_loaded:
    st.info(f"Loaded inspection data for {st.session_state.metrics['building_name']}")

if mapping_loaded:
    st.info("Trade mapping loaded from database")

# Get current user info
user = auth_manager.get_current_user()

# Replace the admin workspace selection section in your streamlit_app.py with this:

if user['dashboard_type'] == 'admin':
    st.markdown(f"""
    <div class="main-header">
        <h1>Administrator Control Center</h1>
        <p>Complete System Management & Data Processing</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{user['name']}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>System Administrator</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # IMPROVED: Radio buttons instead of selectbox + button
    if 'admin_workspace' not in st.session_state:
        st.session_state.admin_workspace = "Data Processing"
    
    st.markdown("### Choose Your Workspace")
    
    workspace_choice = st.radio(
        "Select your admin interface:",
        ["Data Processing", "System Administration"],
        index=0 if st.session_state.admin_workspace == "Data Processing" else 1,
        horizontal=True,
        help="Data Processing: Upload and process inspection files | System Administration: User and system management"
    )
    
    # Auto-update session state when radio selection changes
    if workspace_choice != st.session_state.admin_workspace:
        st.session_state.admin_workspace = workspace_choice
        st.rerun()
    
    st.markdown("---")
    
    # Handle workspace selection
    if st.session_state.admin_workspace == "System Administration":
        try:
            show_admin_dashboard()
        except Exception as e:
            st.error(f"Admin dashboard error: {str(e)}")
            st.info("Falling back to basic admin interface")
            show_basic_admin_interface()
        
        # Stop here to prevent showing processing interface
        st.stop()
    
    else:  # Data Processing mode
        st.info("Full inspection processing interface with administrator privileges")
        # Continue to processing interface below (don't use st.stop())

elif user['dashboard_type'] == 'portfolio':
    # Property Developer Dashboard with report generation
    st.markdown(f"""
    <div class="main-header">
        <h1>Portfolio Management Dashboard</h1>
        <p>Property Developer Interface</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{user['name']}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>Property Developer</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    show_enhanced_property_developer_dashboard()
    st.stop()

elif user['dashboard_type'] == 'builder':
    show_streamlined_builder_interface()  # <-- NEW FUNCTION CALL
    st.stop()

elif user['dashboard_type'] == 'project':
    # Project Manager Dashboard
    st.markdown(f"""
    <div class="main-header">
        <h1>Project Management Dashboard</h1>
        <p>Project Manager Interface</p>
        <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
            <span>Welcome back, <strong>{user['name']}</strong>!</span>
            <span style="margin-left: 2rem;">Role: <strong>Project Manager</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    show_enhanced_project_manager_dashboard()
    st.stop()

# Add this fallback function somewhere before the main routing (add it after your imports)
def show_basic_admin_interface():
    """Basic admin interface when enhanced version fails"""
    st.markdown("### Basic System Administration")
    
    # Show system stats
    try:
        from data_persistence import DataPersistenceManager
        persistence_manager = DataPersistenceManager()
        integrity_report = persistence_manager.validate_data_integrity()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("System Health", "OK" if integrity_report['healthy'] else "Issues")
        with col2:
            st.metric("Active Users", integrity_report['stats'].get('active_users', 0))
        with col3:
            st.metric("Buildings", integrity_report['stats'].get('total_buildings', 0))
        
        if not integrity_report['healthy']:
            st.error("System Issues Detected:")
            for issue in integrity_report['issues']:
                st.warning(f"• {issue}")
        
        # Basic user management
        st.markdown("### User Management")
        st.info("Basic user management available. Install enhanced_admin_management.py for full features.")
        
    except Exception as e:
        st.error(f"Unable to load admin interface: {str(e)}")
        st.info("Please check that all required modules are available.")

# For Inspectors and Admins - show full processing interface
# (Admins fall through to here and get BOTH admin tools AND full processing)
st.markdown(f"""
<div class="main-header">
    <h1>Inspection Report Processor</h1>
    <p>Professional Data Processing Interface</p>
    <div style="margin-top: 1rem; opacity: 0.9; font-size: 0.9em;">
        <span>Welcome back, <strong>{user['name']}</strong>!</span>
        <span style="margin-left: 2rem;">Role: <strong>{user['role'].replace('_', ' ').title()}</strong></span>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# MAIN APPLICATION INTERFACE (INSPECTORS AND ADMINS)
# =============================================================================

# Sidebar configuration with permission-based content
with st.sidebar:
    st.header("Process Status")
    
    # Show status based on permissions
    if st.session_state.step_completed.get("mapping", False):
        st.success("Step 1: Mapping loaded")
        st.caption(f"{len(st.session_state.trade_mapping)} mapping entries")
    else:
        if auth_manager.can_user_perform_action("can_upload"):
            st.info("Step 1: Load mapping")
        else:
            st.info("Mapping managed by your team")
    
    if st.session_state.step_completed.get("processing", False):
        st.success("Step 2: Data processed")
        if st.session_state.metrics:
            st.caption(f"{st.session_state.metrics['total_units']} units processed")
    else:
        if auth_manager.can_user_perform_action("can_process"):
            st.info("Step 2: Process data")
        else:
            st.info("Data processed by your team")
    
    # Unit Lookup Section
    if st.session_state.processed_data is not None:
        st.markdown("---")
        st.header("Quick Unit Lookup")
        
        # Get all unique units for dropdown
        all_units = sorted(st.session_state.processed_data["Unit"].unique())
        
        # Unit search
        selected_unit = st.selectbox(
            "Select Unit Number:",
            options=[""] + all_units,
            help="Quick lookup of defects for any unit",
            key="main_sidebar_unit_lookup"
        )
        
        if selected_unit:
            unit_defects = lookup_unit_defects(st.session_state.processed_data, selected_unit)
            
            if len(unit_defects) > 0:
                st.markdown(f"**Unit {selected_unit} Defects:**")
                
                # Count by urgency
                urgent_count = len(unit_defects[unit_defects["Urgency"] == "Urgent"])
                high_priority_count = len(unit_defects[unit_defects["Urgency"] == "High Priority"])
                normal_count = len(unit_defects[unit_defects["Urgency"] == "Normal"])
                
                if urgent_count > 0:
                    st.error(f"Urgent: {urgent_count}")
                if high_priority_count > 0:
                    st.warning(f"High Priority: {high_priority_count}")
                if normal_count > 0:
                    st.info(f"Normal: {normal_count}")
                
                # Show defects in compact format
                for _, defect in unit_defects.iterrows():
                    urgency_icon = "🚨" if defect["Urgency"] == "Urgent" else "⚠️" if defect["Urgency"] == "High Priority" else "🔧"
                    st.caption(f"{urgency_icon} {defect['Room']} - {defect['Component']} ({defect['Trade']}) - Due: {defect['PlannedCompletion']}")
            else:
                st.success(f"Unit {selected_unit} has no defects!")
    
    st.markdown("---")


# STEP 1: Load Master Trade Mapping (with permission check)
if auth_manager.can_user_perform_action('can_upload'):
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Step 1: Load Master Trade Mapping</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Upload your trade mapping file or use the default template:**")
        
        # Check if mapping is empty and show warning
        if len(st.session_state.trade_mapping) == 0:
            st.warning("Trade mapping is currently blank. Please load a mapping file or use the default template before uploading your inspection CSV.")
    
    with col2:
        # Download default template
        default_mapping = """Room,Component,Trade
Apartment Entry Door,Door Handle,Doors
Apartment Entry Door,Door Locks and Keys,Doors
Apartment Entry Door,Paint,Painting
Balcony,Balustrade,Carpentry & Joinery
Balcony,Drainage Point,Plumbing
Bathroom,Bathtub (if applicable),Plumbing
Bathroom,Ceiling,Painting
Bathroom,Exhaust Fan,Electrical
Bathroom,Tiles,Flooring - Tiles
Kitchen Area,Cabinets,Carpentry & Joinery
Kitchen Area,Kitchen Sink,Plumbing
Kitchen Area,Stovetop and Oven,Appliances
Bedroom,Carpets,Flooring - Carpets
Bedroom,Windows,Windows
Bedroom,Light Fixtures,Electrical"""
        
        st.download_button(
            "Download Template",
            data=default_mapping,
            file_name="trade_mapping_template.csv",
            mime="text/csv",
            help="Download a comprehensive mapping template"
        )
    
    # Upload mapping file
    mapping_file = st.file_uploader("Choose trade mapping CSV", type=["csv"], key="mapping_upload")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Load Master Mapping", type="secondary"):
            try:
                master_mapping = load_master_trade_mapping()
                st.session_state.trade_mapping = master_mapping
                st.session_state.step_completed["mapping"] = True
                save_trade_mapping_to_database(st.session_state.trade_mapping, user['username'])
                
                # Enhanced success message
                trades = master_mapping['Trade'].nunique()
                rooms = master_mapping['Room'].nunique() 
                st.success(f"Master mapping loaded! {len(master_mapping)} entries covering {trades} trades and {rooms} room types")
                st.rerun()
            except Exception as e:
                st.error(f"Error loading master mapping: {e}")
    
    with col2:
        # Use master mapping for template download
        master_mapping = load_master_trade_mapping()
        template_csv = master_mapping.to_csv(index=False)
        
        st.download_button(
            "Download Master Template",
            data=template_csv,
            file_name="MasterTradeMapping_Complete.csv", 
            mime="text/csv",
            help=f"Download complete mapping template ({len(master_mapping)} entries)"
        )
    
    with col3:
        if st.button("Clear Mapping"):
            st.session_state.trade_mapping = pd.DataFrame(columns=["Room", "Component", "Trade"])
            st.session_state.step_completed["mapping"] = False
            st.rerun()
    
    # Display current mapping
    if len(st.session_state.trade_mapping) > 0:
        st.markdown("**Current Trade Mapping:**")
        st.dataframe(st.session_state.trade_mapping, use_container_width=True, height=200)
    else:
        st.info("No trade mapping loaded. Please load the default template or upload your own mapping file.")

else:
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Trade Mapping Information</div>
    </div>
    """, unsafe_allow_html=True)
    
    if len(st.session_state.trade_mapping) > 0:
        st.info(f"Trade mapping available: {len(st.session_state.trade_mapping)} entries")
        st.dataframe(st.session_state.trade_mapping, use_container_width=True, height=200)
    else:
        st.warning("No trade mapping loaded. Contact your team administrator.")

# STEP 2: Upload and Process Data (with permission check)
if auth_manager.can_user_perform_action('can_upload') and auth_manager.can_user_perform_action('can_process'):
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Step 2: Upload Inspection Data</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Upload inspection data
    uploaded_csv = st.file_uploader("Choose inspection CSV file", type=["csv"], key="inspection_upload")
    
    # Check if mapping is loaded before allowing CSV upload
    if len(st.session_state.trade_mapping) == 0:
        st.warning("Please load your trade mapping first before uploading the inspection CSV file.")
        st.stop()
    
    if uploaded_csv is not None:
        if st.button("Process Inspection Data", type="primary", use_container_width=True):
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
                    
                    # Process and save to database
                    processed_df, metrics, saved = process_inspection_data_with_persistence(
                        df, st.session_state.trade_mapping, building_info, user['username']
                    )
                    
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Error processing data: {e}")
                st.code(traceback.format_exc())

else:
    # Show appropriate message based on permissions
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Inspection Data Status</div>
    </div>
    """, unsafe_allow_html=True)
    
    if not auth_manager.can_user_perform_action('can_upload'):
        st.info("Data upload is managed by your team. Contact an inspector or project manager to upload new inspection data.")
    elif not auth_manager.can_user_perform_action('can_process'):
        st.info("Data processing is managed by your team. Contact a project manager or administrator.")
    
    if st.session_state.processed_data is not None:
        st.success("Inspection data has been processed and is available for viewing.")
    else:
        st.warning("No inspection data available. Contact your team to process inspection data.")

# Continue with results display...
# STEP 3: Show Results and Download Options
if st.session_state.processed_data is not None and st.session_state.metrics is not None:
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Step 3: Analysis Results & Downloads</div>
    </div>
    """, unsafe_allow_html=True)
    
    metrics = st.session_state.metrics
    
    # Building Information Section
    st.markdown("### Building Information (Auto-Detected)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        **Building Name:** {metrics['building_name']}  
        **Inspection Date:** {metrics['inspection_date']}  
        **Total Units:** {metrics['total_units']:,} units
        """)
    
    with col2:
        st.markdown(f"""
        **Address:** {metrics['address']}  
        **Unit Types:** {metrics['unit_types_str']}
        """)
    
    st.markdown("---")
    
    # Key Metrics Dashboard
    st.subheader("Key Metrics Dashboard")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Units", f"{metrics['total_units']:,}", help="Total number of units inspected")
    
    with col2:
        st.metric("Total Defects", f"{metrics['total_defects']:,}", delta=f"{metrics['defect_rate']:.1f}% rate")
    
    with col3:
        st.metric("Ready Units", f"{metrics['ready_units']}", delta=f"{metrics['ready_pct']:.1f}%")
    
    with col4:
        st.metric("Avg Defects/Unit", f"{metrics['avg_defects_per_unit']:.1f}", help="Average number of defects per unit")
    
    with col5:
        completion_efficiency = (metrics['ready_units'] / metrics['total_units'] * 100) if metrics['total_units'] > 0 else 0
        st.metric("Completion Efficiency", f"{completion_efficiency:.1f}%", help="Percentage of units ready for immediate handover")
    
    # Enhanced Unit Lookup in Main Area
    st.markdown("---")
    st.markdown("""
    <div class="unit-lookup-container">
        <h3 style="text-align: center; margin-bottom: 1rem;">Unit Defect Lookup</h3>
        <p style="text-align: center;">Quickly search for any unit's complete defect history</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Get all unique units for search
        all_units = sorted(st.session_state.processed_data["Unit"].unique())
        
        # Enhanced unit search with autocomplete
        search_unit = st.selectbox(
            "Enter or Select Unit Number:",
            options=[""] + all_units,
            help="Type to search or select from dropdown",
            key="main_unit_search"
        )
        
        if search_unit:
            unit_defects = lookup_unit_defects(st.session_state.processed_data, search_unit)
            
            if len(unit_defects) > 0:
                st.markdown(f"### Unit {search_unit} - Complete Defect Report")
                
                # Summary metrics for this unit
                col1, col2, col3, col4 = st.columns(4)
                
                urgent_count = len(unit_defects[unit_defects["Urgency"] == "Urgent"])
                high_priority_count = len(unit_defects[unit_defects["Urgency"] == "High Priority"])
                normal_count = len(unit_defects[unit_defects["Urgency"] == "Normal"])
                total_defects = len(unit_defects)
                
                with col1:
                    st.metric("Urgent", urgent_count)
                with col2:
                    st.metric("High Priority", high_priority_count)
                with col3:
                    st.metric("Normal", normal_count)
                with col4:
                    st.metric("Total Defects", total_defects)
                
                # Detailed defect table
                st.markdown("**Detailed Defect List:**")
                
                # Format the data for display
                display_data = unit_defects.copy()
                display_data["Urgency"] = display_data["Urgency"].apply(
                    lambda x: f"🚨 {x}" if x == "Urgent" 
                    else f"⚠️ {x}" if x == "High Priority" 
                    else f"🔧 {x}"
                )
                
                st.dataframe(display_data, use_container_width=True)
                
                # Unit status summary
                if urgent_count > 0:
                    st.error(f"**HIGH ATTENTION REQUIRED** - {urgent_count} urgent defect(s) need immediate attention!")
                elif high_priority_count > 0:
                    st.warning(f"**PRIORITY WORK** - {high_priority_count} high priority defect(s) to address")
                elif normal_count > 0:
                    st.info(f"**STANDARD WORK** - {normal_count} normal defect(s) to complete")
                
            else:
                st.success(f"**Unit {search_unit} is DEFECT-FREE!**")
                st.balloons()
    
    # Summary Tables Section
    st.markdown("---")
    st.subheader("Summary Tables")
    
    # Create tabs for different summary views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Trade Summary", 
        "Unit Summary", 
        "Room Summary", 
        "Urgent Defects", 
        "Planned Work"
    ])
    
    with tab1:
        st.markdown("**Trade-wise defect breakdown - Shows which trades have the most issues**")
        if len(metrics['summary_trade']) > 0:
            st.dataframe(metrics['summary_trade'], use_container_width=True)
        else:
            st.info("No trade defects found")
    
    with tab2:
        st.markdown("**Unit-wise defect breakdown - Shows which units need the most attention**")
        if len(metrics['summary_unit']) > 0:
            st.dataframe(metrics['summary_unit'], use_container_width=True)
        else:
            st.info("No unit defects found")
    
    with tab3:
        st.markdown("**Room-wise defect breakdown - Shows which room types have the most issues**")
        if len(metrics['summary_room']) > 0:
            st.dataframe(metrics['summary_room'], use_container_width=True)
        else:
            st.info("No room defects found")
    
    with tab4:
        st.markdown("**URGENT DEFECTS - These require immediate attention!**")
        if len(metrics['urgent_defects_table']) > 0:
            urgent_display = metrics['urgent_defects_table'].copy()
            urgent_display["PlannedCompletion"] = pd.to_datetime(urgent_display["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
            st.dataframe(urgent_display, use_container_width=True)
            st.error(f"**{len(urgent_display)} URGENT defects require immediate attention!**")
        else:
            st.success("No urgent defects found!")
    
    with tab5:
        st.markdown("**Planned Defect Work Schedule**")
        
        # Sub-tabs for different time periods
        subtab1, subtab2 = st.tabs(["Next 2 Weeks", "Next Month"])
        
        with subtab1:
            st.markdown(f"**Work planned for completion in the next 2 weeks ({metrics['planned_work_2weeks']} items)**")
            st.info("Shows defects due within the next 14 days")
            if len(metrics['planned_work_2weeks_table']) > 0:
                planned_2weeks = metrics['planned_work_2weeks_table'].copy()
                planned_2weeks["PlannedCompletion"] = pd.to_datetime(planned_2weeks["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
                st.dataframe(planned_2weeks, use_container_width=True)
            else:
                st.success("No work planned for the next 2 weeks")
        
        with subtab2:
            st.markdown(f"**Work planned for completion between 2 weeks and 1 month ({metrics['planned_work_month']} items)**")
            st.info("Shows defects due between days 15-30 from today")
            if len(metrics['planned_work_month_table']) > 0:
                planned_month = metrics['planned_work_month_table'].copy()
                planned_month["PlannedCompletion"] = pd.to_datetime(planned_month["PlannedCompletion"]).dt.strftime("%Y-%m-%d")
                st.dataframe(planned_month, use_container_width=True)
            else:
                st.success("No work planned for this period")
    
    # STEP 4: Reports (UNIFIED)
if st.session_state.processed_data is not None and st.session_state.metrics is not None:
    st.markdown("""
    <div class="step-container">
        <div class="step-header">Step 4: Generate & Download Reports</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Check user permissions for reports
    if auth_manager.can_user_perform_action("can_generate_reports") or auth_manager.can_user_perform_action("can_upload"):
        
        user_role = user['role']
        
        if user_role in ['admin', 'inspector', 'project_manager']:
            # Full report suite
            st.subheader("Complete Report Package")
            
            col1, col2 = st.columns(2)
            
            # Complete Package
            with col1:
                st.markdown("### Complete Package")
                st.write("Excel + Word reports in a single ZIP file")
                if st.button("Generate Complete Package", type="primary", use_container_width=True):
                    try:
                        with st.spinner("Generating complete report package..."):
                            # Excel generation
                            if EXCEL_REPORT_AVAILABLE:
                                excel_buffer = generate_professional_excel_report(st.session_state.processed_data, metrics)
                                excel_bytes = excel_buffer.getvalue()
                            else:
                                st.error("Excel generator not available")
                                st.stop()
                            
                            # Word generation
                            word_bytes = None
                            if WORD_REPORT_AVAILABLE:
                                try:
                                    doc = generate_professional_word_report(
                                        st.session_state.processed_data, 
                                        metrics, 
                                        st.session_state.report_images
                                    )
                                    buf = BytesIO()
                                    doc.save(buf)
                                    buf.seek(0)
                                    word_bytes = buf.getvalue()
                                except Exception as e:
                                    st.warning(f"Word report generation failed: {e}")
                            
                            # ZIP package
                            zip_bytes = create_zip_package(excel_bytes, word_bytes, metrics)
                            zip_filename = f"{generate_filename(metrics['building_name'], 'Package')}.zip"
                            
                            st.success("Complete package generated!")
                            st.download_button(
                                "Download Complete Package",
                                data=zip_bytes,
                                file_name=zip_filename,
                                mime="application/zip",
                                use_container_width=True
                            )
                    except Exception as e:
                        st.error(f"Error generating package: {e}")
            
            # Individual Reports
            with col2:
                st.markdown("### Individual Reports")
                
                # Excel Report
                if st.button("Generate Excel Report", type="secondary", use_container_width=True):
                    try:
                        with st.spinner("Generating Excel report..."):
                            if EXCEL_REPORT_AVAILABLE:
                                excel_bytes = generate_professional_excel_report(st.session_state.processed_data, metrics)
                                filename = f"{generate_filename(metrics['building_name'], 'Excel')}.xlsx"
                                
                                st.success("Excel report generated!")
                                st.download_button(
                                    "Download Excel Report",
                                    data=excel_bytes,
                                    file_name=filename,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
                                )
                            else:
                                st.error("Excel generator not available")
                    except Exception as e:
                        st.error(f"Error generating Excel: {e}")
                
                # Word Report
                if WORD_REPORT_AVAILABLE:
                    if st.button("Generate Word Report", type="secondary", use_container_width=True):
                        try:
                            with st.spinner("Generating Word report..."):
                                doc = generate_professional_word_report(
                                    st.session_state.processed_data, 
                                    metrics, 
                                    st.session_state.report_images
                                )
                                buf = BytesIO()
                                doc.save(buf)
                                buf.seek(0)
                                word_bytes = buf.getvalue()
                                filename = f"{generate_filename(metrics['building_name'], 'Word')}.docx"
                                
                                st.success("Word report generated!")
                                st.download_button(
                                    "Download Word Report",
                                    data=word_bytes,
                                    file_name=filename,
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    use_container_width=True
                                )
                        except Exception as e:
                            st.error(f"Error generating Word: {e}")
                else:
                    st.warning("Word generator not available")
        
        elif user_role == 'property_developer':
            # Executive reports only
            st.subheader("Executive Reports")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Executive Summary", type="primary", use_container_width=True):
                    try:
                        if EXCEL_REPORT_AVAILABLE:
                            excel_buffer = generate_professional_excel_report(st.session_state.processed_data, metrics)
                            filename = f"Executive_Summary_{metrics['building_name']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                            
                            st.success("Executive summary generated!")
                            st.download_button(
                                "Download Executive Summary",
                                data=excel_buffer.getvalue(),
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        else:
                            st.error("Excel report generator not available")
                    except Exception as e:
                        st.error(f"Error generating executive summary: {e}")
            
            with col2:
                if st.button("Settlement Readiness Report", type="secondary", use_container_width=True):
                    # Generate CSV with settlement readiness data
                    settlement_data = st.session_state.processed_data[
                        st.session_state.processed_data["StatusClass"] == "Not OK"
                    ].copy()
                    csv = settlement_data.to_csv(index=False)
                    
                    st.download_button(
                        "Download Settlement Report",
                        data=csv,
                        file_name=f"settlement_readiness_{metrics['building_name']}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
        
        elif user_role == 'builder':
            # Work-focused reports
            st.subheader("Work Reports")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Today's Work List", type="primary", use_container_width=True):
                    today_work = st.session_state.processed_data[
                        st.session_state.processed_data["StatusClass"] == "Not OK"
                    ].copy()
                    csv = today_work.to_csv(index=False)
                    
                    st.download_button(
                        "Download Work List",
                        data=csv,
                        file_name=f"work_list_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            
            with col2:
                if st.button("Priority Items", type="secondary", use_container_width=True):
                    priority_work = st.session_state.processed_data[
                        (st.session_state.processed_data["StatusClass"] == "Not OK") &
                        (st.session_state.processed_data["Urgency"].isin(["Urgent", "High Priority"]))
                    ].copy()
                    csv = priority_work.to_csv(index=False)
                    
                    st.download_button(
                        "Download Priority Items",
                        data=csv,
                        file_name=f"priority_items_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            
            with col3:
                if st.button("Weekly Schedule", type="secondary", use_container_width=True):
                    week_work = st.session_state.processed_data[
                        st.session_state.processed_data["StatusClass"] == "Not OK"
                    ].copy()
                    csv = week_work.to_csv(index=False)
                    
                    st.download_button(
                        "Download Weekly Schedule",
                        data=csv,
                        file_name=f"weekly_schedule_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
    
    else:
        st.info("Report generation not available for your role. Contact your team administrator.")    

else:
    # Show upload section with enhanced UI (only for users with upload permissions)
    if auth_manager.can_user_perform_action("can_upload"):
        st.markdown("""
        <div class="step-container">
            <div class="step-header">Ready to Process Your Data</div>
        </div>
        """, unsafe_allow_html=True)
        
        if uploaded_csv is not None:
            try:
                preview_df = pd.read_csv(uploaded_csv)
                
                # Enhanced success message with file info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.success(f"Rows: {len(preview_df):,}")
                with col2:
                    st.success(f"Columns: {len(preview_df.columns)}")
                with col3:
                    file_size = uploaded_csv.size / 1024  # Convert to KB
                    st.success(f"Size: {file_size:.1f} KB")
                
                # Enhanced preview with column analysis
                with st.expander("Data Preview & Analysis", expanded=True):
                    # Show column information
                    st.markdown("**Column Information:**")
                    col_info = pd.DataFrame({
                        'Column': preview_df.columns,
                        'Type': [str(dtype) for dtype in preview_df.dtypes],
                        'Non-Null': [preview_df[col].notna().sum() for col in preview_df.columns],
                        'Null %': [f"{(preview_df[col].isna().sum() / len(preview_df) * 100):.1f}%" for col in preview_df.columns]
                    })
                    st.dataframe(col_info, use_container_width=True, height=200)
                    
                    st.markdown("**Data Sample:**")
                    st.dataframe(preview_df.head(10), use_container_width=True)
                    st.caption(f"Showing first 10 rows of {len(preview_df):,} total rows")
                    
                    # Data quality indicators
                    missing_data_pct = (preview_df.isna().sum().sum() / (len(preview_df) * len(preview_df.columns))) * 100
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if missing_data_pct < 5:
                            st.success(f"Data Quality: Excellent ({missing_data_pct:.1f}% missing)")
                        elif missing_data_pct < 15:
                            st.warning(f"Data Quality: Good ({missing_data_pct:.1f}% missing)")
                        else:
                            st.error(f"Data Quality: Poor ({missing_data_pct:.1f}% missing)")
                    
                    with col2:
                        duplicate_rows = preview_df.duplicated().sum()
                        if duplicate_rows == 0:
                            st.success("No Duplicates")
                        else:
                            st.warning(f"{duplicate_rows} Duplicates")
                    
                    with col3:
                        required_cols = ['Unit', 'Room', 'Component', 'StatusClass']
                        missing_cols = [col for col in required_cols if col not in preview_df.columns]
                        if not missing_cols:
                            st.success("All Required Columns")
                        else:
                            st.info(f"Will auto-generate: {', '.join(missing_cols)}")
                
            except Exception as e:
                st.error(f"Error reading CSV: {e}")
        else:
            st.markdown("""
            <div style="background-color: #e3f2fd; border: 1px solid #2196f3; border-radius: 5px; padding: 1rem; margin: 1rem 0;">
                <h4>Ready to Upload Your Inspection Data</h4>
                <p>Please upload your iAuditor CSV file to begin processing. The system will:</p>
                <ul>
                    <li>Validate the data quality</li>
                    <li>Apply trade mapping</li>
                    <li>Generate comprehensive analytics</li>
                    <li>Create professional reports</li>
                    <li>Identify urgent defects</li>
                    <li>Track planned work schedules</li>
                    <li>Enable quick unit lookups</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
    else:
        # Show info for non-upload users
        st.markdown("""
        <div class="step-container">
            <div class="step-header">Data Processing Information</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("Data processing is handled by your team. Once inspection data is processed, you'll be able to view all analytics and reports here.")

# Enhanced Footer with database authentication info
# Clean footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; padding: 1.5rem; background: #f8f9fa; border-radius: 8px; margin-top: 2rem;">
    <h4 style="color: #2c3e50; margin-bottom: 1rem;">Professional Inspection Report Processor v4.0</h4>
    <div style="display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 1rem;">
        <span><strong>Excel Reports:</strong> Multi-sheet analysis</span>
        <span><strong>Word Reports:</strong> Executive summaries</span>
        <span><strong>Urgent Tracking:</strong> Priority defects</span>
        <span><strong>Unit Lookup:</strong> Instant search</span>
    </div>
    <p style="color: #666; font-size: 0.9em;">
        Logged in as: <strong>{user['name']}</strong> ({user['role'].replace('_', ' ').title()})
    </p>
</div>
""", unsafe_allow_html=True)